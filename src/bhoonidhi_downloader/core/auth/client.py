"""Bhoonidhi authentication client."""

from __future__ import annotations

import json
import re
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

# A wrong-but-well-formed OTP comes back as HTTP 417 with a plain-text body
# ("Invalid or expired code. Attempts remaining : 5"), not HTTP 200 + JSON
# MSG the way other rejections do. There's no structured error code to key
# off, so this phrase is what tells "wrong code, worth another guess" apart
# from a harder 417 (stale session, rate limit) that another guess the same
# way won't fix.
_OTP_ATTEMPTS_REMAINING_HINT = "attempts remaining"

# Extracts the N from that same phrase, so retrying is bounded by however
# many attempts the portal itself is still willing to accept for this
# pending_token.
_ATTEMPTS_REMAINING_RE = re.compile(r"attempts remaining\s*:?\s*(\d+)", re.IGNORECASE)

# Backstop only, not the intended limit: bounds retries if a rejection's
# wording can't be parsed for a count (unexpected message shape), so a stuck
# otp_prompt callback can't loop forever. In normal operation the portal's
# own "0 remaining" ends the loop first.
_OTP_PROMPT_SAFETY_CAP = 10


class _OtpRejected(BhoonidhiAuthError):
    """Internal: the portal rejected one OTP guess (wrong or expired code).

    Kept distinct from other ``BhoonidhiAuthError`` cases (a 417 that isn't
    a per-attempt rejection, a missing ``pending_token``) so the retry loop
    in ``_complete_email_otp`` only re-prompts for the kind of rejection the
    portal's own "Attempts remaining" message is about, not a harder failure
    another guess can't fix. Subclasses ``BhoonidhiAuthError`` as a safety
    net in case it ever escapes uncaught — never raised past this module
    today.
    """


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
        non-interactive use, or ``otp_prompt`` to collect it (CLI) — a wrong
        or malformed code from ``otp_prompt`` is retried against the same
        pending OTP challenge, for as many attempts as the portal's own
        rejection message allows. ``otp`` verifies once and raises
        immediately, since a fixed string can't be corrected without
        someone to ask again.

        Raises:
            BhoonidhiAuthError: if the request fails, credentials are
                rejected, or every OTP attempt is rejected.
            BhoonidhiValidationError: if a non-interactive ``otp`` is not
                6 digits.
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
        """Finish login after VALIDATE_LOGIN reports an email OTP was mailed.

        ``otp`` (non-interactive) verifies once and raises on rejection —
        there's no one to ask for a corrected code. ``otp_prompt``
        (interactive) keeps re-prompting against the same ``pending_token``:
        each rejection's message is parsed for the portal's own "Attempts
        remaining : N" count, and prompting stops as soon as that hits 0 —
        not before, and not later than the portal is actually willing to
        accept. ``_OTP_PROMPT_SAFETY_CAP`` only bounds the rare case where
        that count can't be parsed; it isn't the intended limit. Neither
        path re-fetches ``pending_token`` — that would mail a new code and
        abandon the one already sent.

        Raises:
            BhoonidhiAuthError: if the portal returned no pending_token, no
                code is ever given, or every attempt is rejected.
            BhoonidhiValidationError: if a non-interactive ``otp`` is not
                6 digits.
        """
        pending_token = login_result.get("pending_token")
        if not pending_token:
            raise BhoonidhiAuthError(
                "Login OTP was mailed but the portal returned no pending_token."
            )

        if otp is not None:
            try:
                return self._verify_otp(pending_token, otp)
            except _OtpRejected as e:
                raise BhoonidhiAuthError(f"OTP verification failed. Reason: {e}") from e

        if otp_prompt is None:
            raise BhoonidhiAuthError(
                "Login OTP has been mailed to your registered email. "
                "Re-run `bhd auth login` in a terminal and enter the 6-digit "
                "code when prompted, or pass --otp / otp= for a non-interactive "
                "login."
            )

        message = mailed_message
        attempts_made = 0
        for _ in range(_OTP_PROMPT_SAFETY_CAP):
            code = otp_prompt(message)
            if not code:
                raise BhoonidhiAuthError(
                    "No OTP entered. Re-run `bhd auth login` and enter the "
                    "6-digit code when prompted."
                )
            attempts_made += 1
            try:
                return self._verify_otp(pending_token, code)
            except BhoonidhiValidationError as e:
                # Malformed locally, never reached the portal -- doesn't
                # touch its attempt budget, so always worth another try.
                message = str(e)
            except _OtpRejected as e:
                message = str(e)
                remaining = _parse_attempts_remaining(message)
                if remaining is not None and remaining <= 0:
                    break

        plural = "" if attempts_made == 1 else "s"
        raise BhoonidhiAuthError(
            f"OTP verification failed after {attempts_made} attempt{plural}. "
            f"Reason: {message}"
        )

    def _verify_otp(self, pending_token: str, code: str) -> SessionSchema:
        """Submit one OTP guess against ``pending_token``.

        Raises:
            BhoonidhiValidationError: if ``code`` is not 6 digits — checked
                locally, before any request, so a malformed guess doesn't
                spend a network round trip or count against the portal's
                own attempt budget.
            _OtpRejected: if the portal rejects the code as wrong or
                expired — whether via HTTP 200 with a ``MSG`` naming the
                rejection, or HTTP 417 reporting remaining attempts (see
                :meth:`_post_action`). A per-attempt failure the caller may
                retry against the same ``pending_token``.
            BhoonidhiAuthError: on a harder failure (e.g. a 417 that isn't
                a per-attempt rejection) that trying again won't fix.
        """
        code = str(code).strip()
        if not code.isdigit() or len(code) != 6:
            raise BhoonidhiValidationError("OTP must be exactly 6 digits.")

        verify = self._post_action(
            {"selProds": pending_token, "otp": code, "action": "VERIFY_OTP"},
            encode=True,
        )
        jwt = verify.get("JWT")
        if jwt and jwt != "EXCEPTION":
            return self._session_from_result(verify)

        message = str(verify.get("MSG") or "")
        raise _OtpRejected(message or "no JWT in response")

    def _post_action(self, payload: dict, *, encode: bool = False) -> dict:
        """POST one action to the portal's login servlet and return its first result.

        ``encode`` matches the portal's own ``encodeObject`` behaviour
        (percent-encoding every value) — required for ``VERIFY_OTP``, not
        ``VALIDATE_LOGIN``.

        Raises:
            BhoonidhiAuthError: on a status code other than 200 or 417, a
                417 that isn't a retry-worthy OTP rejection, a non-JSON
                body, or an empty ``Results`` list.
            _OtpRejected: on a 417 whose body names remaining OTP attempts
                — the shape a wrong-but-well-formed code comes back as,
                plain text rather than the HTTP 200 + JSON ``MSG`` shape
                other rejections use. Only ``VERIFY_OTP`` is expected to
                417.
        """
        body = _encode_portal_payload(payload) if encode else payload
        response = requests.post(
            self.LOGIN_URL,
            data=json.dumps(body),
            headers=self.LOGIN_HEADERS,
            timeout=30,
        )
        if response.status_code == 417:
            text = (response.text or "").strip() or "HTTP 417"
            if _OTP_ATTEMPTS_REMAINING_HINT in text.lower():
                raise _OtpRejected(text)
            raise BhoonidhiAuthError(f"OTP verification failed. Reason: {text}")
        if response.status_code != 200:
            raise BhoonidhiAuthError(
                f"Login failed. Status code: {response.status_code}"
            )

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


def _parse_attempts_remaining(text: str) -> int | None:
    """Extract N from the portal's "...Attempts remaining : N" wording.

    Returns None when the text doesn't contain a parseable count, so the
    retry loop falls back to ``_OTP_PROMPT_SAFETY_CAP`` instead of trusting
    an unbounded retry on an unrecognized message shape.
    """
    match = _ATTEMPTS_REMAINING_RE.search(text)
    return int(match.group(1)) if match else None
