"""Client-side scene enrichment, ported from the portal's ``makeInterfaceObj``.

A ``ProductSearch`` result is *not* what the portal puts in a cart. Before
calling any add-to-cart endpoint the portal runs the scene through
``makeInterfaceObj()`` (odap.js:2205-2440), which derives a handful of
identifier fields — ``SAT_SPEC``, ``SCENE_SPEC``, ``SUBSCENE_ID`` and their
scheme strings — and sends *that* object as ``selProds``. The servlet stores
whatever it is given, so those fields end up on the cart record.

They matter because the portal's own cart table and map labels read them
back. Add a scene without them and the servlet still answers ``SUCCESS``,
the record really is in the cart, and the footprint still draws — but the
map label renders ``Scene:undefined_undefined`` and the cart table drops the
row entirely, so the item is invisible in the web UI.

The derivation is pure string manipulation over fields already present on
the scene, so it is reproduced here rather than round-tripped through a
browser. Structure and branch order follow the original closely to keep the
two diffable.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

#: Subscene codes the portal recognises (odap.js:57). Anything else means
#: the ID's trailing character is not a subscene marker.
SUBSCENE_CODES: frozenset[str] = frozenset(
    ["A", "B", "C", "D", "F"]
    + [f"{letter}{digit}" for letter in "ABCD" for digit in range(1, 10)]
)


def _s(value: Any) -> str:
    """Stringify like JS does, treating missing values as empty."""
    return "" if value is None else str(value)


def _part(scene_id: str, index: int) -> str:
    """Return the nth underscore-separated part of an ID, or ''."""
    parts = scene_id.split("_")
    return parts[index] if 0 <= index < len(parts) else ""


def _imaging_mode(scene: dict) -> str:
    """Derive IMAGING_MODE the way the portal does."""
    satellite = _s(scene.get("SATELLITE"))
    if satellite == "NISAR":
        return _s(scene.get("IMAGING_MODE")) or "-"
    scene_id = _s(scene.get("ID"))
    if "_" in scene_id and satellite != "O2":
        return _part(scene_id, 2)
    return "-"


def _subscene_id(scene: dict) -> str:
    """Derive SUBSCENE_ID, defaulting to 'F' (full scene)."""
    scene_id = _s(scene.get("ID"))
    candidate = _part(scene_id, 6)
    # PMETA ids of exactly 41 chars carry the subscene as the final char
    # rather than as an underscore-separated part.
    if scene.get("TABLETYPE") == "PMETA" and len(scene_id) == 41:
        candidate = scene_id[40:]
    return candidate if candidate in SUBSCENE_CODES else "F"


def _sat_spec(scene: dict, imaging_mode: str, subscene_id: str) -> tuple[str, str]:
    """Build SAT_SPEC and its scheme string."""
    satellite = _s(scene.get("SATELLITE"))
    sensor = _s(scene.get("SENSOR"))
    prodtype = _s(scene.get("PRODTYPE"))
    tabletype = _s(scene.get("TABLETYPE"))

    sub = "F"
    if "F" not in subscene_id and sensor != "LIS4":
        sub = "S"
    if (
        satellite in ("1C", "1D")
        and sensor == "PAN"
        and subscene_id in ("A", "B", "C", "D")
    ):
        sub = "F"

    scheme = "Satellite_Sensor_ImagingMode_Subscene"
    spec = f"{satellite}_{sensor}_{imaging_mode}_{sub}"

    if satellite in ("NISAR", "E08", "E04", "E09") or (
        satellite == "N19" and tabletype == "PMETA"
    ):
        scheme = "Satellite_Sensor_ImagingMode"
        spec = f"{satellite}_{sensor}_{imaging_mode}"
    elif satellite == "C03":
        scheme = "Satellite_Sensor_ImagingMode"
        spec = f"{satellite}_{sensor}_{imaging_mode}"
        if "swath" in prodtype:
            spec += f"_{prodtype}"
            scheme += "_Swath"
    elif satellite in ("GISAT-1A", "G1A"):
        sensor = _part(_s(scene.get("ID")), 1)
        scheme = "Satellite_Sensor"
        spec = f"{satellite}_{sensor}"
    elif satellite.startswith("E06") and sensor.startswith("OCM") and "day" in prodtype:
        scheme = "Satellite_Sensor_ImagingMode"
        spec = f"{satellite}_{sensor}_{imaging_mode}"

    if tabletype == "TMETA":
        spec = (
            f"{satellite}_{sensor}_{imaging_mode}_"
            f"{prodtype.replace('CartoDEM-', '')}"
        )
        scheme = "Satellite_Sensor_ImagingMode_Resolution"
    elif tabletype == "PMETA" and prodtype != "Others":
        spec += f"_{prodtype}"
        scheme += "_Product"
        if satellite.startswith("E06") and sensor.startswith("SCT"):
            parts = _s(scene.get("ID")).split("_")
            if len(parts) >= 2:
                spec += f"_{parts[-2]}"
            scheme += "_Resolution"

    if (
        tabletype == "PMETA"
        and satellite in ("E09", "E04")
        and prodtype
        not in (
            "L3B",
            "1x1deg-tiles",
            "WaterSpread",
            "SoilMoisture",
            "ShipDetection",
            "OilSpill",
            "OceanSurfaceWind",
        )
    ):
        spec += f"_{_part(_s(scene.get('ID')), 9)}"
        scheme += "_TxPol"

    if satellite == "NISAR":
        if prodtype == "Others":
            spec += f"_{_part(_s(scene.get('ID')), 3)}"
            scheme += "_Product"
        spec += f"_{_s(scene.get('POLARIZATION'))}"
        scheme += "_Polarization"

    if satellite in ("NPP", "JP1"):
        tail = _s(scene.get("ID")).split("_")[-1]
        spec += f"_{tail}"

    return spec, scheme


def _scene_spec(scene: dict, imaging_mode: str, subscene_id: str) -> tuple[str, str]:
    """Build SCENE_SPEC and its scheme string."""
    satellite = _s(scene.get("SATELLITE"))
    sensor = _s(scene.get("SENSOR"))
    prodtype = _s(scene.get("PRODTYPE"))
    scene_id = _s(scene.get("ID"))
    orbit = _s(scene.get("GROUND_ORBIT_NO"))
    img_orbit = _s(scene.get("IMAGING_ORBIT_NO"))
    strip = _s(scene.get("STRIP_NO"))
    path = _s(scene.get("PATHNO"))
    row = _s(scene.get("SCENE_NO"))

    # Default, overridden by the mission-specific branches below.
    spec = f"{orbit}_{strip}_{row}"
    scheme = "GroundOrbit_Strip_Scene"

    if scene.get("Scene_Identifier"):
        spec = _s(scene.get("Scene_Identifier"))
        scheme = _s(scene.get("Scene_Identifier_Scheme"))
        if scene.get("RCID"):
            spec += f"_{_s(scene.get('RCID'))}"
            scheme += "_RCID"
    elif sensor.startswith("GNSS"):
        spec, scheme = f"{orbit}_{row}", "GroundOrbit_Scene"
    elif satellite.startswith("SEN"):
        spec = f"{orbit}_{_s(scene.get('TILE_ID'))}"
        scheme = "GroundOrbit_TileID"
    elif satellite.startswith(("E04", "E09")):
        if prodtype in ("1x1deg-tiles", "WaterSpread"):
            spec = f"{_part(scene_id, 5)}_{_part(scene_id, 6)}"
            scheme = "CycleNo_TileID"
        else:
            spec = f"{orbit}_{img_orbit}_{_s(scene.get('STRIP_ID'))}_{row}"
            scheme = "GroundOrbit_ImagingOrbit_Strip_Scene"
    elif satellite.startswith("N19"):
        spec = f"{orbit}_{img_orbit}_{strip}_{row}"
        scheme = "GroundOrbit_ImagingOrbit_Strip_Scene"
    elif (satellite.startswith("SC1") and sensor.startswith("SCAT")) or (
        satellite.startswith("E06") and sensor.startswith("SCT")
    ):
        # Two separate branches in odap.js with identical bodies; kept as
        # one condition here, parenthesised so the grouping is explicit.
        spec, scheme = f"{orbit}_{row}", "GroundOrbit_Scene"
    elif satellite.startswith("E06") and _s(scene.get("BINPERIOD")):
        spec = f"{_s(scene.get('BINPERIOD'))}_{_s(scene.get('BINRESOLUTION'))}"
        scheme = "BinningPeriod_Resolution"
    elif satellite.startswith("G29"):
        spec, scheme = f"{orbit}_{row}", "GroundOrbit_Scene"
    elif satellite == "C2":
        spec = f"{orbit}_{img_orbit}_{_part(scene_id, 12)}_{strip}_{row}"
        scheme = "GroundOrbit_ImagingOrbit_Segment_Strip_Scene"
    elif satellite in ("C2A", "C2B", "C2C", "C2D"):
        spec = f"{orbit}_{img_orbit}_{_part(scene_id, 11)}_{strip}_{row}"
        scheme = "GroundOrbit_ImagingOrbit_Session_Strip_Scene"
    elif satellite in ("C2E", "C2F", "C03"):
        spec = f"{orbit}_{_part(scene_id, 11)}_{strip}_{row}"
        scheme = "GroundOrbit_Session_Strip_Scene"
    elif satellite.startswith("O2") and sensor.startswith("SCAT"):
        spec, scheme = orbit, "GroundOrbit"
    elif satellite.startswith("O2") and sensor.startswith("OCM"):
        spec, scheme = f"{path}_{row}", "Path_Row"
    elif satellite.startswith("RS2") and "4x4deg-tiles" in prodtype:
        spec = f"{_part(scene_id, 6)}_{_part(scene_id, 5)}day"
        scheme = "TileID_BinningPeriod"
    elif satellite.startswith(("RS2", "P6")) and "tiles" in prodtype:
        spec = f"{_part(scene_id, 3)}_{_part(scene_id, 4)}_{_part(scene_id, 5)}"
        scheme = "TileID_Path_Row"
    elif satellite.startswith(("RS2", "P6")) and "day" in prodtype:
        spec = f"{_part(scene_id, 5)}day_{path}"
        scheme = "BinningPeriod_TileID"
    elif (
        satellite.startswith(("RS2", "R2A", "L8", "L9", "P4", "P5", "P6"))
        or (satellite.startswith("E06") and sensor.startswith(("OCM", "SST")))
    ):
        spec = f"{orbit}_{path}_{row}"
        scheme = "GroundOrbit_Path_Row"
        if sensor == "AWIF" or imaging_mode in ("FMX", "MN"):
            spec += f"_{subscene_id}"
            scheme += "_Subscene"
        elif satellite.startswith("P6") and imaging_mode == "SMX":
            spec += f"_{_part(scene_id, 13)}"
            scheme += "_StripNo"
        elif satellite.startswith(("RS2", "R2A")) and imaging_mode == "SMX":
            spec += f"_{_part(scene_id, 23)}"
            scheme += "_StripNo"
        elif satellite.startswith("P5") and "CartoDEM" in prodtype:
            spec, scheme = scene_id, "TileID"
    elif satellite.startswith(("1A", "1B", "1C", "1D", "L5", "AQ", "TE", "N1")):
        spec, scheme = f"{path}_{row}", "Path_Row"
        if sensor in ("AWIF", "LIS4", "LIS2", "PAN"):
            spec += f"_{subscene_id}"
            scheme += "_Subscene"

    return spec, scheme


def make_interface_obj(scene: dict) -> dict:
    """Return a copy of ``scene`` enriched the way the portal enriches it.

    Adds ``IMAGING_MODE``, ``SUBSCENE_ID``, ``SAT_SPEC``,
    ``SAT_SPEC_SCHEME``, ``SCENE_SPEC``, ``SCENE_SPEC_SCHEME``,
    ``SCENE_ID`` and ``IMG_PATH``. Without these a cart record is accepted
    by the servlet but cannot be rendered by the portal's cart table.

    The input is not mutated.

    Raises:
        ValueError: if a field the derivation depends on is missing.
            Deriving from absent values would yield a plausible-looking
            but wrong spec (``__SP_F``), which the servlet accepts happily
            and the portal then fails to render — the same silent failure
            this module exists to prevent.
    """
    missing = [
        key
        for key in ("ID", "SATELLITE", "SENSOR", "TABLETYPE")
        if not _s(scene.get(key))
    ]
    if missing:
        raise ValueError(
            f"Cannot derive cart identifiers for scene {scene.get('ID', '<no ID>')!r}: "
            f"missing {', '.join(missing)}"
        )

    enriched = dict(scene)

    imaging_mode = _imaging_mode(enriched)
    enriched["IMAGING_MODE"] = imaging_mode

    subscene_id = _subscene_id(enriched)
    enriched["SUBSCENE_ID"] = subscene_id

    sat_spec, sat_scheme = _sat_spec(enriched, imaging_mode, subscene_id)
    # GISAT rewrites SENSOR off the ID; mirror that so the stored record
    # matches what the portal would have sent.
    if _s(enriched.get("SATELLITE")) in ("GISAT-1A", "G1A"):
        enriched["SENSOR"] = _part(_s(enriched.get("ID")), 1)

    scene_spec, scene_scheme = _scene_spec(enriched, imaging_mode, subscene_id)

    enriched["SAT_SPEC"] = sat_spec
    enriched["SAT_SPEC_SCHEME"] = sat_scheme
    enriched["SCENE_SPEC"] = scene_spec
    enriched["SCENE_SPEC_SCHEME"] = scene_scheme
    enriched["SCENE_ID"] = enriched.get("ID")

    suffix = {"SMETA": ".jpeg", "PMETA": ".jpg"}.get(_s(enriched.get("TABLETYPE")), "")
    dirpath = _s(enriched.get("DIRPATH"))
    filename = _s(enriched.get("FILENAME"))
    enriched["IMG_PATH"] = f"{dirpath}/{filename}{suffix}"

    return enriched
