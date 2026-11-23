"""Selecting one product: ``Others``, unlisted products, the saved list's age.

Pure functions against a fixed product list; the portal is never called.
"""

import io
import os
import time
from datetime import datetime

import pytest
from rich.console import Console

from bhoonidhi_downloader.core.archive import client as archive_client
from bhoonidhi_downloader.core.archive.client import ArchiveManager
from bhoonidhi_downloader.core.archive.render import _satellite_columns
from bhoonidhi_downloader.core.search import utils
from bhoonidhi_downloader.core.search.utils import resolve_selections
from bhoonidhi_downloader.exceptions import BhoonidhiAPIError, BhoonidhiValidationError
from bhoonidhi_downloader.schemas.selection import Selection

START, END = datetime(2026, 1, 1), datetime(2026, 1, 31)


def _row(disp: str, product: str = "Level-2") -> dict:
    return {"dispName": disp, "product": product, "startDate": "01/01/2020"}


MANIFEST = {
    "ResourceSat-2": {
        "AWIFS": [
            _row("ResourceSat-2_AWIFS_L2"),
            _row("ResourceSat-2_AWIFS_BOA-Archives"),
            _row("ResourceSat-2_AWIFS", "Others"),
        ],
        "LISS4": [_row("ResourceSat-2_LISS4", "Others")],
    },
    "IRS-1A": {"LISS1": [_row("IRS-1A_LISS1_L2")]},
}


@pytest.fixture
def out(monkeypatch) -> io.StringIO:
    """Capture warnings as plain text, without colour or line wrapping."""
    buf = io.StringIO()

    def console() -> Console:
        return Console(file=buf, width=400, color_system=None, highlight=False)

    monkeypatch.setattr(utils, "get_console", console)
    monkeypatch.setattr(archive_client, "get_console", console)
    return buf


def _resolve(selection: Selection, manifest=MANIFEST, refresh=None) -> list[str]:
    return resolve_selections([selection], manifest, START, END, refresh=refresh)


def test_others_selects_only_the_suffixless_product():
    sel = Selection(satellite="ResourceSat-2", sensor="AWIFS", product="Others")
    assert _resolve(sel) == ["ResourceSat-2_AWIFS"]


def test_others_is_case_insensitive():
    sel = Selection(satellite="ResourceSat-2", sensor="AWIFS", product="others")
    assert _resolve(sel) == ["ResourceSat-2_AWIFS"]


def test_others_works_for_a_sensor_with_one_product():
    sel = Selection(satellite="ResourceSat-2", sensor="LISS4", product="Others")
    assert _resolve(sel) == ["ResourceSat-2_LISS4"]


def test_a_suffix_named_others_wins():
    manifest = {"X-1": {"S": [_row("X-1_S"), _row("X-1_S_Others")]}}
    sel = Selection(satellite="X-1", sensor="S", product="Others")
    assert _resolve(sel, manifest) == ["X-1_S_Others"]


def test_sensor_alone_still_selects_every_product():
    sel = Selection(satellite="ResourceSat-2", sensor="AWIFS")
    assert len(_resolve(sel)) == 3


def test_listed_product_never_reads_the_portal():
    def refresh():
        raise AssertionError("the portal must not be read")

    sel = Selection(satellite="ResourceSat-2", sensor="AWIFS", product="L2")
    assert _resolve(sel, refresh=refresh) == ["ResourceSat-2_AWIFS_L2"]


def test_missing_product_found_after_one_fresh_read(out):
    fresh = {
        "IRS-1A": {"LISS1": [*MANIFEST["IRS-1A"]["LISS1"], _row("IRS-1A_LISS1_L3")]}
    }
    calls = []

    def refresh():
        calls.append(1)
        return fresh

    sels = [
        Selection(satellite="IRS-1A", sensor="LISS1", product="L3"),
        Selection(satellite="IRS-1A", sensor="LISS1", product="L4"),
    ]
    disp = resolve_selections(sels, MANIFEST, START, END, refresh=refresh)
    assert disp == ["IRS-1A_LISS1_L3", "IRS-1A_LISS1_L4"]
    assert len(calls) == 1
    assert "L3 is not" not in out.getvalue()


def test_unlisted_others_is_searched_under_the_bare_name(out):
    sel = Selection(satellite="IRS-1A", sensor="LISS1", product="Others")
    assert _resolve(sel, refresh=lambda: MANIFEST) == ["IRS-1A_LISS1"]
    assert out.getvalue().strip() == (
        "! IRS-1A LISS1 Others is not in the portal's product list (listed: L2)."
    )


def test_unlisted_named_product_is_searched_with_its_suffix(out):
    sel = Selection(satellite="ResourceSat-2", sensor="AWIFS", product="L9")
    assert _resolve(sel) == ["ResourceSat-2_AWIFS_L9"]
    assert out.getvalue().strip() == (
        "! ResourceSat-2 AWIFS L9 is not in the portal's product list "
        "(listed: BOA-Archives, L2, Others)."
    )


