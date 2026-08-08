"""Search module exports (client + render only — CLI-facing search lives under 'query')."""

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
]
