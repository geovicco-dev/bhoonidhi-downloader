"""Tests for merging the three portal carts into one view.

These use a fake client so the merge logic (which carts are read, how
rows are tagged and de-duplicated) is exercised without any network.
"""

from datetime import datetime

from bhoonidhi_downloader.core.cart.command import _collect_carts, _kinds_to_read
from bhoonidhi_downloader.core.cart.utils import CartKind


class FakeCartClient:
    """Stand-in for CartClient that returns canned rows per cart."""

    def __init__(self, direct=None, order=None, priced=None, srts=None):
        self._direct = direct or {}  # {date: [rows]}
        self._order = order or []
        self._priced = priced or []
        self._srts = srts or {}  # {CartKind: [srt, ...]}

    def view_direct(self, when):
        return list(self._direct.get(when, []))

    def saved_srts(self, kind, start, end):
        return list(self._srts.get(kind, []))

    def view_by_srt(self, kind, srt):
        return list(self._order if kind is CartKind.ORDER else self._priced)


def test_kinds_to_read_defaults_to_all_three():
    assert _kinds_to_read(None) == [
        CartKind.DIRECT,
        CartKind.ORDER,
        CartKind.PRICED,
    ]


def test_kinds_to_read_honours_a_filter():
    assert _kinds_to_read("priced") == [CartKind.PRICED]


def test_collect_merges_all_three_carts_and_tags_each_row():
    day = datetime(2026, 8, 12)
    client = FakeCartClient(
        direct={day: [{"ID": "D1", "STATUS": "ADDED"}]},
        order=[{"SCENE_ID": "O1"}],
        priced=[{"SCENE_ID": "P1"}],
        srts={CartKind.ORDER: ["20260811_ORD"], CartKind.PRICED: ["20260809_PRI"]},
    )
    rows = _collect_carts(
        client,
        [CartKind.DIRECT, CartKind.ORDER, CartKind.PRICED],
        [day],
    )

    by_cart = {r["_cart"] for r in rows}
    assert by_cart == {CartKind.DIRECT, CartKind.ORDER, CartKind.PRICED}
    # The direct row is tagged with the date it was read under.
    direct = next(r for r in rows if r["_cart"] is CartKind.DIRECT)
    assert direct["_cart_date"] == day
    # The srt-addressed carts take their date from the search id.
    order = next(r for r in rows if r["_cart"] is CartKind.ORDER)
    assert order["_cart_date"] == datetime(2026, 8, 11)
    # SCENE_ID is normalised to ID so the row can be removed like a query scene.
    assert order["ID"] == "O1"
    assert order["srt"] == "20260811_ORD"


def test_collect_dedupes_the_same_scene_across_dates():
    d1, d2 = datetime(2026, 8, 12), datetime(2026, 8, 11)
    client = FakeCartClient(
        direct={
            d1: [{"ID": "D1"}],
            d2: [{"ID": "D1"}],  # same scene under an earlier date
        }
    )
    rows = _collect_carts(client, [CartKind.DIRECT], [d1, d2])
    assert len(rows) == 1
    # Kept the first occurrence, tagged with the newest date read.
    assert rows[0]["_cart_date"] == d1


def test_collect_filtered_to_one_cart_skips_the_others():
    day = datetime(2026, 8, 12)
    client = FakeCartClient(
        direct={day: [{"ID": "D1"}]},
        priced=[{"SCENE_ID": "P1"}],
        srts={CartKind.PRICED: ["srtP"]},
    )
    rows = _collect_carts(client, [CartKind.PRICED], [day])
    assert len(rows) == 1
    assert rows[0]["_cart"] is CartKind.PRICED
