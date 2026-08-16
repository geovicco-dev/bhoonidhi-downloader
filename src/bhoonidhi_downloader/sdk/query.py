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
from bhoonidhi_downloader.exceptions import BhoonidhiValidationError
from bhoonidhi_downloader.schemas import QuerySchema, Selection
from bhoonidhi_downloader.sdk._select import normalize_select

if TYPE_CHECKING:
    from bhoonidhi_downloader.sdk.client import BhoonidhiClient


class QueryNamespace:
    """The ``query`` commands, reachable as ``client.query``."""

    def __init__(self, client: BhoonidhiClient) -> None:
        self._client = client

    def create(
        self,
        start_date: datetime,
        end_date: datetime,
        satellite: str | None = None,
        minx: float | None = None,
        maxx: float | None = None,
        miny: float | None = None,
        maxy: float | None = None,
        sensor: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_km: float | None = None,
        name: str | None = None,
        description: str | None = None,
        selections: list[Selection] | None = None,
        save: bool = True,
    ) -> QuerySchema | None:
        """Search an AOI + date range, returning the matching scenes.

        The AOI is either a bounding box (minx/maxx/miny/maxy) or a point
        plus radius (lat/lon/radius_km) — give exactly one of the two.

        Targets are given as ``selections`` — a list of
        :class:`~bhoonidhi_downloader.schemas.Selection`, each naming a
        satellite and optionally a sensor and product. The legacy
        ``satellite`` + ``sensor`` scalar pair is still accepted for a
        single-mission search and is folded into a one-element
        ``selections`` list; giving both is an error.

        By default (``save=True``) the result is persisted as a named query
        under ``~/.bhoonidhi/queries/`` and the returned query carries its
        slug. Pass ``save=False`` for a stateless search: the search runs
        identically but nothing is written to disk and no slug is generated
        — the returned query is ephemeral, with ``.scenes`` populated, for
        callers that only want the scene list.

        Returns the query, or None if nothing matched. Mirrors
        ``bhd query create``.
        """
        resolved = self._resolve_selections(satellite, sensor, selections)
        return _query.run_query_create(
            start_date,
            end_date,
            resolved,
            minx=minx,
            maxx=maxx,
            miny=miny,
            maxy=maxy,
            lat=lat,
            lon=lon,
            radius_km=radius_km,
            name=name,
            description=description,
            save=save,
        )

    @staticmethod
    def _resolve_selections(
        satellite: str | None,
        sensor: str | None,
        selections: list[Selection] | None,
    ) -> list[Selection]:
        """Reconcile the modern ``selections`` list with the legacy scalar pair.

        Exactly one form must be given. The legacy ``satellite`` (+ optional
        ``sensor``) becomes a single-element list; ``selections`` is used
        as-is. Supplying both, or neither, is a usage error.
        """
        if selections is not None:
            if satellite is not None or sensor is not None:
                raise BhoonidhiValidationError(
                    "Give either selections or satellite/sensor, not both."
                )
            return selections
        if satellite is None:
            raise BhoonidhiValidationError(
                "A satellite selection is required (pass selections=... "
                "or satellite=...)."
            )
        return [Selection(satellite=satellite, sensor=sensor)]

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
