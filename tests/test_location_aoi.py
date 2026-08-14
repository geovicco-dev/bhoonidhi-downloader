"""Tests for location-mode AOI: a point + radius as an alternative to a
bounding box.

Covers AOISchema/SearchSchema validation, the search payload builder, and
_build_aoi()'s mode selection in run_query_create().
"""

from datetime import datetime

import pytest

from bhoonidhi_downloader.core.query.command import _build_aoi
from bhoonidhi_downloader.core.search.utils import create_payload
from bhoonidhi_downloader.exceptions import BhoonidhiValidationError
from bhoonidhi_downloader.schemas import AOISchema, SearchSchema

# --------------------------------------------------------------------------
# SearchSchema validation — location mode
# --------------------------------------------------------------------------


def _location_aoi(**overrides) -> AOISchema:
    base = {"mode": "location", "lat": 17.385, "lon": 78.4867, "radius_km": 10.0}
    base.update(overrides)
    return AOISchema(**base)


def test_valid_location_aoi_passes_validation():
    SearchSchema(
        aoi=_location_aoi(),
        satellite="ResourceSat-2A",
        sensor="LISS3",
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 1, 31),
    )


def test_location_aoi_missing_lat_or_lon_is_rejected():
    with pytest.raises(ValueError, match="requires both lat and lon"):
        SearchSchema(
            aoi=_location_aoi(lon=None),
            satellite="ResourceSat-2A",
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )


def test_location_aoi_lat_out_of_range_is_rejected():
    with pytest.raises(ValueError, match=r"lat \(95.0\)"):
        SearchSchema(
            aoi=_location_aoi(lat=95.0),
            satellite="ResourceSat-2A",
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )


def test_location_aoi_radius_below_one_is_rejected():
    with pytest.raises(ValueError, match="between 1 and 100"):
        SearchSchema(
            aoi=_location_aoi(radius_km=0.5),
            satellite="ResourceSat-2A",
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )


def test_location_aoi_radius_above_hundred_is_rejected():
    with pytest.raises(ValueError, match="between 1 and 100"):
        SearchSchema(
            aoi=_location_aoi(radius_km=150.0),
            satellite="ResourceSat-2A",
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 31),
        )


def test_location_aoi_radius_defaults_to_ten_when_unset():
    """radius_km=None is allowed on the schema — the default of 10 applies
    at validation and payload-building time, not as a required field."""
    SearchSchema(
        aoi=_location_aoi(radius_km=None),
        satellite="ResourceSat-2A",
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 1, 31),
    )


# --------------------------------------------------------------------------
# create_payload() — location mode builds queryType=location, not polygon
# --------------------------------------------------------------------------

MANIFEST = {"ResourceSat-2A": {"LISS3": [{"dispName": "ResourceSat-2A LISS3"}]}}


def _cfg(aoi: AOISchema):
    from types import SimpleNamespace

    return SimpleNamespace(
        satellite="ResourceSat-2A",
        sensor="LISS3",
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 1, 31),
        aoi=aoi,
    )


def test_location_mode_payload_has_queryType_location():
    payload = create_payload(_cfg(_location_aoi()), MANIFEST)
    assert payload["queryType"] == "location"
    assert payload["lat"] == 17.385
    assert payload["lon"] == 78.4867
    assert payload["radius"] == 10.0
    assert "tllat" not in payload
    assert "tllon" not in payload


def test_location_mode_payload_defaults_radius_to_ten():
    payload = create_payload(_cfg(_location_aoi(radius_km=None)), MANIFEST)
    assert payload["radius"] == 10.0


def test_bbox_mode_payload_unchanged():
    bbox_aoi = AOISchema(mode="bbox", min_lon=60, min_lat=0, max_lon=100, max_lat=40)
    payload = create_payload(_cfg(bbox_aoi), MANIFEST)
    assert payload["queryType"] == "polygon"
    assert payload["tllat"] == 40
    assert payload["tllon"] == 60
    assert payload["brlat"] == 0
    assert payload["brlon"] == 100
    assert "lat" not in payload
    assert "radius" not in payload


# --------------------------------------------------------------------------
# _build_aoi() — exactly one AOI mode required
# --------------------------------------------------------------------------


def test_build_aoi_with_bbox_only():
    aoi = _build_aoi(60, 100, 0, 40, None, None, None)
    assert aoi.mode == "bbox"
    assert aoi.min_lon == 60
    assert aoi.max_lat == 40


def test_build_aoi_with_location_only():
    aoi = _build_aoi(None, None, None, None, 17.385, 78.4867, 10.0)
    assert aoi.mode == "location"
    assert aoi.lat == 17.385
    assert aoi.radius_km == 10.0


def test_build_aoi_with_both_raises():
    with pytest.raises(BhoonidhiValidationError, match="not both"):
        _build_aoi(60, 100, 0, 40, 17.385, 78.4867, 10.0)


def test_build_aoi_with_neither_raises():
    with pytest.raises(BhoonidhiValidationError, match="Give either"):
        _build_aoi(None, None, None, None, None, None, None)


def test_build_aoi_with_partial_bbox_raises():
    """A partial bbox (e.g. only minx/maxx, no miny/maxy) doesn't count as
    a complete bbox — falls through to the neither-given error."""
    with pytest.raises(BhoonidhiValidationError, match="Give either"):
        _build_aoi(60, 100, None, None, None, None, None)
