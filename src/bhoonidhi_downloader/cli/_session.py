"""Interactive session resolution for the CLI.

``ensure_session`` bridges the saved-on-disk session and the live portal for
the ``query`` and ``cart`` commands: it validates the stored token and, when
run in a terminal, offers to re-authenticate by prompting for the password.

This lives in the CLI layer on purpose — it prompts and reads stdin, which a
library must never do. The SDK path uses the token the client already holds
and raises instead of prompting.
"""

import getpass
import logging
import sys

from rich.console import Console

from bhoonidhi_downloader.core.auth.client import AuthManager
from bhoonidhi_downloader.core.auth.utils import load_session_info, save_session_info
from bhoonidhi_downloader.schemas import SessionSchema

logger = logging.getLogger(__name__)


def ensure_session(console: Console, password: str | None) -> str | None:
    """Get a working JWT, re-authenticating if the stored one is stale.

    The password is never persisted — it only lives in memory for the
    duration of the call. Two paths, depending on how this is invoked:

    - Interactive terminal: if the session's expired, prompt for the
      password here via ``getpass`` and log in fresh, so no separate
      'auth login' step is needed.
    - Non-interactive (script, cron, CI): no prompting. Callers pass
      ``password`` explicitly to opt into the same re-auth, or handle a
      ``None`` return themselves — blocking on stdin would hang a script
      that isn't expecting to be asked for input.

    Returns a valid JWT, or None if no working session could be obtained.
    """
    session_dict = load_session_info()
    jwt = session_dict.get("jwt")
    username = session_dict.get("username")

    if jwt:
        try:
            if AuthManager(cfg=SessionSchema(username=username)).validate_session(jwt):
                return jwt
        except Exception:
            logger.debug("Stored session failed validation; falling back to re-auth.")

    if password is None:
        if not sys.stdin.isatty():
            console.print(
                "[bold red]Not authenticated.[/] Run 'auth login' first, or "
                "pass password= to re-authenticate automatically when calling "
                "this from a script."
            )
            return None
        if not username:
            console.print("[bold red]Not authenticated.[/] Run 'auth login' first.")
            return None
        console.print(
            f"[yellow]Session expired.[/] Re-enter the password for '{username}' "
            "to continue (nothing is written to disk):"
        )
        password = getpass.getpass("Password: ")

    try:
        am = AuthManager(cfg=SessionSchema(username=username, password=password))
        session = am.login()
    except Exception as e:
        console.print(f"[bold red]Re-authentication failed:[/] {e}")
        return None

    save_session_info(dict(session))
    console.print("[green]✓[/] Re-authenticated.")
    return session.jwt
