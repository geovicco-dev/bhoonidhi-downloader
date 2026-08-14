"""Rich rendering for cart commands."""

from collections import Counter

from rich.console import Console, Group
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)
from rich.text import Text

from bhoonidhi_downloader.core.search.availability import Availability
from bhoonidhi_downloader.core.search.utils import (
    full_satellite,
    full_sensor,
    get_quicklook_url,
    get_scene_meta_url,
    link_or_dash,
)
from bhoonidhi_downloader.logger import CUSTOM_THEME
from bhoonidhi_downloader.viewer import Column, show_table

from .utils import CartKind, cart_availability_of


def cart_progress(description: str) -> Progress:
    """A spinner + bar + N-of-M counter for stepping through cart scenes.

    Counts scenes done, not bytes — cart add/remove is one quick request
    per scene, so the useful signal is "12 of 40", not a transfer rate.

    Uses a fresh auto-sized console rather than the app's shared width=300
    one, so the live display redraws in place instead of repeating frames.
    """
    progress_console = Console(theme=CUSTOM_THEME, force_terminal=True)
    return Progress(
        SpinnerColumn(),
        TextColumn(f"[bold blue]{description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=progress_console,
        transient=True,
    )


#: Human-facing labels for each cart.
KIND_LABELS: dict[CartKind, str] = {
    CartKind.DIRECT: "direct download",
    CartKind.ORDER: "on order",
    CartKind.PRICED: "priced",
}


def render_cart_items(
    console: Console,
    items: list[dict],
    title: str,
    srt_to_slug: dict[str, str] | None = None,
    interactive: bool | None = None,
    filter_states: set[Availability] | None = None,
) -> None:
    """Show the cart in a scrollable viewer.

    Every row and column is available — the viewport moves over them
    rather than anything being dropped. ``srt_to_slug`` maps a search id
    back to the saved query it came from, so a cart row can be traced to
    what put it there.

    ``filter_states``, when given, keeps only rows whose
    :func:`.utils.cart_availability_of` is one of the given states — the
    "empty" message distinguishes an empty cart from everything being
    filtered out.
    """
    if filter_states is not None:
        items = [r for r in items if cart_availability_of(r) in filter_states]
        if not items:
            console.print(f"[yellow]{title}: nothing matches that filter.[/]")
            return

    if not items:
        console.print(f"[yellow]{title}: empty.[/]")
        return

    show_table(
        console,
        items,
        cart_columns(srt_to_slug or {}),
        title,
        interactive=interactive,
        footer=_cart_footer(),
    )


def _cart_footer() -> Group:
    """Legend shown below the cart table: the remove hint and the asterisk.

    The ``*`` on a *staged* row is explained here — it marks the row as in
    the cart but not yet ordered (``STATUS: ADDED``), to distinguish it
    from a ``confirmed`` one whose order has been placed in the portal.
    """
    return Group(
        Text.from_markup(
            "[dim]* [yellow]staged[/] = in the cart, order not yet placed; "
            "[green]confirmed[/] = order placed in the portal.[/]",
            justify="center",
        ),
        Text.from_markup(
            "Remove by number with [bold]bhd cart rm -s 1,2[/bold] "
            "(using the same filters you listed with).",
            style="dim",
            justify="center",
        ),
    )


def cart_columns(srt_to_slug: dict[str, str]) -> list[Column]:
    """Every cart column, in scroll order. Nothing is dropped."""

    def _srt(item: dict) -> str:
        return item.get("SRT_ID") or item.get("srt") or ""

    def _confirmed(item: dict) -> str:
        status = item.get("STATUS") or ""
        if status == "CLOSED":
            return "[green]confirmed[/]"
        if status == "ADDED":
            # The asterisk marks "staged" as a reading of STATUS=ADDED, not
            # the portal confirming the order is placed — see the legend.
            return "[yellow]staged[/] *"
        return "[dim]—[/]"

    def _added(item: dict) -> str:
        when = item.get("_cart_date")
        return f"{when:%d %b %Y}" if when else "—"

    return [
        Column("#", lambda _r, i: str(i + 1), style="dim", width=5, justify="center"),
        Column(
            "Scene ID",
            lambda r, _i: r.get("ID") or r.get("SCENE_ID") or r.get("PRODUCTID") or "—",
            style="cyan",
            width=46,
        ),
        Column("Cart", lambda r, _i: _cart_status(r), width=22, justify="center"),
        Column("Confirmed", lambda r, _i: _confirmed(r), width=11, justify="center"),
        Column(
            "Acquired",
            lambda r, _i: r.get("DOP") or "—",
            style="blue",
            width=13,
            justify="center",
        ),
        Column(
            "Added",
            lambda r, _i: _added(r),
            style="blue",
            width=13,
            justify="center",
        ),
        Column(
            "Satellite",
            lambda r, _i: full_satellite(r),
            style="red",
            width=16,
            justify="center",
        ),
        Column(
            "Sensor",
            lambda r, _i: full_sensor(r),
            style="blue",
            width=12,
            justify="center",
        ),
        Column(
            "Query",
            lambda r, _i: srt_to_slug.get(_srt(r), "[dim]—[/]"),
            style="cyan",
            width=16,
            justify="center",
        ),
        Column(
            "Search ID",
            lambda r, _i: _srt(r) or "—",
            style="dim",
            width=20,
            justify="center",
        ),
        Column(
            "Metadata",
            lambda r, _i: link_or_dash(r, get_scene_meta_url, "Metadata"),
            style="red",
            width=12,
            justify="center",
        ),
        Column(
            "Quick View",
            lambda r, _i: link_or_dash(r, get_quicklook_url, "Quick View"),
            style="blue",
            width=12,
            justify="center",
        ),
    ]


def _cart_status(item: dict) -> str:
    """One column that says which cart a row is in and, where it means
    something, its staging state.

    The direct-download cart is the only one where availability varies —
    an open scene there is either staged (Ready) or cold (Archived). For
    the on-order and priced carts the cart itself is the whole story, so
    repeating the pricing as an availability adds nothing.
    """
    kind = item.get("_cart")
    if kind is CartKind.DIRECT:
        ready = item.get("CURR_SCENE_NO") == "Y"
        mark = "[bold green]Ready[/]" if ready else "[dim cyan]Archived[/]"
        return f"[magenta]Direct[/] · {mark}"
    if kind is CartKind.ORDER:
        return "[yellow]On order[/]"
    if kind is CartKind.PRICED:
        return "[magenta]Priced[/]"
    return "—"


def render_add_summary(
    console: Console,
    added: list[tuple[dict, CartKind]],
    failed: list[tuple[dict, str]],
    srt: str | None = None,
    interactive: bool | None = None,
) -> None:
    """Summarise an add run as a scrollable table, one row per scene.

    Every cart here is a staging step only — this CLI adds scenes, and the
    order itself is finished in the Browse & Order portal. A one-line count
    sits above the table; the table itself carries the per-scene result,
    which cart it landed in, the reason for anything that didn't add, and
    the Metadata/Quick View links so a staged scene can be inspected.
    """
    total = len(added) + len(failed)
    if total == 0:
        console.print("[yellow]Nothing to add.[/]")
        return

    if added:
        by_kind = Counter(kind for _, kind in added)
        parts = [f"{n} {KIND_LABELS[k]}" for k, n in by_kind.items()]
        console.print(f"[green]✓[/] Added {len(added)} scene(s): {', '.join(parts)}")
    if failed:
        console.print(f"[red]✗[/] {len(failed)} scene(s) not added — see the table.")

    rows: list[dict] = [
        {"scene": scene, "ok": True, "kind": kind, "detail": "added"}
        for scene, kind in added
    ]
    rows += [
        {"scene": scene, "ok": False, "kind": None, "detail": reason}
        for scene, reason in failed
    ]

    show_table(
        console,
        rows,
        _add_summary_columns(),
        "Cart add results",
        interactive=interactive,
        footer=_add_summary_footer(srt),
    )


def _add_summary_footer(srt: str | None) -> Group:
    """Staging note shown at the bottom of the cart-add results table."""
    lines = [
        Text.from_markup(
            "[dim]Scenes are staged in the portal's cart. Finish the order in "
            "the Browse & Order portal — priced and on-order items are "
            "completed there.[/]",
            justify="center",
        )
    ]
    if srt:
        lines.append(
            Text.from_markup(
                f"[dim]Search ID for the staged items: [bold]{srt}[/bold][/]",
                justify="center",
            )
        )
    return Group(*lines)


def _add_summary_columns() -> list[Column]:
    """Columns for the cart-add results table."""

    def _result(row: dict) -> str:
        return "[green]✓ added[/]" if row["ok"] else "[red]✗ failed[/]"

    def _cart(row: dict) -> str:
        kind = row["kind"]
        return KIND_LABELS[kind] if kind else "[dim]—[/]"

    def _detail(row: dict) -> str:
        return _short_reason(row["detail"]) if not row["ok"] else "[dim]—[/]"

    return [
        Column("#", lambda _r, i: str(i + 1), style="dim", width=5, justify="right"),
        Column(
            "Scene ID",
            lambda r, _i: r["scene"].get("ID", "—"),
            style="cyan",
            width=46,
        ),
        Column("Result", lambda r, _i: _result(r), width=10, justify="center"),
        Column("Cart", lambda r, _i: _cart(r), style="magenta", width=16),
        Column("Detail", lambda r, _i: _detail(r), style="yellow", width=30),
        Column(
            "Metadata",
            lambda r, _i: link_or_dash(r["scene"], get_scene_meta_url, "Metadata"),
            style="red",
            width=12,
        ),
        Column(
            "Quick View",
            lambda r, _i: link_or_dash(r["scene"], get_quicklook_url, "Quick View"),
            style="blue",
            width=12,
        ),
    ]


def _short_reason(reason: str) -> str:
    """Shorten a portal error message for the Detail column.

    The portal phrases some failures verbosely (e.g. "Product already
    added to Priced Cart"). Known verbose phrasings are shortened to a
    brief line; anything unrecognised is shown as-is so no information is
    lost.
    """
    lowered = reason.lower()
    if "already added" in lowered or "already in" in lowered:
        return "already in cart"
    return reason


def render_removed_summary(
    console: Console,
    removed: list[tuple[str, CartKind]],
    failed: list[tuple[str, str]],
) -> None:
    """Summarise a remove run in one or two lines, not one per scene.

    Prints a count grouped by cart, then lists only the failures — a wall
    of one ✓ per scene isn't useful when dozens are removed at once.
    """
    if removed:
        by_kind = Counter(kind for _, kind in removed)
        parts = [f"{n} {KIND_LABELS[k]}" for k, n in by_kind.items()]
        console.print(
            f"[green]✓[/] Removed {len(removed)} scene(s): {', '.join(parts)}"
        )
    if failed:
        console.print(f"[red]✗[/] {len(failed)} could not be removed:")
        for scene_id, reason in failed:
            console.print(f"  [red]✗[/] {scene_id}: {_short_reason(reason)}")
    if not removed and not failed:
        console.print("[yellow]Nothing removed.[/]")


def render_no_session(console: Console) -> None:
    """Tell the user they need to log in first."""
    console.print(
        "[yellow]Not logged in.[/] Run [bold]bhd auth login[/bold] to authenticate."
    )


def render_cart_error(console: Console, error: str) -> None:
    """Render a failed cart operation."""
    panel = Panel(
        f"[red]{error}[/]",
        title="[bold red]✗ Cart operation failed[/]",
        border_style="red",
        padding=(1, 2),
    )
    console.print(panel)
