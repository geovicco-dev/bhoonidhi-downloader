"""Search module exports (client + render only — CLI-facing search lives under 'query')."""

from .availability import (
    AVAILABILITY_DISPLAY,
    AVAILABILITY_LABEL,
    AVAILABILITY_LABEL_STYLE,
    Access,
    Availability,
    access_of,
    availability_label,
    availability_of,
    is_attemptable,
)
from .client import SearchManager
from .render import (
    export_search_results,
    get_scenes_data_for_export,
    render_search_results,
)

__all__ = [
    # Client
    "SearchManager",
    # Render functions
    "render_search_results",
    "export_search_results",
    "get_scenes_data_for_export",
    # Availability classification
    "Availability",
    "Access",
    "AVAILABILITY_DISPLAY",
    "AVAILABILITY_LABEL",
    "AVAILABILITY_LABEL_STYLE",
    "availability_of",
    "availability_label",
    "access_of",
    "is_attemptable",
]
