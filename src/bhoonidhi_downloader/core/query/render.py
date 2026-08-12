"""Rich rendering for query commands."""

from rich.console import Console

from bhoonidhi_downloader.schemas import QuerySchema
from bhoonidhi_downloader.viewer import Column, show_table


def render_query_saved(console: Console, query: QuerySchema) -> None:
    """Render confirmation that a query was saved."""
    console.print(
        f"\n[bold green]Saved as '{query.slug}'[/] \u2014 {query.name}\n"
        f"[dim]{query.description}[/]\n"
        f"[dim]Reference it later with: bhd query show {query.slug}[/]"
    )


def _query_list_columns() -> list[Column]:
    def _sat_sen(q: QuerySchema, _i: int) -> str:
        return f"{q.satellite}/{q.sensor}" if q.sensor else q.satellite

    def _window(q: QuerySchema, _i: int) -> str:
        return (
            f"{q.start_date.strftime('%Y-%m-%d')} \u2192 "
            f"{q.end_date.strftime('%Y-%m-%d')}"
        )

    return [
        Column("Slug", lambda q, _i: q.slug, style="cyan", width=20),
        Column("Name", lambda q, _i: q.name, style="white", width=30),
        Column("Satellite/Sensor", _sat_sen, style="blue", width=20),
        Column("Window", _window, style="magenta", width=23),
        Column(
            "Scenes",
            lambda q, _i: str(len(q.scenes)),
            style="green",
            width=8,
            justify="right",
        ),
        Column(
            "Created",
            lambda q, _i: q.created_at.strftime("%Y-%m-%d %H:%M"),
            style="dim",
            width=16,
        ),
    ]


def render_query_list(
    console: Console, queries: list[QuerySchema], interactive: bool | None = None
) -> None:
    """Render a scrollable table of all saved queries."""
    if not queries:
        console.print("[yellow]No saved queries. Run 'query create' to make one.[/]")
        return

    show_table(console, queries, _query_list_columns(), "Saved Queries", interactive)


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
