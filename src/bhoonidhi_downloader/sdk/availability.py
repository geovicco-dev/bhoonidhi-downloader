"""Scene availability — ``sdk.scene_availability`` and the ``Availability`` enum.

Search results (``client.query.create().scenes``) are raw portal dicts. Whether
a scene can actually be downloaded *now* depends on two portal fields at once —
``PRICED`` (open data vs on-order vs priced) and ``CURR_SCENE_NO`` (whether an
open-data scene is currently staged or archived out of hot storage). This module
publishes the same classification the CLI's Availability column uses, so SDK and
agent consumers can answer "is this downloadable?" without reimplementing it or
reaching into ``core``.

    from bhoonidhi_downloader.sdk import scene_availability

    for scene in query.scenes:
        state = scene_availability(scene)
        state.label            # "Ready" / "Archived" / "OnOrder" / "Priced"
        state.is_downloadable  # True for Ready and Archived
"""

from __future__ import annotations

from typing import Any

from bhoonidhi_downloader.core.search.availability import (
    Availability,
    availability_of,
)


def scene_availability(scene: dict[str, Any]) -> Availability:
    """Classify a search-result scene into its :class:`Availability` state.

    Pass a scene dict from ``client.query.create().scenes``. Reconciles the
    scene's ``PRICED`` and ``CURR_SCENE_NO`` fields the same way the CLI does:
    an open-data scene is ``DIRECT_AVAILABLE`` ("Ready") only when it is staged,
    otherwise ``DIRECT_UNAVAILABLE`` ("Archived") and may 404 until requested on
    the portal; on-order and priced scenes classify accordingly.
    """
    return availability_of(scene)


__all__ = ["Availability", "scene_availability"]
