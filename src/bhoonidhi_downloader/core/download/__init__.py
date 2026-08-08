"""Download module exports."""

from .client import DownloadManager, DownloadOutcome, sha256_of_file
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
    "sha256_of_file",
    # Render functions
    "make_progress",
    "render_download_report",
]
