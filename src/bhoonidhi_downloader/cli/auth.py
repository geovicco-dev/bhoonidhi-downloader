"""Auth CLI subcommands."""

import typer
from rich.status import Status

from bhoonidhi_downloader.core.auth.command import (
    run_login,
    run_logout,
    run_refresh,
    run_status,
    run_whoami,
)
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
from bhoonidhi_downloader.exceptions import BhoonidhiError
from bhoonidhi_downloader.logger import get_console

auth_app = typer.Typer(
    name="auth",
    help=(
        "Authenticate with the Bhoonidhi portal and manage the saved "
        "session.\n\n"
        "Logging in once is enough for most workflows — query and cart "
        "commands re-authenticate automatically when the session goes "
        "stale, as long as you're within the portal's refresh window."
    ),
    no_args_is_help=True,
    add_completion=False,
)

console = get_console()


@auth_app.command()
def login(
    username: str = typer.Option(None, prompt=True, help="Bhoonidhi username"),
    password: str = typer.Option(
        None, prompt=True, hide_input=True, help="Bhoonidhi password"
    ),
    save: bool = typer.Option(True, "--save/--no-save", help="Persist session to disk"),
) -> None:
    """Log in to Bhoonidhi and save the session to ~/.bhoonidhi/session.

    Prompts for username and password if not given as options. Every
    other command reads this saved session automatically, so you only
    log in once per session lifetime.

    Examples:
      bhd auth login                                  # prompts for both
      bhd auth login --username myuser                # prompts for password only
      bhd auth login --username myuser --password X   # fully non-interactive

    Use --no-save for a one-off session you don't want written to disk.
    """
    try:
        with Status("[bold blue]Authenticating...", console=console):
            session = run_login(username, password, save)
    except BhoonidhiError as e:
        render_login_error(console, str(e))
        raise typer.Exit(code=1) from e
    render_login_success(console, session)


@auth_app.command()
def logout() -> None:
    """Clear the saved session from ~/.bhoonidhi/session.

    The next command that needs authentication will prompt you to log
    in again.

    Example:
      bhd auth logout
    """
    if run_logout():
        render_logout_success(console)
    else:
        render_logout_no_session(console)


@auth_app.command()
def status() -> None:
    """Show the current session and whether its token is still valid.

    Exits with code 1 if there's no saved session, or the token has
    expired past the portal's refresh window — in both cases you need
    'bhd auth login' again.

    Example:
      bhd auth status
    """
    result = run_status()
    if result is None:
        render_status_no_session(console)
        raise typer.Exit(code=1)
    session, is_valid = result
    render_status(console, session, is_valid)
    if not is_valid:
        raise typer.Exit(code=1)


@auth_app.command()
def whoami() -> None:
    """Print the username of the currently logged-in session.

    Exits with code 1 if there's no saved session.

    Example:
      bhd auth whoami
    """
    username = run_whoami()
    if not username:
        raise typer.Exit(code=1)
    console.print(username)


@auth_app.command()
def refresh() -> None:
    """Get a fresh token without re-entering your password.

    Only works while the current token is still within the portal's
    refresh window. Once that window has closed, this fails and you
    need 'bhd auth login' again with your credentials.

    Example:
      bhd auth refresh
    """
    try:
        with Status("[bold blue]Refreshing session...", console=console):
            session = run_refresh()
    except BhoonidhiError as e:
        render_refresh_error(console, str(e))
        raise typer.Exit(code=1) from e
    if session is None:
        render_status_no_session(console)
        raise typer.Exit(code=1)
    render_refresh_success(console)
