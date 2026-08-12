"""Query command handlers: create, list, show, rename, fork, export, refresh, rm, download."""

import getpass
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from rich.console import Console

from bhoonidhi_downloader.core.archive import ArchiveManager
from bhoonidhi_downloader.core.auth.client import AuthManager
from bhoonidhi_downloader.core.auth.utils import load_session_info, save_session_info
from bhoonidhi_downloader.core.download import (
    DownloadManager,
    DownloadOutcome,
    is_downloadable,
    make_progress,
    render_download_report,
    sha256_of_file,
)
from bhoonidhi_downloader.core.search.availability import (
    AVAILABILITY_LABEL,
    AVAILABILITY_LABEL_STYLE,
    Availability,
    availability_of,
)
from bhoonidhi_downloader.core.search.client import SearchManager
from bhoonidhi_downloader.schemas import (
    AOISchema,
    QuerySchema,
    SearchSchema,
    SessionSchema,
)

from .client import (
    delete_query,
    generate_description,
    generate_name,
    generate_slug,
    list_queries,
    load_query,
    save_query,
)
from .render import (
    render_query_deleted,
    render_query_list,
    render_query_not_found,
    render_query_saved,
    render_refresh_result,
)

logger = logging.getLogger(__name__)

REFRESH_LOOKBACK_DAYS = 3


def run_query_create(
    console: Console,
    minx: float,
    maxx: float,
    miny: float,
    maxy: float,
    start_date: datetime,
    end_date: datetime,
    satellite: str,
    sensor: str | None = None,
    name: str | None = None,
    description: str | None = None,
    interactive: bool | None = None,
) -> QuerySchema | None:
    """Run a search and save the result as a new named query.

    Returns the saved QuerySchema on success, None on failure.
    """
    from bhoonidhi_downloader.core.search.render import render_search_results

    aoi = AOISchema(name="aoi", max_lat=maxy, min_lat=miny, max_lon=maxx, min_lon=minx)

    try:
        config = SearchSchema(
            aoi=aoi,
            satellite=satellite,
            sensor=sensor,
            start_date=start_date,
            end_date=end_date,
        )
        manifest = ArchiveManager().build_manifest()
        scenes = SearchManager(config, manifest).search()
    except Exception as e:
        console.print(f"[bold red]Search failed:[/] {e}")
        return None

    if not scenes:
        console.print("No scenes found.")
        return None

    scenes.sort(
        key=lambda x: datetime.strptime(x.get("DOP", "01-Jan-1900"), "%d-%b-%Y")
    )

    slug = generate_slug()
    query = QuerySchema(
        slug=slug,
        name=name or generate_name(satellite, sensor, start_date, end_date),
        description=description
        or generate_description(
            satellite, sensor, aoi, start_date, end_date, len(scenes)
        ),
        created_at=datetime.now(),
        satellite=satellite,
        sensor=sensor,
        aoi=aoi,
        start_date=start_date,
        end_date=end_date,
        scenes=scenes,
    )
    save_query(query)

    render_search_results(
        console, scenes, slug=slug, interactive=interactive, header_srt=True
    )
    render_query_saved(console, query)
    return query


def run_query_list(console: Console, interactive: bool | None = None) -> None:
    """List all saved queries."""
    queries = list_queries()
    render_query_list(console, queries, interactive=interactive)


def run_query_show(
    console: Console, slug: str, interactive: bool | None = None
) -> bool:
    """Redisplay a saved query's cached scenes. Returns True if found."""
    from bhoonidhi_downloader.core.search.render import render_search_results

    query = load_query(slug)
    if query is None:
        render_query_not_found(console, slug)
        return False

    console.print(f"\n[bold]{query.name}[/]\n{query.description}\n")
    render_search_results(console, query.scenes, slug=slug, interactive=interactive)
    return True


def run_query_rename(
    console: Console, slug: str, name: str | None = None, description: str | None = None
) -> bool:
    """Update a saved query's name/description in place. Returns True if found."""
    query = load_query(slug)
    if query is None:
        render_query_not_found(console, slug)
        return False

    if name:
        query.name = name
    if description:
        query.description = description
    save_query(query)
    console.print(f"[green]Updated '{slug}'.[/]")
    return True


