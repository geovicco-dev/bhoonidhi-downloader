"""Preview a download — ``sdk.preview_download`` and ``DownloadPreview``.

A search returns scenes, but not every scene downloads the same way: some are
staged and ready, some are open data that may 404 until requested, and priced
or on-order scenes are skipped entirely. This previews exactly what a real
``client.query.download`` would do for a set of scenes — status, filename, and
destination — without touching the network or needing a login.

    from bhoonidhi_downloader.sdk import preview_download

    for item in preview_download(query.scenes, Path("./downloads")):
        item.status    # "would_download" / "may_404" / "already_here" / ...
        item.filename
        item.out_path

No file size is available ahead of time: the portal exposes it only in the
download response headers, so a preview reports what and where, not how big.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bhoonidhi_downloader.core.download.preview import (
    DownloadPreview,
    build_preview,
)


def preview_download(
    scenes: list[dict[str, Any]], out_dir: str | Path, force: bool = False
) -> list[DownloadPreview]:
    """Classify what downloading ``scenes`` into ``out_dir`` would do, no fetch.

    Pass scenes from ``client.query.create().scenes``. Each returned
    :class:`DownloadPreview` carries a ``status`` — ``would_download`` (staged,
    open data), ``may_404`` (open data but archived, attempted anyway),
    ``already_here`` / ``already_elsewhere`` (a matching file already exists),
    or ``skipped_on_order`` / ``skipped_priced`` (needs the portal) — plus the
    predicted ``filename`` and ``out_path``. ``force`` previews a re-download,
    ignoring files already present. No network call and no login required.
    """
    return build_preview(scenes, Path(out_dir), force=force)


__all__ = ["DownloadPreview", "preview_download"]
