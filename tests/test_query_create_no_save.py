"""Tests for issue #36: a stateless ``query create`` that saves nothing.

``run_query_create(save=False)`` (and its CLI ``--no-save`` / SDK ``save=False``
surfaces) must run the search identically but write no query file and generate
no slug — while still returning a fully populated ``QuerySchema``. The default
``save=True`` must keep persisting exactly as before.

The portal-facing search is mocked so these run offline: only the save/slug
behaviour is under test, not the network path.
"""

from datetime import datetime

import pytest

from bhoonidhi_downloader.core.query import command as cmd
from bhoonidhi_downloader.schemas import QuerySchema, Selection

_SCENES = [
    {"scene_id": "S1", "DOP": "05-Jan-2026", "srt": "SRT-1"},
    {"scene_id": "S2", "DOP": "03-Jan-2026", "srt": "SRT-1"},
]


@pytest.fixture
def mock_search(monkeypatch):
    """Stub the portal search + manifest and record every save_query call."""

    class _FakeSearchManager:
        def __init__(self, *args, **kwargs):
            pass

        def search(self):
            # Return a copy so the command's in-place sort can't mutate ours.
            return [dict(s) for s in _SCENES]

    class _FakeArchiveManager:
        def build_manifest(self):
            return {}

    saved: list[QuerySchema] = []
    slugs = iter(["fixed-slug", "second-slug"])

    monkeypatch.setattr(cmd, "SearchManager", _FakeSearchManager)
    monkeypatch.setattr(cmd, "ArchiveManager", _FakeArchiveManager)
    monkeypatch.setattr(cmd, "save_query", lambda q: saved.append(q))
    monkeypatch.setattr(cmd, "generate_slug", lambda: next(slugs))
    return saved


def _run(save: bool):
    return cmd.run_query_create(
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 1, 31),
        selections=[Selection(satellite="ResourceSat-2A", sensor="LISS3")],
        minx=91.7,
        maxx=92.0,
        miny=25.5,
        maxy=25.7,
        save=save,
    )


def test_save_false_writes_nothing_and_has_no_slug(mock_search):
    query = _run(save=False)

    assert mock_search == []  # save_query never called
    assert isinstance(query, QuerySchema)
    assert query.slug == ""  # no slug generated
    assert len(query.scenes) == 2  # scene list fully populated


def test_save_true_persists_and_generates_slug(mock_search):
    query = _run(save=True)

    assert query is not None
    assert len(mock_search) == 1  # save_query called exactly once
    assert mock_search[0] is query  # the very query returned was saved
    assert query.slug == "fixed-slug"  # slug generated
    assert len(query.scenes) == 2


def test_save_false_runs_search_identically(mock_search):
    """The scene list is the same whether or not the result is saved —
    save=False only skips the disk write, never changes the search."""
    saved_query = _run(save=True)
    ephemeral_query = _run(save=False)

    assert saved_query is not None and ephemeral_query is not None
    saved_ids = [s["scene_id"] for s in saved_query.scenes]
    ephemeral_ids = [s["scene_id"] for s in ephemeral_query.scenes]
    assert saved_ids == ephemeral_ids
    # Only the one save=True run touched disk.
    assert len(mock_search) == 1
