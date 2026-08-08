"""Query command handlers: create, list, show, rename, fork, export, refresh, rm, download."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from rich.console import Console

from bhoonidhi_downloader.core.archive import ArchiveManager
from bhoonidhi_downloader.core.auth.utils import load_session_info
from bhoonidhi_downloader.core.download import (
    DownloadManager,
    DownloadOutcome,
    is_downloadable,
    make_progress,
    render_download_report,
)
from bhoonidhi_downloader.core.search.client import SearchManager
from bhoonidhi_downloader.schemas import AOISchema, QuerySchema, SearchSchema

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

    render_search_results(console, scenes)
    render_query_saved(console, query)
    return query


def run_query_list(console: Console) -> None:
    """List all saved queries."""
    queries = list_queries()
    render_query_list(console, queries)


def run_query_show(console: Console, slug: str) -> bool:
    """Redisplay a saved query's cached scenes. Returns True if found."""
    from bhoonidhi_downloader.core.search.render import render_search_results

    query = load_query(slug)
    if query is None:
        render_query_not_found(console, slug)
        return False

    console.print(f"\n[bold]{query.name}[/]\n{query.description}\n")
    render_search_results(console, query.scenes)
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


def _resolve_scene_selection(
    scenes: list[dict[str, Any]], select: list[str] | None
) -> list[dict[str, Any]]:
    """Resolve a --select list (1-based indices and/or scene IDs) to scenes.

    Empty/None select means "the whole query" (Option: pass the entire
    query and let PRICED-gating decide what's actually fetched). Each
    --select token may itself be comma-separated (``-s 1,2,3``) since
    that's the syntax most people reach for first; repeated flags
    (``-s 1 -s 2``) keep working too.
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


def run_query_download(
    console: Console,
    slug: str,
    out: str,
    select: list[str] | None = None,
    parallel: int = 4,
    force: bool = False,
) -> list[DownloadOutcome] | None:
    """Download open-access scenes from a saved query to ``out``.

    Priced/on-order scenes are skipped (metadata/planning-only until the
    cart/order flow exists). Downloads are verified with a SHA256 written
    back onto the query's cached scene record, so re-running is fast and
    idempotent unless ``force`` is set. Bhoonidhi's servers don't honor
    HTTP Range requests, so an interrupted download cannot be resumed —
    a leftover partial file is discarded and the scene is re-fetched from
    scratch. Returns the list of per-scene DownloadOutcome, or None if the
    query or scene selection couldn't be resolved.
    """
    query = load_query(slug)
    if query is None:
        render_query_not_found(console, slug)
        return None

    if not query.scenes:
        console.print(f"[yellow]'{slug}' has no scenes to download.[/]")
        return None

    scenes = _resolve_scene_selection(query.scenes, select)
    if not scenes:
        console.print("[yellow]No scenes matched the given --select values.[/]")
        return None

    session = load_session_info()
    jwt = session.get("jwt")
    if not jwt:
        console.print("[bold red]Not authenticated.[/] Run 'auth login' first.")
        return None

    eligible = [s for s in scenes if is_downloadable(s)]
    priced = len(scenes) - len(eligible)
    if priced:
        console.print(
            f"[yellow]Skipping {priced} priced/on-order scene(s) "
            "(direct download not available yet).[/]"
        )

    already = sum(1 for s in eligible if s.get("_bhx_download") and not force)
    if already:
        console.print(
            f"[cyan]{already} scene(s) already downloaded previously "
            "(will skip-fast unless --force).[/]"
        )

    if not eligible:
        console.print("[yellow]No open-access scenes in the selection.[/]")
        return []

    manager = DownloadManager(jwt=jwt, out_dir=Path(out), parallel=parallel, force=force)
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

    render_download_report(console, outcomes)
    return outcomes
