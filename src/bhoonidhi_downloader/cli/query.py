"""Query CLI subcommands."""

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import typer

from bhoonidhi_downloader.cli._session import ensure_session
from bhoonidhi_downloader.core.download import (
    DownloadOutcome,
    build_preview,
    is_downloadable,
    make_progress,
    render_download_preview,
    render_download_report,
    sha256_of_file,
)
from bhoonidhi_downloader.core.query.client import load_query
from bhoonidhi_downloader.core.query.command import (
    execute_download,
    resolve_scene_selection,
    run_query_create,
    run_query_fork,
    run_query_list,
    run_query_refresh,
    run_query_rename,
    run_query_rm,
    run_query_show,
)
from bhoonidhi_downloader.core.query.render import (
    render_query_deleted,
    render_query_list,
    render_query_not_found,
    render_query_saved,
    render_refresh_result,
)
from bhoonidhi_downloader.core.search.availability import (
    AVAILABILITY_LABEL,
    AVAILABILITY_LABEL_STYLE,
    Availability,
    availability_of,
    parse_availability_filter,
)
from bhoonidhi_downloader.core.search.render import render_search_results
from bhoonidhi_downloader.exceptions import BhoonidhiError, BhoonidhiNotFoundError
from bhoonidhi_downloader.logger import get_console
from bhoonidhi_downloader.schemas.selection import parse_sat_tokens

query_app = typer.Typer(
    name="query",
    help=(
        "Search for scenes and manage the results as saved, named "
        "queries.\n\n"
        "A search is never lost: every 'query create' is saved under a "
        "short slug (like 'velvet-wren') you can revisit, refresh for "
        "new scenes, or download from without re-querying the portal."
    ),
    no_args_is_help=True,
    add_completion=False,
)

console = get_console()


