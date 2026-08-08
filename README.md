# bhoonidhi-downloader

[![PyPI version](https://badge.fury.io/py/bhoonidhi-downloader.svg)](https://badge.fury.io/py/bhoonidhi-downloader)
[![Documentation](https://img.shields.io/badge/docs-MkDocs-blue.svg)](https://geovicco-dev.github.io/bhoonidhi-downloader/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![YouTube Video Demo](https://img.shields.io/badge/YouTube-Demo-red)](https://www.youtube.com/watch?v=3K6VEqq-CWE)

A CLI and Python SDK for searching, saving, and downloading satellite imagery from [ISRO's Bhoonidhi Earth Observation Portal](https://bhoonidhi.nrsc.gov.in/).

## Features

- **Search by bounding box** — filter by satellite, sensor, and date range.
- **Named, persistent queries** — every search is saved under a short slug (`misty-falcon`), so you can come back to it later, refresh it for new scenes, or download from it without re-querying the portal.
- **Concurrent, verified downloads** — fetches multiple scenes in parallel, verifies each with a SHA256, and skips anything already downloaded.
- **Browse the archive** — list every satellite/sensor Bhoonidhi currently supports, live from the portal.
- **Session management** — login once, refresh your token when it goes stale, no need to keep re-entering credentials.
- **Usable as a library** — every command has a matching Python function, so you can script searches/downloads directly instead of shelling out.

## Installation

```shell
pip install bhoonidhi-downloader
```

This installs two equivalent commands — `bhoonidhi-downloader` and the shorter `bhd`. They're the same tool; use whichever you'd rather type.

## Quickstart

Log in, run a search, and download what you find — three commands, start to finish:

```shell
# 1. Authenticate (prompts for username/password if omitted)
bhd auth login

# 2. Search a bounding box + date range, save the results as a named query
bhd query create 91.77 92 25.496 25.695 2023-12-01 2023-12-30 --sat Sentinel-2A --sen MSI

# 3. Download everything the query found
bhd query download misty-falcon --out ./downloads
```

`query create` prints the scenes it found in a table and tells you what slug it saved them under (here, `misty-falcon` — yours will be different). You don't have to download right away: come back anytime with `bhd query show misty-falcon`, or `bhd query refresh misty-falcon` to check for newly published scenes in the same area.

## Command reference

Every command supports `--help` for its full option list. This is the short version; see the [full documentation](https://geovicco-dev.github.io/bhoonidhi-downloader/usage/) for every flag and example.

### `auth` — session management

| Command | What it does |
|---|---|
| `bhd auth login` | Authenticate and save your session to `~/.bhoonidhi/session`. |
| `bhd auth status` | Show whether you're logged in and whether the token is still valid. |
| `bhd auth whoami` | Print the current username. |
| `bhd auth refresh` | Get a fresh token without logging out and back in. |
| `bhd auth logout` | Clear the saved session. |

### `archive` — browse what's available

| Command | What it does |
|---|---|
| `bhd archive list` | List every satellite and sensor Bhoonidhi currently supports. |
| `bhd archive list --sat ResourceSat-2A` | Filter the list to one satellite. |
| `bhd archive export --out archive.json` | Export the archive data to a file. |

### `query` — search, save, and download

| Command | What it does |
|---|---|
| `bhd query create <bbox> <dates> --sat ... --sen ...` | Search and save the results as a new named query. |
| `bhd query list` | List all your saved queries. |
| `bhd query show <slug>` | Redisplay a saved query's scenes. |
| `bhd query refresh <slug>` | Check for new scenes matching an existing query. |
| `bhd query fork <slug>` | Clone a query under a new name, without re-searching. |
| `bhd query download <slug> --out <dir>` | Download scenes from a saved query. Add `--select` to pick specific scenes, `--parallel` to control concurrency, `--force` to re-download. |
| `bhd query rename <slug>` | Update a saved query's name/description. |
| `bhd query rm <slug>` | Delete a saved query. |

## Using it as a library

Every CLI command is a thin wrapper around a plain Python function — nothing about the underlying logic depends on being invoked from a terminal. If you're scripting a bulk ingestion pipeline or wiring this into a notebook, call into `bhoonidhi_downloader.core` directly instead of shelling out:

```python
from bhoonidhi_downloader.core.archive import ArchiveManager
from bhoonidhi_downloader.core.query.command import run_query_create, run_query_download
from bhoonidhi_downloader.logger import get_console
from datetime import datetime

console = get_console()

# Browse the archive programmatically
manifest = ArchiveManager().build_manifest()
print(manifest["Sentinel-2A"].keys())  # -> dict_keys(['MSI'])

# Search + save a query (same thing `bhd query create` does)
query = run_query_create(
    console,
    minx=91.77, maxx=92, miny=25.496, maxy=25.695,
    start_date=datetime(2023, 12, 1), end_date=datetime(2023, 12, 30),
    satellite="Sentinel-2A", sensor="MSI",
)

# Download everything it found
run_query_download(console, slug=query.slug, out="./downloads")
```

Command handlers live under `core/<domain>/command.py` (`auth`, `archive`, `search`, `query`, `download`) — each one takes a `rich.console.Console` (get one via `bhoonidhi_downloader.logger.get_console()`) and returns plain data (a `QuerySchema`, a list of scenes, a bool) rather than printing-and-exiting like a CLI would. The `render.py` modules alongside them are what turn that data into the tables you see on screen — you can skip them entirely and just work with the returned objects.

## What's actually downloadable

Bhoonidhi's archive covers far more than what this tool can fetch directly. Every scene has a `PRICED` status, and only scenes marked `OpenData_DirectDownload` come back from a search or get pulled by `query download` — anything priced or on-order is metadata/planning-only for now, since there's no cart/order flow implemented yet.

The satellite/sensor list itself isn't hardcoded anywhere in this tool — `bhd archive list` fetches it live from the portal every time, so it's always current. Run it to see exactly what's searchable today rather than relying on a list here that would just go stale.

A couple of Bhoonidhi-specific quirks worth knowing about going in:

- **No resumable downloads.** The portal doesn't honor HTTP Range requests, so an interrupted download restarts from byte 0 rather than picking up where it left off. `query download` reports this explicitly (`↺ restarted from scratch`) when it happens.
- **Cold storage.** Scenes older than roughly a year often fail with a 404 error on direct download — Bhoonidhi's archiving policy isn't publicly documented, but this age threshold is a consistent pattern. The download report flags these as `cold_storage` rather than a generic failure. This CLI can only fetch `OpenData_DirectDownload` scenes; a 404'd scene can't be retrieved through it at all. You can request the scene directly on the [Bhoonidhi Browse & Order Portal](https://bhoonidhi.nrsc.gov.in/bhoonidhi/index.html#) — cart/order support is planned for this CLI but not yet implemented.

## Limitations

- Search is bounding-box only — no point-coordinate or shapefile-based search yet.
- Only `OpenData_DirectDownload` scenes can be fetched directly; priced/on-order scenes show up in search results but are skipped on download (see above).
- No cart/order integration, so scenes that need to be requested first aren't reachable through this tool at all.

## Development

```shell
git clone https://github.com/geovicco-dev/bhoonidhi-downloader.git
cd bhoonidhi-downloader
uv sync --group dev
```

Before committing, run the same checks CI runs:

```shell
uv run ruff check src/
uv run ruff format --check src/
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for what's changed release to release.

## License

[MIT](LICENSE)
