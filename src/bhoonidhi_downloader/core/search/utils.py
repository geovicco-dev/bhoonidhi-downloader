import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from rich.live import Live
from rich.spinner import Spinner

from bhoonidhi_downloader.exceptions import BhoonidhiValidationError
from bhoonidhi_downloader.logger import get_console
from bhoonidhi_downloader.schemas.selection import product_token as _product_token


def _parse_manifest_date(s: str | None) -> datetime | None:
    """Parse a manifest 'MM/DD/YYYY' date, or None."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%m/%d/%Y")
    except ValueError:
        return None


def _within_window(
    cols: list[dict[str, Any]], start_date: datetime, end_date: datetime
) -> str | None:
    """Check a search window against the data window of the given products.

    Returns None if the window is valid, else a short reason string. The
    valid window spans the earliest product start to the latest product end
    (an ongoing product has no end and imposes no upper bound).
    """
    starts = [d for d in (_parse_manifest_date(c.get("startDate")) for c in cols) if d]
    parsed_ends = [_parse_manifest_date(c.get("endDate")) for c in cols]
    # An ongoing product (no end date) means the sensor still produces data, so
    # the selection has no upper bound. Only clamp the window when every product
    # is retired; a single ongoing product removes the ceiling.
    any_ongoing = any(e is None for e in parsed_ends)
    ends = [e for e in parsed_ends if e]
    earliest = min(starts) if starts else None
    latest = None if any_ongoing else (max(ends) if ends else None)

    if earliest and start_date < earliest:
        return f"data starts {earliest:%Y-%m-%d}, after search start"
    if latest and end_date > latest:
        return f"data ends {latest:%Y-%m-%d}, before search end"
    return None


def resolve_selections(
    selections: list[Any],
    manifest: dict[str, Any],
    start_date: datetime,
    end_date: datetime,
) -> list[str]:
    """Resolve selections to the raw dispNames the portal searches on.

    Each selection narrows the satellite → sensor → product hierarchy to a
    set of products. Selections are validated against the archive manifest
    and the search date window; an invalid one (unknown satellite/sensor,
    no matching product, or out of the data window) is warned about and
    skipped rather than failing the whole search. Returned dispNames are
    deduplicated with first-seen order preserved.

    Raises:
        BhoonidhiValidationError: if every selection is skipped, so there
            is nothing to search.
    """
    console = get_console()
    disp_names: list[str] = []
    seen: set[str] = set()

    def skip(label: str, reason: str) -> None:
        console.print(f"[yellow]![/] skipped [bold]{label}[/] — {reason}")

    for sel in selections:
        label = sel.label()

        if sel.satellite not in manifest:
            skip(label, f"unknown satellite; available: {sorted(manifest)}")
            continue

        # Which sensors this selection covers.
        if sel.sensor is not None:
            if sel.sensor not in manifest[sel.satellite]:
                available = sorted(manifest[sel.satellite])
                skip(label, f"unknown sensor; available: {available}")
                continue
            sensors = [sel.sensor]
        else:
            sensors = list(manifest[sel.satellite])

        # Gather candidate product columns across the covered sensors,
        # narrowing to a single product token when one was given.
        cols: list[dict[str, Any]] = []
        for sensor in sensors:
            for col in manifest[sel.satellite][sensor]:
                disp = col.get("dispName")
                if not disp:
                    continue
                if sel.product is not None:
                    token = _product_token(str(disp), sel.satellite, sensor)
                    if token.lower() != sel.product.lower():
                        continue
                cols.append(col)

        if not cols:
            valid = sorted(
                {
                    _product_token(str(c["dispName"]), sel.satellite, sensor)
                    for sensor in sensors
                    for c in manifest[sel.satellite][sensor]
                    if c.get("dispName")
                }
                - {""}
            )
            skip(label, f"no such product; valid: {valid}")
            continue

        reason = _within_window(cols, start_date, end_date)
        if reason:
            skip(label, reason)
            continue

        for col in cols:
            disp = str(col["dispName"])
            if disp not in seen:
                seen.add(disp)
                disp_names.append(disp)

    if not disp_names:
        # The skip() calls above already printed each reason in yellow;
        # repeating the joined list of them in the exception would show
        # the user (and their scrollback) the same error text twice.
        raise BhoonidhiValidationError(
            "No valid selections to search — see the warnings above for why."
        )

    return disp_names


def create_payload(cfg: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    sdate: str = cfg.start_date.strftime("%b%%2F%d%%2F%Y").upper()
    edate: str = cfg.end_date.strftime("%b%%2F%d%%2F%Y").upper()

    disp_names = resolve_selections(
        cfg.selections, manifest, cfg.start_date, cfg.end_date
    )

    # The portal URL-decodes selSats server-side (that's why the comma
    # separator has to be sent as %2C rather than a literal ","). Any
    # sensor's name containing a character that's meaningful in a URL-encoded
    # string therefore has to be percent-encoded too, or it gets mangled
    # on arrival and silently matches nothing:
    #
    #   "LandSat-8_OLI+TIRS_L1"  ->  "+" decodes to a space  ->  0 results
    #   "LandSat-8_OLI%2BTIRS_L1"                            ->  500 results

    sat_sen: Any = [quote("".join(disp.split()), safe="") for disp in disp_names]

    if len(sat_sen) > 1:
        sat_sen = "%2C".join(sat_sen)
    elif len(sat_sen) == 1:
        sat_sen = sat_sen[0]
    aoi_fields: dict[str, Any]
    if cfg.aoi.mode == "location":
        aoi_fields = {
            "queryType": "location",
            "lat": cfg.aoi.lat,
            "lon": cfg.aoi.lon,
            "radius": cfg.aoi.radius_km if cfg.aoi.radius_km is not None else 10.0,
            "loc": "Decimal",
        }
    else:
        aoi_fields = {
            "queryType": "polygon",
            "tllat": cfg.aoi.max_lat,
            "tllon": cfg.aoi.min_lon,
            "brlat": cfg.aoi.min_lat,
            "brlon": cfg.aoi.max_lon,
        }

    return {
        "userId": "T",
        "prod": "Standard",
        "selSats": sat_sen,
        "offset": "0",
        "sdate": sdate,
        "edate": edate,
        "query": "area",
        "isMX": "No",
        **aoi_fields,
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


def scene_resolution(scene: dict, manifest: dict[str, Any] | None = None) -> str:
    """Look up a scene's spatial resolution from the archive manifest.

    A scene carries ``SELECTION`` (its full dispName) but no resolution
    field of its own — the portal only publishes resolution in the
    ``SatSenServlet`` archive catalogue, not on individual search results.
    Matches the scene's dispName back to the manifest entry it came from
    and returns that entry's ``resolution`` (a numeric string, e.g. "23.5"
    or "360"). Returns ``"-"`` when nothing matches: no SELECTION on the
    scene, no cached manifest available, or the dispName isn't in it.

    ``manifest`` is the dict from ``ArchiveManager.build_manifest`` (or
    what's cached at ``~/.bhoonidhi/manifest.json``). Loads it lazily
    from disk when not supplied, so this stays a pure helper safe for
    tight table-render loops.
    """
    selection = scene.get("SELECTION")
    if not selection:
        return "-"

    satellite = full_satellite(scene)
    sensor = full_sensor(scene)
    if not satellite or not sensor:
        return "-"

    if manifest is None:
        manifest = _load_cached_manifest()
    if not manifest:
        return "-"

    for col in manifest.get(satellite, {}).get(sensor, []):
        if col.get("dispName") == selection:
            return str(col.get("resolution") or "-")
    return "-"


def _load_cached_manifest() -> dict[str, Any]:
    """Read the on-disk manifest, or an empty dict if it isn't cached yet."""
    path = Path.home() / ".bhoonidhi" / "manifest.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
