"""Auth CLI subcommands."""

import typer

from bhoonidhi_downloader.core.auth.command import (
    run_login,
    run_logout,
    run_refresh,
    run_status,
    run_whoami,
)
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
    success = run_login(console, username, password, save)
    if not success:
        raise typer.Exit(code=1)


@auth_app.command()
def logout() -> None:
    """Clear the saved session."""
    run_logout(console)


@auth_app.command()
def status() -> None:
    """Show current session status."""
    success = run_status(console)
    if not success:
        raise typer.Exit(code=1)


@auth_app.command()
def whoami() -> None:
    """Print the current username."""
    username = run_whoami(console)
    if not username:
        raise typer.Exit(code=1)


@auth_app.command()
def refresh() -> None:
    """Refresh the authentication token."""
    if not run_refresh(console):
        raise typer.Exit(code=1)
