"""Query command handlers: create, list, show, rename, fork, refresh, rm, download.

Command logic is pure: it returns plain data or raises a typed
:class:`~bhoonidhi_downloader.exceptions.BhoonidhiError`. Rendering, progress
bars, and interactive prompts live in the CLI layer (``cli/query.py``).
"""

import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from bhoonidhi_downloader.core.archive import ArchiveManager
from bhoonidhi_downloader.core.download import (
    DownloadManager,
    DownloadOutcome,
    is_downloadable,
)
from bhoonidhi_downloader.core.search.client import SearchManager
from bhoonidhi_downloader.exceptions import (
    BhoonidhiNotFoundError,
    BhoonidhiValidationError,
)
from bhoonidhi_downloader.schemas import (
    AOISchema,
    QuerySchema,
    SearchSchema,
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

logger = logging.getLogger(__name__)

REFRESH_LOOKBACK_DAYS = 3

# scene_id, bytes_so_far, total_bytes (None if unknown)
ProgressCallback = Callable[[str, int, "int | None"], None]


def _build_search_schema(**kwargs: Any) -> SearchSchema:
    """Construct a ``SearchSchema``, translating bad input into a clean error.

    ``SearchSchema`` validates the satellite/sensor combination in a
    pydantic model validator, which raises a plain ``ValueError``. Pydantic
    wraps that in its own ``ValidationError`` — not a ``BhoonidhiError`` —
    so it slips past the CLI's ``except BhoonidhiError`` handler and dumps a
    raw pydantic traceback to the terminal (bug #26). Catch it here and
    re-raise the underlying message as ``BhoonidhiValidationError`` so every
    caller gets the same clean, typed error the rest of the codebase relies on.
    """
    try:
        return SearchSchema(**kwargs)
    except ValidationError as e:
        messages = [err["msg"].removeprefix("Value error, ") for err in e.errors()]
        raise BhoonidhiValidationError("; ".join(messages)) from e


def run_query_create(
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

    Returns the saved query, or None if the search matched no scenes (in
    which case nothing is saved).

    Raises:
        BhoonidhiAPIError: if the search request fails.
        BhoonidhiValidationError: if the satellite/sensor is invalid.
    """
    aoi = AOISchema(name="aoi", max_lat=maxy, min_lat=miny, max_lon=maxx, min_lon=minx)

    config = _build_search_schema(
        aoi=aoi,
        satellite=satellite,
        sensor=sensor,
        start_date=start_date,
        end_date=end_date,
    )
    manifest = ArchiveManager().build_manifest()
    scenes = SearchManager(config, manifest).search()

    if not scenes:
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
    return query


def run_query_list() -> list[QuerySchema]:
    """Return every saved query."""
    return list_queries()


def run_query_show(slug: str) -> QuerySchema:
    """Return a saved query by slug.

    Raises:
        BhoonidhiNotFoundError: if no query has that slug.
    """
    query = load_query(slug)
    if query is None:
        raise BhoonidhiNotFoundError(slug)
    return query


def run_query_rename(
    slug: str, name: str | None = None, description: str | None = None
) -> QuerySchema:
    """Update a saved query's name/description in place and return it.

    Raises:
        BhoonidhiNotFoundError: if no query has that slug.
    """
    query = load_query(slug)
    if query is None:
        raise BhoonidhiNotFoundError(slug)

    if name:
        query.name = name
    if description:
        query.description = description
    save_query(query)
    return query


def run_query_fork(slug: str, name: str | None = None) -> QuerySchema:
    """Clone a saved query's params + scenes under a new slug (no re-query).

    Returns the new query.

    Raises:
        BhoonidhiNotFoundError: if the source query doesn't exist.
    """
    source = load_query(slug)
    if source is None:
        raise BhoonidhiNotFoundError(slug)

    new_slug = generate_slug()
    fork = source.model_copy(
        update={
            "slug": new_slug,
            "name": name or f"{source.name} (fork)",
            "created_at": datetime.now(),
        }
    )
    save_query(fork)
    return fork


def run_query_rm(slug: str) -> None:
    """Delete a saved query.

    Raises:
        BhoonidhiNotFoundError: if no query has that slug.
    """
    if not delete_query(slug):
        raise BhoonidhiNotFoundError(slug)


def run_query_refresh(slug: str) -> tuple[QuerySchema, int | None]:
    """Re-query the portal for scenes newer than the query's stored end_date.

    AOI, satellite, and sensor stay fixed. Only the date window advances —
    from (stored end_date - lookback buffer) through today — to catch
    late-arriving archive backfill without re-fetching the full history.
    New scenes are deduped by ID and appended.

    Returns ``(query, added)`` where ``added`` is the count of new scenes,
    or ``None`` when the query was already up to date (no re-query run).

    Raises:
        BhoonidhiNotFoundError: if no query has that slug.
        BhoonidhiAPIError: if the search request fails.
    """
    query = load_query(slug)
    if query is None:
        raise BhoonidhiNotFoundError(slug)

    refresh_start = query.end_date - timedelta(days=REFRESH_LOOKBACK_DAYS)
    refresh_end = datetime.now()

    if refresh_start >= refresh_end:
        return query, None

    config = _build_search_schema(
        aoi=query.aoi,
        satellite=query.satellite,
        sensor=query.sensor,
        start_date=refresh_start,
        end_date=refresh_end,
    )
    manifest = ArchiveManager().build_manifest()
    new_scenes = SearchManager(config, manifest).search()

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
    return query, len(added)


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


def execute_download(
    query: QuerySchema,
    eligible: list[dict[str, Any]],
    jwt: str,
    out: str,
    parallel: int = 4,
    force: bool = False,
    on_progress: ProgressCallback | None = None,
) -> list[DownloadOutcome]:
    """Download the given open-access scenes and record the results.

    The caller resolves and filters the scenes (``eligible`` must already be
    downloadable). Download state (path/sha256/downloaded_at) is written back
    onto the query's cached scene records so re-runs are skip-fast, and the
    query is saved. ``on_progress(scene_id, downloaded, total)`` is invoked as
    bytes arrive, if given.

    Returns the per-scene outcomes (empty if ``eligible`` was empty).
    """
    if not eligible:
        return []

    manager = DownloadManager(
        jwt=jwt, out_dir=Path(out), parallel=parallel, force=force
    )
    outcomes = manager.run(eligible, on_progress=on_progress)

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
    return outcomes


def run_query_download(
    slug: str,
    out: str,
    jwt: str,
    select: list[str] | None = None,
    parallel: int = 4,
    force: bool = False,
    on_progress: ProgressCallback | None = None,
) -> list[DownloadOutcome]:
    """Download open-access scenes from a saved query to ``out``.

    Priced/on-order scenes are skipped automatically, and scenes already
    present in ``out`` are skip-fast unless ``force`` is set. Requires a
    valid ``jwt`` — this never prompts for credentials; obtain a token via
    ``BhoonidhiClient.login`` first. Returns the per-scene outcomes (empty
    if the query, selection, or eligibility resolved to nothing).

    Raises:
        BhoonidhiNotFoundError: if no query has that slug.
    """
    query = load_query(slug)
    if query is None:
        raise BhoonidhiNotFoundError(slug)

    scenes = resolve_scene_selection(query.scenes, select)
    eligible = [s for s in scenes if is_downloadable(s)]
    return execute_download(
        query,
        eligible,
        jwt,
        out,
        parallel=parallel,
        force=force,
        on_progress=on_progress,
    )