@query_app.command("create")
def create(
    start_date: datetime = typer.Argument(
        ..., formats=["%Y-%m-%d"], help="Start date (YYYY-MM-DD)"
    ),
    end_date: datetime = typer.Argument(
        ..., formats=["%Y-%m-%d"], help="End date (YYYY-MM-DD)"
    ),
    satellite: list[str] = typer.Option(
        None,
        "--sat",
        help="Satellite target as SAT[:SEN[:PROD]]. Repeat for several "
        "missions, e.g. --sat ResourceSat-2A:LISS3 --sat CartoSat-3. "
        "Omit the sensor/product to search everything under it.",
    ),
    sensor: str = typer.Option(
        None,
        "--sen",
        help="Sensor name (legacy; only with a single plain --sat). "
        "Prefer --sat SAT:SENSOR.",
    ),
    minx: float = typer.Option(None, "--minx", help="Minimum longitude (bounding box)"),
    maxx: float = typer.Option(None, "--maxx", help="Maximum longitude (bounding box)"),
    miny: float = typer.Option(None, "--miny", help="Minimum latitude (bounding box)"),
    maxy: float = typer.Option(None, "--maxy", help="Maximum latitude (bounding box)"),
    lat: float = typer.Option(None, "--lat", help="Point latitude (location mode)"),
    lon: float = typer.Option(None, "--lon", help="Point longitude (location mode)"),
    radius_km: float = typer.Option(
        10.0, "--radius", help="Search radius in km around --lat/--lon (1-100)"
    ),
    name: str = typer.Option(None, "--name", help="Override the auto-generated name"),
    description: str = typer.Option(
        None, "--desc", help="Override the auto-generated description"
    ),
    plain: bool = typer.Option(
        False, "--plain", help="Print the whole table at once instead of scrolling"
    ),
    no_save: bool = typer.Option(
        False,
        "--no-save",
        help="Run the search but don't persist it: no query file is written "
        "under ~/.bhoonidhi/queries/ and no slug is generated. For "
        "programmatic/stateless use where you only want the scene list.",
    ),
) -> None:
    """Search for scenes and save the results as a new named query.

    Targets are given with --sat, which is repeatable and accepts
    SAT[:SEN[:PROD]]:

      --sat JPSS1                    every sensor, every product
      --sat JPSS1:VIIRS              every product under that sensor
      --sat JPSS1:VIIRS:Imagery_L1   exactly that one product
      --sat A --sat B                combine several missions in one search

    Quote values containing parentheses so the shell doesn't eat them,
    e.g. --sat "EOS-06:OCM(GAC):L2C-Chlorophyll". An invalid satellite,
    sensor, or product is skipped with a warning rather than failing
    the whole search — see 'bhd archive list --sat X' for valid names
    first.

    Give the area of interest as either a bounding box
    (--minx/--maxx/--miny/--maxy) or a point plus radius
    (--lat/--lon/--radius) — exactly one of the two.

    Examples:
      # Single mission, bounding box
      bhd query create 2026-01-01 2026-01-31 --sat ResourceSat-2A:LISS3 \\
          --minx 91.7 --maxx 92.0 --miny 25.5 --maxy 25.7

      # Multiple missions in one search
      bhd query create 2026-01-01 2026-01-31 \\
          --sat ResourceSat-2A:LISS3 --sat CartoSat-3 \\
          --minx 91.7 --maxx 92.0 --miny 25.5 --maxy 25.7

      # One product within a sensor
      bhd query create 2026-01-01 2026-01-31 \\
          --sat "EOS-06:OCM(GAC):L2C-Chlorophyll" \\
          --minx 74 --maxx 80 --miny 12 --maxy 18

      # Point plus radius instead of a bounding box
      bhd query create 2026-01-01 2026-01-31 --sat Sentinel-2A:MSI \\
          --lat 25.58 --lon 91.89 --radius 15

    The results print as a table and are saved under an auto-generated
    slug — come back to them with 'bhd query show <slug>'.
    """
    interactive = False if plain else None
    try:
        selections = parse_sat_tokens(satellite, legacy_sensor=sensor)
        query = run_query_create(
            start_date=start_date,
            end_date=end_date,
            selections=selections,
            minx=minx,
            maxx=maxx,
            miny=miny,
            maxy=maxy,
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            name=name,
            description=description,
            save=not no_save,
        )
    except BhoonidhiError as e:
        console.print(f"[bold red]Search failed:[/] {e}")
        raise typer.Exit(code=1) from e

    if query is None:
        console.print("No scenes found.")
        raise typer.Exit(code=1)

    render_search_results(
        console,
        query.scenes,
        slug=query.slug or None,
        interactive=interactive,
        header_srt=True,
    )
    if no_save:
        console.print(
            f"\n[dim]Not saved (--no-save) \u2014 "
            f"{len(query.scenes)} scene(s), nothing written to disk.[/]"
        )
    else:
        render_query_saved(console, query)


@query_app.command("list")
def list_cmd(
    plain: bool = typer.Option(
        False, "--plain", help="Print the whole table at once instead of scrolling"
    ),
) -> None:
    """List every saved query: slug, name, missions searched, scene
    count, and window.

    Example:
      bhd query list
    """
    queries = run_query_list()
    render_query_list(console, queries, interactive=False if plain else None)


@query_app.command("show")
def show(
    slug: str = typer.Argument(..., help="Query slug"),
    filter_by: list[str] = typer.Option(
        None,
        "--filter",
        "-f",
        help="Show only scenes in these states: ready, archived, onorder, "
        "priced. Comma-separated (-f ready,archived) or repeat the flag.",
    ),
    plain: bool = typer.Option(
        False, "--plain", help="Print the whole table at once instead of scrolling"
    ),
) -> None:
    """Show a saved query's scenes.

    Examples:
      bhd query show velvet-wren                    # everything
      bhd query show velvet-wren -f ready            # only what's ready to download
      bhd query show velvet-wren -f onorder,priced   # only what needs the portal
    """
    try:
        query = run_query_show(slug)
    except BhoonidhiNotFoundError as e:
        render_query_not_found(console, slug)
        raise typer.Exit(code=1) from e

    try:
        filter_states = parse_availability_filter(filter_by)
    except ValueError as e:
        console.print(f"[bold red]{e}[/]")
        raise typer.Exit(code=1) from e

    console.print(f"\n[bold]{query.name}[/]\n{query.description}\n")
    render_search_results(
        console,
        query.scenes,
        slug=slug,
        interactive=False if plain else None,
        filter_states=filter_states,
    )


