"""Slug generation, auto-naming, and storage for saved queries."""

import json
import logging
import random
from datetime import datetime
from pathlib import Path

from bhoonidhi_downloader.schemas import AOISchema, QuerySchema

QUERIES_DIR = Path.home() / ".bhoonidhi" / "queries"

logger = logging.getLogger(__name__)

_ADJECTIVES = [
    "amber",
    "azure",
    "brisk",
    "cosmic",
    "crimson",
    "dusky",
    "ember",
    "fleet",
    "gentle",
    "golden",
    "hazy",
    "hidden",
    "ivory",
    "jade",
    "keen",
    "lucid",
    "misty",
    "noble",
    "opal",
    "pale",
    "quiet",
    "rustic",
    "sable",
    "silent",
    "steel",
    "still",
    "sunny",
    "swift",
    "teal",
    "umber",
    "velvet",
    "violet",
    "wild",
    "wispy",
    "amber",
    "bold",
    "calm",
    "coral",
    "deep",
    "dusty",
]

_NOUNS = [
    "falcon",
    "glacier",
    "heron",
    "meadow",
    "ridge",
    "canyon",
    "harbor",
    "summit",
    "valley",
    "prairie",
    "delta",
    "cove",
    "grove",
    "reef",
    "plateau",
    "tundra",
    "orchard",
    "basin",
    "cliff",
    "marsh",
    "dune",
    "fjord",
    "peak",
    "lagoon",
    "forest",
    "hollow",
    "mesa",
    "shoal",
    "spire",
    "brook",
    "thicket",
    "vale",
    "wren",
    "otter",
    "lynx",
    "sparrow",
    "heath",
    "moor",
    "cape",
    "isle",
]


def generate_slug() -> str:
    """Generate a unique adjective-noun slug, avoiding collisions with existing queries."""
    QUERIES_DIR.mkdir(parents=True, exist_ok=True)
    for _ in range(50):
        slug = f"{random.choice(_ADJECTIVES)}-{random.choice(_NOUNS)}"
        if not (QUERIES_DIR / f"{slug}.json").exists():
            return slug
    # Extremely unlikely: fall back to a numbered suffix.
    base = f"{random.choice(_ADJECTIVES)}-{random.choice(_NOUNS)}"
    n = 2
    while (QUERIES_DIR / f"{base}-{n:02d}.json").exists():
        n += 1
    return f"{base}-{n:02d}"


def generate_name(
    satellite: str, sensor: str | None, start_date: datetime, end_date: datetime
) -> str:
    """Auto-generate a human-readable name from query params."""
    sensor_part = f" {sensor}" if sensor else ""
    if start_date.strftime("%b %Y") == end_date.strftime("%b %Y"):
        window = start_date.strftime("%b %Y")
    else:
        window = f"{start_date.strftime('%b %Y')}\u2013{end_date.strftime('%b %Y')}"
    return f"{satellite}{sensor_part} scenes, {window}"


def generate_description(
    satellite: str,
    sensor: str | None,
    aoi: AOISchema,
    start_date: datetime,
    end_date: datetime,
    scene_count: int,
) -> str:
    """Auto-generate a description from query params + result count."""
    sensor_part = f"/{sensor}" if sensor else ""
    bbox = (
        f"[{aoi.min_lon:.2f}, {aoi.min_lat:.2f}, {aoi.max_lon:.2f}, {aoi.max_lat:.2f}]"
    )
    return (
        f"{satellite}{sensor_part} query over bbox {bbox}, "
        f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} "
        f"\u2014 {scene_count} scene(s) found."
    )


def query_path(slug: str) -> Path:
    return QUERIES_DIR / f"{slug}.json"


def save_query(query: QuerySchema) -> None:
    QUERIES_DIR.mkdir(parents=True, exist_ok=True)
    query_path(query.slug).write_text(query.model_dump_json(indent=2))


def load_query(slug: str) -> QuerySchema | None:
    path = query_path(slug)
    if not path.exists():
        return None
    return QuerySchema.model_validate(json.loads(path.read_text()))


def list_queries() -> list[QuerySchema]:
    QUERIES_DIR.mkdir(parents=True, exist_ok=True)
    queries = []
    for path in sorted(QUERIES_DIR.glob("*.json")):
        try:
            queries.append(QuerySchema.model_validate(json.loads(path.read_text())))
        except Exception:
            logger.warning(
                "Skipping unreadable/corrupt query file: %s", path, exc_info=True
            )
            continue
    return queries


def delete_query(slug: str) -> bool:
    path = query_path(slug)
    if path.exists():
        path.unlink()
        return True
    return False
