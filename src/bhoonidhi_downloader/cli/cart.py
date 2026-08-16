"""Cart CLI subcommands."""

from datetime import datetime

import typer

from bhoonidhi_downloader.cli._session import ensure_session
from bhoonidhi_downloader.core.auth.utils import load_session_info
from bhoonidhi_downloader.core.cart.client import CartClient
from bhoonidhi_downloader.core.cart.command import (
    cart_title,
    collect_removable,
    resolve_add_scenes,
    run_cart_add,
    run_cart_list,
    run_cart_rm,
    srt_to_slug,
)
from bhoonidhi_downloader.core.cart.render import (
    cart_progress,
    render_add_summary,
    render_cart_error,
    render_cart_items,
    render_no_session,
    render_removed_summary,
)
from bhoonidhi_downloader.core.query.render import render_query_not_found
from bhoonidhi_downloader.core.search.availability import parse_availability_filter
from bhoonidhi_downloader.exceptions import BhoonidhiError, BhoonidhiNotFoundError
from bhoonidhi_downloader.logger import get_console

cart_app = typer.Typer(
    name="cart",
    help=(
        "Stage scenes in the Bhoonidhi cart before placing an order.\n\n"
        "Every scene the portal returns falls into one of four availability "
        "states — direct download, on-order, priced, or archived — and each "
        "goes to a different cart. 'cart add' routes automatically based on "
        "each scene's state, so a mixed query just works. 'cart list' shows "
        "all three carts in one table, numbered for use with 'cart rm'.\n\n"
        "This CLI only stages; placing the order (and any payment for priced "
        "data) still happens in the Browse & Order web portal — there is no "
        "ordering step here. Login is required for every cart command; an "
        "expired session re-authenticates on its own when run interactively."
    ),
    no_args_is_help=True,
    add_completion=False,
)

console = get_console()


def _build_client(password: str | None = None) -> CartClient | None:
    """Build a CartClient from the saved session, re-authenticating if needed.

    Reuses the shared interactive session handling so cart commands behave
    the same way ``query download`` does — prompting on an expired session
    when interactive, and failing cleanly when not.
    """
    jwt = ensure_session(console, password)
    if not jwt:
        return None

    user_id = load_session_info().get("userId")
    if not user_id:
        render_no_session(console)
        return None

    return CartClient(jwt=jwt, user_id=user_id)


@cart_app.command("add")
def add(
    slug: str = typer.Argument(..., help="Saved query slug"),
    select: list[str] = typer.Option(
        None,
        "--select",
        "-s",
        help="Scenes to add: 1-based indices and/or scene IDs "
        "(repeatable, comma-separated)",
    ),
    plain: bool = typer.Option(
        False,
        "--plain",
        help="Print the whole results table at once instead of scrolling",
    ),
) -> None:
    """Add a saved query's scenes to the Bhoonidhi cart.

    Each scene is routed automatically to the cart that fits its access
    type — direct download, on-order, or priced — so a mixed query just
    works. With no --select, the whole query is added.

    Examples:
      bhd cart add velvet-wren            # add every scene in the query
      bhd cart add velvet-wren -s 1,3,7   # add scenes 1, 3 and 7

    Caveat: this only stages scenes. Placing the order (and any payment
    for priced data) is finished in the Browse & Order portal — there is
    no ordering step in the CLI. An expired session re-authenticates
    automatically when run interactively.
    """
    interactive = False if plain else None

    try:
        scenes = resolve_add_scenes(slug, select)
    except BhoonidhiNotFoundError as e:
        render_query_not_found(console, slug)
        raise typer.Exit(code=1) from e

    if not scenes:
        console.print("[yellow]No scenes matched that selection.[/]")
        raise typer.Exit(code=1)

    client = _build_client()
    if client is None:
        raise typer.Exit(code=1)

    with cart_progress("Adding to cart") as progress:
        task = progress.add_task("add", total=len(scenes))

        def on_progress(_scene_id: str) -> None:
            progress.advance(task)

        added, failed, srt = run_cart_add(
            client, slug, select=select, on_progress=on_progress
        )

    render_add_summary(console, added, failed, srt=srt, interactive=interactive)
    if not added:
        raise typer.Exit(code=1)


