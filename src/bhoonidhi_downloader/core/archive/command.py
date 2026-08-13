"""Archive command handlers.

Pure logic: these return plain data or raise a typed
:class:`~bhoonidhi_downloader.exceptions.BhoonidhiError`. Rendering lives in
the CLI layer (``cli/archive.py``).
"""

import json
from pathlib import Path
from typing import Any

from .client import ArchiveManager


def run_archive_list(refresh: bool = False) -> list[dict[str, Any]]:
    """Return the raw archive records (every satellite the portal supports).

    Raises:
        BhoonidhiAPIError: if the archive can't be fetched.
    """
    return ArchiveManager(refresh=refresh).archive


def run_archive_export(
    path: str, sat: str | None = None, refresh: bool = False
) -> list[dict[str, Any]]:
    """Write the parsed archive (optionally one satellite) to ``path`` as JSON.

    Returns the parsed records that were written.

    Raises:
        BhoonidhiAPIError: if the archive can't be fetched.
        OSError: if the file can't be written.
    """
    archive = ArchiveManager(refresh=refresh).archive
    return write_archive_export(archive, path, sat)


def write_archive_export(
    archive: list[dict[str, Any]], path: str, sat: str | None = None
) -> list[dict[str, Any]]:
    """Format an already-loaded archive and write it to ``path`` as JSON.

    Returns the parsed records that were written. Lets a caller that already
    holds the raw archive export it without re-reading it.

    Raises:
        OSError: if the file can't be written.
    """
    parsed = ArchiveManager.format_archive(archive, sat)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(parsed, indent=2))
    return parsed
