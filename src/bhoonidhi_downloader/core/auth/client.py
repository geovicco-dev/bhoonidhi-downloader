"""Bhoonidhi authentication client."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import ClassVar
from urllib.parse import quote

import requests

from bhoonidhi_downloader.exceptions import BhoonidhiAuthError, BhoonidhiValidationError
from bhoonidhi_downloader.schemas import SessionSchema

from .utils import load_session_info, save_session_info

# Portal login.html / LoginVals.js: VALIDATE_LOGIN returns this MSG (and a
# pending_token) instead of a JWT when email OTP is required. The browser then
# calls VERIFY_OTP. The CLI used to treat that MSG as a hard failure.
_OTP_MAILED_PREFIX = "Login OTP has been mailed"


class AuthManager:
    """Manages authentication with Bhoonidhi portal."""

    LOGIN_URL = "https://bhoonidhi.nrsc.gov.in/bhoonidhi/LoginServlet"
    LOGIN_HEADERS: ClassVar[dict[str, str]] = {
        "Host": "bhoonidhi.nrsc.gov.in",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Referer": "https://bhoonidhi.nrsc.gov.in/bhoonidhi/login.html",
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": "https://bhoonidhi.nrsc.gov.in",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
    }

    def __init__(self, cfg: SessionSchema):
        self.cfg = cfg
        self.session: SessionSchema | None = None

    def login(
        self,
        *,
        otp: str | None = None,
        otp_prompt: Callable[[str], str] | None = None,
    ) -> SessionSchema:
        """Authenticate against Bhoonidhi and return the session.

        Some accounts (including most recent portal registrations) require a
        6-digit email OTP after username/password. The portal mails the code
        and returns ``pending_token`` with no JWT. Pass ``otp`` for
        non-interactive use, or ``otp_prompt`` to collect it (CLI).

        Raises:
            BhoonidhiAuthError: if the request fails or credentials are rejected.
            BhoonidhiValidationError: if a provided OTP is not 6 digits.
        """
        result = self._post_action(
            {
                "userId": self.cfg.username,
                "password": self.cfg.password,
                "action": "VALIDATE_LOGIN",
                "oldDB": "false",
            }
        )

        jwt = result.get("JWT")
        if jwt and jwt != "EXCEPTION":
            return self._session_from_result(result)

        message = str(result.get("MSG") or "")
        if message.startswith(_OTP_MAILED_PREFIX):
            return self._complete_email_otp(
                result, otp=otp, otp_prompt=otp_prompt, mailed_message=message
            )

        raise BhoonidhiAuthError(f"Login failed. Reason: {message or 'unknown reason'}")

    def _complete_email_otp(
        self,
        login_result: dict,
        *,
        otp: str | None,
        otp_prompt: Callable[[str], str] | None,
        mailed_message: str,
    ) -> SessionSchema:
        pending_token = login_result.get("pending_token")
        if not pending_token:
            raise BhoonidhiAuthError(
                "Login OTP was mailed but the portal returned no pending_token."
            )

        code = otp
        if not code and otp_prompt is not None:
            code = otp_prompt(mailed_message)
        if not code:
            raise BhoonidhiAuthError(
                "Login OTP has been mailed to your registered email. "
                "Re-run `bhd auth login` in a terminal and enter the 6-digit "
                "code when prompted, or pass --otp / otp= for a non-interactive "
                "login. The previous CLI treated this message as a failure "
                "and never waited for the code."
            )

        code = str(code).strip()
        if not code.isdigit() or len(code) != 6:
            raise BhoonidhiValidationError("OTP must be exactly 6 digits.")

        verify = self._post_action(
            {
                "selProds": pending_token,
                "otp": code,
                "action": "VERIFY_OTP",
            },
            encode=True,
        )
        jwt = verify.get("JWT")
        verify_message = str(verify.get("MSG") or "")
        if jwt and jwt != "EXCEPTION":
            return self._session_from_result(verify)

        raise BhoonidhiAuthError(
            f"OTP verification failed. Reason: {verify_message or 'no JWT in response'}"
        )

    def _post_action(self, payload: dict, *, encode: bool = False) -> dict:
        body = _encode_portal_payload(payload) if encode else payload
        response = requests.post(
            self.LOGIN_URL,
            data=json.dumps(body),
            headers=self.LOGIN_HEADERS,
            timeout=30,
        )
        # VERIFY_OTP returns HTTP 417 with a text body on some failures
        # (invalid session / wait-to-resend). Surface that as auth failure.
        if response.status_code not in (200, 417):
            raise BhoonidhiAuthError(
                f"Login failed. Status code: {response.status_code}"
            )
        if response.status_code == 417:
            text = (response.text or "").strip() or "HTTP 417"
            raise BhoonidhiAuthError(f"OTP verification failed. Reason: {text}")

        try:
            data = response.json()
        except ValueError as exc:
            raise BhoonidhiAuthError("Login failed. Reason: empty response") from exc

        results = data.get("Results") or []
        if not results:
            raise BhoonidhiAuthError("Login failed. Reason: empty response")
        return results[0]

    def _session_from_result(self, result: dict) -> SessionSchema:
        self.session = SessionSchema(
            jwt=result.get("JWT"),
            userId=result.get("USERID"),
            user_email=result.get("USEREMAIL"),
            username=self.cfg.username,
            password=self.cfg.password,
            sid=None,
            scenes=[],
        )
        return self.session

    def validate_session(self, jwt: str) -> bool:
        """Validate a session token against Bhoonidhi.

        A 200 response alone doesn't mean the session is valid — a stale/
        expired token still gets HTTP 200 back, just with an empty JWT and
        placeholder fields (observed live: {"MSG": "NEW", "JWT": "",
        "USERID": "", ...}). The only reliable signal is whether the
        response actually carries a real JWT, same check login() and
        refresh_session() already use.

        Raises:
            BhoonidhiAuthError: if the request itself fails.
        """
        payload = {"action": "VALIDATE_SESSION"}
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "token": jwt,
        }
        response = requests.post(
            self.LOGIN_URL, data=json.dumps(payload), headers=headers, timeout=30
        )
        if response.status_code != 200:
            raise BhoonidhiAuthError(
                f"Session validation failed. Status code: {response.status_code}"
            )

        results = response.json().get("Results") or []
        return bool(results and results[0].get("JWT"))

    def refresh_session(self, jwt: str) -> str:
        """Renew a JWT against Bhoonidhi's VALIDATE_SESSION endpoint.

        Only works on a token that's still within Bhoonidhi's refresh
        window: it succeeds immediately after a fresh login and fails
        once the token has aged (the exact window is undocumented, but a
        ~1-day-old token is already past it). Once that window closes
        the portal returns HTTP 200 with an empty JWT rather than a
        clear expiry signal, so "still refreshable" and "needs a full
        login" can't be distinguished ahead of time — if this raises,
        fall back to 'auth logout' + 'auth login'.

        Raises:
            BhoonidhiAuthError: if the token is rejected or the response
                is missing a new JWT.
        """
        payload = {"action": "VALIDATE_SESSION"}
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "token": jwt,
        }
        response = requests.post(
            self.LOGIN_URL, data=json.dumps(payload), headers=headers, timeout=30
        )
        if response.status_code != 200:
            raise BhoonidhiAuthError(
                f"Session refresh failed. Status code: {response.status_code}"
            )

        results = response.json().get("Results") or []
        new_jwt = results[0].get("JWT") if results else None
        if not new_jwt:
            raise BhoonidhiAuthError("Session refresh failed: no JWT in response.")
        return new_jwt

    def save(self) -> None:
        """Persist current session to disk."""
        if self.session:
            save_session_info(dict(self.session))

    @staticmethod
    def load() -> dict:
        """Load session from disk."""
        return load_session_info()


def _encode_portal_payload(payload: dict) -> dict[str, str]:
    """Match LoginVals.js ``encodeObject`` (encodeURIComponent of every value)."""
    return {key: quote(str(value), safe="") for key, value in payload.items()}
