"""URL building and download-eligibility helpers for Bhoonidhi scenes."""

from __future__ import annotations

from pathlib import PurePosixPath

BASE_URL = "https://bhoonidhi.nrsc.gov.in"

# (satellite, sensor) -> short code the portal's data path expects.
# Sensors not listed here are used as-is (dynamic path). A few satellites
# (P5/PAN, NISAR/SSAR) additionally need a hard-coded path shape below —
# more of these may turn up as new sensors are exercised.
_SENSOR_REMAP = {
    ("R2A", "LIS3"): "3",
    ("R2A", "LIS4"): "F",
    ("R2A", "AWIF"): "W",
    ("RS2", "LIS3"): "3",
    ("RS2", "LIS4"): "F",
    ("RS2", "AWIF"): "W",
    ("SEN2A", "MSI"): "MSI",
    ("SEN2B", "MSI"): "MSI",
    ("SEN1A", "SAR"): "SAR",
    ("SEN1B", "SAR"): "SAR",
    ("L8", "O"): "O",
    ("L9", "O"): "O",
}


def download_filename(scene: dict) -> str:
    """Filename (with extension) a scene will be saved as.

    The name is taken from portal-supplied metadata, so it is reduced to
    a bare basename before use: a FILENAME containing path separators
    (``../..``, ``/etc/passwd``) would otherwise escape the user's --out
    directory when joined onto it. Anything that reduces to nothing
    usable falls back to the scene ID.
    """
    satellite = scene.get("SATELLITE")
    sensor = scene.get("SENSOR")
    raw = scene.get("FILENAME") or scene.get("ID") or ""
    # PurePosixPath/ntpath both matter: the portal is Unix-side, but a
    # backslash-bearing name must not become a path component on Windows.
    stem = PurePosixPath(str(raw).replace("\\", "/")).name
    if stem in ("", ".", ".."):
        stem = str(scene.get("ID") or "scene")
    ext = "h5" if satellite == "NISAR" and sensor == "SSAR" else "zip"
    return f"{stem}.{ext}"


def build_download_url(scene: dict, jwt: str) -> str:
    """Build the direct-download URL for a scene, given a valid session JWT.

    Mirrors the satellite/sensor short-code remapping the portal's data
    path expects (e.g. ResourceSat-2A LISS3 -> '3'). The year/month path
    segments are derived from ``DIRPATH.split("/")[-4:][:2]`` — the first
    two of the last four path segments, which for a typical DIRPATH lands
    on year and month with no day folder.
    """
    satellite = scene.get("SATELLITE")
    sensor = scene.get("SENSOR")
    dirpath = scene.get("DIRPATH") or ""
    filename = scene.get("FILENAME") or scene.get("ID")

    if not satellite or not sensor or not filename:
        raise ValueError(f"Scene missing SATELLITE/SENSOR/FILENAME: {scene.get('ID')}")

    mapped_sensor = _SENSOR_REMAP.get((satellite, sensor), sensor)

    base = f"{BASE_URL}/bhoonidhi/data"
    date_parts = dirpath.split("/")[-4:][:2]
    year = date_parts[0] if len(date_parts) > 0 else ""
    month = date_parts[1] if len(date_parts) > 1 else ""

    if satellite == "P5" and mapped_sensor == "PAN":
        return (
            f"{base}/CARTODEM/{satellite}/{mapped_sensor}/30m/{filename}.zip"
            f"?token={jwt}&product_id={filename}"
        )
    if satellite == "NISAR" and sensor == "SSAR":
        return (
            f"{base}/{satellite}/{sensor}/{year}/{month}/{filename}.h5"
            f"?token={jwt}&product_id={filename}"
        )
    return (
        f"{base}/{satellite}/{mapped_sensor}/{year}/{month}/{filename}.zip"
        f"?token={jwt}&product_id={filename}"
    )
