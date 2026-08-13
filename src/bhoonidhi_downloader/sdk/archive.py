"""Archive namespace — ``client.archive.*``.

Browse and export the portal's satellite/sensor catalogue. None of this
needs a login, so these calls work on a fresh ``BhoonidhiClient()``.
"""

from __future__ import annotations

from typing import Any

from bhoonidhi_downloader.core.archive import command as _archive


class ArchiveNamespace:
    """The ``archive`` commands, reachable as ``client.archive``."""

    def list(self, refresh: bool = False) -> list[dict[str, Any]]:
        """Return every satellite/sensor record. Mirrors ``bhd archive list``."""
        return _archive.run_archive_list(refresh=refresh)

    def export(
        self, path: str, sat: str | None = None, refresh: bool = False
    ) -> list[dict[str, Any]]:
        """Write the parsed archive to ``path`` as JSON and return the records.

        Mirrors ``bhd archive export``.
        """
        return _archive.run_archive_export(path, sat=sat, refresh=refresh)
