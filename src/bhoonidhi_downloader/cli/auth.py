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
    help="Authenticate with Bhoonidhi Portal.",
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
    """Authenticate and save session to ~/.bhoonidhi/session."""
    try:
        with Status("[bold blue]Authenticating...", console=console):
            session = run_login(username, password, save)
    except BhoonidhiError as e:
        render_login_error(console, str(e))
        raise typer.Exit(code=1) from e
    render_login_success(console, session)


@auth_app.command()
def logout() -> None:
    """Clear the saved session."""
    if run_logout():
        render_logout_success(console)
    else:
        render_logout_no_session(console)


@auth_app.command()
def status() -> None:
    """Show current session status."""
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
    """Print the current username."""
    username = run_whoami()
    if not username:
        raise typer.Exit(code=1)
    console.print(username)


@auth_app.command()
def refresh() -> None:
    """Refresh the authentication token."""
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
