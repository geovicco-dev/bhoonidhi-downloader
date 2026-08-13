import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from bhoonidhi_downloader.exceptions import BhoonidhiAPIError

CACHE_DIR = Path(os.path.join(os.path.expanduser("~"), ".bhoonidhi"))
ARCHIVE_PATH = CACHE_DIR / "archive.json"
MANIFEST_PATH = CACHE_DIR / "manifest.json"

# ------------------------------
# Fetch entire Bhoonidhi archive JSON from the web and cache it locally
# ------------------------------


class ArchiveManager:
    def __init__(self, refresh: bool | None = False):
        self.archive: list[dict[str, Any]] = []
        self.manifest: dict[str, dict[str, list[dict]]] = {}

        if refresh:
            self.refresh()
        else:
            self._load()

    def refresh(self) -> None:
        """Fetch the full archive from the web and update the local cache."""
        self.fetch()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        ARCHIVE_PATH.write_text(json.dumps(self.archive, indent=2))
        self.manifest = self.build_manifest(save=True)

    def _load(self) -> None:
        """Load the cached archive + manifest, fetching + caching on first run."""
        if not ARCHIVE_PATH.exists():
            self.refresh()
            return
        self.archive = json.loads(ARCHIVE_PATH.read_text())
        if MANIFEST_PATH.exists():
            self.manifest = json.loads(MANIFEST_PATH.read_text())
        else:
            self.manifest = self.build_manifest(save=True)

    def fetch(self) -> list[dict[str, Any]]:
        """Fetch the entire Bhoonidhi archive JSON from the web.
        Returns:
            A list of satellite records, each a dict with keys like 'name', 'sensors', etc.
        """

        url = "https://bhoonidhi.nrsc.gov.in/bhoonidhi/SatSenServlet"
        payload = {"userId": "T", "action": "GETAVCONFIG", "userEmail": "abc@xyz.com"}
        response = requests.post(url, json=payload, timeout=30)

        if response.status_code != 200:
            raise BhoonidhiAPIError(
                f"Archive request failed. Status code: {response.status_code}"
            )

        self.archive = response.json().get("Results", [])
        return self.archive

    def parse(self, satellite_filter: str | None = None) -> list[dict[str, Any]]:

        if satellite_filter:
            self.archive = self.format_archive(self.archive, satellite_filter)
        else:
            self.archive = self.format_archive(self.archive)

        return self.archive

    @staticmethod
    def format_archive(
        archive_data: list[dict[str, Any]],
        satellite_filter: str | None = None,
    ) -> list[dict[str, Any]]:

        def _normalize_products(products: Any | None) -> str | None:
            """Normalize products to a list of strings."""
            if products is None:
                return None
            if isinstance(products, list):
                return next(str(p).strip() for p in products if str(p).strip())
            return str(products)

        results: list[dict[str, Any]] = []

        for idx, record in enumerate(archive_data, start=1):
            # Skip if filtering by satellite
            if satellite_filter and record.get("satName") != satellite_filter:
                continue

            min_res = record.get("thisMinRes")
            max_res = record.get("thisMaxRes")
            resolution = f"{min_res} - {max_res}" if min_res != max_res else min_res

            start_raw = record.get("totalStartDate")
            start = (
                datetime.strptime(start_raw, "%m/%d/%Y").strftime("%d %B %Y")
                if start_raw
                else "N/A"
            )

            end_raw = record.get("totalEndDate", "")
            end = (
                datetime.strptime(end_raw, "%m/%d/%Y").strftime("%d %B %Y")
                if end_raw != ""
                else "till date"
            )
            availability = f"{start} - {end}"

            collections: list[dict[str, dict[str, Any]]] = [
                {
                    str(r.get("dispName", "")): {
                        "sensor": r.get("senName"),
                        "resolution": r.get("res"),
                        "start_date": r.get("stDate"),
                        "end_date": r.get("endDate"),
                        "product": _normalize_products(r.get("products")),
                    }
                }
                for r in record.get("sensors", [])
                if r.get("dispName")
            ]

            access_level = record.get("priced", "N/A").split("_")[-1]

            results.append(
                {
                    "index": idx,
                    "satellite": record.get("satName"),
                    "availability": availability,
                    "availability_start": start,
                    "availability_end": end,
                    "access_level": access_level,
                    "collections": collections,
                    "resolution": resolution,
                    "min_resolution": min_res,
                    "max_resolution": max_res,
                }
            )

        return results

    def build_manifest(self, save: bool = False) -> dict[str, dict[str, list[dict]]]:
        """Build nested Dict: satellite -> sensor -> [{product, dispName}]."""
        manifest: dict[str, dict[str, list[dict]]] = {}
        for record in self.archive:
            sat = record.get("satName")
            if not sat:
                continue
            if sat not in manifest:
                manifest[sat] = {}
            for sensor in record.get("sensors", []):
                sen_name = sensor["senName"]
                if sen_name not in manifest[sat]:
                    manifest[sat][sen_name] = []
                manifest[sat][sen_name].append(
                    {
                        "product": sensor.get("products"),
                        "dispName": sensor.get("dispName"),
                        "resolution": sensor.get("res"),
                        "startDate": sensor.get("stDate"),
                        "endDate": None
                        if sensor.get("endDate") == ""
                        else sensor.get("endDate"),
                    }
                )

        if save:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
        return manifest
