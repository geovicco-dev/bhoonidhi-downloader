"""Tests for the quicklook/metadata URL builders.

The extension for both is decided by the scene's own portal-supplied
fields, not guessed — get_quicklook_url() previously guessed from PRICED,
which was wrong: TABLETYPE is the field that actually predicts it,
SMETA -> .jpeg, PMETA -> .jpg, no exceptions.

get_scene_meta_url() used to return a .meta/.met URL unconditionally.
The portal only ever serves a metadata file when a scene is open data
(PRICED starts with "OpenData_") AND TABLETYPE is "PMETA" — everything
else has no metadata file at all, and a handful of satellites (Sentinel-1,
Sentinel-2, Novasar) serve different files entirely even when the gate
passes.
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
# get_scene_meta_url — gate: only OpenData_* + PMETA scenes have a file
# --------------------------------------------------------------------------


def test_smeta_scene_has_no_metadata_url():
    """SMETA scenes never have a separate metadata file, regardless of
    pricing — this used to return a .meta URL that always 404'd."""
    assert get_scene_meta_url(_scene(TABLETYPE="SMETA")) is None


def test_priced_pmeta_scene_has_no_metadata_url():
    """Priced scenes never have a metadata file even when PMETA."""
    assert get_scene_meta_url(_scene(TABLETYPE="PMETA", PRICED="Priced")) is None


def test_opendata_pmeta_scene_has_a_metadata_url():
    url = get_scene_meta_url(_scene(TABLETYPE="PMETA", PRICED="OpenData_DirectDownload"))
    assert url is not None


def test_opendata_onorder_pmeta_scene_has_a_metadata_url():
    """OpenData_OnOrder counts as open data too, not just DirectDownload."""
    url = get_scene_meta_url(_scene(TABLETYPE="PMETA", PRICED="OpenData_OnOrder"))
    assert url is not None


# --------------------------------------------------------------------------
# get_scene_meta_url — base extension: NISAR uses .met, everything else .meta
# --------------------------------------------------------------------------


def test_nisar_scene_gets_met_extension():
    url = get_scene_meta_url(
        _scene(
            ID="NISAR_SSAR_20260101_1_1_SAN_PLD",
            SATELLITE="NISAR",
            TABLETYPE="PMETA",
        )
    )
    assert url is not None
    assert url.endswith(".met")


def test_non_nisar_scene_gets_meta_extension():
    url = get_scene_meta_url(_scene(TABLETYPE="PMETA"))
    assert url is not None
    assert url.endswith(".meta")


# --------------------------------------------------------------------------
# get_scene_meta_url — satellite-specific rewrites (Sentinel-1/2, Novasar)
# --------------------------------------------------------------------------


def test_sentinel1_scene_opens_vh_xml_not_meta():
    url = get_scene_meta_url(
        _scene(
            ID="SEN1A_SAR_IW_01MAY2026_064330_13A6_ESA_ST0000KTD_DV",
            SATELLITE="SEN1A",
            TABLETYPE="PMETA",
        )
    )
    assert url is not None
    assert url.endswith("_VH.xml")


def test_sentinel2_scene_opens_mtd_xml_not_meta():
    url = get_scene_meta_url(
        _scene(
            ID="SEN2A_MSI_L2A_01MAY2026_T44RQK",
            SATELLITE="SEN2A",
            TABLETYPE="PMETA",
        )
    )
    assert url is not None
    assert url.endswith("_MTD.xml")


def test_novasar_scene_uses_productmeta_dir_and_xml_extension():
    url = get_scene_meta_url(
        _scene(
            ID="NV_S_A_18JUN2025_062090_zzz_zzz_zzz_zzz_01_001_P_SAN_SP0000NTD_F_VVHH",
            DIRPATH="/imgarchive/PRODUCTJPGS//NVS/S/2025/JUN/18",
            FILENAME="NV_S_A_18JUN2025_062090_zzz_zzz_zzz_zzz_01_001_P_SAN_SP0000NTD_F_VVHH",
            SATELLITE="NVS",
            TABLETYPE="PMETA",
        )
    )
    assert url is not None
    assert "PRODUCTMETA" in url
    assert url.endswith(".xml")
