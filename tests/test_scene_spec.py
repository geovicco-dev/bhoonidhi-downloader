"""Tests for the port of the portal's makeInterfaceObj().

The R2A/AWiFS expectations are ground truth: they are the SAT_SPEC and
SCENE_SPEC values the portal itself wrote onto a cart record when the same
scene was added through the web UI. If this port drifts, the portal's cart
table silently drops the row — the failure is invisible server-side, so
these assertions are the guard.
"""

import pytest

from bhoonidhi_downloader.core.cart.scene_spec import make_interface_obj

# Added via the portal UI; SAT_SPEC/SCENE_SPEC below are what it stored.
PORTAL_ADDED_AWIFS = {
    "ID": "RAW18JUL2026049872010400062PSANSTLCSRHTDC",
    "SATELLITE": "R2A",
    "SENSOR": "AWIF",
    "PRODTYPE": "BOA-Archives",
    "TABLETYPE": "PMETA",
    "GROUND_ORBIT_NO": "049872",
    "PATHNO": "104",
    "SCENE_NO": "62",
    "DIRPATH": "/imgarchive/PRODUCTJPGS//R2A/AWIF/2026/JUL/18/",
    "FILENAME": "RAW18JUL2026049872010400062PSANSTLCSRHTDC",
}

# The scene the CLI added, whose row the portal refused to render.
CLI_ADDED_AWIFS = {
    "ID": "RAW12JUL2026049787009800051PSANSTLC00GTDA",
    "SATELLITE": "R2A",
    "SENSOR": "AWIF",
    "PRODTYPE": "L2",
    "TABLETYPE": "PMETA",
    "GROUND_ORBIT_NO": "049787",
    "PATHNO": "98",
    "SCENE_NO": "51",
    "DIRPATH": "/imgarchive/PRODUCTJPGS//R2A/AWIF/2026/JUL/12/",
    "FILENAME": "RAW12JUL2026049787009800051PSANSTLC00GTDA",
}

CARTOSAT3_PAN = {
    "ID": "C03_PAN_SP_16-MAR-2026_9_3_SAN_34936_16-MAR-2026_SSR_34936_1_4077_F_f",
    "SATELLITE": "C03",
    "SENSOR": "PAN",
    "PRODTYPE": "Others",
    "TABLETYPE": "SMETA",
    "GROUND_ORBIT_NO": "34936",
    "STRIP_NO": "4077",
    "SCENE_NO": "3",
    "DIRPATH": "/imgarchive//IRSC03/PAN/2026/MAR/16/",
    "FILENAME": "cbsf034936_004077_003_SAN_pas_c03.16mar2026",
}


def test_matches_what_the_portal_itself_stored():
    """Ground truth: same scene, added through the web UI."""
    out = make_interface_obj(PORTAL_ADDED_AWIFS)
    assert out["SAT_SPEC"] == "R2A_AWIF_-_S_BOA-Archives"
    assert out["SCENE_SPEC"] == "049872_104_62_C"
    assert out["SAT_SPEC_SCHEME"] == "Satellite_Sensor_ImagingMode_Subscene_Product"
    assert out["SCENE_SPEC_SCHEME"] == "GroundOrbit_Path_Row_Subscene"
    assert out["SUBSCENE_ID"] == "C"


def test_awifs_subscene_comes_from_last_char_of_41_char_pmeta_id():
    """PMETA ids of exactly 41 chars carry the subscene as the final char."""
    out = make_interface_obj(CLI_ADDED_AWIFS)
    assert out["SUBSCENE_ID"] == "A"
    assert out["SAT_SPEC"] == "R2A_AWIF_-_S_L2"
    assert out["SCENE_SPEC"] == "049787_98_51_A"


def test_cartosat3_uses_imaging_mode_and_session_scheme():
    """C03 overrides both specs: no subscene, session taken from the ID."""
    out = make_interface_obj(CARTOSAT3_PAN)
    assert out["SAT_SPEC"] == "C03_PAN_SP"
    assert out["SAT_SPEC_SCHEME"] == "Satellite_Sensor_ImagingMode"
    assert out["SCENE_SPEC"] == "34936_1_4077_3"
    assert out["SCENE_SPEC_SCHEME"] == "GroundOrbit_Session_Strip_Scene"


def test_cartosat3_swath_variant_appends_prodtype():
    out = make_interface_obj({**CARTOSAT3_PAN, "PRODTYPE": "17km-swath"})
    assert out["SAT_SPEC"] == "C03_PAN_SP_17km-swath"
    assert out["SAT_SPEC_SCHEME"] == "Satellite_Sensor_ImagingMode_Swath"


def test_imaging_mode_is_dash_when_id_has_no_underscores():
    assert make_interface_obj(CLI_ADDED_AWIFS)["IMAGING_MODE"] == "-"


def test_imaging_mode_read_from_id_when_underscored():
    assert make_interface_obj(CARTOSAT3_PAN)["IMAGING_MODE"] == "SP"


@pytest.mark.parametrize(
    ("tabletype", "expected_suffix"),
    [("PMETA", ".jpg"), ("SMETA", ".jpeg")],
)
def test_img_path_extension_depends_on_tabletype(tabletype, expected_suffix):
    out = make_interface_obj({**CLI_ADDED_AWIFS, "TABLETYPE": tabletype})
    assert out["IMG_PATH"].endswith(expected_suffix)


def test_unknown_subscene_char_falls_back_to_full_scene():
    out = make_interface_obj({**CLI_ADDED_AWIFS, "ID": "X" * 41})
    assert out["SUBSCENE_ID"] == "F"


def test_input_scene_is_not_mutated():
    original = dict(CLI_ADDED_AWIFS)
    make_interface_obj(CLI_ADDED_AWIFS)
    assert CLI_ADDED_AWIFS == original


def test_scene_id_mirrors_id():
    assert make_interface_obj(CARTOSAT3_PAN)["SCENE_ID"] == CARTOSAT3_PAN["ID"]
