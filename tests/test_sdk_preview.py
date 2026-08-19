"""The public SDK exposes download preview classification.

Verifies preview_download and DownloadPreview are reachable through the public
sdk namespace and classify scenes the way build_preview does. The exhaustive
status matrix lives in test_download_preview.py; this guards the public surface.
"""

from pathlib import Path

from bhoonidhi_downloader.sdk import DownloadPreview, preview_download

_READY = {
    "ID": "R2A_READY_1",
    "PRICED": "OpenData_DirectDownload",
    "CURR_SCENE_NO": "Y",
    "SATELLITE": "R2A",
    "SENSOR": "LIS3",
    "FILENAME": "scene_ready",
    "DIRPATH": "archive/2026/08",
}
_ARCHIVED = {**_READY, "ID": "R2A_ARCHIVED_1", "CURR_SCENE_NO": "N"}
_PRICED = {**_READY, "ID": "PR_1", "PRICED": "Priced"}


def test_public_preview_classifies_a_scene_set(tmp_path):
    previews = preview_download([_READY, _ARCHIVED, _PRICED], tmp_path)
    assert [p.status for p in previews] == [
        "would_download",
        "may_404",
        "skipped_priced",
    ]
    assert all(isinstance(p, DownloadPreview) for p in previews)


def test_public_preview_reports_filename_and_destination():
    previews = preview_download([_READY], Path("/tmp/out"))
    assert previews[0].filename == "scene_ready.zip"
    assert previews[0].out_path == str(Path("/tmp/out/scene_ready.zip"))


def test_public_preview_accepts_str_out_dir(tmp_path):
    # out_dir may be a plain string, not only a Path.
    previews = preview_download([_READY], str(tmp_path))
    assert previews[0].status == "would_download"


def test_force_previews_a_redownload(tmp_path):
    (tmp_path / "scene_ready.zip").write_bytes(b"x")
    assert preview_download([_READY], tmp_path)[0].status == "already_here"
    assert preview_download([_READY], tmp_path, force=True)[0].status == "would_download"
