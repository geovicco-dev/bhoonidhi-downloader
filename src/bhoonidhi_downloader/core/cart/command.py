"""Cart command handlers.

Pure logic: these build structured results (added/failed/removed lists) or
raise a typed :class:`~bhoonidhi_downloader.exceptions.BhoonidhiError`. The
caller supplies a ready :class:`CartClient`; rendering, progress bars, and
interactive session prompts live in the CLI layer (``cli/cart.py``).
"""

import logging
from collections.abc import Callable
from datetime import datetime

from bhoonidhi_downloader.core.query.client import list_queries, load_query
from bhoonidhi_downloader.core.query.command import resolve_scene_selection
from bhoonidhi_downloader.core.search.availability import Availability
from bhoonidhi_downloader.exceptions import BhoonidhiNotFoundError

from .client import CartClient
from .utils import (
    CartKind,
    cart_availability_of,
    cart_kind_for,
    cart_kinds_for_states,
    parse_srt_date,
    resolve_cart_dates,
)

logger = logging.getLogger(__name__)

# scene_id (str) — called once per scene as an add/remove completes.
ProgressCallback = Callable[[str], None]


def resolve_add_scenes(slug: str, select: list[str] | None) -> list[dict]:
    """Resolve which of a saved query's scenes an add request addresses.

    Raises:
        BhoonidhiNotFoundError: if no query has that slug.
    """
    query = load_query(slug)
    if query is None:
        raise BhoonidhiNotFoundError(slug)
    return resolve_scene_selection(query.scenes, select)


def run_cart_add(
    client: CartClient,
    slug: str,
    select: list[str] | None = None,
    on_progress: ProgressCallback | None = None,
) -> tuple[list[tuple[dict, CartKind]], list[tuple[dict, str]], str | None]:
    """Add scenes from a saved query to the portal cart.

    Each scene is routed to whichever of the portal's three carts its
    access type selects. One scene failing doesn't stop the rest.

    Returns ``(added, failed, srt)``: the scenes that were added with the
    cart each landed in, the scenes that failed with the reason, and the
    shared search id (for finding priced/on-order items in the portal).
    ``on_progress(scene_id)`` is called as each scene is processed.

    Raises:
        BhoonidhiNotFoundError: if no query has that slug.
    """
    scenes = resolve_add_scenes(slug, select)

    added: list[tuple[dict, CartKind]] = []
    failed: list[tuple[dict, str]] = []
    for scene in scenes:
        scene_id = scene.get("ID", "<unknown>")
        try:
            kind, _ = client.add(scene)
            added.append((scene, kind))
        except Exception as e:
            logger.debug("Add failed for %s", scene_id, exc_info=True)
            failed.append((scene, str(e)))
        if on_progress:
            on_progress(scene_id)

    # Every scene in one add shares a search, so the srt is the same;
    # surface it so priced/on-order items can be found in the portal.
    srt = scenes[0].get("srt") if scenes else None
    return added, failed, srt


def srt_to_slug() -> dict[str, str]:
    """Map each search id to the saved query that produced it.

    Lets a cart row name the query it came from — the cart itself only
    knows the SRT, and a cart routinely holds items from several queries.
    """
    index: dict[str, str] = {}
    for query in list_queries():
        for scene in query.scenes:
            srt = scene.get("srt")
            if srt:
                index.setdefault(srt, query.slug)
    return index


def run_cart_list(
    client: CartClient,
    since: datetime | None = None,
    until: datetime | None = None,
    last: str | None = None,
    filter_states: set[Availability] | None = None,
) -> tuple[list[dict], list[CartKind], list[datetime]]:
    """Read the cart — all three carts merged into one list of rows.

    The portal keeps three separate carts (direct download, on-order,
    priced) addressed in different ways; this reads all of them and merges
    the rows. Cart items are filed by the date they were added, so the date
    window controls how far back to look: nothing set means today,
    ``since``/``until`` an explicit span, ``last`` a preset like
    ``"1 week"``. ``filter_states`` limits which carts are read, since each
    state can only come from one cart.

    Returns ``(items, kinds, dates)`` — the merged rows plus the carts and
    date window they were read under (the caller uses those for the title).

    Raises:
        BhoonidhiAPIError: if a cart request fails.
    """
    dates = resolve_cart_dates(since=since, until=until, last=last)
    kinds = cart_kinds_for_states(filter_states)
    items = _collect_carts(client, kinds, dates)
    return items, kinds, dates