@query_app.command("rename")
def rename(
    slug: str = typer.Argument(..., help="Query slug"),
    name: str = typer.Option(None, "--name", help="New name"),
    description: str = typer.Option(None, "--desc", help="New description"),
) -> None:
    """Update a saved query's name and/or description in place.

    Overrides the auto-generated text; the search itself and its
    scenes are unaffected.

    Example:
      bhd query rename velvet-wren --name "Shillong winter" \\
          --desc "For the January flood assessment"
    """
    try:
        run_query_rename(slug, name, description)
    except BhoonidhiNotFoundError as e:
        render_query_not_found(console, slug)
        raise typer.Exit(code=1) from e
    console.print(f"[green]Updated '{slug}'.[/]")


@query_app.command("fork")
def fork(
    slug: str = typer.Argument(..., help="Query slug to fork"),
    name: str = typer.Option(None, "--name", help="Name for the forked query"),
) -> None:
    """Clone a saved query's parameters and scenes under a new slug,
    without re-querying the portal.

    Useful for branching off before an experimental change — rename,
    re-filter, or download differently from the copy while the
    original stays untouched.

    Examples:
      bhd query fork velvet-wren                          # auto-named copy
      bhd query fork velvet-wren --name "Winter subset"    # explicit name
    """
    try:
        forked = run_query_fork(slug, name)
    except BhoonidhiNotFoundError as e:
        render_query_not_found(console, slug)
        raise typer.Exit(code=1) from e
    console.print(f"[green]Forked '{slug}' \u2192 '{forked.slug}'.[/]")


@query_app.command("rm")
def rm(slug: str = typer.Argument(..., help="Query slug")) -> None:
    """Delete a saved query and its cached scenes.

    This does not affect anything already staged in the Bhoonidhi cart
    or already downloaded to disk — only the local query record.

    Example:
      bhd query rm velvet-wren
    """
    try:
        run_query_rm(slug)
    except BhoonidhiNotFoundError as e:
        render_query_not_found(console, slug)
        raise typer.Exit(code=1) from e
    render_query_deleted(console, slug)


@query_app.command("refresh")
def refresh(slug: str = typer.Argument(..., help="Query slug")) -> None:
    """Check for scenes newer than what's already saved, without
    re-running the whole search.

    Looks from just before the query's last known end date through
    now, so late-arriving archive backfill isn't missed. New scenes
    are appended to the existing ones; nothing is re-downloaded or
    removed.

    Example:
      bhd query refresh velvet-wren
    """
    try:
        query, added = run_query_refresh(slug)
    except BhoonidhiNotFoundError as e:
        render_query_not_found(console, slug)
        raise typer.Exit(code=1) from e
    except BhoonidhiError as e:
        console.print(f"[bold red]Refresh failed:[/] {e}")
        raise typer.Exit(code=1) from e

    if added is None:
        console.print(f"[yellow]'{slug}' is already up to date.[/]")
        return
    render_refresh_result(console, slug, added, len(query.scenes))


