"""Cart namespace — ``client.cart.*``.

Stage scenes into the portal's carts, list what's staged, and remove items.
All three reach the portal and use the client's held session — log in first.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

from bhoonidhi_downloader.core.cart import command as _cart
from bhoonidhi_downloader.core.cart.client import CartClient
from bhoonidhi_downloader.core.cart.utils import CartKind
from bhoonidhi_downloader.core.search.availability import (
    Availability,
    parse_availability_filter,
)
from bhoonidhi_downloader.exceptions import BhoonidhiAuthError
from bhoonidhi_downloader.sdk._select import normalize_filter, normalize_select

if TYPE_CHECKING:
    from bhoonidhi_downloader.sdk.client import BhoonidhiClient


class CartNamespace:
    """The ``cart`` commands, reachable as ``client.cart``."""

    def __init__(self, client: BhoonidhiClient) -> None:
        self._client = client

    def _cart_client(self) -> CartClient:
        """Build a portal CartClient from the held session, or raise."""
        account = self._client.require_account()
        if not account.userId:
            raise BhoonidhiAuthError(
                "The current session has no user id — log in again."
            )
        return CartClient(jwt=account.jwt, user_id=account.userId)

    def add(
        self,
        slug: str,
        select: list[int | str] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> tuple[list[tuple[dict, CartKind]], list[tuple[dict, str]], str | None]:
        """Add a saved query's scenes to the cart. Mirrors ``bhd cart add``.

        Each scene is routed to the cart its access type selects. ``select``
        is a list of 1-based indices and/or scene IDs (e.g. ``[1, 2, 3]``);
        omit it to add the whole query.

        Returns ``(added, failed, srt)`` — scenes added with their cart,
        scenes that failed with the reason, and the shared search id.

        Raises:
            BhoonidhiAuthError: if the client isn't authenticated.
            BhoonidhiNotFoundError: if the slug is unknown.
        """
        client = self._cart_client()
        return _cart.run_cart_add(
            client, slug, select=normalize_select(select), on_progress=on_progress
        )

    def list(
        self,
        since: datetime | None = None,
        until: datetime | None = None,
        last: str | None = None,
        filter_by: str | list[str] | None = None,
    ) -> list[dict]:
        """List staged scenes — all three carts merged. Mirrors ``bhd cart list``.

        Cart items are filed by add-date, so with no date option this shows
        today only; widen it with ``since``/``until`` or ``last`` (e.g.
        ``"1 week"``). ``filter_by`` limits to states: ready, archived,
        onorder, priced.

        Raises:
            BhoonidhiAuthError: if the client isn't authenticated.
            BhoonidhiAPIError: if a cart request fails.
        """
        client = self._cart_client()
        filter_states = self._filter_states(filter_by)
        items, _kinds, _dates = _cart.run_cart_list(
            client, since=since, until=until, last=last, filter_states=filter_states
        )
        if filter_states is not None:
            from bhoonidhi_downloader.core.cart.utils import cart_availability_of

            items = [r for r in items if cart_availability_of(r) in filter_states]
        return items

    def rm(
        self,
        slug: str | None = None,
        select: list[int | str] | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        last: str | None = None,
        filter_by: str | list[str] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> tuple[list[tuple[str, CartKind]], list[tuple[str, str]]]:
        """Remove scenes from the cart. Mirrors ``bhd cart rm``.

        Two ways to address rows: pass ``slug`` to index a saved query's
        scenes, or omit it and ``select`` indexes the merged cart itself
        (same numbers as ``list`` under the same filters/date window).

        Returns ``(removed, failed)`` — scene ids removed with their cart,
        and ids that failed with the reason.

        Raises:
            BhoonidhiAuthError: if the client isn't authenticated.
            BhoonidhiNotFoundError: if a slug is given but unknown.
            BhoonidhiAPIError: if a cart request fails.
        """
        client = self._cart_client()
        scenes = _cart.collect_removable(
            client,
            slug,
            normalize_select(select),
            since=since,
            until=until,
            last=last,
            filter_states=self._filter_states(filter_by),
        )
        return _cart.run_cart_rm(client, scenes, on_progress=on_progress)

    @staticmethod
    def _filter_states(
        filter_by: str | list[str] | None,
    ) -> set[Availability] | None:
        """Parse a state-filter (single value or list), raising ValueError if bad."""
        return parse_availability_filter(normalize_filter(filter_by))
