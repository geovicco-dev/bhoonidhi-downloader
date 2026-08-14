import random
import time
from typing import Any
from urllib.parse import quote

import requests
from rich.live import Live
from rich.spinner import Spinner

from bhoonidhi_downloader.logger import get_console


def create_payload(cfg: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    sdate: str = cfg.start_date.strftime("%b%%2F%d%%2F%Y").upper()
    edate: str = cfg.end_date.strftime("%b%%2F%d%%2F%Y").upper()
    assert cfg.satellite is not None

    # No sensor given: search every sensor under this satellite instead of
    # failing. The portal itself treats a satellite-only search as "all
    # sensors" — this just matches that instead of erroring with a bare
    # AssertionError (which surfaced to users as an opaque "Search failed").
    if cfg.sensor:
        col_meta = manifest[cfg.satellite][cfg.sensor]
    else:
        col_meta = [
            col for cols in manifest[cfg.satellite].values() for col in cols
        ]

    # The portal URL-decodes selSats server-side (that's why the comma
    # separator has to be sent as %2C rather than a literal ","). Any
    # sensor's name containing a character that's meaningful in a URL-encoded
    # string therefore has to be percent-encoded too, or it gets mangled
    # on arrival and silently matches nothing:
    #
    #   "LandSat-8_OLI+TIRS_L1"  ->  "+" decodes to a space  ->  0 results
    #   "LandSat-8_OLI%2BTIRS_L1"                            ->  500 results

    sat_sen = [
        quote("".join(str(col["dispName"]).split()), safe="")
        for col in col_meta
        if col.get("dispName")
    ]

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

    Pages are deduplicated by scene ``ID`` (falling back to
    ``sceneId``/``id``) since overlapping pages can repeat a scene.
    Transient failures (5xx, 429, network errors) are retried with
    jittered exponential back-off; 4xx fails fast. The caller's
    ``payload`` is never mutated.
    """
    # Shallow copy: per-page offset/srt are set below and must not leak
    # back to the caller's dict.
    payload = {**payload}
    console = get_console()

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


# TABLETYPE decides the quicklook extension: SMETA scenes are always
# served as .jpeg, PMETA scenes as .jpg. PRICED has nothing to do with
# it, despite the old guess here basing the extension on it.
_QUICKLOOK_EXT_BY_TABLETYPE = {"SMETA": ".jpeg", "PMETA": ".jpg"}


def get_scene_meta_url(scene: dict) -> str | None:
    """Build the metadata download URL for a scene, or None if it has none.

    The portal only ever shows a metadata download link when a scene is
    open data (PRICED starts with "OpenData_") AND TABLETYPE is "PMETA" —
    every priced scene, and every SMETA scene regardless of pricing, has
    no separate metadata file at all (its fields are shown inline from the
    search response instead). Returning a URL unconditionally, as this
    function used to, handed out a broken link for the majority of scenes.

    A handful of satellites also don't serve a plain .meta/.met file even
    when the gate passes -- the portal opens different files for them
    instead. Where the portal opens more than one file (Sentinel-1,
    Sentinel-2), the first is returned as the primary link.
    """
    priced = str(scene.get("PRICED") or "")
    tabletype = str(scene.get("TABLETYPE") or "")
    if not (priced.startswith("OpenData_") and tabletype == "PMETA"):
        return None

    dirpath = scene["DIRPATH"]
    filename = scene["FILENAME"]
    scene_id = str(scene.get("ID") or "")
    satellite = str(scene.get("SATELLITE") or "").strip()

    if satellite == "NISAR" and not scene_id.startswith("NISAR_S4"):
        base = f"https://bhoonidhi.nrsc.gov.in/{dirpath}/{filename}.met"
    else:
        base = f"https://bhoonidhi.nrsc.gov.in/{dirpath}/{filename}.meta"

    id_prefix4 = scene_id[:4]
    id_prefix2 = scene_id[:2]
    if id_prefix4 == "SEN1":
        # Sentinel-1: the portal opens the VH and VV polarization sidecars
        # instead of a .meta file. VH is returned as the primary link; VV
        # is the same base with the suffix swapped.
        return base.replace(".meta", "_VH.xml")
    if id_prefix4 == "SEN2":
        # Sentinel-2: the portal opens the tile metadata + INSPIRE sidecars
        # instead of a .meta file. MTD is returned as the primary link;
        # INSPIRE is the same base with the suffix swapped.
        return base.replace(".meta", "_MTD.xml")
    if id_prefix2 == "NV":
        # Novasar: the portal serves metadata from a differently-named
        # directory (PRODUCTJPGS -> PRODUCTMETA) as .xml, not .meta.
        return base.replace("JPGS", "META").replace(".meta", ".xml")
    return base


def get_quicklook_url(scene: dict) -> str:
    dirpath = scene["DIRPATH"]
    filename = scene["FILENAME"]
    ext = _QUICKLOOK_EXT_BY_TABLETYPE.get(str(scene.get("TABLETYPE") or ""), ".jpg")
    return f"https://bhoonidhi.nrsc.gov.in/{dirpath}/{filename}{ext}"


def create_clickable_link(url: str, text: str) -> str:
    """Create a Rich-compatible clickable link."""
    from rich.markup import escape

    return f"[link={url}]{escape(text)}[/link]"


def link_or_dash(item: dict, builder, text: str) -> str:
    """Build a clickable link from item via builder, or a dash if there's
    nothing to link to.

    Covers two cases: builder raises (e.g. a cart record missing
    DIRPATH/FILENAME) and builder returns None (e.g. get_scene_meta_url()
    for a scene the portal never gives a metadata file to). Either way,
    a dash beats a broken link.
    """
    try:
        url = builder(item)
    except (KeyError, TypeError):
        return "[dim]—[/]"
    return create_clickable_link(url, text) if url else "[dim]—[/]"


def full_satellite(scene: dict) -> str:
    """The satellite's full name, e.g. 'ResourceSat-2A' not 'R2A'.

    Search and cart records carry ``SELECTION`` (like
    ``ResourceSat-2A_AWIFS_BOA-Archives``) alongside the short ``SATELLITE``
    code. The full name is the first underscore-separated part; falls back
    to the short code when ``SELECTION`` is missing.
    """
    selection = scene.get("SELECTION") or ""
    if selection:
        return selection.split("_")[0]
    return scene.get("SATELLITE", "N/A")


def full_sensor(scene: dict) -> str:
    """The sensor's full name, e.g. 'AWIFS' not 'AWIF'.

    The second part of ``SELECTION``; falls back to the short ``SENSOR``
    code when ``SELECTION`` is absent.
    """
    selection = scene.get("SELECTION") or ""
    parts = selection.split("_")
    if len(parts) >= 2 and parts[1]:
        return parts[1]
    return scene.get("SENSOR", "N/A")
