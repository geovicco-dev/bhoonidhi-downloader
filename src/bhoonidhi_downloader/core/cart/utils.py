"""Pure request-shaping rules for the portal's three carts.

Everything here mirrors logic in the portal's own front-end (``odap.js``,
``LoginVals.js``) and is side-effect free so it can be unit tested without
touching the network.
"""

import json
import re
import urllib.parse
from datetime import datetime, timedelta
from enum import Enum
from zoneinfo import ZoneInfo

from bhoonidhi_downloader.core.search.availability import (
    Access,
    Availability,
    access_of,
)

from .scene_spec import make_interface_obj

#: The portal files every cart record under the server's own clock, which
#: is IST (Asia/Kolkata) — not the caller's local time zone. A cart action
#: that defaults to local "now" can file under the wrong date for anyone
#: outside IST (e.g. UTC+10 querying "today" gets yesterday's IST date and
#: sees an empty cart even though the add succeeded). Every cart date
#: default goes through here instead of a bare ``datetime.now()``.
_IST = ZoneInfo("Asia/Kolkata")


def ist_now() -> datetime:
    """The current date/time in IST, naive (tzinfo stripped).

    Naive because the rest of the cart date-handling (``cart_date_long``,
    ``cart_date_short``, ``resolve_cart_dates``) works with naive
    ``datetime`` objects throughout — this just anchors "now" to the
    portal's clock before entering that naive arithmetic.
    """
    return datetime.now(_IST).replace(tzinfo=None)


class CartKind(str, Enum):
    """Which of the portal's three carts a scene belongs in.

    The portal does not have one cart — it has three, each on its own
    servlet with its own add/view/delete payload shape.
    """

    DIRECT = "direct"
    ORDER = "order"
    PRICED = "priced"


#: Per-cart servlet and action names. Keyed by :class:`CartKind`.
CART_ENDPOINTS: dict[CartKind, dict[str, str]] = {
    CartKind.DIRECT: {
        "servlet": "CartServlet",
        "add": "ADDTOCART",
        "view": "VIEWCART",
    },
    CartKind.ORDER: {
        "servlet": "OpenOrderCart",
        "add": "ADDTOORDERCART",
        "view": "VIEWOPENCART",
    },
    CartKind.PRICED: {
        "servlet": "PICartServlet",
        "add": "ADDTOPICART",
        "view": "VIEWPICART",
    },
}


#: How a scene's access type selects its cart. Open scenes go to the
#: direct-download cart, on-order scenes to the open-order cart, and
#: everything priced to the PI cart.
_ACCESS_TO_CART: dict[Access, CartKind] = {
    Access.OPEN: CartKind.DIRECT,
    Access.ON_ORDER: CartKind.ORDER,
    Access.PRICED: CartKind.PRICED,
}


def cart_kind_for(scene: dict) -> CartKind:
    """Route a scene to a cart by its access type.

    Reuses the same ``access_of`` classification that search and download
    already apply, so a scene lands in the cart that matches how the rest
    of the CLI describes it — there is no second pricing parser to drift
    out of sync.
    """
    return _ACCESS_TO_CART[access_of(scene)]


def cart_availability_of(item: dict) -> Availability:
    """Classify a cart row the same way ``cart list``'s Cart column does.

    Cart rows are already tagged with ``_cart`` (which cart they came
    from) by the collector in ``core/cart/command.py``, so this reads that
    tag directly rather than re-deriving it from ``PRICED`` — a cart
    row's own pricing field isn't reliably present the way a fresh search
    result's is. Only the direct-download cart's staging varies
    (Ready/Archived); on-order and priced rows are that state outright,
    matching :func:`bhoonidhi_downloader.core.cart.render._cart_status`.
    """
    kind = item.get("_cart")
    if kind is CartKind.ORDER:
        return Availability.ON_ORDER
    if kind is CartKind.PRICED:
        return Availability.PRICED
    # DIRECT (or an untagged/legacy row): fall back to staging.
    if item.get("CURR_SCENE_NO") == "Y":
        return Availability.DIRECT_AVAILABLE
    return Availability.DIRECT_UNAVAILABLE


