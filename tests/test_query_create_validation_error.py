"""Tests for bug #26: invalid --sat/--sen leaked a raw pydantic traceback.

run_query_create() builds a SearchSchema, whose model validator raises a
plain ValueError on a bad satellite/sensor. Pydantic wraps that in its own
ValidationError, which is not a BhoonidhiError, so it slipped past the
CLI's `except BhoonidhiError` handler and dumped an unreadable pydantic
traceback straight to the terminal instead of a clean message.
"""

from datetime import datetime

import pytest

from bhoonidhi_downloader.core.query.command import run_query_create
from bhoonidhi_downloader.exceptions import BhoonidhiValidationError


def _dates():
    return datetime(2026, 8, 1), datetime(2026, 8, 5)


def test_invalid_satellite_raises_bhoonidhi_validation_error_not_pydantic():
    start, end = _dates()
    with pytest.raises(BhoonidhiValidationError) as exc_info:
        run_query_create(
            minx=68,
            maxx=98,
            miny=6,
            maxy=38,
            start_date=start,
            end_date=end,
            satellite="Sentinel",  # not a real satellite name (real ones are e.g. Sentinel-1A)
            sensor="ad",
        )
    # The message should read like plain English, not a pydantic dump.
    assert "Invalid satellite 'Sentinel'" in str(exc_info.value)
    assert "pydantic" not in str(exc_info.value).lower()


def test_invalid_sensor_for_valid_satellite_raises_bhoonidhi_validation_error():
    start, end = _dates()
    with pytest.raises(BhoonidhiValidationError) as exc_info:
        run_query_create(
            minx=68,
            maxx=98,
            miny=6,
            maxy=38,
            start_date=start,
            end_date=end,
            satellite="Sentinel-2A",
            sensor="not-a-real-sensor",
        )
    assert "Invalid sensor 'not-a-real-sensor'" in str(exc_info.value)
