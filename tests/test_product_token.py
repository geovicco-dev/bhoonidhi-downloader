"""Tests for product_token/sat_value: the shared logic behind the archive's
Product/--sat-value columns and the search resolver's SAT:SEN:PROD matching.

Pure string functions — no network. Round-trip correctness against the
live portal (every real dispName the archive currently returns) is
exercised manually, not in CI, since it requires a live fetch.
"""

from bhoonidhi_downloader.schemas.selection import product_token, sat_value


def test_product_token_strips_known_prefix():
    assert (
        product_token("EOS-06_OCM(GAC)_L2C-Chlorophyll", "EOS-06", "OCM(GAC)")
        == "L2C-Chlorophyll"
    )


def test_product_token_empty_for_bare_dispname():
    assert product_token("ResourceSat-2A_AWIFS", "ResourceSat-2A", "AWIFS") == ""


def test_product_token_preserves_internal_underscores():
    # The product token itself can contain underscores, so the split must
    # be a prefix-strip, not a split-on-underscore.
    assert product_token("JPSS1_VIIRS_Imagery_L1", "JPSS1", "VIIRS") == "Imagery_L1"


def test_product_token_no_match_returns_empty():
    # dispName that doesn't even start with satellite_sensor_ at all.
    assert product_token("SomethingElse", "EOS-06", "OCM(GAC)") == ""


def test_sat_value_with_product():
    assert (
        sat_value("EOS-06", "OCM(GAC)", "L2C-Chlorophyll")
        == "EOS-06:OCM(GAC):L2C-Chlorophyll"
    )


def test_sat_value_without_product_stops_at_sensor():
    assert sat_value("ResourceSat-2A", "AWIFS", "") == "ResourceSat-2A:AWIFS"
