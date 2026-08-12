"""Tests for search/query rendering: full names and the Search IDs column."""

from datetime import datetime

from bhoonidhi_downloader.core.query.render import _query_list_columns
from bhoonidhi_downloader.core.search.utils import full_satellite, full_sensor
from bhoonidhi_downloader.schemas import QuerySchema
from bhoonidhi_downloader.schemas.aoi import AOISchema

# --------------------------------------------------------------------------
# Full satellite / sensor names (shared by search and cart tables)
# --------------------------------------------------------------------------


def test_full_satellite_takes_the_first_part_of_selection():
    scene = {"SELECTION": "ResourceSat-2A_AWIFS_BOA-Archives", "SATELLITE": "R2A"}
    assert full_satellite(scene) == "ResourceSat-2A"


def test_full_sensor_takes_the_second_part_of_selection():
    scene = {"SELECTION": "ResourceSat-2A_AWIFS_BOA-Archives", "SENSOR": "AWIF"}
    assert full_sensor(scene) == "AWIFS"


def test_full_name_handles_parenthesised_sensor():
    scene = {"SELECTION": "CartoSat-3_PAN(SPOT)", "SATELLITE": "C03", "SENSOR": "PAN"}
    assert full_satellite(scene) == "CartoSat-3"
    assert full_sensor(scene) == "PAN(SPOT)"


def test_full_satellite_falls_back_to_short_code_without_selection():
    assert full_satellite({"SATELLITE": "R2A"}) == "R2A"


def test_full_sensor_falls_back_to_short_code_without_selection():
    assert full_sensor({"SENSOR": "AWIF"}) == "AWIF"


def test_full_sensor_falls_back_when_selection_has_no_second_part():
    assert full_sensor({"SELECTION": "OnlySatellite", "SENSOR": "AWIF"}) == "AWIF"


# --------------------------------------------------------------------------
# query list — Search IDs column
# --------------------------------------------------------------------------


def _query(scenes: list[dict]) -> QuerySchema:
    return QuerySchema(
        slug="misty-falcon",
        name="test",
        description="test",
        created_at=datetime(2026, 8, 12),
        satellite="Sentinel-2A",
        aoi=AOISchema(),
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 1, 30),
        scenes=scenes,
    )


def _search_ids_cell(query: QuerySchema) -> str:
    column = next(c for c in _query_list_columns() if c.header == "Search IDs")
    return column.render(query, 0)


def test_query_list_has_a_search_ids_column():
    headers = [c.header for c in _query_list_columns()]
    assert "Search IDs" in headers


def test_search_ids_lists_every_distinct_srt_for_a_refreshed_query():
    query = _query(
        [
            {"srt": "20260101_AAA"},
            {"srt": "20260101_AAA"},  # duplicate collapses
            {"srt": "20260115_BBB"},  # a later refresh's search
        ]
    )
    assert _search_ids_cell(query) == "20260101_AAA\n20260115_BBB"


def test_search_ids_is_na_when_no_scene_carries_one():
    assert _search_ids_cell(_query([{"ID": "x"}])) == "N/A"

