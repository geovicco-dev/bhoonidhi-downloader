"""Tests for the download dry-run preview (build_preview).

build_preview mirrors the real download classification (availability,
on-disk duplicates, recorded duplicates elsewhere) without touching the
network or filesystem beyond read-only existence checks.
"""

from pathlib import Path

from bhoonidhi_downloader.core.download.preview import build_preview

OPEN_READY = {
    "ID": "R2A_READY_1",
    "PRICED": "OpenData_DirectDownload",
    "CURR_SCENE_NO": "Y",
    "SATELLITE": "R2A",
    "SENSOR": "LIS3",
    "FILENAME": "scene_ready",
    "DIRPATH": "archive/2026/08",
}

OPEN_ARCHIVED = {
    "ID": "R2A_ARCHIVED_1",
    "PRICED": "OpenData_DirectDownload",
    "CURR_SCENE_NO": "N",
    "SATELLITE": "R2A",
    "SENSOR": "LIS3",
    "FILENAME": "scene_archived",
    "DIRPATH": "archive/2026/08",
}

ON_ORDER = {
    "ID": "OO_1",
    "PRICED": "OpenData_OnOrder",
    "SATELLITE": "SEN1A",
    "SENSOR": "SAR",
    "FILENAME": "scene_onorder",
    "DIRPATH": "archive/2026/08",
}

PRICED = {
    "ID": "PR_1",
    "PRICED": "Priced",
    "SATELLITE": "C03",
    "SENSOR": "PAN",
    "FILENAME": "scene_priced",
    "DIRPATH": "archive/2026/08",
}


def test_ready_scene_would_download(tmp_path):
    previews = build_preview([OPEN_READY], tmp_path)
    assert previews[0].status == "would_download"
    assert previews[0].scene_id == "R2A_READY_1"


def test_archived_scene_flagged_as_may_404(tmp_path):
    previews = build_preview([OPEN_ARCHIVED], tmp_path)
    assert previews[0].status == "may_404"


def test_on_order_scene_is_skipped_not_attempted(tmp_path):
    previews = build_preview([ON_ORDER], tmp_path)
    assert previews[0].status == "skipped_on_order"


def test_priced_scene_is_skipped_not_attempted(tmp_path):
    previews = build_preview([PRICED], tmp_path)
    assert previews[0].status == "skipped_priced"


def test_file_already_at_destination_is_already_here(tmp_path):
    # download_filename() appends ".zip" for a non-NISAR/SSAR scene.
    (tmp_path / "scene_ready.zip").write_bytes(b"x")
    previews = build_preview([OPEN_READY], tmp_path)
    assert previews[0].status == "already_here"


def test_force_ignores_an_existing_file_at_destination(tmp_path):
    (tmp_path / "scene_ready.zip").write_bytes(b"x")
    previews = build_preview([OPEN_READY], tmp_path, force=True)
    assert previews[0].status == "would_download"


def test_recorded_elsewhere_and_still_present_is_flagged(tmp_path):
    elsewhere_dir = tmp_path / "elsewhere"
    elsewhere_dir.mkdir()
    elsewhere_file = elsewhere_dir / "scene_ready.zip"
    elsewhere_file.write_bytes(b"x")

    scene = {**OPEN_READY, "_bhx_download": {"path": str(elsewhere_file)}}
    previews = build_preview([scene], tmp_path / "here")
    assert previews[0].status == "already_elsewhere"
    assert previews[0].note == str(elsewhere_file)


def test_recorded_elsewhere_but_missing_is_treated_as_a_normal_download(tmp_path):
    # The recorded file no longer exists (moved/deleted) — not a duplicate.
    scene = {
        **OPEN_READY,
        "_bhx_download": {"path": str(tmp_path / "gone" / "scene_ready.zip")},
    }
    previews = build_preview([scene], tmp_path / "here")
    assert previews[0].status == "would_download"


def test_filename_and_out_path_are_reported():
    previews = build_preview([OPEN_READY], Path("/tmp/out"))
    assert previews[0].filename == "scene_ready.zip"
    assert previews[0].out_path == str(Path("/tmp/out/scene_ready.zip"))
