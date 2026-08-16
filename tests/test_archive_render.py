"""Tests for the archive's --sat X view: Product column and --sat value.

_annotate_ambiguous_defaults flags a bare (no-suffix) dispName when a
sibling under the same satellite+sensor DOES have a distinct product
suffix — in that case SAT:SEN alone resolves to every sibling, not just
the bare one, so no single --sat value can isolate it. Confirmed live
against the real archive: ResourceSat-1/2/2A's AWIFS and LISS3 sensors
hit this; most sensors don't.
"""

from bhoonidhi_downloader.core.archive.render import _annotate_ambiguous_defaults


def _row(sat: str, sen: str, disp: str) -> dict:
    return {"satName": sat, "senName": sen, "dispName": disp}


def test_bare_dispname_with_no_siblings_is_not_flagged():
    rows = [_row("CartoSat-3", "PAN(SPOT)", "CartoSat-3_PAN(SPOT)")]
    annotated = _annotate_ambiguous_defaults(rows)
    assert "_sibling_products" not in annotated[0]


def test_bare_dispname_with_suffixed_sibling_is_flagged():
    rows = [
        _row("ResourceSat-1", "AWIFS", "ResourceSat-1_AWIFS"),
        _row("ResourceSat-1", "AWIFS", "ResourceSat-1_AWIFS_1x1deg-tiles"),
    ]
    annotated = _annotate_ambiguous_defaults(rows)
    bare = next(r for r in annotated if r["dispName"] == "ResourceSat-1_AWIFS")
    suffixed = next(
        r for r in annotated if r["dispName"] == "ResourceSat-1_AWIFS_1x1deg-tiles"
    )
    assert bare["_sibling_products"] == ["ResourceSat-1_AWIFS_1x1deg-tiles"]
    # The suffixed row itself has its own distinct product token, so it
    # isn't ambiguous even though it has a sibling.
    assert "_sibling_products" not in suffixed


def test_different_sensors_never_cross_contaminate():
    rows = [
        _row("EOS-06", "OCM(GAC)", "EOS-06_OCM(GAC)_L1C"),
        _row("EOS-06", "OCM(LAC)", "EOS-06_OCM(LAC)_L1C"),
    ]
    annotated = _annotate_ambiguous_defaults(rows)
    assert all("_sibling_products" not in r for r in annotated)


def test_does_not_mutate_input_rows():
    original = _row("ResourceSat-1", "AWIFS", "ResourceSat-1_AWIFS")
    rows = [
        original,
        _row("ResourceSat-1", "AWIFS", "ResourceSat-1_AWIFS_1x1deg-tiles"),
    ]
    _annotate_ambiguous_defaults(rows)
    assert "_sibling_products" not in original
