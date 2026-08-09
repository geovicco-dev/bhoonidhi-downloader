"""Archive CLI subcommands."""

import typer

from bhoonidhi_downloader.core.archive.command import (
    run_archive_export,
    run_archive_list,
)
from bhoonidhi_downloader.logger import get_console

archive_app = typer.Typer(
    name="archive",
    help="Browse available satellites and sensors.",
    no_args_is_help=True,
    add_completion=False,
)

console = get_console()


@archive_app.command("list")
def list_archive(
    sat: str = typer.Option(
        None,
        "--sat",
        "-s",
        help="Filter by satellite name.",
    ),
    refresh: bool = typer.Option(
        False,
        "--refresh",
        help="Re-fetch archive data from the portal.",
    ),
) -> None:
    """List satellites and sensors from the archive."""
    success = run_archive_list(console, sat, refresh)
    if not success:
        raise typer.Exit(code=1)


@archive_app.command("export")
def export_archive(
    out: str = typer.Option(..., "--out", "-o", help="Output file path."),
    sat: str = typer.Option(None, "--sat", "-s", help="Filter by satellite name."),
    refresh: bool = typer.Option(
        False,
        "--refresh",
        help="Re-fetch archive data from the portal.",
    ),
) -> None:
    """Export archive data to a JSON file."""
    success = run_archive_export(console, out, sat, refresh)
    if not success:
        raise typer.Exit(code=1)
