# bhoonidhi-downloader

[![PyPI version](https://img.shields.io/pypi/v/bhoonidhi-downloader.svg?logo=python&logoColor=white&label=PyPI&style=flat)](https://pypi.org/project/bhoonidhi-downloader/)
[![Documentation](https://img.shields.io/badge/docs-MkDocs-blue.svg)](https://geovicco-dev.github.io/bhoonidhi-downloader/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![YouTube Video Demo](https://img.shields.io/badge/YouTube-Demo-red)](https://youtu.be/Y3naYuyr3NA)

CLI and SDK for [ISRO's EO Portal - Bhoonidhi Browse & Order](https://bhoonidhi.nrsc.gov.in/) — search by bounding box or a point plus radius, save results as named queries you can revisit and refresh, download open-access scenes with concurrency and SHA256 verification, and stage priced/on-order/archived scenes to the Bhoonidhi cart. Every command is also callable from Python through the `bhoonidhi_downloader.sdk` package — a single `BhoonidhiClient` that mirrors the CLI one-to-one.

## Features

- **Search by bounding box or point + radius** — filter by satellite, sensor, and date range.
- **Named, persistent queries** — every search is saved under a short slug (`misty-falcon`), so you can come back to it later, refresh it for new scenes, or download from it without re-querying the portal.
- **Concurrent, verified downloads** — fetches multiple scenes in parallel, verifies each with a SHA256, and skips anything already downloaded.
- **Cart staging** — stage scenes into the Bhoonidhi cart from a saved query — priced, on-order, open-but-archived, or direct-download — and finish the order in the Browse & Order portal.
- **Browse the archive** — list every satellite/sensor Bhoonidhi currently supports, live from the portal.
- **Session management** — login once, refresh your token automatically while it's still within Bhoonidhi's refresh window; re-enter credentials only once that window has closed.
- **Scriptable** — every command has a matching method on `BhoonidhiClient`, so you can drive searches and downloads from a Python script or notebook for programmatically accessing the entire archive.

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
bhd query create 2025-12-01 2025-12-30 --sat Sentinel-2A --sen MSI --minx 91.77 --maxx 92 --miny 25.496 --maxy 25.695

# 3. Download everything the query found
bhd query download misty-falcon --out ./downloads
```

`query create` prints the scenes it found in a table and tells you what slug it saved them under (here, `misty-falcon` — yours will be different). You don't have to download right away: come back anytime with `bhd query show misty-falcon`, or `bhd query refresh misty-falcon` to check for newly published scenes in the same area.

Prefer a point and radius over a bounding box? Swap `--minx`/`--maxx`/`--miny`/`--maxy` for `--lat`/`--lon`/`--radius` (radius defaults to 10km, 1-100km):

```shell
bhd query create 2025-12-01 2025-12-30 --sat Sentinel-2A --sen MSI --lat 25.58 --lon 91.89 --radius 15
```

## Command reference

Every command supports `--help` for its full option list. This is the short version; see the [API Reference](https://geovicco-dev.github.io/bhoonidhi-downloader/api/) for the underlying functions this calls into.

### `auth` — session management


| Command            | What it does                                                                                                                                         |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bhd auth login`   | Authenticate and save your session to `~/.bhoonidhi/session`.                                                                                        |
| `bhd auth status`  | Show whether you're logged in and whether the token is still valid.                                                                                  |
| `bhd auth whoami`  | Print the current username.                                                                                                                          |
| `bhd auth refresh` | Get a fresh token without logging out and back in — only works if your session's still recent; once it's properly stale you'll need to log in again. |
| `bhd auth logout`  | Clear the saved session.                                                                                                                             |


### `archive` — browse what's available


| Command                                 | What it does                                                  |
| --------------------------------------- | ------------------------------------------------------------- |
| `bhd archive list`                      | List every satellite and sensor Bhoonidhi currently supports. |
| `bhd archive list --sat ResourceSat-2A` | Filter the list to one satellite.                             |
| `bhd archive export --out archive.json` | Export the archive data to a file.                            |


### `query` — search, save, and download


| Command                                               | What it does                                                                                                                                                                                       |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bhd query create <dates> --sat ... --sen ... (--minx --maxx --miny --maxy | --lat --lon [--radius])` | Search and save the results as a new named query. Give the area as a bounding box or a point + radius, not both. |
| `bhd query list`                                      | List all your saved queries.                                                                                                                                                                       |
| `bhd query show <slug>`                               | Redisplay a saved query's scenes. `--filter ready\|archived\|onorder\|priced` narrows the table to one or more states.                                                                              |
| `bhd query refresh <slug>`                            | Check for new scenes matching an existing query.                                                                                                                                                   |
| `bhd query fork <slug>`                               | Clone a query under a new name, without re-searching.                                                                                                                                              |
| `bhd query download <slug> --out <dir>`               | Download scenes from a saved query. Add `--select` to pick specific scenes, `--parallel` to control concurrency, `--force` to re-download, `--dry-run` to preview without fetching. Re-logs you in automatically if your session's expired. |
| `bhd query rename <slug>`                             | Update a saved query's name/description.                                                                                                                                                           |
| `bhd query rm <slug>`                                 | Delete a saved query.                                                                                                                                                                              |

### `cart` — stage scenes to the Bhoonidhi cart

For scenes that `query download` can't fetch directly — priced, on-order, or open-but-archived — add them to the Bhoonidhi cart from a saved query, then finish the order in the Browse & Order portal. Direct-download scenes can be downloaded with `query download` *or* staged to the cart; every access type routes automatically to the portal's direct-download, on-order, or priced cart based on its access type.

| Command                          | What it does                                                                                                                                                             |
| -------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `bhd cart add <slug>`            | Stage a saved query's scenes into the cart. Add `--select` to pick specific scenes; omit it to add the whole query.                                                     |
| `bhd cart list`                  | Show everything staged — all three carts in one table. `--last`/`--since`/`--until` widen the date window; `--filter ready\|archived\|onorder\|priced` narrows to one or more states (and only reads the carts that could match). |
| `bhd cart rm`                    | Remove scenes — by cart row number (`--select 1,2`) or by a saved query's scenes (`<slug> --select 1`). Takes the same `--filter` as `cart list` to narrow which rows a number refers to. |


## Calling it from Python

Every command shown above is also available from Python through the
`BhoonidhiClient` — same behaviour, no subprocess. This is the way to script
bulk ingestion or wire Bhoonidhi into a pipeline:

```python
from datetime import datetime

from bhoonidhi_downloader.sdk import BhoonidhiClient

client = BhoonidhiClient()
client.login("my-username", "my-password")

query = client.query.create(
    datetime(2025, 12, 1), datetime(2025, 12, 30),
    satellite="Sentinel-2A", sensor="MSI",
    minx=91.77, maxx=92.0, miny=25.496, maxy=25.695,
)

client.query.download(query.slug, "./downloads")
```

See the [Python SDK guide](https://geovicco-dev.github.io/bhoonidhi-downloader/sdk/)
for the full walkthrough, the [API Reference](https://geovicco-dev.github.io/bhoonidhi-downloader/api/)
for every method, and the [notebook examples](https://geovicco-dev.github.io/bhoonidhi-downloader/api/notebooks/auth/)
for runnable worksheets.

## What's actually downloadable

Every scene is searchable and shows up in results. Scenes marked `OpenData_DirectDownload` can be pulled straight to disk with `query download`. The other access types — priced, on-order, and open-but-archived — can't be fetched directly by the CLI, but all of them, including the direct-download ones, can be staged with `bhd cart add` and finished in the Browse & Order portal. So the cart is a single collection path for every scene regardless of access type; `query download` is just the shortcut for the subset that's immediately fetchable.

The satellite/sensor list itself isn't hardcoded anywhere in this tool — `bhd archive list` fetches it live from the portal every time, so it's always current. Run it to see exactly what's searchable today rather than relying on a list here that would just go stale.

A couple of Bhoonidhi-specific quirks worth knowing about going in:

- **No resumable downloads.** The portal doesn't honor HTTP Range requests, so an interrupted download restarts from byte 0 rather than picking up where it left off. `query download` reports this explicitly (`↺ restarted from scratch`) when it happens.
- **Already have it somewhere else?** `query download` checks if a scene's already downloaded and SHA-verified in a different folder before re-fetching it — if it finds one, it'll tell you and ask before wasting bandwidth. `--force` skips the check and downloads anyway.

## Limitations

- Search is bounding-box or point + radius (up to 100km) — no shapefile-based search yet.
- `query download` fetches only `OpenData_DirectDownload` scenes; priced, on-order, and archived scenes aren't fetched directly. Every access type — including direct-download scenes — can also be staged with `bhd cart add`.
- Cart support stages scenes only. Placing the order — and any payment for priced data — is finished in the Browse & Order portal; there's no order-placement step in the CLI.

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
