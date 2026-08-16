"""Migration test: legacy saved queries load into the selections model.

Queries saved before multi-selection carried scalar ``satellite`` +
optional ``sensor`` fields. QuerySchema folds those into a one-element
``selections`` list on read, so old files keep working.
"""

from bhoonidhi_downloader.schemas import QuerySchema

_BASE = {
    "slug": "velvet-wren",
    "name": "old query",
    "description": "saved before multi-selection",
    "created_at": "2026-01-01T00:00:00",
    "aoi": {
        "name": "aoi",
        "mode": "bbox",
        "min_lon": 91.8,
        "min_lat": 25.5,
        "max_lon": 92.0,
        "max_lat": 25.7,
    },
    "start_date": "2026-01-01T00:00:00",
    "end_date": "2026-01-31T00:00:00",
    "scenes": [],
}


def test_legacy_satellite_and_sensor_migrates():
    data = {**_BASE, "satellite": "ResourceSat-2A", "sensor": "LISS3"}
    q = QuerySchema.model_validate(data)
    assert len(q.selections) == 1
    assert q.selections[0].satellite == "ResourceSat-2A"
    assert q.selections[0].sensor == "LISS3"
    assert q.selections[0].product is None


def test_legacy_satellite_only_migrates():
    data = {**_BASE, "satellite": "CartoSat-3"}
    q = QuerySchema.model_validate(data)
    assert len(q.selections) == 1
    assert q.selections[0].satellite == "CartoSat-3"
    assert q.selections[0].sensor is None


def test_new_selections_shape_loads_unchanged():
    data = {
        **_BASE,
        "selections": [
            {"satellite": "EOS-06", "sensor": "OCM(GAC)", "product": "L2C-NDVI"},
            {"satellite": "CartoSat-3"},
        ],
    }
    q = QuerySchema.model_validate(data)
    assert [s.label() for s in q.selections] == [
        "EOS-06/OCM(GAC)/L2C-NDVI",
        "CartoSat-3",
    ]
