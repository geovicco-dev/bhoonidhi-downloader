"""Tests for the quicklook/metadata URL builders.

The extension for both is decided by the scene's own portal-supplied
fields, not guessed — get_quicklook_url() previously guessed from PRICED,
which was wrong (a live audit across every satellite/sensor/product
variant showed TABLETYPE is the only field that actually predicts it:
SMETA -> .jpeg, PMETA -> .jpg, no exceptions).
"""

from bhoonidhi_downloader.core.search.utils import get_quicklook_url, get_scene_meta_url


def _scene(**overrides):
    base = {
        "ID": "R2A_LIS3_20260101_1_1_SAN_PLD",
        "DIRPATH": "data/2026/01",
        "FILENAME": "R2A_LIS3_20260101_1_1_SAN_PLD",
        "TABLETYPE": "SMETA",
        "PRICED": "OpenData_DirectDownload",
    }
    base.update(overrides)
    return base


# --------------------------------------------------------------------------
# get_quicklook_url — TABLETYPE decides the extension, not PRICED
# --------------------------------------------------------------------------


def test_smeta_scene_gets_jpeg_quicklook():
    url = get_quicklook_url(_scene(TABLETYPE="SMETA"))
    assert url.endswith(".jpeg")


def test_pmeta_scene_gets_jpg_quicklook():
    url = get_quicklook_url(_scene(TABLETYPE="PMETA"))
    assert url.endswith(".jpg")


def test_priced_smeta_scene_still_gets_jpeg_not_jpg():
    """A priced scene used to force .jpeg regardless of TABLETYPE; that
    guess was wrong and broke every priced PMETA scene's quicklook."""
    url = get_quicklook_url(_scene(TABLETYPE="SMETA", PRICED="Priced"))
    assert url.endswith(".jpeg")


def test_priced_pmeta_scene_gets_jpg_not_jpeg():
    url = get_quicklook_url(_scene(TABLETYPE="PMETA", PRICED="Priced"))
    assert url.endswith(".jpg")


def test_unknown_tabletype_falls_back_to_jpg():
    url = get_quicklook_url(_scene(TABLETYPE="TMETA"))
    assert url.endswith(".jpg")


def test_missing_tabletype_falls_back_to_jpg():
    scene = _scene()
    del scene["TABLETYPE"]
    assert get_quicklook_url(scene).endswith(".jpg")


# --------------------------------------------------------------------------
# get_scene_meta_url — NISAR uses .met, everything else .meta
# --------------------------------------------------------------------------


def test_nisar_scene_gets_met_extension():
    url = get_scene_meta_url(_scene(ID="NISAR_SSAR_20260101_1_1_SAN_PLD"))
    assert url.endswith(".met")


def test_non_nisar_scene_gets_meta_extension():
    url = get_scene_meta_url(_scene(ID="R2A_LIS3_20260101_1_1_SAN_PLD"))
    assert url.endswith(".meta")
