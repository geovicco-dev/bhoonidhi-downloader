"""Cart CLI subcommands."""

from datetime import datetime

import typer

from bhoonidhi_downloader.core.cart.command import (
    run_cart_add,
    run_cart_list,
    run_cart_rm,
)
from bhoonidhi_downloader.logger import get_console

cart_app = typer.Typer(
    name="cart",
    help="Stage scenes in the Bhoonidhi cart: add, list, and remove.",
    no_args_is_help=True,
    add_completion=False,
)

console = get_console()


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
    if not run_cart_add(
        console, slug, select, interactive=False if plain else None
    ):
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
    kind: str = typer.Option(
        None,
        "--kind",
        help="Show only one cart: 'direct', 'order', or 'priced' (default: all three)",
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
      bhd cart list --kind priced         # just the priced cart

    Caveat: the portal files items by the date they were added, so with
    no date option this shows today only — widen it with --since/--until
    or --last to see scenes staged on earlier days.
    """
    if not run_cart_list(
        console,
        kind=kind,
        since=since,
        until=until,
        last=last,
        interactive=False if plain else None,
    ):
        raise typer.Exit(code=1)


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
    kind: str = typer.Option(
        None, "--kind", help="Limit to one cart: 'direct', 'order', or 'priced'"
    ),
    since: datetime = typer.Option(
        None, "--since", formats=["%Y-%m-%d"], help="Window start (YYYY-MM-DD)"
    ),
    until: datetime = typer.Option(
        None, "--until", formats=["%Y-%m-%d"], help="Window end (YYYY-MM-DD)"
    ),
    last: str = typer.Option(
        None, "--last", help="Look back a preset, e.g. '1 week'"
    ),
) -> None:
    """Remove scenes from the cart.

    Two ways to pick what to remove:
      - by a saved query's scenes:  bhd cart rm velvet-wren -s 1,3
      - by the row numbers 'cart list' printed:  bhd cart rm -s 1,2

    Caveat: those row numbers are only stable for the same view. When
    removing by number, pass the same --kind and date window you listed
    with, so the numbering lines up.
    """
    if not run_cart_rm(
        console, slug, select, kind=kind, since=since, until=until, last=last
    ):
        raise typer.Exit(code=1)
