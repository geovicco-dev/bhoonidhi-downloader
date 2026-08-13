"""Tests for the shared --filter option: parse_availability_filter and
cart_availability_of.

parse_availability_filter turns a --filter option's raw values into a set
of Availability states; cart_availability_of applies the same states to a
cart row (which is shaped differently from a fresh search result).
"""

import pytest

from bhoonidhi_downloader.core.cart.utils import CartKind, cart_availability_of
from bhoonidhi_downloader.core.search.availability import (
    Availability,
    parse_availability_filter,
)

# --------------------------------------------------------------------------
# parse_availability_filter
# --------------------------------------------------------------------------


def test_no_values_means_no_filter():
    assert parse_availability_filter(None) is None
    assert parse_availability_filter([]) is None


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("ready", Availability.DIRECT_AVAILABLE),
        ("archived", Availability.DIRECT_UNAVAILABLE),
        ("onorder", Availability.ON_ORDER),
        ("priced", Availability.PRICED),
    ],
)
def test_recognises_each_state_word(word, expected):
    assert parse_availability_filter([word]) == {expected}


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("Ready", Availability.DIRECT_AVAILABLE),
        ("READY", Availability.DIRECT_AVAILABLE),
        ("onOrder", Availability.ON_ORDER),
        ("on-order", Availability.ON_ORDER),
        ("on_order", Availability.ON_ORDER),
    ],
)
def test_case_and_separator_insensitive(word, expected):
    assert parse_availability_filter([word]) == {expected}


def test_comma_separated_values_in_one_flag():
    result = parse_availability_filter(["ready,archived"])
    assert result == {Availability.DIRECT_AVAILABLE, Availability.DIRECT_UNAVAILABLE}


def test_repeated_flag_values_combine():
    result = parse_availability_filter(["ready", "priced"])
    assert result == {Availability.DIRECT_AVAILABLE, Availability.PRICED}


def test_unknown_word_raises_naming_valid_ones():
    with pytest.raises(ValueError, match="Unknown filter 'bogus'"):
        parse_availability_filter(["bogus"])


# --------------------------------------------------------------------------
# cart_availability_of — same states, applied to a cart row's shape
# --------------------------------------------------------------------------


def test_direct_cart_ready_row():
    row = {"_cart": CartKind.DIRECT, "CURR_SCENE_NO": "Y"}
    assert cart_availability_of(row) is Availability.DIRECT_AVAILABLE


def test_direct_cart_archived_row():
    row = {"_cart": CartKind.DIRECT, "CURR_SCENE_NO": "N"}
    assert cart_availability_of(row) is Availability.DIRECT_UNAVAILABLE


def test_order_cart_row_is_always_on_order():
    # An on-order cart row's own CURR_SCENE_NO (if present at all) doesn't
    # matter -- being in that cart is the classification.
    row = {"_cart": CartKind.ORDER, "CURR_SCENE_NO": "Y"}
    assert cart_availability_of(row) is Availability.ON_ORDER


def test_priced_cart_row_is_always_priced():
    row = {"_cart": CartKind.PRICED}
    assert cart_availability_of(row) is Availability.PRICED


def test_untagged_row_falls_back_to_staging():
    # A row with no _cart tag (shouldn't normally happen -- the collector
    # always tags one -- but a missing tag should degrade safely).
    ready = cart_availability_of({"CURR_SCENE_NO": "Y"})
    archived = cart_availability_of({"CURR_SCENE_NO": "N"})
    assert ready is Availability.DIRECT_AVAILABLE
    assert archived is Availability.DIRECT_UNAVAILABLE
