"""Rich rendering for query commands."""

from rich.console import Console
from rich.table import Table

from bhoonidhi_downloader.schemas import QuerySchema


def render_query_saved(console: Console, query: QuerySchema) -> None:
    """Render confirmation that a query was saved."""
    console.print(
        f"\n[bold green]Saved as '{query.slug}'[/] \u2014 {query.name}\n"
        f"[dim]{query.description}[/]\n"
        f"[dim]Reference it later with: bhoonidhi-downloader query show {query.slug}[/]"
    )


def render_query_list(console: Console, queries: list[QuerySchema]) -> None:
    """Render a table of all saved queries."""
    if not queries:
        console.print("[yellow]No saved queries. Run 'query create' to make one.[/]")
        return

    table = Table(title="Saved Queries")
    table.add_column("Slug", style="cyan")
    table.add_column("Name", style="white", overflow="fold")
    table.add_column("Satellite/Sensor", style="blue")
    table.add_column("Window", style="magenta")
    table.add_column("Scenes", style="green", justify="right")
    table.add_column("Created", style="dim")

    for q in queries:
        sat_sen = f"{q.satellite}/{q.sensor}" if q.sensor else q.satellite
        window = f"{q.start_date.strftime('%Y-%m-%d')} \u2192 {q.end_date.strftime('%Y-%m-%d')}"
        table.add_row(
            q.slug,
            q.name,
            sat_sen,
            window,
            str(len(q.scenes)),
            q.created_at.strftime("%Y-%m-%d %H:%M"),
        )

    console.print(table)


def render_query_not_found(console: Console, slug: str) -> None:
    """Render a not-found error for a query slug."""
    console.print(
        f"[bold red]No saved query named '{slug}'.[/] Run 'query list' to see available queries."
    )


def render_query_deleted(console: Console, slug: str) -> None:
    """Render confirmation that a query was deleted."""
    console.print(f"[green]Deleted '{slug}'.[/]")


def render_refresh_result(console: Console, slug: str, added: int, total: int) -> None:
    """Render the outcome of a refresh operation."""
    if added == 0:
        console.print(
            f"[yellow]'{slug}' refreshed \u2014 no new scenes found.[/] ({total} total)"
        )
    else:
        console.print(
            f"[bold green]'{slug}' refreshed \u2014 +{added} new scene(s)[/] ({total} total)"
        )
