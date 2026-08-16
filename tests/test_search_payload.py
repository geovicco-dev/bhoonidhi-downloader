"""Tests for the search request payload builder and selection resolver.

create_payload() shapes the portal's search request from a config object
holding a list of selections plus the archive manifest.
resolve_selections() maps those selections to the raw dispNames the portal
searches on, warning-and-skipping invalid ones. Pure functions — no network.
"""

from datetime import datetime
from types import SimpleNamespace

import pytest

from bhoonidhi_downloader.core.search.utils import (
    create_payload,
    resolve_selections,
)
from bhoonidhi_downloader.exceptions import BhoonidhiValidationError
from bhoonidhi_downloader.schemas.selection import Selection


def _cfg(selections: list[Selection]) -> SimpleNamespace:
    """A minimal stand-in for SearchSchema with just the fields
    create_payload reads."""
    return SimpleNamespace(
        selections=selections,
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 1, 31),
        aoi=SimpleNamespace(
            mode="bbox", max_lat=25.7, min_lon=91.8, min_lat=25.5, max_lon=92.0
        ),
    )


# A manifest with an open data window (2020 → ongoing) so the default
# 2026 search window in _cfg always validates.
MANIFEST = {
    "ResourceSat-2A": {
        "LISS3": [
            {"dispName": "ResourceSat-2A_LISS3", "startDate": "01/01/2020"},
            {"dispName": "ResourceSat-2A_LISS3_L2", "startDate": "01/01/2020"},
        ],
        "AWIFS": [{"dispName": "ResourceSat-2A_AWIFS", "startDate": "01/01/2020"}],
    },
    "CartoSat-3": {
        "PAN": [{"dispName": "CartoSat-3_PAN", "startDate": "01/01/2020"}],
    },
    "EOS-06": {
        "OCM(GAC)": [
            {"dispName": "EOS-06_OCM(GAC)_L1C", "startDate": "01/01/2020"},
            {
                "dispName": "EOS-06_OCM(GAC)_L2C-Chlorophyll",
                "startDate": "01/01/2020",
            },
            {"dispName": "EOS-06_OCM(GAC)_L2C-NDVI", "startDate": "01/01/2020"},
        ],
    },
}


# ── resolve_selections ────────────────────────────────────────────────


def test_satellite_only_resolves_every_sensor():
    disp = resolve_selections(
        [Selection(satellite="ResourceSat-2A")],
        MANIFEST,
        datetime(2026, 1, 1),
        datetime(2026, 1, 31),
    )
    assert "ResourceSat-2A_LISS3" in disp
    assert "ResourceSat-2A_AWIFS" in disp


def test_sensor_narrows_to_that_sensor():
    disp = resolve_selections(
        [Selection(satellite="ResourceSat-2A", sensor="LISS3")],
        MANIFEST,
        datetime(2026, 1, 1),
        datetime(2026, 1, 31),
    )
    assert disp == ["ResourceSat-2A_LISS3", "ResourceSat-2A_LISS3_L2"]
    assert all("AWIFS" not in d for d in disp)


def test_product_narrows_to_one_dispname():
    disp = resolve_selections(
        [Selection(satellite="EOS-06", sensor="OCM(GAC)", product="L2C-Chlorophyll")],
        MANIFEST,
        datetime(2026, 1, 1),
        datetime(2026, 1, 31),
    )
    assert disp == ["EOS-06_OCM(GAC)_L2C-Chlorophyll"]


def test_product_with_implied_sensor():
    disp = resolve_selections(
        [Selection(satellite="EOS-06", product="L2C-NDVI")],
        MANIFEST,
        datetime(2026, 1, 1),
        datetime(2026, 1, 31),
    )
    assert disp == ["EOS-06_OCM(GAC)_L2C-NDVI"]


def test_multi_mission_flattens_across_satellites():
    disp = resolve_selections(
        [
            Selection(satellite="ResourceSat-2A", sensor="LISS3"),
            Selection(satellite="CartoSat-3"),
        ],
        MANIFEST,
        datetime(2026, 1, 1),
        datetime(2026, 1, 31),
    )
    assert "ResourceSat-2A_LISS3" in disp
    assert "CartoSat-3_PAN" in disp


def test_invalid_selection_is_skipped_not_fatal():
    # One bad product, one good satellite — the good one survives.
    disp = resolve_selections(
        [
            Selection(satellite="EOS-06", sensor="OCM(GAC)", product="Nonexistent"),
            Selection(satellite="CartoSat-3"),
        ],
        MANIFEST,
        datetime(2026, 1, 1),
        datetime(2026, 1, 31),
    )
    assert disp == ["CartoSat-3_PAN"]


def test_all_invalid_selections_raises():
    with pytest.raises(BhoonidhiValidationError, match="No valid selections"):
        resolve_selections(
            [Selection(satellite="NoSuchSat")],
            MANIFEST,
            datetime(2026, 1, 1),
            datetime(2026, 1, 31),
        )


def test_duplicate_dispnames_deduped():
    disp = resolve_selections(
        [
            Selection(satellite="CartoSat-3"),
            Selection(satellite="CartoSat-3", sensor="PAN"),
        ],
        MANIFEST,
        datetime(2026, 1, 1),
        datetime(2026, 1, 31),
    )
    assert disp == ["CartoSat-3_PAN"]


# ── create_payload ────────────────────────────────────────────────────


def test_payload_joins_multiple_dispnames_with_encoded_comma():
    payload = create_payload(
        _cfg([Selection(satellite="ResourceSat-2A", sensor="LISS3")]), MANIFEST
    )
    assert payload["selSats"] == "ResourceSat-2A_LISS3%2CResourceSat-2A_LISS3_L2"


def test_payload_single_dispname_no_comma():
    payload = create_payload(_cfg([Selection(satellite="CartoSat-3")]), MANIFEST)
    assert payload["selSats"] == "CartoSat-3_PAN"
