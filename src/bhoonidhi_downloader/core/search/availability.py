"""Classify how a scene can actually be obtained.

Search results conflate two different questions: *is it open access*
(pricing) and *is it staged for download right now* (availability).

A scene can be open access direct download and still 404, because the
portal moves older products out of hot storage until they are requested.

Staging comes from the ``CURR_SCENE_NO`` response field, which is what the
portal itself uses to mark search results as available or archived. This
supersedes the earlier age-based heuristic: the archiving policy is not
fixed by age, and scenes from 2023 can be staged while some from 2024 are
not.
"""

from enum import Enum

DIRECT_DOWNLOAD_PRICED = "OpenData_DirectDownload"
ON_ORDER_PRICED = "OpenData_OnOrder"


class Availability(str, Enum):
    """How a scene can be obtained, and therefore what to do next."""

    #: Open access and staged — ``query download`` will fetch it.
    DIRECT_AVAILABLE = "direct_available"
    #: Open access but not staged. Still worth attempting; if it 404s it
    #: has to be requested on the portal first.
    DIRECT_UNAVAILABLE = "direct_unavailable"
    #: Open access but must be requested before it can be fetched.
    ON_ORDER = "on_order"
    #: Requires payment; ordered through the portal's PI workflow.
    PRICED = "priced"


class Access(str, Enum):
    """What kind of access a scene needs, independent of staging."""

    OPEN = "Open"
    ON_ORDER = "OnOrder"
    PRICED = "Priced"


def access_of(scene: dict) -> Access:
    """Classify a scene by what it costs you to obtain, not by staging."""
    priced = (scene.get("PRICED") or "").strip()
    if priced == ON_ORDER_PRICED:
        return Access.ON_ORDER
    if priced == DIRECT_DOWNLOAD_PRICED:
        return Access.OPEN
    return Access.PRICED


#: Availability state -> the word shown in the Availability column.
#: Both DIRECT_* states are open data; they differ only in staging.
AVAILABILITY_LABEL: dict[Availability, str] = {
    Availability.DIRECT_AVAILABLE: "Ready",
    Availability.DIRECT_UNAVAILABLE: "Archived",
    Availability.ON_ORDER: "OnOrder",
    Availability.PRICED: "Priced",
}

#: Availability state -> rich style for its label. The label alone
#: identifies the state, so the column still reads without colour.
AVAILABILITY_LABEL_STYLE: dict[Availability, str] = {
    Availability.DIRECT_AVAILABLE: "bold green",
    Availability.DIRECT_UNAVAILABLE: "dim cyan",
    Availability.ON_ORDER: "yellow",
    Availability.PRICED: "magenta",
}


def availability_label(scene: dict) -> str:
    """Styled label for the Availability column."""
    state = availability_of(scene)
    return f"[{AVAILABILITY_LABEL_STYLE[state]}]{AVAILABILITY_LABEL[state]}[/]"


#: Availability state -> its meaning and what to do about it, for the
#: legend below the results table. Only DIRECT_AVAILABLE names a command:
#: ``query download`` is the only action this CLI supports, and the rest
#: have to be requested on the Bhoonidhi portal.
AVAILABILITY_DISPLAY: dict[Availability, tuple[str, str]] = {
    Availability.DIRECT_AVAILABLE: (
        "open data, staged",
        "bhd query download <slug>",
    ),
    Availability.DIRECT_UNAVAILABLE: (
        "open data, cold-stored",
        "download will likely 404 — request it on the Bhoonidhi portal",
    ),
    Availability.ON_ORDER: (
        "must be requested",
        "order it on the Bhoonidhi portal",
    ),
    Availability.PRICED: (
        "requires payment",
        "purchase it on the Bhoonidhi portal",
    ),
}


def availability_of(scene: dict) -> Availability:
    """Classify a scene by pricing first, then staging status.

    Pricing and onOrder scenes are the hard constraint, so they are checked before
    ``CURR_SCENE_NO``. If a scene is priced/onOrder, it is not downloadable regardless
    of whether it is staged or not.
    """
    priced = (scene.get("PRICED") or "").strip()

    if priced == ON_ORDER_PRICED:
        return Availability.ON_ORDER
    if priced != DIRECT_DOWNLOAD_PRICED:
        # Priced, and anything unrecognised: treat as needing the portal
        # rather than implying it can be fetched.
        return Availability.PRICED

    if scene.get("CURR_SCENE_NO") == "Y":
        return Availability.DIRECT_AVAILABLE
    return Availability.DIRECT_UNAVAILABLE


def is_attemptable(scene: dict) -> bool:
    """True if ``query download`` should try to fetch this scene.

    Both DIRECT_* states are attempted. An unstaged scene may still be
    fetchable, and a failed request costs less than refusing it outright.
    """
    return availability_of(scene) in (
        Availability.DIRECT_AVAILABLE,
        Availability.DIRECT_UNAVAILABLE,
    )