#: Availability state -> the cart it can only ever come from. Both
#: DIRECT_AVAILABLE and DIRECT_UNAVAILABLE map to the direct-download
#: cart — its two states are staging, not a different cart.
_AVAILABILITY_TO_CART: dict[Availability, CartKind] = {
    Availability.DIRECT_AVAILABLE: CartKind.DIRECT,
    Availability.DIRECT_UNAVAILABLE: CartKind.DIRECT,
    Availability.ON_ORDER: CartKind.ORDER,
    Availability.PRICED: CartKind.PRICED,
}


def cart_kinds_for_states(states: set[Availability] | None) -> list[CartKind]:
    """Which carts to read for a given set of ``--filter`` states.

    Reading only the carts a filter could actually match avoids fetching
    ones that would just be discarded afterwards — e.g. ``--filter
    priced`` only ever needs the priced cart. With no filter, all three
    are read, same as before ``--filter`` existed.
    """
    if not states:
        return [CartKind.DIRECT, CartKind.ORDER, CartKind.PRICED]
    kinds = {_AVAILABILITY_TO_CART[state] for state in states}
    return [k for k in (CartKind.DIRECT, CartKind.ORDER, CartKind.PRICED) if k in kinds]


def encode_article(article: dict) -> dict[str, str]:
    """URL-encode every value, the way the portal's ``encodeObject()`` does.

    The portal encodes *all* values, not just the JSON-valued ones
    (LoginVals.js:101). Encoding only ``selProds`` leaves ``/`` and ``{}``
    in sibling fields to be misparsed server-side.
    """
    return {k: urllib.parse.quote(str(v), safe="") for k, v in article.items()}


def compact_json(payload: object) -> str:
    """Serialise without whitespace.

    The WAF in front of the portal rejects JSON bodies containing spaces,
    so the default ``json.dumps`` separators are not usable here.
    """
    return json.dumps(payload, separators=(",", ":"))


def cart_date_long(when: datetime) -> str:
    """Cart date as VIEWCART and DELETE want it, e.g. ``10 August 2026``."""
    return f"{when.day:02d} {when.strftime('%B')} {when.year}"


#: Uppercase 3-letter months, matching the portal's getMonth() in odap.js.
_MONTHS = (
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
)


def cart_date_short(when: datetime) -> str:
    """Cart date as GETSRT_IDS wants it, e.g. ``10-AUG-2026``.

    The day is *not* zero-padded, matching the portal's own
    ``getDate() + "-" + getMonth(...)`` in odap.js. This is the form the
    priced/on-order search-id enumeration expects for its date window.
    """
    return f"{when.day}-{_MONTHS[when.month - 1]}-{when.year}"


#: How many days each named unit spans, for ``--last`` presets.
_UNIT_DAYS = {
    "day": 1,
    "week": 7,
    "month": 30,
    "year": 365,
}

#: "10 days", "1 week", "2 months", "week", "10d", "2w"...
_LAST_PATTERN = re.compile(
    r"^\s*(\d+)?\s*(day|week|month|year|d|w|m|y)s?\s*$", re.IGNORECASE
)

#: Short single-letter aliases accepted in a ``--last`` value.
_UNIT_ALIASES = {"d": "day", "w": "week", "m": "month", "y": "year"}


def parse_last(preset: str) -> timedelta:
    """Turn a ``--last`` preset into a lookback window.

    Accepts things like ``"10 days"``, ``"1 week"``, ``"2 months"``, or
    the shorthand ``"10d"`` / ``"2w"``. A bare unit (``"week"``) means one
    of that unit.

    Raises:
        ValueError: if the preset doesn't parse, so a typo surfaces
            loudly instead of silently defaulting to some window.
    """
    match = _LAST_PATTERN.match(preset)
    if not match:
        raise ValueError(
            f"Could not read '{preset}'. Try '10 days', '2 weeks', or '1 month'."
        )
    count = int(match.group(1)) if match.group(1) else 1
    unit = match.group(2).lower()
    unit = _UNIT_ALIASES.get(unit, unit)
    return timedelta(days=count * _UNIT_DAYS[unit])