def _render_selection_summary(scenes: list[dict[str, Any]]) -> None:
    """Break the selection down by availability before downloading."""
    counts: dict[Availability, int] = {}
    for scene in scenes:
        state = availability_of(scene)
        counts[state] = counts.get(state, 0) + 1

    def described(states: list[Availability]) -> str:
        return ", ".join(
            f"[{AVAILABILITY_LABEL_STYLE[s]}]{counts[s]} {AVAILABILITY_LABEL[s]}[/]"
            for s in states
            if counts.get(s)
        )

    attempting = described(
        [Availability.DIRECT_AVAILABLE, Availability.DIRECT_UNAVAILABLE]
    )
    if attempting:
        caveat = (
            " [dim](Archived may 404)[/]"
            if counts.get(Availability.DIRECT_UNAVAILABLE)
            else ""
        )
        console.print(f"Downloading {attempting}{caveat}")

    skipping = described([Availability.ON_ORDER, Availability.PRICED])
    if skipping:
        console.print(
            f"Skipping {skipping} [dim]— request those on the Bhoonidhi portal[/]"
        )


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
    password: str = typer.Option(
        None,
        "--password",
        help="Password to re-authenticate with if the session has expired "
        "(non-interactive use only; omit to be prompted instead).",
    ),
    plain: bool = typer.Option(
        False, "--plain", help="Print the whole table at once instead of scrolling"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be downloaded without downloading anything "
        "or requiring a session",
    ),
) -> None:
    """Download scenes from a saved query.

    Priced scenes are skipped; interrupted downloads restart from scratch.
    Re-authenticates automatically if the session has expired.

    Examples:
      bhd query download velvet-wren -o ./scenes            # download it
      bhd query download velvet-wren -o ./scenes --dry-run   # preview only

    --dry-run prints what would happen — attempted, skipped, or already
    present — without touching the network or needing to be logged in.
    """
    interactive = False if plain else None

    query = load_query(slug)
    if query is None:
        render_query_not_found(console, slug)
        raise typer.Exit(code=1)

    if not query.scenes:
        console.print(f"[yellow]'{slug}' has no scenes to download.[/]")
        raise typer.Exit(code=1)

    scenes = resolve_scene_selection(query.scenes, select)
    if not scenes:
        console.print("[yellow]No scenes matched the given --select values.[/]")
        raise typer.Exit(code=1)

    if dry_run:
        out_dir = Path(out).expanduser().resolve()
        previews = build_preview(scenes, out_dir, force=force)
        render_download_preview(
            console, previews, str(out_dir), interactive=interactive
        )
        return

    jwt = ensure_session(console, password)
    if not jwt:
        raise typer.Exit(code=1)

    eligible = [s for s in scenes if is_downloadable(s)]
    _render_selection_summary(scenes)

    out_dir = Path(out).expanduser().resolve()
    already_here = 0
    elsewhere: list[tuple[dict[str, Any], Path]] = []
    for s in eligible:
        record = s.get("_bhx_download") if not force else None
        if not record or not record.get("path"):
            continue
        recorded_path = Path(record["path"]).expanduser().resolve()
        if recorded_path.parent == out_dir:
            already_here += 1
        elif recorded_path.exists() and record.get("sha256") == sha256_of_file(
            recorded_path
        ):
            elsewhere.append((s, recorded_path))
        # else: recorded elsewhere but the file's missing or corrupted (SHA
        # mismatch) -- treat as not-a-duplicate, download normally instead
        # of warning about a file that's effectively gone.

    if already_here:
        console.print(
            f"[cyan]{already_here} scene(s) already downloaded previously to "
            f"{out_dir} (will skip-fast unless --force).[/]"
        )

    if elsewhere:
        console.print(
            f"\n[yellow]{len(elsewhere)} scene(s) are already downloaded and "
            f"verified elsewhere:[/]"
        )
        for s, path in elsewhere:
            console.print(f"  \u2022 {s.get('ID')} \u2192 {path}")
        console.print(
            f"\nDownloading again to {out_dir} will re-fetch "
            f"{len(elsewhere)} file(s) unnecessarily."
        )
        if not sys.stdin.isatty():
            console.print(
                "[bold red]Refusing to proceed non-interactively.[/] Re-run with "
                "--force to download anyway, or point --out at the existing location."
            )
            raise typer.Exit(code=1)
        proceed = input("Download to the new location anyway? [y/N] ").strip().lower()
        if proceed not in ("y", "yes"):
            console.print("[yellow]Aborted.[/]")
            raise typer.Exit(code=1)

    if not eligible:
        console.print("[yellow]No open-access scenes in the selection.[/]")
        return

    progress = make_progress()
    tasks: dict[str, Any] = {}

    def on_progress(scene_id: str, downloaded: int, total: int | None) -> None:
        if scene_id not in tasks:
            tasks[scene_id] = progress.add_task(
                "download", scene_id=scene_id, total=total or 0
            )
        task_id = tasks[scene_id]
        if total and progress.tasks[task_id].total != total:
            progress.update(task_id, total=total)
        progress.update(task_id, completed=downloaded)

    with progress:
        outcomes: list[DownloadOutcome] = execute_download(
            query,
            eligible,
            jwt,
            out,
            parallel=parallel,
            force=force,
            on_progress=on_progress,
        )

    render_download_report(console, outcomes, interactive=interactive)
