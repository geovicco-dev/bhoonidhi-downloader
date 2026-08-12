# Changelog

All notable changes to this project are documented here.

## [0.3.0]

Scenes that `bhd query download` can't fetch — open-but-archived, on-order, and priced — can now be staged from the terminal. Add them to the Bhoonidhi cart straight from a saved query and finish the order in the Browse & Order portal, so you skip re-searching for the same scenes by hand.

### Added

- **`bhd cart add <slug>`** stages scenes from a saved query into the portal's cart. Use `--select` with the 1-based numbers or scene IDs from `query show` to pick specific scenes (`--select 1,3,7`), or omit it to add the whole query. The portal keeps three separate carts — direct download, on-order, and priced — and each scene is routed to the right one automatically based on its access type, so a query mixing all three just works in one command. A progress bar tracks the run and a results table lists what was added, what each scene's cart is, and the reason for anything that didn't add.
- **`bhd cart list`** shows everything staged — the portal's three carts (direct download, on-order, and priced) merged into one table. Each row shows which cart it's in and, for direct-download scenes, whether they're ready or still archived; the satellite and sensor names; the date it was added; and whether the order has been placed (from the item's `STATUS`), alongside Metadata and Quick View links. Because items are filed by the date they were added, `--since`/`--until` (YYYY-MM-DD) take an explicit span and `--last` takes a preset like `10 days`, `2 weeks`, or `1 month`; with nothing set it shows today, so scenes staged earlier need a wider window. `--kind direct|order|priced` limits the view to one cart. Rows are numbered for `cart rm` and open in the same scrollable viewer as search results (`--plain` to dump everything at once).
- **`bhd cart rm`** removes scenes — by cart row number (`cart rm --select 1,2`) or by a saved query's scenes (`cart rm <slug> --select 1`).

### Changed

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
- **Cold-storage detection.** Scenes older than ~365 days often fail with a 404 error on direct download — Bhoonidhi's archiving policy isn't publicly documented, but this age is a consistent trigger. The download report flags these explicitly instead of just calling it a generic failure.
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

