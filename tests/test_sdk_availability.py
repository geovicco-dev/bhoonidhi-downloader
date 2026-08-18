"""The public SDK exposes scene availability classification.

Verifies scene_availability reconciles PRICED + CURR_SCENE_NO the way the CLI
does, and that the Availability enum carries a stable label and downloadable
flag. Imported through the public sdk namespace consumers use.
"""

import pytest

from bhoonidhi_downloader.sdk import Availability, scene_availability


def _scene(priced, curr_scene_no=None):
    scene = {"PRICED": priced}
    if curr_scene_no is not None:
        scene["CURR_SCENE_NO"] = curr_scene_no
    return scene


@pytest.mark.parametrize(
    ("scene", "expected"),
    [
        # open data + staged -> Ready
        (_scene("OpenData_DirectDownload", "Y"), Availability.DIRECT_AVAILABLE),
        # open data + not staged -> Archived (may 404)
        (_scene("OpenData_DirectDownload", "N"), Availability.DIRECT_UNAVAILABLE),
        (_scene("OpenData_DirectDownload"), Availability.DIRECT_UNAVAILABLE),
        # on order
        (_scene("OpenData_OnOrder"), Availability.ON_ORDER),
        # priced / anything else
        (_scene("Priced"), Availability.PRICED),
        (_scene(""), Availability.PRICED),
    ],
)
def test_scene_availability_reconciles_both_fields(scene, expected):
    assert scene_availability(scene) is expected


def test_direct_download_is_not_enough_on_its_own():
    """The bug this feature fixes: DirectDownload without staging is not Ready."""
    staged = scene_availability(_scene("OpenData_DirectDownload", "Y"))
    archived = scene_availability(_scene("OpenData_DirectDownload", "N"))
    assert staged is not archived
    assert staged.is_downloadable and archived.is_downloadable  # both attempted
    assert staged.label == "Ready"
    assert archived.label == "Archived"


@pytest.mark.parametrize(
    ("state", "label", "downloadable"),
    [
        (Availability.DIRECT_AVAILABLE, "Ready", True),
        (Availability.DIRECT_UNAVAILABLE, "Archived", True),
        (Availability.ON_ORDER, "OnOrder", False),
        (Availability.PRICED, "Priced", False),
    ],
)
def test_enum_label_and_downloadable(state, label, downloadable):
    assert state.label == label
    assert state.is_downloadable is downloadable