def resolve_cart_dates(
    since: datetime | None = None,
    until: datetime | None = None,
    last: str | None = None,
    today: datetime | None = None,
) -> list[datetime]:
    """Work out which cart dates to read, newest first.

    The portal files cart items by the date they were added, and only
    lets you read one date at a time. Reading a span therefore means
    reading each day in it. The window is chosen like this:

    - ``last`` (e.g. ``"1 week"``): from that far back up to ``until`` (or
      today);
    - ``since``/``until``: an explicit span, either end optional;
    - nothing set: just today.

    "Today" means the current date in IST (:func:`ist_now`), matching the
    date the portal itself files new cart items under, not the caller's
    local time zone.

    ``today`` is injectable so the logic can be tested without depending
    on the clock.

    Raises:
        ValueError: if ``since`` is after ``until``.
    """
    today = today or ist_now()
    end = until or today

    if last is not None:
        start = end - parse_last(last)
    elif since is not None:
        start = since
    else:
        # Nothing asked for: today only.
        return [_midnight(end)]

    start = _midnight(start)
    end = _midnight(end)
    if start > end:
        raise ValueError("The start of the range is after its end.")

    days = (end - start).days
    return [end - timedelta(days=offset) for offset in range(days + 1)]


def _midnight(when: datetime) -> datetime:
    """Drop the time part so date arithmetic lands on whole days."""
    return datetime(when.year, when.month, when.day)


def parse_srt_date(srt: str | None) -> datetime | None:
    """Pull the add-date out of a search id.

    A search id looks like ``20260810_EFM013660`` — the leading eight
    digits are the date it was created (which is when its scenes were
    added to the priced/on-order cart). Returns None if the id doesn't
    start with a readable date.
    """
    match = re.match(r"(\d{8})", srt or "")
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%d")
    except ValueError:
        return None


def build_add_payload(scene: dict, user_id: str) -> tuple[CartKind, dict]:
    """Build the add-to-cart request body appropriate to the scene's cart.

    Returns the resolved :class:`CartKind` alongside the (un-encoded)
    payload, so callers know which servlet to post it to.

    ``queryType`` is taken from the scene's own ``TABLETYPE`` rather than
    being fixed per endpoint — priced CartoSat-3 scenes carry
    ``TABLETYPE="SMETA"``, so pinning it per cart sends malformed bodies.

    The scene is enriched first: the portal derives SAT_SPEC/SCENE_SPEC
    client-side and sends *those* in ``selProds``. Omitting them still
    gets a SUCCESS from the servlet, but leaves a cart record the portal's
    own UI cannot render — see :mod:`.scene_spec`.
    """
    kind = cart_kind_for(scene)
    action = CART_ENDPOINTS[kind]["add"]
    scene = make_interface_obj(scene)

    if kind is CartKind.DIRECT:
        # CartServlet uses PROD_ID rather than sceneID, and takes no queryType.
        return kind, {
            "dop": scene["DOP"],
            "PROD_ID": scene["ID"],
            # The portal defaults this to "N" and only promotes it to "Y"
            # for a current scene; defaulting to "Y" would mark unavailable
            # products as ready.
            "PROD_AV": "Y" if scene.get("CURR_SCENE_NO") == "Y" else "N",
            "srt": scene["srt"],
            "selProds": compact_json(scene),
            "action": action,
            "userId": user_id,
        }

    # SAT_SPEC is present on cart records but absent from fresh search
    # results, where SELECTION carries the same satellite/sensor string.
    return kind, {
        "sceneID": scene["ID"],
        "srt": scene["srt"],
        "queryType": scene["TABLETYPE"],
        "action": action,
        "userId": user_id,
        "selProds": compact_json(scene),
        "selOtherProds": "NA",
        "selSats": scene.get("SAT_SPEC") or scene.get("SELECTION", ""),
        "prod": "Standard",
    }


def build_delete_payload(
    scene: dict, user_id: str, when: datetime
) -> tuple[CartKind, dict]:
    """Build the delete request body appropriate to the scene's cart.

    The direct-download cart deletes by ``prodId`` + ``cartDate``; the
    other two delete by ``sceneID`` + ``srt``.
    """
    kind = cart_kind_for(scene)

    if kind is CartKind.DIRECT:
        return kind, {
            "prodId": scene["ID"],
            "action": "DELETE",
            "userId": user_id,
            "cartDate": cart_date_long(when),
        }

    return kind, {
        "sceneID": scene["ID"],
        "srt": scene["srt"],
        "action": "DELETE",
        "userId": user_id,
    }
