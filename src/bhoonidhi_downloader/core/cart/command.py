"""Cart command handlers."""

import logging
from datetime import datetime

from rich.console import Console

from bhoonidhi_downloader.core.auth.utils import load_session_info
from bhoonidhi_downloader.core.query.client import list_queries, load_query
from bhoonidhi_downloader.core.query.command import (
    ensure_session,
    resolve_scene_selection,
)
from bhoonidhi_downloader.core.query.render import render_query_not_found
from bhoonidhi_downloader.core.search.availability import (
    parse_availability_filter,
)

from .client import CartClient
from .render import (
    cart_progress,
    render_add_summary,
    render_cart_error,
    render_cart_items,
    render_no_session,
    render_removed_summary,
)
from .utils import (
    CartKind,
    cart_availability_of,
    cart_kind_for,
    cart_kinds_for_states,
    parse_srt_date,
    resolve_cart_dates,
)

logger = logging.getLogger(__name__)


def _client(console: Console, password: str | None = None) -> CartClient | None:
    """Build a CartClient from the saved session, re-authenticating if needed.

    Reuses the query module's session handling so cart commands behave
    the same way ``query download`` does — prompting on an expired
    session when interactive, and failing cleanly when not.
    """
    jwt = ensure_session(console, password)
    if not jwt:
        return None

    user_id = load_session_info().get("userId")
    if not user_id:
        render_no_session(console)
        return None

    return CartClient(jwt=jwt, user_id=user_id)


def run_cart_add(
    console: Console,
    slug: str,
    select: list[str] | None = None,
    password: str | None = None,
    interactive: bool | None = None,
) -> bool:
    """Add scenes from a saved query to the portal cart.

    Each scene is routed to whichever of the portal's three carts its
    access type selects, so a single query spanning open and priced data
    lands in the right place without the caller thinking about it.

    Returns True if at least one scene was added.
    """
    query = load_query(slug)
    if query is None:
        render_query_not_found(console, slug)
        return False

    scenes = resolve_scene_selection(query.scenes, select)
    if not scenes:
        console.print("[yellow]No scenes matched that selection.[/]")
        return False

    client = _client(console, password)
    if client is None:
        return False

    added: list[tuple[dict, CartKind]] = []
    failed: list[tuple[dict, str]] = []

    with cart_progress("Adding to cart") as progress:
        task = progress.add_task("add", total=len(scenes))
        for scene in scenes:
            scene_id = scene.get("ID", "<unknown>")
            try:
                kind, _ = client.add(scene)
                added.append((scene, kind))
            except Exception as e:
                logger.debug("Add failed for %s", scene_id, exc_info=True)
                failed.append((scene, str(e)))
            progress.advance(task)

    # Every scene in one add shares a search, so the srt is the same;
    # surface it so priced/on-order items can be found in the portal.
    srt = scenes[0].get("srt") if scenes else None
    render_add_summary(console, added, failed, srt=srt, interactive=interactive)
    return bool(added)


def _srt_to_slug() -> dict[str, str]:
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
    console: Console,
    since: datetime | None = None,
    until: datetime | None = None,
    last: str | None = None,
    password: str | None = None,
    interactive: bool | None = None,
    filter_by: list[str] | None = None,
) -> bool:
    """Show everything in the cart — all three carts in one table.

    The portal keeps three separate carts (direct download, on-order,
    priced) addressed in different ways, so this reads all of them and
    merges the rows. Each row shows which cart it's in, its access type,
    whether it's staged/ready, the date it was added, and whether it's
    been confirmed (STATUS).

    Because cart items are filed by the date they were added, the date
    window controls how far back to look: nothing set means today,
    ``since``/``until`` an explicit span, ``last`` a preset like
    ``"1 week"``. ``filter_by`` narrows the view by state (``ready``,
    ``archived``, ``onorder``, ``priced``) — since each state can only
    ever come from one cart, this also limits which carts are read, so
    filtering to ``priced`` only ever fetches the priced cart.
    """
    try:
        filter_states = parse_availability_filter(filter_by)
    except ValueError as e:
        console.print(f"[bold red]{e}[/]")
        return False

    client = _client(console, password)
    if client is None:
        return False

    try:
        dates = resolve_cart_dates(since=since, until=until, last=last)
        kinds = cart_kinds_for_states(filter_states)
        items = _collect_carts(client, kinds, dates)
    except Exception as e:
        render_cart_error(console, str(e))
        return False

    title = _cart_title(kinds, dates)
    render_cart_items(
        console,
        items,
        title,
        srt_to_slug=_srt_to_slug(),
        interactive=interactive,
        filter_states=filter_states,
    )
    return True


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


