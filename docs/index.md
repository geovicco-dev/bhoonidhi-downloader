# Bhoonidhi Downloader

CLI and SDK for [ISRO's EO Portal - Bhoonidhi Browse & Order](https://bhoonidhi.nrsc.gov.in/) — search by bounding box or a point plus radius, save results as named queries you can revisit and refresh, download open-access scenes with concurrency and SHA256 verification, and stage priced/on-order/archived scenes to the Bhoonidhi cart. Every command is also callable from Python through the `bhoonidhi_downloader.sdk` package — a single `BhoonidhiClient` that mirrors the CLI one-to-one.

[![PyPI version](https://img.shields.io/pypi/v/bhoonidhi-downloader.svg?logo=python&logoColor=white&label=PyPI&style=flat)](https://pypi.org/project/bhoonidhi-downloader/)
[![YouTube Video Demo](https://img.shields.io/badge/YouTube-Demo-red)](https://youtu.be/Y3naYuyr3NA)
[:octicons-mark-github-16: View on GitHub](https://github.com/geovicco-dev/bhoonidhi-downloader){ .md-button }
[:material-language-python: PyPI](https://pypi.org/project/bhoonidhi-downloader/){ .md-button }

## Demo

<iframe width="100%" style="aspect-ratio: 16 / 9;" src="https://www.youtube.com/embed/Y3naYuyr3NA" title="Bhoonidhi Downloader demo" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen></iframe>

## What it does

- **Search by bounding box or point + radius** — filter by satellite, sensor, and date range.
- **Named, persistent queries** — every search is saved under a short slug (`misty-falcon`), so you can come back to it later, refresh it for new scenes, or download from it without re-querying the portal.
- **Concurrent, verified downloads** — fetches multiple scenes in parallel, verifies each with a SHA256, and skips anything already downloaded.
- **Cart staging** — stage scenes into the Bhoonidhi cart from a saved query — priced, on-order, open-but-archived, or direct-download — and finish the order in the Browse & Order portal.
- **Browse the archive** — list every satellite/sensor Bhoonidhi currently supports, live from the portal.
- **Session management** — log in once, refresh your token when it goes stale; no need to keep re-entering credentials.
- **Scriptable** — every command has a matching method on `BhoonidhiClient`, so you can drive searches and downloads from a Python script or notebook instead of shelling out.

## Installation

```shell
pip install bhoonidhi-downloader
```

This installs two equivalent commands — `bhoonidhi-downloader` and the shorter `bhd`. They're the same tool; use whichever you'd rather type.

## Quickstart

Log in, run a search, and download what you find — three commands, start to finish:

```shell
# 1. Authenticate (prompts for username/password; waits for email OTP if the portal sends one)
bhd auth login

# 2. Search a bounding box + date range, save the results as a named query
bhd query create 2025-12-01 2025-12-30 --sat Sentinel-2A:MSI --minx 91.77 --maxx 92 --miny 25.496 --maxy 25.695

# 3. Download everything the query found
bhd query download misty-falcon --out ./downloads
```

`query create` prints the scenes it found in a table and tells you what slug it saved them under (here, `misty-falcon` — yours will be different). You don't have to download right away: come back anytime with `bhd query show misty-falcon`, or `bhd query refresh misty-falcon` to check for newly published scenes in the same area.

Prefer a point and radius over a bounding box? Swap `--minx`/`--maxx`/`--miny`/`--maxy` for `--lat`/`--lon`/`--radius` (radius defaults to 10km, 1-100km):

```shell
bhd query create 2025-12-01 2025-12-30 --sat Sentinel-2A:MSI --lat 25.58 --lon 91.89 --radius 15
```

`--sat` is repeatable and accepts `SAT[:SEN[:PROD]]` — combine several missions in one search, or narrow to a single product within a sensor. See the [Examples](examples.md) page for both. Add `--no-save` to run a search without writing a query file or generating a slug — handy for one-off or scripted use.

## Quickstart from Python

The same three steps, from a script — one client, no subprocess:

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

See the [Python SDK guide](sdk.md) for the full walkthrough and the [API Reference](api/index.md) for every method.

## Where to go next

<div class="grid cards" markdown>

- :material-language-python: **[Python SDK](sdk.md)**

    The user-facing SDK guide — install, authenticate, search, download, and use the cart from Python.

- :material-code-tags: **[Examples](examples.md)**

    Worked walkthroughs of the CLI, including calling it from Python.

- :material-api: **[API Reference](api/index.md)**

    Class and function documentation generated from the source, covering every SDK method.

- :material-file-document-outline: **[Changelog](CHANGELOG.md)**

    What changed release to release.

</div>

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

## License

[MIT](https://github.com/geovicco-dev/bhoonidhi-downloader/blob/main/LICENSE)
