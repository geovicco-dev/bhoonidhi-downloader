"""Archive CLI subcommands."""

import typer

from bhoonidhi_downloader.core.archive.command import (
    run_archive_list,
    write_archive_export,
)
from bhoonidhi_downloader.core.archive.render import (
    render_archive_full,
    render_archive_satellite,
)
from bhoonidhi_downloader.exceptions import BhoonidhiError
from bhoonidhi_downloader.logger import get_console

archive_app = typer.Typer(
    name="archive",
    help=(
        "Browse the satellites and sensors Bhoonidhi currently supports.\n\n"
        "The list is fetched live from the portal and cached locally, "
        "so it's always current — nothing here is hardcoded. No login "
        "required."
    ),
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
    plain: bool = typer.Option(
        False, "--plain", help="Print the whole table at once instead of scrolling"
    ),
) -> None:
    """List every satellite and sensor the portal currently supports.

    Cached locally after the first call; use --refresh to re-fetch.
    Narrow to one satellite with --sat to see every product under each
    sensor plus the exact --sat value that selects it — copy that value
    straight into 'bhd query create --sat ...'.

    Examples:
      bhd archive list                          # every satellite
      bhd archive list --sat ResourceSat-2A     # one satellite's sensors/products
      bhd archive list --refresh                # force a re-fetch from the portal
    """
    interactive = False if plain else None
    try:
        data = run_archive_list(refresh=refresh)
    except BhoonidhiError as e:
        console.print(f"[bold red]Error fetching archive data:[/] {e}")
        raise typer.Exit(code=1) from e

    if sat:
        render_archive_satellite(console, data, sat, interactive)
    else:
        render_archive_full(console, data, interactive)


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
    """Write the archive catalogue to a JSON file.

    Useful for scripting against the full satellite/sensor/product
    list without going through the SDK, or for diffing what's changed
    between two points in time.

    Examples:
      bhd archive export --out archive.json                     # everything
      bhd archive export --out resourcesat.json --sat ResourceSat-2A
      bhd archive export --out fresh.json --refresh              # re-fetch first
    """
    try:
        data = run_archive_list(refresh=refresh)
        write_archive_export(data, out, sat)
    except (BhoonidhiError, OSError) as e:
        console.print(f"[bold red]Error exporting archive data:[/] {e}")
        raise typer.Exit(code=1) from e

    if sat:
        console.print(f"[green]Exported archive data for satellite '{sat}' to {out}[/]")
        render_archive_satellite(console, data, sat, interactive=False)
    else:
        console.print(f"[green]Exported full archive data to {out}[/]")
        render_archive_full(console, data, interactive=False)
