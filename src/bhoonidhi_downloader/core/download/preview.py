"""Predict what 'query download' would do, without touching the network.

Mirrors the real classification rules used by ``_download_one`` and
``run_query_download`` (availability, on-disk duplicates, recorded
duplicates elsewhere) so a dry run is an honest preview of the real
command, not a separate approximation that can drift out of sync with it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..search.availability import Availability, availability_of, is_downloadable
from .utils import download_filename


@dataclass
class DownloadPreview:
    scene_id: str
    status: str
    # "would_download" | "may_404" | "already_here" | "already_elsewhere"
    # | "skipped_on_order" | "skipped_priced"
    filename: str
    out_path: str
    note: str | None = None  # e.g. the other location a duplicate was found at


def build_preview(
    scenes: list[dict[str, Any]], out_dir: Path, force: bool = False
) -> list[DownloadPreview]:
    """Classify each scene the way a real download would, without fetching it.

    No file size is known ahead of time — the portal doesn't expose one in
    scene metadata, only in the response headers of the download request
    itself — so this predicts status and destination, not bytes.
    """
    previews: list[DownloadPreview] = []

    for scene in scenes:
        scene_id = scene.get("ID", "unknown")
        filename = download_filename(scene)
        out_path = out_dir / filename

        if not is_downloadable(scene):
            state = availability_of(scene)
            status = (
                "skipped_on_order"
                if state is Availability.ON_ORDER
                else "skipped_priced"
            )
            previews.append(DownloadPreview(scene_id, status, filename, str(out_path)))
            continue

        # Same on-disk check _download_one uses: a real file already sitting
        # at the destination is skip-fast unless --force is passed.
        if not force and out_path.exists() and out_path.stat().st_size > 0:
            previews.append(
                DownloadPreview(scene_id, "already_here", filename, str(out_path))
            )
            continue

        # Same recorded-elsewhere check run_query_download uses: a scene
        # already downloaded and verified to a different --out in the past.
        record = None if force else scene.get("_bhx_download")
        if record and record.get("path"):
            recorded_path = Path(record["path"]).expanduser().resolve()
            if recorded_path.parent != out_dir and recorded_path.exists():
                previews.append(
                    DownloadPreview(
                        scene_id,
                        "already_elsewhere",
                        filename,
                        str(out_path),
                        note=str(recorded_path),
                    )
                )
                continue

        status = (
            "would_download"
            if availability_of(scene) is Availability.DIRECT_AVAILABLE
            else "may_404"  # DIRECT_UNAVAILABLE: attempted for real too, but archived
        )
        previews.append(DownloadPreview(scene_id, status, filename, str(out_path)))

    return previews
