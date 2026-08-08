from typing import Any

from bhoonidhi_downloader.schemas import SearchSchema

from .utils import create_payload, recursive_search


class SearchManager:
    def __init__(self, cfg: SearchSchema, manifest: dict[str, Any]):
        # Get Archive Manifest
        self.manifest = manifest
        # Get SearchScema
        self.cfg = cfg
        # Get Payload
        self.payload = create_payload(self.cfg, self.manifest)

    def search(self):

        # Define Request Headers
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        # Define Base URL
        url = "https://bhoonidhi.nrsc.gov.in/bhoonidhi/ProductSearch"

        # Perform Recursive Search
        self.results = recursive_search(
            payload=self.payload,
            headers=headers,
            url=url,
            max_pages=None,
            verbose=False,
        )

        return self.results
