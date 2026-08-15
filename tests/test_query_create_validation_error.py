"""Tests for bug #26: an all-invalid search leaked a raw pydantic traceback.

A search with no usable selection must surface a clean, typed
``BhoonidhiValidationError`` — not a pydantic ``ValidationError`` dump or a
bare ``AssertionError``. Invalid selections are warned-and-skipped by the
resolver; only when every selection drops does the search fail, and it must
fail cleanly.
"""

from datetime import datetime

import pytest

from bhoonidhi_downloader.core.query.command import run_query_create
from bhoonidhi_downloader.exceptions import BhoonidhiValidationError
from bhoonidhi_downloader.schemas import Selection


def _dates():
    return datetime(2026, 8, 1), datetime(2026, 8, 5)


def test_all_invalid_selections_raise_bhoonidhi_validation_error_not_pydantic():
    start, end = _dates()
    with pytest.raises(BhoonidhiValidationError) as exc_info:
        run_query_create(
            minx=68,
            maxx=98,
            miny=6,
            maxy=38,
            start_date=start,
            end_date=end,
            # Not a real satellite name (real ones are e.g. Sentinel-1A).
            selections=[Selection(satellite="Sentinel")],
        )
    # The message should read like plain English, not a pydantic dump.
    assert "No valid selections" in str(exc_info.value)
    assert "pydantic" not in str(exc_info.value).lower()


def test_invalid_sensor_for_valid_satellite_raises_when_only_selection():
    start, end = _dates()
    with pytest.raises(BhoonidhiValidationError) as exc_info:
        run_query_create(
            minx=68,
            maxx=98,
            miny=6,
            maxy=38,
            start_date=start,
            end_date=end,
            selections=[Selection(satellite="Sentinel-2A", sensor="not-a-real-sensor")],
        )
    assert "No valid selections" in str(exc_info.value)
