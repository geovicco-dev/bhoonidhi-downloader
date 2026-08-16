"""Tests for the ``--sat SAT[:SEN[:PROD]]`` token parser.

Pure string parsing — no manifest, no network. Manifest resolution
(is field-2 a sensor or a product, does it exist) is tested separately
against ``resolve_selections``.
"""

import pytest

from bhoonidhi_downloader.exceptions import BhoonidhiValidationError
from bhoonidhi_downloader.schemas.selection import (
    parse_sat_token,
    parse_sat_tokens,
)


def test_satellite_only():
    sel = parse_sat_token("ResourceSat-2A")
    assert (sel.satellite, sel.sensor, sel.product) == ("ResourceSat-2A", None, None)


def test_satellite_and_sensor():
    sel = parse_sat_token("ResourceSat-2A:LISS3")
    assert (sel.satellite, sel.sensor, sel.product) == (
        "ResourceSat-2A",
        "LISS3",
        None,
    )


def test_all_three_levels():
    sel = parse_sat_token("JPSS1:VIIRS:Imagery_L1")
    assert (sel.satellite, sel.sensor, sel.product) == (
        "JPSS1",
        "VIIRS",
        "Imagery_L1",
    )


def test_empty_middle_field_is_product_with_implied_sensor():
    sel = parse_sat_token("EOS-06::L2C-Chlorophyll")
    assert (sel.satellite, sel.sensor, sel.product) == (
        "EOS-06",
        None,
        "L2C-Chlorophyll",
    )


def test_whitespace_is_trimmed():
    sel = parse_sat_token("  EOS-06 : OCM(GAC) ")
    assert (sel.satellite, sel.sensor) == ("EOS-06", "OCM(GAC)")


def test_empty_satellite_rejected():
    with pytest.raises(BhoonidhiValidationError, match="satellite name is empty"):
        parse_sat_token(":LISS3")


def test_too_many_fields_rejected():
    with pytest.raises(BhoonidhiValidationError, match="colon-separated"):
        parse_sat_token("A:B:C:D")


def test_multiple_tokens_parse_independently():
    sels = parse_sat_tokens(["ResourceSat-2A:LISS3", "CartoSat-3:PAN"])
    assert [s.label() for s in sels] == [
        "ResourceSat-2A/LISS3",
        "CartoSat-3/PAN",
    ]


def test_no_tokens_rejected():
    with pytest.raises(BhoonidhiValidationError, match="At least one --sat"):
        parse_sat_tokens([])


def test_legacy_sensor_fills_single_plain_sat():
    sels = parse_sat_tokens(["ResourceSat-2A"], legacy_sensor="LISS3")
    assert (sels[0].satellite, sels[0].sensor) == ("ResourceSat-2A", "LISS3")


def test_legacy_sensor_with_multiple_sats_rejected():
    with pytest.raises(BhoonidhiValidationError, match="single --sat"):
        parse_sat_tokens(["ResourceSat-2A", "CartoSat-3"], legacy_sensor="LISS3")


def test_legacy_sensor_conflicts_with_inline_sensor():
    with pytest.raises(BhoonidhiValidationError, match="already"):
        parse_sat_tokens(["ResourceSat-2A:LISS3"], legacy_sensor="AWIFS")