def run_query_fork(
    console: Console, slug: str, name: str | None = None
) -> QuerySchema | None:
    """Clone a saved query's params + scenes under a new slug (no re-query).

    Returns the new QuerySchema on success, None if the source wasn't found.
    """
    source = load_query(slug)
    if source is None:
        render_query_not_found(console, slug)
        return None

    new_slug = generate_slug()
    fork = source.model_copy(
        update={
            "slug": new_slug,
            "name": name or f"{source.name} (fork)",
            "created_at": datetime.now(),
        }
    )
    save_query(fork)
    console.print(f"[green]Forked '{slug}' \u2192 '{new_slug}'.[/]")
    return fork


def run_query_rm(console: Console, slug: str) -> bool:
    """Delete a saved query. Returns True if it existed."""
    if delete_query(slug):
        render_query_deleted(console, slug)
        return True
    render_query_not_found(console, slug)
    return False


def run_query_refresh(console: Console, slug: str) -> QuerySchema | None:
    """Re-query the portal for scenes newer than the query's stored end_date.

    AOI, satellite, and sensor stay fixed. Only the date window advances \u2014
    from (stored end_date - lookback buffer) through today \u2014 to catch
    late-arriving archive backfill without re-fetching the full history.
    New scenes are deduped by ID and appended. Returns the updated
    QuerySchema on success, None if the query wasn't found.
    """
    query = load_query(slug)
    if query is None:
        render_query_not_found(console, slug)
        return None

    refresh_start = query.end_date - timedelta(days=REFRESH_LOOKBACK_DAYS)
    refresh_end = datetime.now()

    if refresh_start >= refresh_end:
        console.print(f"[yellow]'{slug}' is already up to date.[/]")
        return query

    try:
        config = SearchSchema(
            aoi=query.aoi,
            satellite=query.satellite,
            sensor=query.sensor,
            start_date=refresh_start,
            end_date=refresh_end,
        )
        manifest = ArchiveManager().build_manifest()
        new_scenes = SearchManager(config, manifest).search()
    except Exception as e:
        console.print(f"[bold red]Refresh failed:[/] {e}")
        return None

    seen_ids = {s.get("ID") for s in query.scenes if s.get("ID")}
    added: list[dict[str, Any]] = [
        s for s in (new_scenes or []) if s.get("ID") and s["ID"] not in seen_ids
    ]

    query.scenes.extend(added)
    query.scenes.sort(
        key=lambda x: datetime.strptime(x.get("DOP", "01-Jan-1900"), "%d-%b-%Y")
    )
    query.end_date = refresh_end
    save_query(query)

    render_refresh_result(console, slug, len(added), len(query.scenes))
    return query


def resolve_scene_selection(
    scenes: list[dict[str, Any]], select: list[str] | None
) -> list[dict[str, Any]]:
    """Resolve a --select list (1-based indices and/or scene IDs) to scenes.

    Empty/None select means the whole query. Each --select token may
    itself be comma-separated (``-s 1,2,3``); repeated flags
    (``-s 1 -s 2``) work too.
    """
    if not select:
        return scenes

    tokens = [t.strip() for raw in select for t in raw.split(",") if t.strip()]

    by_id = {s.get("ID"): s for s in scenes if s.get("ID")}
    resolved: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for token in tokens:
        scene: dict[str, Any] | None = None
        if token.isdigit():
            idx = int(token) - 1
            if 0 <= idx < len(scenes):
                scene = scenes[idx]
        if scene is None:
            scene = by_id.get(token)
        scene_id = scene.get("ID") if scene else None
        if scene is not None and scene_id and scene_id not in seen_ids:
            seen_ids.add(scene_id)
            resolved.append(scene)

    return resolved


