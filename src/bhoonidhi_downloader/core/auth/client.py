"""Bhoonidhi authentication client."""

import json
from typing import ClassVar

import requests

from bhoonidhi_downloader.exceptions import BhoonidhiAuthError
from bhoonidhi_downloader.schemas import SessionSchema

from .utils import load_session_info, save_session_info


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

    def login(self) -> SessionSchema:
        """Authenticate against Bhoonidhi and return the session.

        Raises:
            BhoonidhiAuthError: if the request fails or credentials are rejected.
        """
        payload = {
            "userId": self.cfg.username,
            "password": self.cfg.password,
            "action": "VALIDATE_LOGIN",
            "oldDB": "false",
        }

        response = requests.post(
            self.LOGIN_URL,
            data=json.dumps(payload),
            headers=self.LOGIN_HEADERS,
            timeout=30,
        )
        if response.status_code != 200:
            raise BhoonidhiAuthError(
                f"Login failed. Status code: {response.status_code}"
            )

        results = response.json().get("Results") or []
        if not results or not results[0].get("JWT"):
            message = (
                results[0].get("MSG", "unknown reason") if results else "empty response"
            )
            raise BhoonidhiAuthError(f"Login failed. Reason: {message}")

        result = results[0]

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

        Raises:
            BhoonidhiAuthError: if the token is rejected or the request fails.
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
        return True

    def refresh_session(self, jwt: str) -> str:
        """Renew a JWT against Bhoonidhi's VALIDATE_SESSION endpoint.

        The portal issues a fresh JWT on every VALIDATE_SESSION call (verified:
        it differs from the token sent in), so this doubles as a token refresh
        with no re-entry of credentials needed. Useful when downloads start
        failing due to a stale/rate-limited token — previously the only fix
        was 'bhoonidhi-downloader auth logout' + 'auth login' again.

        Raises:
            BhoonidhiAuthError: if the token is rejected or the response is
                missing a new JWT.
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
