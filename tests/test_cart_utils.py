"""Tests for the portal's cart-routing and request-encoding rules.

These lock in behaviour observed from the live portal. They are
pure-function tests — nothing here touches the network.
"""

import json
from datetime import datetime

import pytest

from bhoonidhi_downloader.core.cart.utils import (
    CartKind,
    build_add_payload,
    build_delete_payload,
    cart_date_long,
    cart_kind_for,
    compact_json,
    encode_article,
)

# --------------------------------------------------------------------------
# Cart routing — reuses the same access_of classification as search/download
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("priced", "expected"),
    [
        ("OpenData_DirectDownload", CartKind.DIRECT),
        ("OpenData_OnOrder", CartKind.ORDER),
        ("Priced", CartKind.PRICED),
    ],
)
def test_cart_kind_routes_by_access_type(priced, expected):
    assert cart_kind_for({"PRICED": priced}) is expected


@pytest.mark.parametrize("priced", ["", "Mystery", None])
def test_unrecognised_priced_routes_to_priced_cart(priced):
    """An unknown PRICED value is treated as priced, the same way search and
    download classify it — a scene the CLI shows as Priced must not crash
    when it is added, and priced items can only be finished in the portal
    anyway, so routing there is the safe, consistent choice.
    """
    assert cart_kind_for({"PRICED": priced}) is CartKind.PRICED


def test_missing_priced_key_routes_to_priced_cart():
    assert cart_kind_for({}) is CartKind.PRICED


# --------------------------------------------------------------------------
# Encoding
# --------------------------------------------------------------------------


def test_encode_article_encodes_every_value_not_just_json():
    """The portal's encodeObject() encodes all values, not only selProds."""
    out = encode_article({"selSats": "CartoSat-3_MX(SPOT)", "filters": "{}", "n": 5})
    assert out == {
        "selSats": "CartoSat-3_MX%28SPOT%29",
        "filters": "%7B%7D",
        "n": "5",
    }


def test_encode_article_escapes_slashes():
    """safe='' matters: an unescaped '/' in a date field is misparsed."""
    assert encode_article({"d": "JUL/18/2026"}) == {"d": "JUL%2F18%2F2026"}


def test_compact_json_emits_no_whitespace():
    """The WAF rejects bodies containing spaces."""
    body = compact_json({"a": 1, "b": "c"})
    assert body == '{"a":1,"b":"c"}'
    assert " " not in body


# --------------------------------------------------------------------------
# Cart date format — VIEWCART and DELETE want the long, day-padded form
# --------------------------------------------------------------------------


def test_long_form_pads_the_day_and_spells_the_month():
    assert cart_date_long(datetime(2026, 8, 5)) == "05 August 2026"
    assert cart_date_long(datetime(2026, 8, 10)) == "10 August 2026"


# --------------------------------------------------------------------------
# Payload construction
# --------------------------------------------------------------------------

DIRECT_SCENE = {
    "ID": "RAW18JUL2026049872010400062PSANSTLCSRHTDC",
    "srt": "20260810_O0P011242",
    "DOP": "18-Jul-2026",
    "PRICED": "OpenData_DirectDownload",
    "TABLETYPE": "PMETA",
    "SELECTION": "ResourceSat-2A_AWIFS_BOA-Archives",
    "SATELLITE": "R2A",
    "SENSOR": "AWIF",
    "PRODTYPE": "BOA-Archives",
    "CURR_SCENE_NO": "Y",
    "GROUND_ORBIT_NO": "049872",
    "PATHNO": "104",
    "SCENE_NO": "62",
}

PRICED_SCENE = {
    "ID": "C03_PAN_SP_16-MAR-2026_9_3_SAN_34936_16-MAR-2026_SSR_34936_1_4077_F_f",
    "srt": "20260810_EFM013660",
    "DOP": "16-Mar-2026",
    "PRICED": "Priced",
    "TABLETYPE": "SMETA",
    "SELECTION": "CartoSat-3_PAN(SPOT)",
    "SATELLITE": "C03",
    "SENSOR": "PAN",
    "PRODTYPE": "Others",
    "GROUND_ORBIT_NO": "34936",
    "STRIP_NO": "4077",
    "SCENE_NO": "3",
}


def test_direct_add_payload_uses_prod_id_and_omits_query_type():
    kind, payload = build_add_payload(DIRECT_SCENE, "ONL_user")
    assert kind is CartKind.DIRECT
    assert payload["action"] == "ADDTOCART"
    assert payload["PROD_ID"] == DIRECT_SCENE["ID"]
    assert "sceneID" not in payload
    assert "queryType" not in payload


def test_priced_add_payload_uses_scene_id_and_scene_table_type():
    """queryType comes off the scene, not a per-endpoint constant.

    A priced CartoSat-3 scene carries TABLETYPE=SMETA, so hardcoding
    TMETA for the PI cart (the intuitive-but-wrong mapping) would send a
    malformed body.
    """
    kind, payload = build_add_payload(PRICED_SCENE, "ONL_user")
    assert kind is CartKind.PRICED
    assert payload["action"] == "ADDTOPICART"
    assert payload["sceneID"] == PRICED_SCENE["ID"]
    assert payload["queryType"] == "SMETA"
    assert "PROD_ID" not in payload


def test_priced_add_payload_uses_the_derived_sat_spec():
    """selSats is the derived SAT_SPEC, matching what the portal sends.

    Search results carry SELECTION, not SAT_SPEC; the portal computes the
    latter client-side before adding, and this payload matches.
    """
    _, payload = build_add_payload(PRICED_SCENE, "ONL_user")
    assert payload["selSats"] == "C03_PAN_SP"


def test_add_payload_embeds_the_derived_identifiers():
    """selProds must carry SAT_SPEC/SCENE_SPEC or the portal drops the row."""
    _, payload = build_add_payload(DIRECT_SCENE, "ONL_user")
    embedded = json.loads(payload["selProds"])
    assert embedded["SAT_SPEC"] == "R2A_AWIF_-_S_BOA-Archives"
    assert embedded["SCENE_SPEC"] == "049872_104_62_C"
    assert embedded["SCENE_ID"] == DIRECT_SCENE["ID"]


def test_direct_prod_av_follows_curr_scene_no():
    """The portal sends N unless the scene is the current one."""
    _, payload = build_add_payload(DIRECT_SCENE, "ONL_user")
    assert payload["PROD_AV"] == "Y"

    _, payload = build_add_payload({**DIRECT_SCENE, "CURR_SCENE_NO": "N"}, "ONL_user")
    assert payload["PROD_AV"] == "N"


def test_add_payload_embeds_scene_as_compact_json():
    _, payload = build_add_payload(PRICED_SCENE, "ONL_user")
    assert " " not in payload["selProds"]


def test_direct_delete_uses_prod_id_and_cart_date():
    kind, payload = build_delete_payload(DIRECT_SCENE, "ONL_user", datetime(2026, 8, 10))
    assert kind is CartKind.DIRECT
    assert payload == {
        "prodId": DIRECT_SCENE["ID"],
        "action": "DELETE",
        "userId": "ONL_user",
        "cartDate": "10 August 2026",
    }


def test_priced_delete_uses_scene_id_and_srt_without_date():
    kind, payload = build_delete_payload(PRICED_SCENE, "ONL_user", datetime(2026, 8, 10))
    assert kind is CartKind.PRICED
    assert payload == {
        "sceneID": PRICED_SCENE["ID"],
        "srt": PRICED_SCENE["srt"],
        "action": "DELETE",
        "userId": "ONL_user",
    }
