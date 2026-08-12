"""Tests for the cart-date range resolver used by 'bhd cart list'.

The direct-download cart is filed by add-date and read one date at a
time, so listing a span means resolving the window into a list of days.
These are pure-function tests with an injected 'today'.
"""

from datetime import datetime, timedelta

import pytest

from bhoonidhi_downloader.core.cart.utils import (
    cart_date_short,
    parse_last,
    parse_srt_date,
    resolve_cart_dates,
)

TODAY = datetime(2026, 8, 12, 15, 30)  # a fixed 'now', with a time part


# --------------------------------------------------------------------------
# parse_srt_date — the add-date lives in the leading digits of a search id
# --------------------------------------------------------------------------


def test_parse_srt_date_reads_leading_yyyymmdd():
    assert parse_srt_date("20260810_EFM013660") == datetime(2026, 8, 10)


@pytest.mark.parametrize("bad", ["", None, "EFM013660", "2026_EFM", "99999999_X"])
def test_parse_srt_date_returns_none_when_unreadable(bad):
    assert parse_srt_date(bad) is None



# --------------------------------------------------------------------------
# cart_date_short — the D-MON-YYYY form GETSRT_IDS wants
# --------------------------------------------------------------------------


def test_cart_date_short_is_unpadded_day_uppercase_month():
    assert cart_date_short(datetime(2026, 8, 5)) == "5-AUG-2026"
    assert cart_date_short(datetime(2026, 8, 12)) == "12-AUG-2026"
    assert cart_date_short(datetime(2026, 1, 1)) == "1-JAN-2026"



# --------------------------------------------------------------------------
# --last presets
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("preset", "days"),
    [
        ("10 days", 10),
        ("1 week", 7),
        ("2 weeks", 14),
        ("1 month", 30),
        ("1 year", 365),
        ("week", 7),  # bare unit means one
        ("10d", 10),  # shorthand
        ("2w", 14),
        ("3M", 90),  # case-insensitive
    ],
)
def test_parse_last_windows(preset, days):
    assert parse_last(preset) == timedelta(days=days)


@pytest.mark.parametrize("bad", ["", "soon", "10 fortnights", "abc days"])
def test_parse_last_rejects_garbage(bad):
    with pytest.raises(ValueError, match="Could not read"):
        parse_last(bad)


# --------------------------------------------------------------------------
# resolve_cart_dates
# --------------------------------------------------------------------------


def test_no_options_is_today_only():
    dates = resolve_cart_dates(today=TODAY)
    assert dates == [datetime(2026, 8, 12)]


def test_last_spans_from_that_far_back_up_to_today_newest_first():
    dates = resolve_cart_dates(last="3 days", today=TODAY)
    assert dates == [
        datetime(2026, 8, 12),
        datetime(2026, 8, 11),
        datetime(2026, 8, 10),
        datetime(2026, 8, 9),
    ]


def test_explicit_since_until_span_is_inclusive():
    dates = resolve_cart_dates(
        since=datetime(2026, 8, 10),
        until=datetime(2026, 8, 12),
        today=TODAY,
    )
    assert dates == [
        datetime(2026, 8, 12),
        datetime(2026, 8, 11),
        datetime(2026, 8, 10),
    ]


def test_since_alone_runs_up_to_today():
    dates = resolve_cart_dates(since=datetime(2026, 8, 11), today=TODAY)
    assert dates == [datetime(2026, 8, 12), datetime(2026, 8, 11)]


def test_until_alone_with_last_ends_on_until_not_today():
    dates = resolve_cart_dates(
        last="2 days", until=datetime(2026, 8, 10), today=TODAY
    )
    assert dates == [
        datetime(2026, 8, 10),
        datetime(2026, 8, 9),
        datetime(2026, 8, 8),
    ]


def test_same_day_span_is_a_single_date():
    dates = resolve_cart_dates(
        since=datetime(2026, 8, 12), until=datetime(2026, 8, 12), today=TODAY
    )
    assert dates == [datetime(2026, 8, 12)]


def test_start_after_end_raises():
    with pytest.raises(ValueError, match="start of the range is after"):
        resolve_cart_dates(
            since=datetime(2026, 8, 15), until=datetime(2026, 8, 12), today=TODAY
        )


def test_time_of_day_is_dropped():
    """A 'today' with a time part still yields whole-day midnights."""
    dates = resolve_cart_dates(last="1 day", today=TODAY)
    assert all(d.hour == 0 and d.minute == 0 for d in dates)
