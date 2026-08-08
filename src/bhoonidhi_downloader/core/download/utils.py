"""URL building and download-eligibility helpers for Bhoonidhi scenes."""

from __future__ import annotations

BASE_URL = "https://bhoonidhi.nrsc.gov.in"

# Only scenes with this PRICED value support direct, cart-free download.
# Anything else (OpenData_OnOrder, Priced_*, ...) is metadata/planning-only
# until the cart/order flow is implemented.
DIRECT_DOWNLOAD_PRICED = "OpenData_DirectDownload"

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


def is_downloadable(scene: dict) -> bool:
    """True if a scene can be fetched directly, without going through the cart."""
    return scene.get("PRICED") == DIRECT_DOWNLOAD_PRICED


def download_filename(scene: dict) -> str:
    """Filename (with extension) a scene will be saved as."""
    satellite = scene.get("SATELLITE")
    sensor = scene.get("SENSOR")
    filename = scene.get("FILENAME") or scene.get("ID")
    ext = "h5" if satellite == "NISAR" and sensor == "SSAR" else "zip"
    return f"{filename}.{ext}"


def build_download_url(scene: dict, jwt: str) -> str:
    """Build the direct-download URL for a scene, given a valid session JWT.

    Mirrors the satellite/sensor short-code remapping the portal's data
    path expects (e.g. ResourceSat-2A LISS3 -> '3'). The year/month path
    segments are derived the same way the original implementation did:
    ``DIRPATH.split("/")[-4:][:2]`` (the first two of the last four path
    segments) — for a typical DIRPATH this lands on year and month, no
    day folder.
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
