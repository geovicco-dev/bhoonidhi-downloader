"""Auth command handlers."""

from rich.console import Console
from rich.status import Status

from bhoonidhi_downloader.core.auth.client import AuthManager
from bhoonidhi_downloader.core.auth.render import (
    render_login_error,
    render_login_success,
    render_logout_no_session,
    render_logout_success,
    render_refresh_error,
    render_refresh_success,
    render_status,
    render_status_no_session,
)
from bhoonidhi_downloader.core.auth.utils import (
    clear_session_info,
    load_session_info,
    save_session_info,
    SESSION_FILE,
)
from bhoonidhi_downloader.schemas import SessionSchema


def run_login(
    console: Console, username: str, password: str, save: bool = True
) -> bool:
    """Authenticate against Bhoonidhi and optionally save session.

    Returns True on success, False on failure.
    """
    if not username or not password:
        render_login_error(console, "Username and password cannot be empty.")
        return False

    try:
        with Status("[bold blue]Authenticating...", console=console):
            am = AuthManager(cfg=SessionSchema(username=username, password=password))
            session = am.login()
            is_valid = am.validate_session(session.jwt) if session.jwt else False

        if not is_valid:
            render_login_error(console, "Session validation failed.")
            return False

        if save:
            am.save()

        render_login_success(console, session)
        return True

    except Exception as e:
        render_login_error(console, str(e))
        return False


def run_logout(console: Console) -> bool:
    """Clear the session file.

    Returns True if session was cleared, False if no session existed.
    """
    if clear_session_info():
        render_logout_success(console)
        return True
    else:
        render_logout_no_session(console)
        return False


def run_status(console: Console) -> bool:
    """Display current session status.

    Returns True if valid session exists, False otherwise.
    """
    if not SESSION_FILE.exists():
        render_status_no_session(console)
        return False

    session_dict = load_session_info()
    session = SessionSchema(**session_dict)

    if not session.jwt:
        render_status_no_session(console)
        return False

    # Validate token
    try:
        am = AuthManager(cfg=SessionSchema(username=session.username))
        is_valid = am.validate_session(session.jwt)
    except Exception:
        is_valid = False

    render_status(console, session, is_valid)
    return is_valid


def run_whoami(console: Console) -> str | None:
    """Return username if logged in, None otherwise."""
    if not SESSION_FILE.exists():
        return None

    session_dict = load_session_info()
    username = session_dict.get("username")

    if username:
        console.print(username)
        return username
    return None


def run_refresh(console: Console) -> bool:
    """Renew the current session's JWT without re-entering credentials.

    Useful when downloads start failing (commonly under rate-limiting) and
    a fresh token resolves it — previously the only fix was logging out
    and back in. Returns True on success, False if there's no session to
    refresh or the refresh fails.
    """
    if not SESSION_FILE.exists():
        render_status_no_session(console)
        return False

    session_dict = load_session_info()
    session = SessionSchema(**session_dict)

    if not session.jwt:
        render_status_no_session(console)
        return False

    try:
        with Status("[bold blue]Refreshing session...", console=console):
            am = AuthManager(cfg=session)
            new_jwt = am.refresh_session(session.jwt)
    except Exception as e:
        render_refresh_error(console, str(e))
        return False

    session.jwt = new_jwt
    save_session_info(dict(session))
    render_refresh_success(console)
    return True