def ensure_session(console: Console, password: str | None) -> str | None:
    """Get a working JWT for download, re-authenticating if the stored one is stale.

    The password is never persisted — it only lives in memory for the
    duration of the call. Two paths, depending on how this is invoked:

    - Interactive terminal: if the session's expired, prompt for the
      password here via ``getpass`` and log in fresh, so no separate
      'auth login' step is needed.
    - Non-interactive (script, cron, CI): no prompting. Callers pass
      ``password`` explicitly to opt into the same re-auth, or handle a
      ``None`` return themselves — blocking on stdin would hang a script
      that isn't expecting to be asked for input.

    Returns a valid JWT, or None if no working session could be obtained.
    """
    session_dict = load_session_info()
    jwt = session_dict.get("jwt")
    username = session_dict.get("username")

    if jwt:
        try:
            if AuthManager(cfg=SessionSchema(username=username)).validate_session(jwt):
                return jwt
        except Exception:
            logger.debug("Stored session failed validation; falling back to re-auth.")

    if password is None:
        if not sys.stdin.isatty():
            console.print(
                "[bold red]Not authenticated.[/] Run 'auth login' first, or "
                "pass password= to re-authenticate automatically when calling "
                "this from a script."
            )
            return None
        if not username:
            console.print("[bold red]Not authenticated.[/] Run 'auth login' first.")
            return None
        console.print(
            f"[yellow]Session expired.[/] Re-enter the password for '{username}' "
            "to continue (nothing is written to disk):"
        )
        password = getpass.getpass("Password: ")

    try:
        am = AuthManager(cfg=SessionSchema(username=username, password=password))
        session = am.login()
    except Exception as e:
        console.print(f"[bold red]Re-authentication failed:[/] {e}")
        return None

    save_session_info(dict(session))
    console.print("[green]✓[/] Re-authenticated.")
    return session.jwt


def _render_selection_summary(console: Console, scenes: list[dict[str, Any]]) -> None:
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


def run_query_download(
    console: Console,
    slug: str,
    out: str,
    select: list[str] | None = None,
    parallel: int = 4,
    force: bool = False,
    password: str | None = None,
    interactive: bool | None = None,
) -> list[DownloadOutcome] | None:
    """Download open-access scenes from a saved query to ``out``.

    Priced/on-order scenes are skipped — they have to be requested on the
    Bhoonidhi portal. Downloads are verified with a SHA256 written
    back onto the query's cached scene record, so re-running is fast and
    idempotent unless ``force`` is set. Bhoonidhi's servers don't honor
    HTTP Range requests, so an interrupted download cannot be resumed —
    a leftover partial file is discarded and the scene is re-fetched from
    scratch. If the stored session has expired, this re-authenticates
    automatically (prompting interactively on a CLI, or using ``password``
    if given — see ``ensure_session``). Returns the list of
    per-scene DownloadOutcome, or None if the query, scene selection, or
    authentication couldn't be resolved.
    """
    query = load_query(slug)
    if query is None:
        render_query_not_found(console, slug)
        return None

    if not query.scenes:
        console.print(f"[yellow]'{slug}' has no scenes to download.[/]")
        return None

    scenes = resolve_scene_selection(query.scenes, select)
    if not scenes:
        console.print("[yellow]No scenes matched the given --select values.[/]")
        return None

    jwt = ensure_session(console, password)
    if not jwt:
        return None

    eligible = [s for s in scenes if is_downloadable(s)]
    _render_selection_summary(console, scenes)

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
            return None
        proceed = input("Download to the new location anyway? [y/N] ").strip().lower()
        if proceed not in ("y", "yes"):
            console.print("[yellow]Aborted.[/]")
            return None

    if not eligible:
        console.print("[yellow]No open-access scenes in the selection.[/]")
        return []

    manager = DownloadManager(
        jwt=jwt, out_dir=Path(out), parallel=parallel, force=force
    )
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
        outcomes = manager.run(eligible, on_progress=on_progress)

    # Write download state (path/sha256/downloaded_at) back onto the
    # query's cached scene records so 'query show' can reflect it and
    # re-downloads are skip-fast.
    outcomes_by_id = {o.scene_id: o for o in outcomes}
    for scene in query.scenes:
        scene_id = scene.get("ID")
        outcome = outcomes_by_id.get(scene_id) if scene_id else None
        if outcome and outcome.status in ("downloaded", "already_downloaded"):
            scene["_bhx_download"] = {
                "path": outcome.path,
                "sha256": outcome.sha256,
                "downloaded_at": datetime.now().isoformat(),
            }
    save_query(query)

    render_download_report(console, outcomes, interactive=interactive)
    return outcomes
