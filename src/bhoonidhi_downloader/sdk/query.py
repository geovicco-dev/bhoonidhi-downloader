"""Query namespace — ``client.query.*``.

Search the portal and manage saved queries. ``create``, ``refresh``, and
``download`` reach the portal; the rest work on the local query store.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

from bhoonidhi_downloader.core.download import DownloadOutcome
from bhoonidhi_downloader.core.query import command as _query
from bhoonidhi_downloader.schemas import QuerySchema
from bhoonidhi_downloader.sdk._select import normalize_select

if TYPE_CHECKING:
    from bhoonidhi_downloader.sdk.client import BhoonidhiClient


class QueryNamespace:
    """The ``query`` commands, reachable as ``client.query``."""

    def __init__(self, client: BhoonidhiClient) -> None:
        self._client = client

    def create(
        self,
        minx: float,
        maxx: float,
        miny: float,
        maxy: float,
        start_date: datetime,
        end_date: datetime,
        satellite: str,
        sensor: str | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> QuerySchema | None:
        """Search a bounding box + date range, save the result as a named query.

        Returns the saved query, or None if nothing matched. Mirrors
        ``bhd query create``.
        """
        return _query.run_query_create(
            minx,
            maxx,
            miny,
            maxy,
            start_date,
            end_date,
            satellite,
            sensor=sensor,
            name=name,
            description=description,
        )

    def list(self) -> list[QuerySchema]:
        """Return every saved query. Mirrors ``bhd query list``."""
        return _query.run_query_list()

    def show(self, slug: str) -> QuerySchema:
        """Return a saved query by slug. Mirrors ``bhd query show``.

        Raises ``BhoonidhiNotFoundError`` if the slug is unknown.
        """
        return _query.run_query_show(slug)

    def rename(
        self, slug: str, name: str | None = None, description: str | None = None
    ) -> QuerySchema:
        """Update a query's name/description. Mirrors ``bhd query rename``."""
        return _query.run_query_rename(slug, name=name, description=description)

    def fork(self, slug: str, name: str | None = None) -> QuerySchema:
        """Clone a query under a new slug. Mirrors ``bhd query fork``."""
        return _query.run_query_fork(slug, name=name)

    def rm(self, slug: str) -> None:
        """Delete a saved query. Mirrors ``bhd query rm``.

        Raises ``BhoonidhiNotFoundError`` if the slug is unknown.
        """
        _query.run_query_rm(slug)

    def refresh(self, slug: str) -> tuple[QuerySchema, int | None]:
        """Re-query for newer scenes. Mirrors ``bhd query refresh``.

        Returns ``(query, added_count)``; ``added_count`` is None if the
        query was already up to date.
        """
        return _query.run_query_refresh(slug)

    def download(
        self,
        slug: str,
        out: str,
        select: list[int | str] | None = None,
        parallel: int = 4,
        force: bool = False,
        on_progress: Callable[[str, int, int | None], None] | None = None,
    ) -> list[DownloadOutcome]:
        """Download a query's open-access scenes to ``out``.

        Mirrors ``bhd query download``. Uses the client's held session — log
        in first. Priced/on-order scenes are skipped; ``on_progress`` is
        called with ``(scene_id, bytes_so_far, total_bytes)`` as data arrives.

        ``select`` narrows the download to specific scenes: an ``int`` is a
        1-based index into the query, a ``str`` is a full scene ID. Omit it
        to download the whole query. Example: ``select=[1, 2, 3]``.

        Raises:
            BhoonidhiAuthError: if the client isn't authenticated.
            BhoonidhiNotFoundError: if the slug is unknown.
            BhoonidhiValidationError: if a ``select`` entry isn't a plain
                index or scene ID.
        """
        account = self._client.require_account()
        return _query.run_query_download(
            slug,
            out,
            account.jwt,
            select=normalize_select(select),
            parallel=parallel,
            force=force,
            on_progress=on_progress,
        )