def _collect_carts(
    client: CartClient, kinds: list[CartKind], dates: list[datetime]
) -> list[dict]:
    """Read the requested carts over the date window and merge their rows.

    Each row is tagged with the cart it belongs to (``_cart``) and, for the
    direct-download cart, the date it was read under (``_cart_date``). Rows
    are de-duplicated by (cart, scene id) so an item that appears under two
    dates isn't listed twice.
    """
    merged: list[dict] = []
    seen: set[tuple[str, str]] = set()

    def add(
        item: dict, kind: CartKind, when: datetime | None, srt: str | None = None
    ) -> None:
        # Cart rows name the scene SCENE_ID and the search SRT_ID, but the
        # rest of the code (selection, delete payloads) keys off ID/srt.
        # Normalise here so a listed row can be removed the same way a
        # query scene can.
        scene_id = item.get("ID") or item.get("SCENE_ID") or item.get("PRODUCTID") or ""
        if scene_id:
            item.setdefault("ID", scene_id)
        # Prefer the row's own SRT_ID, else the id it was fetched under.
        srt = item.get("SRT_ID") or item.get("srt") or srt
        if srt:
            item.setdefault("srt", srt)
            item.setdefault("SRT_ID", srt)

        key = (kind.value, scene_id)
        if scene_id and key in seen:
            return
        if scene_id:
            seen.add(key)

        item["_cart"] = kind
        # The direct cart is read under a date; the priced/on-order carts
        # aren't, but their add-date is encoded in the search id.
        item["_cart_date"] = when if when is not None else parse_srt_date(srt)
        merged.append(item)

    for kind in kinds:
        if kind is CartKind.DIRECT:
            for when in dates:
                for item in client.view_direct(when):
                    add(item, kind, when)
        else:
            # Priced/on-order carts are addressed by search id; discover the
            # ids with items over the window, then read each one.
            start, end = dates[-1], dates[0]
            for srt in client.saved_srts(kind, start, end):
                for item in client.view_by_srt(kind, srt):
                    add(item, kind, None, srt=srt)

    return merged


def cart_title(kinds: list[CartKind], dates: list[datetime]) -> str:
    """A title naming which carts and which date window are shown."""
    if len(kinds) == 1:
        scope = f"{kinds[0].value.title()} cart"
    else:
        scope = "Cart"
    if len(dates) == 1:
        return f"{scope} — {dates[0]:%d %b %Y}"
    return f"{scope} — {dates[-1]:%d %b %Y} to {dates[0]:%d %b %Y}"


def collect_removable(
    client: CartClient,
    slug: str | None,
    select: list[str] | None,
    since: datetime | None = None,
    until: datetime | None = None,
    last: str | None = None,
    filter_states: set[Availability] | None = None,
) -> list[dict]:
    """Resolve which scenes a remove request addresses, without removing them.

    Two ways to address the rows, because the cart is its own collection —
    it can hold items from several queries, so query indices don't line up
    with what ``cart list`` prints:

    - without ``slug``: ``select`` indexes the merged cart itself, matching
      the numbers shown by ``cart list``; the same ``filter_states`` and
      date window narrow it to the same rows;
    - with ``slug``: ``select`` indexes that saved query's scenes.

    Returns the resolved scenes (possibly empty).

    Raises:
        BhoonidhiNotFoundError: if a slug is given but no query has it.
        BhoonidhiAPIError: if a cart request fails.
    """
    if slug is None:
        dates = resolve_cart_dates(since=since, until=until, last=last)
        kinds = cart_kinds_for_states(filter_states)
        items = _collect_carts(client, kinds, dates)
        if filter_states is not None:
            items = [r for r in items if cart_availability_of(r) in filter_states]
        return resolve_scene_selection(items, select)

    query = load_query(slug)
    if query is None:
        raise BhoonidhiNotFoundError(slug)
    return resolve_scene_selection(query.scenes, select)


def run_cart_rm(
    client: CartClient,
    scenes: list[dict],
    on_progress: ProgressCallback | None = None,
) -> tuple[list[tuple[str, CartKind]], list[tuple[str, str]]]:
    """Remove the given scenes from the cart, collecting per-scene results.

    One failure isn't fatal — every scene is attempted. Returns
    ``(removed, failed)``: the scene ids removed with the cart each came
    from, and the ids that failed with the reason. ``on_progress(scene_id)``
    is called as each scene is processed.
    """
    removed: list[tuple[str, CartKind]] = []
    failed: list[tuple[str, str]] = []

    for scene in scenes:
        scene_id = (
            scene.get("ID")
            or scene.get("SCENE_ID")
            or scene.get("PRODUCTID")
            or "<unknown>"
        )
        # Prefer the cart the row was listed under; fall back to routing by
        # pricing for scenes addressed straight from a saved query.
        kind = scene.get("_cart") or cart_kind_for(scene)
        try:
            client.remove(scene)
            removed.append((scene_id, kind))
        except Exception as e:
            logger.debug("Remove failed for %s", scene_id, exc_info=True)
            failed.append((scene_id, str(e)))
        if on_progress:
            on_progress(scene_id)

    return removed, failed
