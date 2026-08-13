"""Auth command handlers.

These functions carry the auth logic only: they return plain data or raise
a typed :class:`~bhoonidhi_downloader.exceptions.BhoonidhiError`. All terminal
rendering lives in the CLI layer (``cli/auth.py``), so the same functions can
be called directly from a Python script without a console.
"""

import requests

from bhoonidhi_downloader.core.auth.client import AuthManager
from bhoonidhi_downloader.core.auth.utils import (
    SESSION_FILE,
    clear_session_info,
    load_session_info,
    save_session_info,
)
from bhoonidhi_downloader.exceptions import (
    BhoonidhiAuthError,
    BhoonidhiValidationError,
)
from bhoonidhi_downloader.schemas import SessionSchema


def run_login(username: str, password: str, save: bool = True) -> SessionSchema:
    """Authenticate against Bhoonidhi and optionally save the session.

    Returns the validated session.

    Raises:
        BhoonidhiValidationError: if username or password is empty.
        BhoonidhiAuthError: if the credentials are rejected or the new
            session fails validation.
    """
    if not username or not password:
        raise BhoonidhiValidationError("Username and password cannot be empty.")

    am = AuthManager(cfg=SessionSchema(username=username, password=password))
    session = am.login()
    is_valid = am.validate_session(session.jwt) if session.jwt else False
    if not is_valid:
        raise BhoonidhiAuthError("Session validation failed.")

    if save:
        am.save()

    return session


def run_logout() -> bool:
    """Clear the session file. Returns True if a session was removed."""
    return clear_session_info()


def run_status() -> tuple[SessionSchema, bool] | None:
    """Return the stored session and whether its token still validates.

    Returns None if there is no stored session (or it carries no token).
    A network failure while probing the token counts as invalid rather
    than an error, matching how the CLI has always treated it.
    """
    if not SESSION_FILE.exists():
        return None

    session = SessionSchema(**load_session_info())
    if not session.jwt:
        return None

    try:
        am = AuthManager(cfg=SessionSchema(username=session.username))
        is_valid = am.validate_session(session.jwt)
    except (BhoonidhiAuthError, requests.RequestException):
        is_valid = False

    return session, is_valid


def run_whoami() -> str | None:
    """Return the stored username, or None if not logged in."""
    if not SESSION_FILE.exists():
        return None
    return load_session_info().get("username")


def run_refresh() -> SessionSchema | None:
    """Renew the current session's JWT without re-entering credentials.

    Only works if the current token is still within Bhoonidhi's refresh
    window (confirmed live: works right after login, fails once the
    token's aged past some threshold — exact window unknown). If it
    fails, 'auth logout' + 'auth login' is the only fallback.

    Returns the session with its refreshed token, or None if there is no
    session to refresh.

    Raises:
        BhoonidhiAuthError: if the refresh request is rejected.
    """
    if not SESSION_FILE.exists():
        return None

    session = SessionSchema(**load_session_info())
    if not session.jwt:
        return None

    am = AuthManager(cfg=session)
    session.jwt = am.refresh_session(session.jwt)
    save_session_info(dict(session))
    return session
