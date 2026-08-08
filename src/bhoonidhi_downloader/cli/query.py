"""Query CLI subcommands."""

from datetime import datetime

import typer

from bhoonidhi_downloader.core.query.command import (
    run_query_create,
    run_query_download,
    run_query_fork,
    run_query_list,
    run_query_refresh,
    run_query_rename,
    run_query_rm,
    run_query_show,
)
from bhoonidhi_downloader.logger import get_console

query_app = typer.Typer(
    name="query",
    help="Search and manage saved queries.",
    no_args_is_help=True,
)

console = get_console()


@query_app.command("create")
def create(
    minx: float = typer.Argument(..., help="Minimum longitude"),
    maxx: float = typer.Argument(..., help="Maximum longitude"),
    miny: float = typer.Argument(..., help="Minimum latitude"),
    maxy: float = typer.Argument(..., help="Maximum latitude"),
    start_date: datetime = typer.Argument(
        ..., formats=["%Y-%m-%d"], help="Start date (YYYY-MM-DD)"
    ),
    end_date: datetime = typer.Argument(
        ..., formats=["%Y-%m-%d"], help="End date (YYYY-MM-DD)"
    ),
    satellite: str = typer.Option(
        None, "--sat", help="Satellite name (Ex: ResourceSat-2)"
    ),
    sensor: str = typer.Option(None, "--sen", help="Sensor name (Ex: LISS3)"),
    name: str = typer.Option(None, "--name", help="Override the auto-generated name"),
    description: str = typer.Option(
        None, "--desc", help="Override the auto-generated description"
    ),
) -> None:
    """Search for scenes and save the results as a new named query."""
    result = run_query_create(
        console,
        minx=minx,
        maxx=maxx,
        miny=miny,
        maxy=maxy,
        start_date=start_date,
        end_date=end_date,
        satellite=satellite,
        sensor=sensor,
        name=name,
        description=description,
    )
    if result is None:
        raise typer.Exit(code=1)


@query_app.command("list")
def list_cmd() -> None:
    """List all saved queries."""
    run_query_list(console)


@query_app.command("show")
def show(slug: str = typer.Argument(..., help="Query slug")) -> None:
    """Show a saved query's scenes."""
    if not run_query_show(console, slug):
        raise typer.Exit(code=1)


@query_app.command("rename")
def rename(
    slug: str = typer.Argument(..., help="Query slug"),
    name: str = typer.Option(None, "--name", help="New name"),
    description: str = typer.Option(None, "--desc", help="New description"),
) -> None:
    """Update a saved query's name/description."""
    if not run_query_rename(console, slug, name, description):
        raise typer.Exit(code=1)


@query_app.command("fork")
def fork(
    slug: str = typer.Argument(..., help="Query slug to fork"),
    name: str = typer.Option(None, "--name", help="Name for the forked query"),
) -> None:
    """Clone a saved query under a new name."""
    if run_query_fork(console, slug, name) is None:
        raise typer.Exit(code=1)


@query_app.command("rm")
def rm(slug: str = typer.Argument(..., help="Query slug")) -> None:
    """Delete a saved query."""
    if not run_query_rm(console, slug):
        raise typer.Exit(code=1)


@query_app.command("refresh")
def refresh(slug: str = typer.Argument(..., help="Query slug")) -> None:
    """Check for new scenes matching this query."""
    if run_query_refresh(console, slug) is None:
        raise typer.Exit(code=1)


@query_app.command("download")
def download(
    slug: str = typer.Argument(..., help="Query slug"),
    out: str = typer.Option(
        ..., "--out", "-o", help="Directory to save downloaded scenes into"
    ),
    select: list[str] = typer.Option(
        None,
        "--select",
        "-s",
        help="Scene(s) to download: 1-based index or scene ID from "
        "'query show'. Comma-separated (-s 1,3,5) or repeat the flag "
        "(-s 1 -s 3). Omit to download the entire query.",
    ),
    parallel: int = typer.Option(
        4, "--parallel", "-p", help="Number of scenes to download concurrently"
    ),
    force: bool = typer.Option(
        False, "--force", help="Re-download scenes even if already present in --out"
    ),
) -> None:
    """Download scenes from a saved query.

    Priced scenes are skipped; interrupted downloads restart from scratch.
    """
    if run_query_download(console, slug, out, select, parallel, force) is None:
        raise typer.Exit(code=1)
