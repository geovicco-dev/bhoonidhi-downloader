"""Rich rendering for auth commands."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from bhoonidhi_downloader.schemas import SessionSchema


def render_login_success(console: Console, session: SessionSchema) -> None:
    """Display successful login panel."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()
    table.add_row("Username", session.username or "—")
    table.add_row("Email", session.user_email or "—")
    table.add_row("User ID", session.userId or "—")

    panel = Panel(
        table,
        title="[bold green]✓ Login Successful[/]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(panel)


def render_login_error(console: Console, error: str) -> None:
    """Display login error panel."""
    panel = Panel(
        f"[red]{error}[/]",
        title="[bold red]✗ Login Failed[/]",
        border_style="red",
        padding=(1, 2),
    )
    console.print(panel)


def render_logout_success(console: Console) -> None:
    """Display logout success message."""
    console.print("[green]✓[/] Logged out")


def render_logout_no_session(console: Console) -> None:
    """Display no active session message."""
    console.print("[yellow]No active session[/]")


def render_status(console: Console, session: SessionSchema, is_valid: bool) -> None:
    """Display session status panel."""
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold")
    table.add_column()

    table.add_row("Username", session.username or "—")
    table.add_row("Email", session.user_email or "—")
    table.add_row("User ID", session.userId or "—")

    valid_text = (
        Text("✓ Valid", style="green") if is_valid else Text("✗ Invalid", style="red")
    )
    table.add_row("Token", valid_text)

    has_scenes = len(session.scenes) if session.scenes else 0
    table.add_row("Cached Scenes", str(has_scenes))

    panel = Panel(
        table,
        title="[bold]Session Status[/]",
        border_style="green" if is_valid else "yellow",
        padding=(1, 2),
    )
    console.print(panel)


def render_status_no_session(console: Console) -> None:
    """Display not logged in panel."""
    panel = Panel(
        "[yellow]Run [bold]bhd auth login[/bold] to authenticate[/]",
        title="[bold yellow]Not Logged In[/]",
        border_style="yellow",
        padding=(1, 2),
    )
    console.print(panel)


def render_refresh_success(console: Console) -> None:
    """Display session refresh success message."""
    console.print("[green]✓[/] Session refreshed — new token saved.")


def render_refresh_error(console: Console, error: str) -> None:
    """Display session refresh error panel."""
    panel = Panel(
        f"[red]{error}[/]\n\n"
        "[dim]This usually means the token's past Bhoonidhi's refresh "
        "window. Run [bold]auth logout[/bold] then [bold]auth login[/bold] "
        "to get a fresh session.[/]",
        title="[bold red]✗ Refresh Failed[/]",
        border_style="red",
        padding=(1, 2),
    )
    console.print(panel)
