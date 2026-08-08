"""Download module exports."""

from .client import DownloadManager, DownloadOutcome
from .render import make_progress, render_download_report
from .utils import build_download_url, download_filename, is_downloadable

__all__ = [
    # URL / eligibility helpers
    "build_download_url",
    "download_filename",
    "is_downloadable",
    # Client
    "DownloadManager",
    "DownloadOutcome",
    # Render functions
    "make_progress",
    "render_download_report",
]