def _cart_title(kinds: list[CartKind], dates: list[datetime]) -> str:
    """A title naming which carts and which date window are shown."""
    if len(kinds) == 1:
        scope = f"{kinds[0].value.title()} cart"
    else:
        scope = "Cart"
    if len(dates) == 1:
        return f"{scope} — {dates[0]:%d %b %Y}"
    return f"{scope} — {dates[-1]:%d %b %Y} to {dates[0]:%d %b %Y}"


def run_cart_rm(
    console: Console,
    slug: str | None = None,
    select: list[str] | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    last: str | None = None,
    password: str | None = None,
    filter_by: list[str] | None = None,
) -> bool:
    """Remove scenes from the portal cart.

    Two ways to address the rows, because the cart is its own collection —
    it can hold items from several queries, so query indices don't line up
    with what ``cart list`` prints:

    - without ``slug``: ``select`` indexes the merged cart itself, matching
      the numbers shown by ``cart list``. The same ``filter_by`` and date
      window options narrow it to the same rows, so the numbering lines
      up with what was listed;
    - with ``slug``: ``select`` indexes that saved query's scenes.
    """
    try:
        filter_states = parse_availability_filter(filter_by)
    except ValueError as e:
        console.print(f"[bold red]{e}[/]")
        return False

    client = _client(console, password)
    if client is None:
        return False

    if slug is None:
        try:
            dates = resolve_cart_dates(since=since, until=until, last=last)
            kinds = cart_kinds_for_states(filter_states)
            items = _collect_carts(client, kinds, dates)
        except Exception as e:
            render_cart_error(console, str(e))
            return False

        if filter_states is not None:
            items = [r for r in items if cart_availability_of(r) in filter_states]

        if not items:
            console.print("[yellow]Cart is empty — nothing to remove.[/]")
            return False

        scenes = resolve_scene_selection(items, select)
        if not scenes:
            console.print(
                "[yellow]No cart rows matched that selection.[/] "
                "Run [bold]bhd cart list[/bold] to see the numbers."
            )
            return False
        return _remove_scenes(console, client, scenes)

    query = load_query(slug)
    if query is None:
        render_query_not_found(console, slug)
        return False

    scenes = resolve_scene_selection(query.scenes, select)
    if not scenes:
        console.print("[yellow]No scenes matched that selection.[/]")
        return False

    return _remove_scenes(console, client, scenes)


def _remove_scenes(console: Console, client: CartClient, scenes: list[dict]) -> bool:
    """Remove each scene, collecting results so one failure isn't fatal.

    Shows a progress bar while it works, then a compact summary — one line
    per outcome group, not one per scene.
    """
    removed: list[tuple[str, CartKind]] = []
    failed: list[tuple[str, str]] = []

    with cart_progress("Removing from cart") as progress:
        task = progress.add_task("rm", total=len(scenes))
        for scene in scenes:
            scene_id = (
                scene.get("ID") or scene.get("SCENE_ID") or scene.get("PRODUCTID")
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
            progress.advance(task)

    render_removed_summary(console, removed, failed)
    return bool(removed)
