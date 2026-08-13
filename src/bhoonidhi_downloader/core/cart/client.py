"""HTTP layer for the portal's three carts.

Request shaping lives in :mod:`.utils`; this module is the thin network
wrapper around it.
"""

import logging
from datetime import datetime
from typing import Any

import requests

from bhoonidhi_downloader.constants import BASE_URL
from bhoonidhi_downloader.exceptions import BhoonidhiAPIError

from .utils import (
    CART_ENDPOINTS,
    CartKind,
    build_add_payload,
    build_delete_payload,
    cart_date_long,
    cart_date_short,
    compact_json,
    encode_article,
    ist_now,
)

logger = logging.getLogger(__name__)

TIMEOUT = 30


class CartClient:
    """Talks to CartServlet, OpenOrderCart and PICartServlet."""

    def __init__(self, jwt: str, user_id: str):
        self.jwt = jwt
        self.user_id = user_id

    # -- plumbing ---------------------------------------------------------

    def _post(self, servlet: str, article: dict) -> dict[str, Any]:
        """POST an article, applying both of the portal's encoding rules.

        Raises:
            BhoonidhiAPIError: on a non-200 response or a body that isn't
                the ``{"Results": [...]}`` envelope every servlet returns.
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "token": self.jwt,
        }
        body = compact_json(encode_article(article))
        url = f"{BASE_URL}/bhoonidhi/{servlet}"

        logger.debug("POST %s action=%s", servlet, article.get("action"))
        response = requests.post(url, data=body, headers=headers, timeout=TIMEOUT)

        if response.status_code == 401:
            raise BhoonidhiAPIError(
                f"{servlet} rejected the session token. Run 'bhd auth login' again."
            )
        if response.status_code != 200:
            raise BhoonidhiAPIError(
                f"{servlet} request failed. Status code: {response.status_code}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise BhoonidhiAPIError(
                f"{servlet} returned a non-JSON body: {response.text[:200]!r}"
            ) from exc

        if "Results" not in payload:
            raise BhoonidhiAPIError(
                f"{servlet} returned an unexpected payload: {payload!r}"
            )
        return payload

    @staticmethod
    def _first_result(payload: dict) -> dict[str, Any]:
        results = payload.get("Results") or []
        return results[0] if results else {}

    # -- cart operations --------------------------------------------------

    def add(self, scene: dict) -> tuple[CartKind, str]:
        """Add one scene to whichever cart its access type selects.

        Returns the cart it landed in and the portal's status message.

        Raises:
            BhoonidhiAPIError: if the portal reports anything but SUCCESS.
        """
        kind, article = build_add_payload(scene, self.user_id)
        payload = self._post(CART_ENDPOINTS[kind]["servlet"], article)

        result = self._first_result(payload)
        msg = result.get("MSG", "")
        if msg != "SUCCESS":
            # Raise the portal's own message, not a re-statement of the scene
            # ID and cart — the caller already has both, and repeating them
            # buries the actual reason. Callers log the ID separately.
            raise BhoonidhiAPIError(msg or f"unexpected response: {payload!r}")
        return kind, msg

    def view_direct(self, when: datetime | None = None) -> list[dict[str, Any]]:
        """List the direct-download cart, which is addressed by date.

        Defaults to today in IST — the server's own clock — not the
        caller's local time zone, since that's the date the portal filed
        today's adds under.
        """
        when = when or ist_now()
        payload = self._post(
            "CartServlet",
            {
                "userId": self.user_id,
                "cartDate": cart_date_long(when),
                "action": "VIEWCART",
            },
        )
        return payload.get("Results", [])

    def view_by_srt(self, kind: CartKind, srt: str) -> list[dict[str, Any]]:
        """List the priced or on-order cart, which are addressed by SRT.

        Raises:
            ValueError: if called for the direct-download cart, which has
                no SRT-based view — use :meth:`view_direct` instead.
        """
        if kind is CartKind.DIRECT:
            raise ValueError(
                "The direct-download cart is listed by date, not SRT — "
                "use view_direct()."
            )
        payload = self._post(
            CART_ENDPOINTS[kind]["servlet"],
            {
                "userId": self.user_id,
                "srt": srt,
                "action": CART_ENDPOINTS[kind]["view"],
            },
        )
        return payload.get("Results", [])

    def saved_srts(
        self, kind: CartKind, start: datetime, end: datetime
    ) -> list[str]:
        """List the search ids that have items in the priced or on-order cart.

        The priced and on-order carts are addressed by search id, not date,
        and the portal only reveals which ids have anything in them through
        this call (``GETSRT_IDS``, dated by add-date). A search only appears
        once a scene from it has been added to that cart.

        Ids are de-duplicated while preserving the order the portal sent
        them, since it sometimes repeats one.

        Raises:
            ValueError: for the direct-download cart, which is addressed by
                date and has no search-id enumeration.
        """
        if kind is CartKind.DIRECT:
            raise ValueError(
                "The direct-download cart has no search-id list — it is "
                "addressed by date."
            )
        payload = self._post(
            CART_ENDPOINTS[kind]["servlet"],
            {
                "userId": self.user_id,
                "sDate": cart_date_short(start),
                "eDate": cart_date_short(end),
                "action": "GETSRT_IDS",
            },
        )
        seen: dict[str, None] = {}
        for row in payload.get("Results", []):
            srt = row.get("SRT_ID")
            if srt:
                seen.setdefault(srt, None)
        return list(seen)

    def remove(self, scene: dict, when: datetime | None = None) -> str:
        """Remove one scene from whichever cart it belongs to.

        ``when`` (for the direct-download cart's ``cartDate``) defaults to
        today in IST, matching the date the item was filed under.
        """
        when = when or ist_now()
        kind, article = build_delete_payload(scene, self.user_id, when)
        payload = self._post(CART_ENDPOINTS[kind]["servlet"], article)
        return self._first_result(payload).get("MSG", "")
