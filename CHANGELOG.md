# Changelog

All notable changes to this project are documented here.

## [0.5.1]

### Added

- **`bhd query create --no-save` (CLI) / `client.query.create(save=False)` (SDK) runs the search without persisting a query file** — the portal call, pagination, and dedup are identical to a normal create, but nothing is written to `~/.bhoonidhi/queries/` and no slug is generated. The returned `QuerySchema` still carries `.scenes` so the caller gets the full scene list exactly as before — the only difference is that the result is ephemeral. This is the stateless path programmatic consumers (bhoonidhi-explorer ingest DAGs) need so they don't accumulate hidden per-worker query files that grow unbounded and break in multi-worker orchestrators.

## [0.5.0]

### Added

- **`bhd query create --sat` is now repeatable and accepts `SAT[:SEN[:PROD]]`, so one search can span several missions or narrow to a single product within a sensor** — `--sat ResourceSat-2A:LISS3 --sat CartoSat-3` searches both in one request, and `--sat "EOS-06:OCM(GAC):L2C-Chlorophyll"` narrows to that one product instead of every product a sensor bundles (EOS-06's OCM(GAC) alone has eight). The portal already searches on a flat list of dispName tokens, so this stays one HTTP request regardless of how many selections are combined — the server fans them out, not the client. An unknown satellite, sensor, or product is skipped with a warning and the search continues with whatever's left; only an all-invalid selection list fails outright. `--sen` still works as shorthand for a single plain `--sat`. The SDK's `client.query.create(...)` gains a `selections=[Selection(...), ...]` parameter alongside the existing `satellite=`/`sensor=` pair — give one or the other, not both.
- **`bhd archive list --sat X` now shows every product as its own row with the exact `--sat` value that selects it, instead of a `dispName`/`Products` pair you had to decode by hand.** The old table wrapped every long-suffixed satellite (EOS-06's 15 products, previously spread across two hard-to-read columns) across 2-4 lines per row; the new `Product` column is the short token itself and `--sat value` is copy-pasteable straight into `query create`. The unfiltered `bhd archive list` now shows a per-sensor product count (`OCM(GAC) (8 products)`) instead of a bare sensor-name list, so the extra depth is visible before drilling in. A handful of sensors mix a bare, no-suffix product with other, distinctly-suffixed ones (some ResourceSat-1/2/2A AWIFS and LISS3 variants) — for those, `SAT:SEN` alone selects every product under the sensor rather than just the bare one, and the table says so instead of showing a value that wouldn't do what it implies. `archive export`'s JSON gains matching `product_token`/`sat_value` fields on every collection entry. Verified against a live fetch of the full 41-satellite/132-product catalogue: every product token round-trips through `query create --sat` back to exactly the dispName it came from.
- **Search results include a Resolution (m) column** — scenes only carry `SELECTION` (the full dispName), not a resolution field, so the value is looked up against the cached archive manifest per row. Closes a gap where the search table showed everything about a scene except how coarse it was.
- **`bhd cart --help` explains what the cart commands actually do** — the four-way availability routing `cart add` performs, that ordering (and payment for priced data) still finishes in the web portal not the CLI, and that login is required with automatic refresh. Previously it was one sentence with no mention of any of that.

### Changed

- **`SearchSchema` and `QuerySchema` hold a `selections` list instead of scalar `satellite`/`sensor` fields.** Saved queries written before this release are migrated automatically on read — no manual step, no version-gated loader — but **`query.satellite`/`query.sensor` no longer exist as attributes on the returned object**; anything reading those directly (not just constructing with the legacy keywords, which still works) needs `query.selections` instead. `generate_name`/`generate_description` and the `query list` table now show the full mission mix rather than one satellite.
- **`bhd auth refresh` failure is framed as a warning, not a red error**, and no longer tells you to run `auth logout` first — `auth login` overwrites the saved session on its own. The old copy sent people through a needless extra step for a normal end-of-refresh-window event.
- **Satellite, Sensor, Metadata, and Quick View columns are centered** in the search results table so both real values and the `-` placeholder line up under their (already centered) headers.

### Fixed

- **`Selection` wasn't exported from `bhoonidhi_downloader.sdk`**, even though every other SDK-facing type (`BhoonidhiClient`, the `BhoonidhiError` family) is — a script had to know to reach into `bhoonidhi_downloader.schemas` instead. `from bhoonidhi_downloader.sdk import Selection` now works alongside the rest.
- **`bhd query create` no longer prints the same "available satellites" list twice** when every selection is invalid — the yellow skip warnings above the raised error were already showing it once. Exception message now points to those warnings instead of concatenating them.
- **`bhd archive list --sat X` shows `-` in the Product column for a bare-suffix product**, not `(default)` — matches the placeholder style already used elsewhere in the table.

## [0.4.0]

### Added

- **`bhd query create` accepts a location AOI as an alternative to a bounding box** — `--lat`/`--lon` (CLI) or `lat=`/`lon=` (SDK) search a point plus a surrounding radius instead of four corner coordinates. `--radius`/`radius_km` defaults to 10km and accepts 1-100km, matching the portal's own limit. Give exactly one AOI mode; mixing a bounding box with a location, or giving neither, fails with a clear error before any request is sent.

### Changed

- **`bhd query create`'s bounding box moved from positional arguments to `--minx`/`--maxx`/`--miny`/`--maxy` flags** — needed so the same command could accept either AOI mode without four required positionals blocking the location-only case. `client.query.create(...)` in the SDK follows the same shape: `start_date`, `end_date`, and `satellite` stay positional-friendly; the AOI args (both bbox and location) are keyword-only in practice. **Breaking for any script calling the SDK's `create()` with bbox values as positional arguments** — pass `minx=`/`maxx=`/`miny=`/`maxy=` by keyword instead. This is why the version bumps to 0.4.0 rather than a patch release.

### Fixed

- **Metadata links (`Metadata` column, both search and cart tables) were broken for most scenes.** `get_scene_meta_url()` used to hand out a `.meta`/`.met` URL for every scene unconditionally, but most scenes never have a metadata file at all — the portal only serves one when a scene is open data (`PRICED` starts with `OpenData_`) *and* `TABLETYPE` is `PMETA`; everything else now correctly shows a dash instead of a link that always 404s. Three satellite families that do qualify also serve a different file than a plain `.meta`: Sentinel-1 opens the `_VH`/`_VV` polarization sidecars, Sentinel-2 opens the tile-metadata/INSPIRE sidecars, and Novasar rewrites the directory and extension entirely — all three are now handled. A meaningful chunk of otherwise-qualifying scenes (JPSS1/Suomi-NPP VIIRS from roughly mid-2025 on, LandSat-8/9, MetOp-B/C, Sentinel-1 SAR(IW)_SLC, most Novasar-1 products since ~2023) still 404 because the file genuinely isn't hosted at the URL the portal's own logic would build — that's a portal-side gap, not something a client-side fix can repair.
- **Quicklook thumbnail links (`Quick View` column) picked the wrong file extension for priced scenes.** `get_quicklook_url()` guessed `.jpg` vs `.jpeg` from `PRICED`, which has nothing to do with it — a priced PMETA scene got a broken `.jpeg` link when the real file was `.jpg`, and the reverse for open-data SMETA scenes. The extension is actually determined by `TABLETYPE` (`SMETA` → `.jpeg`, `PMETA` → `.jpg`, no exceptions across every satellite/sensor/product combination the portal supports), which the fix now reads instead.
- **An invalid `--sat`/`--sen` value on `bhd query create` dumped a raw, unreadable pydantic traceback** instead of a clean error message — the CLI's error handler only caught `BhoonidhiError` subclasses, and pydantic's own `ValidationError` slipped past it. Now prints `Search failed: Invalid satellite '...'. Available: [...]` and exits cleanly, same as every other validation failure.

## [0.3.3]

Every `bhd` command was already a thin wrapper over plain Python functions, but calling into them meant reaching past a `console`/`rich` rendering layer built for the terminal, not for a script. This release splits that apart: command logic that returns data lives in `core/`, terminal rendering moves entirely into `cli/`, and a new `sdk/` package sits on top of the same core the CLI calls — so the two entry points can't drift, and scripting no longer means fighting the CLI's own plumbing.

### Added

- **`bhoonidhi_downloader.sdk.BhoonidhiClient`** gives one object whose namespaces mirror the CLI one-to-one — `client.archive`, `client.query`, `client.cart`, plus the auth methods (`login`, `logout`, `whoami`, `status`, `refresh`). Methods return plain data or raise a typed error instead of rendering to the terminal, and the client holds the session in memory and reuses the one saved at `~/.bhoonidhi/session`, so a script logs in once. SDK inputs are typed to their own shape rather than the CLI's wire format — `select` takes `[1, 2, 3]` (indices or scene IDs), `filter_by` takes a bare string or a list — so a caller never has to know the CLI accepts `--select 1,2,3` as one comma-joined string.
- **`BhoonidhiError` base exception**, so a single `except BhoonidhiError` catches any portal failure. Its subclasses (`BhoonidhiAuthError`, `BhoonidhiValidationError`, `BhoonidhiNotFoundError`, `BhoonidhiAPIError`) keep their matching built-in bases, so existing `except ValueError`/`except LookupError` handlers still work.
- **A `py.typed` marker**, so a consumer's type checker reads the package's type hints instead of treating it as untyped — confirmed by building the wheel and checking a fresh import with pyright, which previously showed every SDK method as `Unknown`.
- **Runnable example notebooks** — one per namespace (`auth`, `archive`, `query`, `cart`) — built into the documentation site as pages under API Reference → Notebook examples via `mkdocs-jupyter`, instead of living as side files in the repo that the docs only linked to.

### Fixed

- **`bhd archive export` failed after writing the file.** The command reformats the archive's raw field names before writing the export, then re-ran the summary render against that already-reformatted data — which crashed on a full export and printed an empty table for a single-satellite export. The file itself was always written correctly; the summary now renders from the original data before it's reshaped.
- **`bhd archive` calls had no request timeout.** Every other portal call in the codebase set one; this one didn't, so a hung connection to the archive endpoint could block indefinitely instead of failing.

## [0.3.1]

Three fixes surfaced while using the cart and download commands day to day.

### Added

- **`bhd query download --dry-run`** shows what a download would do — which scenes would be attempted, which would be skipped and why, which are already downloaded — without fetching anything or requiring a session. Uses the exact same classification rules as a real download, so a dry run never disagrees with what actually happens.
- **`-f`/`--filter`** on `bhd query show`, `bhd cart list`, and `bhd cart rm` narrows the table to one or more availability states — `ready`, `archived`, `onorder`, `priced` (comma-separated or repeatable). On the cart commands it also limits which of the portal's three carts get fetched, so `--filter priced` only ever reads the priced cart.

### Changed

- **`bhd cart list`/`bhd cart rm` no longer take `--kind`.** It did the same thing `--filter` now does — `--kind priced` and `--filter priced` selected identical rows — so `--filter` replaces it: `--filter ready,archived` in place of `--kind direct`, `--filter onorder` in place of `--kind order`, `--filter priced` unchanged.

### Fixed

- **Cart actions used the caller's local time instead of IST.** The portal files every cart record under IST — its own server date — but `cart list`/`cart rm`'s date window and the cart's add/remove calls defaulted to local `datetime.now()`. Outside IST, an add could succeed server-side while `cart list` queried the wrong date and showed nothing.
- **Searching a satellite with no sensor failed with an opaque "Search failed".** It now searches every sensor under that satellite instead, matching how the portal's own UI treats a satellite-only search.

## [0.3.0]

Scenes that `bhd query download` can't fetch — open-but-archived, on-order, and priced — can now be staged from the terminal. Add them to the Bhoonidhi cart straight from a saved query and finish the order in the Browse & Order portal, so you skip re-searching for the same scenes by hand.

### Added

- **`bhd cart add <slug>`** stages scenes from a saved query into the portal's cart. Use `--select` with the 1-based numbers or scene IDs from `query show` to pick specific scenes (`--select 1,3,7`), or omit it to add the whole query. The portal keeps three separate carts — direct download, on-order, and priced — and each scene is routed to the right one automatically based on its access type, so a query mixing all three just works in one command. A progress bar tracks the run and a results table lists what was added, what each scene's cart is, and the reason for anything that didn't add.
- **`bhd cart list`** shows everything staged — the portal's three carts (direct download, on-order, and priced) merged into one table. Each row shows which cart it's in and, for direct-download scenes, whether they're ready or still archived; the satellite and sensor names; the date it was added; and whether the order has been placed (from the item's `STATUS`), alongside Metadata and Quick View links. Because items are filed by the date they were added, `--since`/`--until` (YYYY-MM-DD) take an explicit span and `--last` takes a preset like `10 days`, `2 weeks`, or `1 month`; with nothing set it shows today, so scenes staged earlier need a wider window. `--kind direct|order|priced` limits the view to one cart. Rows are numbered for `cart rm` and open in the same scrollable viewer as search results (`--plain` to dump everything at once).
- **`bhd cart rm`** removes scenes — by cart row number (`cart rm --select 1,2`) or by a saved query's scenes (`cart rm <slug> --select 1`).

### Changed

- Search-result tables (`query create`, `query show`) and the cart table now show full satellite and sensor names — `ResourceSat-2A` / `AWIFS` instead of the short `R2A` / `AWIF` codes.
- `bhd query list` now has a Search IDs column listing every search a saved query holds — a query refreshed one or more times gathers scenes from several searches, and each search's ID is shown. `bhd query create` shows the single search's ID in its results-table header.
- The project now has a test suite (pytest), covering the cart's scene-identifier derivation and request-routing rules — the parts that fail silently against the live portal if they drift.

## [0.2.3]

Every table you'd previously have to scroll past all at once — search
results, saved queries, the archive, download reports — is now a
scrollable viewer you move around with vim-style keys.

### Added

- **Scrollable table viewer with vim-style navigation.** `query create`,
  `query list`, `query show`, `query download`, and `archive list` now
  open results in a table you scroll with `j`/`k` (rows), `h`/`l`
  (columns), `f`/`b` (page), `g`/`G` (top/end), `0`/`$` (first/last
  column), and `q` to quit. A controls table and status line are always
  visible so you don't lose track of where you are.
- **`--plain` flag.** Every command above accepts `--plain` to print the
  full table at once instead of opening the scrollable view — useful for
  piping into `grep` or a file. Output automatically falls back to this
  when it isn't going to a real terminal anyway.
- Search results now show a centered Availability Legend table (what
  each state means and what to do about it) and a one-line tip on how to
  open the Metadata/Quick View links — both stay visible while scrolling
  instead of disappearing off screen or only showing up after you quit.

## [0.2.2]

Two bug fixes surfaced while verifying scene availability against the live portal.

### Fixed

- **Landsat-9 and JPSS1 downloads returned 404 even when marked available.** The sensor short-code lookup was keyed on the wrong value — Landsat scenes report `SENSOR="OLI"`, not `"O"`, and JPSS1 (`SENSOR="VIR"`) had no entry at all — so requests fell through to a data path that doesn't exist. Verified live: both missions now resolve to `/data/L9/O/...` and `/data/JP1/V/...` and return 200.
- **The availability legend showed a literal `<slug>` placeholder** instead of the query's actual slug in the `bhd query download <slug>` hint printed by `query create` and `query show`.

## [0.2.1]

Replaces the generic age-based scene availability guess from 0.2.0 with a real availability indicator. Search (bhd query create) and downloads (bhd query download) are aware of which Open scenes are available for direct download and which ones are in archive.

### Added

- **Scene availability classification.** Search results now read `CURR_SCENE_NO` from the portal response and classify each scene as `Ready`, `Archived`, `OnOrder`, or `Priced`, shown as an Availability column with a legend explaining what each state means and what to do about it. This replaces the old 365-day heuristic, which was wrong in both directions — some year-old scenes are staged and ready, some recent ones aren't.
- **Pre-flight download summary.** Before `query download` starts fetching, it now breaks the selection down by state (`Downloading 12 Ready, 5 Archived (may 404)` / `Skipping 3 OnOrder, 1 Priced`), so what's about to happen is stated up front.

### Changed

- Download statuses and messaging now match the availability classification instead of guessing by age. `cold_storage` is renamed to `archived`, and the old catch-all `skipped_priced` status is split into `skipped_on_order` and `skipped_priced`, so the download report says which action each scene actually needs — order it, or pay for it.
- `is_downloadable()` is now a single function (`core/search/availability.py`), reused by both search and download instead of being implemented twice. The two could previously drift out of sync with each other.

## [0.2.0]

This version represents a significant departure from the current version (v0.1.21). This release is my attempt to modernise the project — a rewrite of the entire codebase. If you've been using `bhoonidhi-downloader` 0.1.x, **your commands will need to change** — see the migration notes below. Nothing about *what* this tool does has changed; how you talk to it has.

### Why the rewrite

The original work (0.1x) grew out of a semi-reverse-engineered approach where the goal was to just get things up and working — every  feature was thought out according to my use case at the time which was to bulk ingest scenes from ResourceSat-2. While the core logic around authentication and search capabilities still hold in this newer version, the interface and commands have been re-worked, both in how the information is organised on the screen,  how codebase is structred for better readability and debugging, and the ease of calling API directly into scripts/notebooks . Previous work had  HTTP calls, business logic, and terminal output all lived in the same functions. That worked fine for a while, but it made two things hard: testing anything without hitting the live Bhoonidhi portal, and adding features without touching five unrelated things at once.

This version splits the tool into three components per feature  (auth, archive, search, query, download):

- `client.py` — talks to the Bhoonidhi portal, nothing else
- `command.py` — orchestrates the client + does the actual work, returns plain data
- `render.py` — turns that data into the Rich tables/panels you see on screen

The CLI layer (`cli/*.py`) is now *just* argument parsing — it calls into `command.py` and gets back a result or a `None`/`False` to know whether to exit non-zero. None of it talks to the network directly anymore.

### Breaking: command surface

Every top-level command from 0.1.x is now a subcommand group:


| 0.1.x                                                             | 0.2.x                                                                  |
| ----------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `bhoonidhi-downloader authenticate --username ... --password ...` | `bhd auth login`                                      |
| `bhoonidhi-downloader archive --sat ResourceSat-2`                | `bhd archive list --sat ResourceSat-2`                |
| `bhoonidhi-downloader search <bbox> <dates> --sat ... --sen ...`  | `bhd query create <bbox> <dates> --sat ... --sen ...` |


The old `search` command ran once and forgot everything the moment your terminal closed. `query create` does the same search, but *saves* the result under a short slug (like `misty-falcon`) so you can come back to it later with `query show misty-falcon`, re-check for new scenes with `query refresh`, or download from it whenever you're ready — no need to re-run the search.

### Added

- **Named, persistent queries.** Every search is now saved to `~/.bhoonidhi/queries/<slug>.json`. `query list` shows everything you've saved; `query fork` clones one under a new name without re-querying the portal.
- **Real download engine.** `query download` fetches scenes concurrently (`--parallel`, default 4), verifies each one with a SHA256 written back onto the saved query, and skips anything already downloaded unless you pass `--force`. Bhoonidhi's servers don't support HTTP Range requests, so an interrupted download can't resume — it restarts from byte 0, and the download report tells you when that happened.
- **`auth refresh`.** Gets you a fresh token without logging out and back in — but only works while your session is still recent. Once it's properly stale, refresh can't save it and you'll need to log in again.
- **Archived-scene detection.** Scenes marked `Archived` in search results aren't currently staged for direct download and may 404 if fetched — the download report flags these instead of calling it a generic failure. Classification reads `CURR_SCENE_NO` from the portal response, replacing the former age-based heuristic.
- **Auto re-login on `query download`.** If your session's expired, it'll just ask for your password right there and log you back in instead of making you run `auth login` separately. Password never touches disk. Scripted use doesn't get prompted — pass `password=` if you want the same behavior, otherwise it fails with a clear message instead of hanging.
- **Warns before re-downloading scenes you already have somewhere else.** If a scene's already downloaded and SHA-verified in a different folder, pointing `--out` at a new location now tells you and asks before wasting bandwidth re-fetching it. `--force` skips the check.

### Removed

- `geopandas`, `shapely` — were only used by an `AOISchema.to_gdf()` method nothing called.
- `wget` — downloads now stream through `requests` directly.
- `tqdm` — replaced by `rich.progress`, which is already a dependency.
- Cart/order support (`cart_actions.py`) — existed in 0.1.x but was already half-commented-out and never wired into a working command. It's gone for now; may come back once there's a real `cart` subcommand to attach it to.

### Fixed

- **Sensor names are now URL-encoded in the search payload.** Sensors with names that contain characters needing URL encoding (spaces, `/`, etc.) previously produced a malformed request and could come back empty; `query create` now encodes them correctly before hitting the portal.
- **Hardened session storage, error logging, and download filename generation.** Session files are written/read more consistently across auth, portal HTTP errors now produce clearer log messages instead of hiding the underlying cause, and scene filenames on download are built more robustly (no more collisions or mangled names for scenes with special characters).

### Also

- Added `bhd` as a shorter alias for `bhoonidhi-downloader` — same tool, less typing.
- Requires Python 3.10+ (was 3.8+) — the rewrite uses `X | None` union syntax throughout.
- No test suite yet — this release was verified by hand against the live portal (login, search, download, re-auth, duplicate detection), not an automated CI run.

## [0.1.21]

- Added MkDocs + GitHub Pages workflow — first version of this tool with hosted documentation.
- Added PyPI and docs badges to the README.

## [0.1.2]

- **`archive` command.** New command to list every satellite/sensor Bhoonidhi supports, with results cached locally instead of re-fetched on every run.
- **Sentinel-1 and Landsat 8/9 support** in the search command, alongside the satellites already supported.
- `search` no longer requires `--sat`/`--sen` — both became optional, searching across everything if omitted.
- Search results can be exported to a file; the export path's parent directory is created automatically if missing, instead of failing.
- Fixed a `while True` loop bug from 0.1.1's multi-select prompt that could hang on bad input.
- Refactored `search()` and the archive command to cut down on inline `typer.echo()` clutter.

## [0.1.1]

- **Multi-scene selection.** `search` could previously only download one scene per run; you can now select several with a comma-separated list (`1,2,3`) instead of downloading them one search at a time.
- Replaced manual download plumbing with `wget` as a dependency.
- Added debug logging for the expired-session scenario during download.
- Set up GitHub Actions workflows for publishing to PyPI (via TestPyPI first).

## [0.1]

First public release. Search Bhoonidhi's archive by bounding box and date range, authenticate, and download a single scene at a time. Started as a `rye`-managed project; the cart/order-viewing command (`show-cart`) that existed during early development was removed before this release since it was never fully wired up.