def test_unlisted_product_skips_the_date_check(out):
    # The product list has no dates for a product it doesn't hold.
    sel = Selection(satellite="IRS-1A", sensor="LISS1", product="Others")
    disp = resolve_selections(
        [sel], MANIFEST, datetime(1991, 5, 13), datetime(1991, 5, 15)
    )
    assert disp == ["IRS-1A_LISS1"]


def test_portal_down_keeps_the_saved_list(out):
    def refresh():
        raise BhoonidhiAPIError("down")

    sel = Selection(satellite="IRS-1A", sensor="LISS1", product="Others")
    assert _resolve(sel, refresh=refresh) == ["IRS-1A_LISS1"]


def test_product_without_sensor_is_still_skipped(out):
    sel = Selection(satellite="IRS-1A", product="L9")
    with pytest.raises(BhoonidhiValidationError, match="No valid selections"):
        _resolve(sel)
    assert "no such product" in out.getvalue()


def test_unknown_sensor_is_still_skipped(out):
    sel = Selection(satellite="IRS-1A", sensor="LISS9", product="Others")
    with pytest.raises(BhoonidhiValidationError):
        _resolve(sel)
    assert "unknown sensor" in out.getvalue()


def test_create_payload_reads_the_portal_on_a_miss(monkeypatch, out):
    calls = []

    def fresh():
        calls.append(1)
        return MANIFEST

    monkeypatch.setattr(utils, "_fresh_manifest", fresh)
    cfg = type(
        "Cfg",
        (),
        {
            "selections": [
                Selection(satellite="IRS-1A", sensor="LISS1", product="Others")
            ],
            "start_date": START,
            "end_date": END,
            "aoi": type(
                "Aoi",
                (),
                {
                    "mode": "bbox",
                    "max_lat": 1,
                    "min_lon": 0,
                    "min_lat": 0,
                    "max_lon": 1,
                },
            )(),
        },
    )()
    payload = utils.create_payload(cfg, MANIFEST)
    assert payload["selSats"] == "IRS-1A_LISS1"
    assert calls == [1]


# --- the saved list's age ---------------------------------------------------


@pytest.fixture
def saved_list(tmp_path, monkeypatch):
    archive = tmp_path / "archive.json"
    archive.write_text("[]")
    monkeypatch.setattr(archive_client, "ARCHIVE_PATH", archive)
    monkeypatch.setattr(archive_client, "MANIFEST_PATH", tmp_path / "manifest.json")
    monkeypatch.setattr(archive_client, "_stale_notice_shown", False)

    def age(days: float) -> None:
        then = time.time() - days * 86400
        os.utime(archive, (then, then))

    return age


def test_week_old_list_gets_no_notice(saved_list, out):
    saved_list(6.5)
    ArchiveManager()
    assert out.getvalue() == ""


def test_old_list_gets_one_notice(saved_list, out):
    saved_list(54.2)
    ArchiveManager()
    ArchiveManager()
    assert out.getvalue().strip() == (
        "! The product list was saved 54 days ago. "
        "Run bhd archive list --refresh to update it."
    )


# --- the exact --sat value per product row ----------------------------------

ARCHIVE = [
    {
        "satName": "ResourceSat-2",
        "sensors": [
            {"senName": "AWIFS", "dispName": "ResourceSat-2_AWIFS_L2"},
            {"senName": "AWIFS", "dispName": "ResourceSat-2_AWIFS"},
            {"senName": "LISS4", "dispName": "ResourceSat-2_LISS4"},
        ],
    }
]


def test_formatted_archive_names_the_shared_bare_product_others():
    values = {
        disp: info["sat_value"]
        for col in ArchiveManager.format_archive(ARCHIVE)[0]["collections"]
        for disp, info in col.items()
    }
    assert values == {
        "ResourceSat-2_AWIFS_L2": "ResourceSat-2:AWIFS:L2",
        "ResourceSat-2_AWIFS": "ResourceSat-2:AWIFS:Others",
        "ResourceSat-2_LISS4": "ResourceSat-2:LISS4",
    }


def test_archive_list_prints_others_for_the_shared_bare_product():
    from bhoonidhi_downloader.core.archive.render import _annotate_ambiguous_defaults

    rows = [{"satName": "ResourceSat-2", **s} for s in ARCHIVE[0]["sensors"]]
    sat_flag = next(c for c in _satellite_columns() if c.header == "--sat value")
    printed = [sat_flag.render(r, 0) for r in _annotate_ambiguous_defaults(rows)]
    assert printed == [
        "ResourceSat-2:AWIFS:L2",
        "ResourceSat-2:AWIFS:Others",
        "ResourceSat-2:LISS4",
    ]
