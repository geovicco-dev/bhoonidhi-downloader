"""Tests for the search request payload builder.

create_payload() shapes the portal's search request from a SearchSchema
and the archive manifest. These are pure-function tests — no network.
"""

from datetime import datetime
from types import SimpleNamespace

from bhoonidhi_downloader.core.search.utils import create_payload


def _cfg(satellite: str, sensor: str | None) -> SimpleNamespace:
    """A minimal stand-in for SearchSchema with just the fields
    create_payload reads."""
    return SimpleNamespace(
        satellite=satellite,
        sensor=sensor,
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 1, 31),
        aoi=SimpleNamespace(
            mode="bbox", max_lat=25.7, min_lon=91.8, min_lat=25.5, max_lon=92.0
        ),
    )


MANIFEST = {
    "ResourceSat-2A": {
        "LISS3": [{"dispName": "ResourceSat-2A LISS3"}],
        "AWIFS": [{"dispName": "ResourceSat-2A AWIFS"}],
    }
}


# --------------------------------------------------------------------------
# No sensor given: search every sensor under the satellite instead of
# raising. This was previously a bare `assert cfg.sensor is not None`,
# which surfaced to users as an opaque "Search failed" error.
# --------------------------------------------------------------------------


def test_missing_sensor_searches_every_sensor_under_the_satellite():
    payload = create_payload(_cfg("ResourceSat-2A", None), MANIFEST)
    # Both sensors' dispNames should be present (whitespace stripped, as
    # create_payload does for every dispName), comma-joined.
    assert "ResourceSat-2ALISS3" in payload["selSats"]
    assert "ResourceSat-2AAWIFS" in payload["selSats"]


def test_given_sensor_searches_only_that_sensor():
    payload = create_payload(_cfg("ResourceSat-2A", "LISS3"), MANIFEST)
    assert payload["selSats"] == "ResourceSat-2ALISS3"
    assert "AWIFS" not in payload["selSats"]


def test_missing_sensor_with_a_single_sensor_satellite_still_works():
    single = {"CartoSat-3": {"PAN": [{"dispName": "CartoSat-3 PAN"}]}}
    payload = create_payload(_cfg("CartoSat-3", None), single)
    assert payload["selSats"] == "CartoSat-3PAN"
