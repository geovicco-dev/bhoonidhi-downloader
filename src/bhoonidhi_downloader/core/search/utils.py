import random
import time
from typing import Any
import requests
from rich.live import Live
from rich.spinner import Spinner
from bhoonidhi_downloader.logger import get_console


def create_payload(cfg: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    sdate: str = cfg.start_date.strftime("%b%%2F%d%%2F%Y").upper()
    edate: str = cfg.end_date.strftime("%b%%2F%d%%2F%Y").upper()
    assert cfg.satellite is not None
    assert cfg.sensor is not None
    col_meta = manifest[cfg.satellite][cfg.sensor]

    sat_sen = [str(col.get("dispName", "")) for col in col_meta if col.get("dispName")]

    if isinstance(sat_sen, list) and len(sat_sen) > 1:
        sat_sen = "%2C".join(sat_sen)
    elif isinstance(sat_sen, list) and len(sat_sen) == 1:
        sat_sen = sat_sen[0]
    return {
        "userId": "T",
        "prod": "Standard",
        "selSats": sat_sen,
        "offset": "0",
        "sdate": sdate,
        "edate": edate,
        "query": "area",
        "queryType": "polygon",
        "isMX": "No",
        "tllat": cfg.aoi.max_lat,
        "tllon": cfg.aoi.min_lon,
        "brlat": cfg.aoi.min_lat,
        "brlon": cfg.aoi.max_lon,
        "filters": "%7B%7D",
    }


def recursive_search(
    payload: dict,
    headers: dict,
    url: str,
    verbose: bool = False,
    max_pages: int | None = None,
    max_results: int | None = None,
    session: requests.Session | None = None,
) -> list:
    """Fetch every page of a Bhoonidhi search using the ``srt`` cursor + offset.

    Improvements over the original:
    - Does NOT mutate the caller's ``payload`` Dict (makes a shallow copy).
    - Retries transient server errors (5xx, 429) with exponential back-off.
    - Validates that the response has the expected shape.
    - Deduplicates scenes by their ``ID`` (or ``sceneId``/``id``) so overlapping
      pages do not produce duplicates.
    - Adds jitter to the inter-page sleep to avoid thundering-herds.
    - Optionally reuses a ``requests.Session`` for connection pooling.
    - Returns a plain ``List`` of scene Dicts (same public API).
    """
    # --- public API: never mutate the caller's payload ---
    payload = {**payload}
    console = get_console()

    # --- helpers ---
    _post = session.post if session else requests.post
    max_retries = 3
    base_delay = 1.0

    def _fetch_page(
        page_num: int, cur_offset: int, cur_srt: str | None, spinner: Any = None
    ) -> tuple[dict, int]:
        """Single POST with retry. Returns (parsed JSON, page_size)."""
        page_payload = {**payload, "offset": str(cur_offset)}
        if cur_srt:
            page_payload["srt"] = cur_srt

        if verbose:
            console.print(f"\n--- Fetching page {page_num} ---")
            console.print(f"  offset={cur_offset}, srt={cur_srt}")

        for attempt in range(1, max_retries + 1):
            try:
                resp = _post(url, headers=headers, json=page_payload, timeout=(10, 60))
                # 4xx → fail fast; 5xx / 429 → retry
                if resp.status_code >= 500 or resp.status_code == 429:
                    delay = base_delay * (2 ** (attempt - 1)) + random.random() * 0.5
                    if verbose:
                        console.print(
                            f"  Server error {resp.status_code}, retry {attempt}/{max_retries} in {delay:.1f}s"
                        )
                    if spinner:
                        spinner.update(
                            Spinner(
                                "dots", f"Retrying… (attempt {attempt}/{max_retries})"
                            )
                        )
                    time.sleep(delay)
                    continue
                resp.raise_for_status()
                data = resp.json()
                results = data.get("Results", [])
                page_size = len(results)
                if verbose:
                    console.print(f"  Results returned: {page_size}")
                return data, page_size
            except requests.RequestException as exc:
                if attempt == max_retries:
                    raise
                delay = base_delay * (2 ** (attempt - 1)) + random.random() * 0.5
                if verbose:
                    console.print(
                        f"  Network error: {exc}, retry {attempt}/{max_retries} in {delay:.1f}s"
                    )
                if spinner:
                    spinner.update(
                        Spinner("dots", f"Retrying… (attempt {attempt}/{max_retries})")
                    )
                time.sleep(delay)
        raise ValueError("unreachable — all retries should have raised")

    # --- page 1 ---
    spinner = Spinner("dots", "Fetching scenes…")
    with Live(spinner, console=console, refresh_per_second=12) as live:
        data, page_size = _fetch_page(1, 0, None, live)
        results = data.get("Results", [])

        if not results:
            return []

        all_results: list = []
        seen_ids: set[str] = set()
        for r in results:
            sid = r.get("ID") or r.get("sceneId") or r.get("id")
            if sid and sid not in seen_ids:
                seen_ids.add(sid)
                all_results.append(r)

        srt_cursor = results[0].get("srt") if results else None
        live.update(Spinner("dots", f"Fetched {len(all_results)} scenes…"))
        if verbose:
            console.print(f"  Pagination cursor (srt): {srt_cursor}")

        if not srt_cursor:
            console.print(f"Fetched {len(all_results)} scenes")
            return all_results

        # Derive the actual page size from page 1's result count.
        # If page 1 returns fewer than 500, that IS the page size —
        # jumping to offset=500 would skip past all available data.
        offset = page_size

        # --- subsequent pages ---
        page = 2
        while True:
            data, page_size = _fetch_page(page, offset, srt_cursor, live)
            results = data.get("Results", [])

            if not results:
                if verbose:
                    console.print("  Last page reached (empty Results), stopping.")
                break

            # Deduplicate by scene-level "ID" (primary key), with
            # "sceneId"/"id" as fallbacks — prevents counting the
            # same scene multiple times when it has multiple products.
            new_count = 0
            for r in results:
                sid = r.get("ID") or r.get("sceneId") or r.get("id")
                if sid and sid in seen_ids:
                    continue
                seen_ids.add(sid)
                all_results.append(r)
                new_count += 1

            live.update(Spinner("dots", f"Fetched {len(all_results)} scenes…"))

            if verbose:
                console.print(
                    f"  Page {page}: {len(results)} returned, {new_count} new"
                )
                if max_results:
                    console.print(
                        f"  Running total: {len(all_results)} (max_results={max_results})"
                    )

            if max_results and len(all_results) >= max_results:
                if verbose:
                    console.print(f"  Reached max_results ({max_results}), stopping.")
                break

            offset += len(results)
            page += 1

            if max_pages and page > max_pages:
                if verbose:
                    console.print(f"  Reached max_pages limit ({max_pages}), stopping.")
                break

            time.sleep(0.5 + random.random() * 0.3)  # jittered sleep

        live.update(Spinner("dots", f"Found {len(all_results)} scenes."))

    return all_results


def get_scene_meta_url(scene: dict) -> str:
    dirpath = scene["DIRPATH"]
    filename = scene["FILENAME"]
    scene_id = scene.get("ID")
    if scene_id and "NISAR" in scene_id:
        return f"https://bhoonidhi.nrsc.gov.in/{dirpath}/{filename}.met"
    return f"https://bhoonidhi.nrsc.gov.in/{dirpath}/{filename}.meta"


def get_quicklook_url(scene: dict) -> str:
    dirpath = scene["DIRPATH"]
    filename = scene["FILENAME"]
    if (
        scene.get("PRICED", "").lower() == "priced"
        or scene.get("PRICED", "").lower() == "opendata_onorder"
    ):
        return f"https://bhoonidhi.nrsc.gov.in/{dirpath}/{filename}.jpeg"
    return f"https://bhoonidhi.nrsc.gov.in/{dirpath}/{filename}.jpg"


def create_clickable_link(url: str, text: str) -> str:
    """Create a Rich-compatible clickable link."""
    from rich.markup import escape

    return f"[link={url}]{escape(text)}[/link]"