@cart_app.command("list")
def list_cart(
    since: datetime = typer.Option(
        None,
        "--since",
        formats=["%Y-%m-%d"],
        help="Show items added on/after this date (YYYY-MM-DD)",
    ),
    until: datetime = typer.Option(
        None,
        "--until",
        formats=["%Y-%m-%d"],
        help="Show items added on/before this date (YYYY-MM-DD, default: today)",
    ),
    last: str = typer.Option(
        None,
        "--last",
        help="Look back a preset window, e.g. '10 days', '2 weeks', '1 month'",
    ),
    filter_by: list[str] = typer.Option(
        None,
        "--filter",
        "-f",
        help="Show only rows in these states: ready, archived, onorder, "
        "priced. Comma-separated (-f ready,archived) or repeat the flag.",
    ),
    plain: bool = typer.Option(
        False, "--plain", help="Print the whole table at once instead of scrolling"
    ),
) -> None:
    """List staged scenes — all three carts in one table.

    Each row shows which cart it's in, whether it's ready or archived,
    when it was added, and whether the order has been placed. Rows are
    numbered for 'bhd cart rm --select'.

    Examples:
      bhd cart list                       # everything added today
      bhd cart list --last "1 week"       # added in the past 7 days
      bhd cart list --since 2026-08-01    # added on/after a date
      bhd cart list --filter priced       # just the priced cart
      bhd cart list -f ready,archived     # only direct-download rows

    Caveat: the portal files items by the date they were added, so with
    no date option this shows today only — widen it with --since/--until
    or --last to see scenes staged on earlier days.
    """
    interactive = False if plain else None

    try:
        filter_states = parse_availability_filter(filter_by)
    except ValueError as e:
        console.print(f"[bold red]{e}[/]")
        raise typer.Exit(code=1) from e

    client = _build_client()
    if client is None:
        raise typer.Exit(code=1)

    try:
        items, kinds, dates = run_cart_list(
            client, since=since, until=until, last=last, filter_states=filter_states
        )
    except BhoonidhiError as e:
        render_cart_error(console, str(e))
        raise typer.Exit(code=1) from e

    render_cart_items(
        console,
        items,
        cart_title(kinds, dates),
        srt_to_slug=srt_to_slug(),
        interactive=interactive,
        filter_states=filter_states,
    )


@cart_app.command("rm")
def rm(
    slug: str = typer.Argument(
        None, help="Saved query slug. Omit to address rows by their cart number."
    ),
    select: list[str] = typer.Option(
        None,
        "--select",
        "-s",
        help="What to remove: 1-based numbers and/or scene IDs",
    ),
    since: datetime = typer.Option(
        None, "--since", formats=["%Y-%m-%d"], help="Window start (YYYY-MM-DD)"
    ),
    until: datetime = typer.Option(
        None, "--until", formats=["%Y-%m-%d"], help="Window end (YYYY-MM-DD)"
    ),
    last: str = typer.Option(None, "--last", help="Look back a preset, e.g. '1 week'"),
    filter_by: list[str] = typer.Option(
        None,
        "--filter",
        "-f",
        help="Limit to rows in these states: ready, archived, onorder, "
        "priced. Comma-separated (-f ready,archived) or repeat the flag.",
    ),
) -> None:
    """Remove scenes from the cart.

    Two ways to pick what to remove:
      - by a saved query's scenes:  bhd cart rm velvet-wren -s 1,3
      - by the row numbers 'cart list' printed:  bhd cart rm -s 1,2

    Caveat: those row numbers are only stable for the same view. When
    removing by number, pass the same --filter and date window you
    listed with, so the numbering lines up.
    """
    try:
        filter_states = parse_availability_filter(filter_by)
    except ValueError as e:
        console.print(f"[bold red]{e}[/]")
        raise typer.Exit(code=1) from e

    client = _build_client()
    if client is None:
        raise typer.Exit(code=1)

    try:
        scenes = collect_removable(
            client,
            slug,
            select,
            since=since,
            until=until,
            last=last,
            filter_states=filter_states,
        )
    except BhoonidhiNotFoundError as e:
        render_query_not_found(console, slug)
        raise typer.Exit(code=1) from e
    except BhoonidhiError as e:
        render_cart_error(console, str(e))
        raise typer.Exit(code=1) from e

    if not scenes:
        if slug is None:
            console.print(
                "[yellow]No cart rows matched that selection.[/] "
                "Run [bold]bhd cart list[/bold] to see the numbers."
            )
        else:
            console.print("[yellow]No scenes matched that selection.[/]")
        raise typer.Exit(code=1)

    with cart_progress("Removing from cart") as progress:
        task = progress.add_task("rm", total=len(scenes))

        def on_progress(_scene_id: str) -> None:
            progress.advance(task)

        removed, failed = run_cart_rm(client, scenes, on_progress=on_progress)

    render_removed_summary(console, removed, failed)
    if not removed:
        raise typer.Exit(code=1)
