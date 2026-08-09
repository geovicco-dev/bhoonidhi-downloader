# Bhoonidhi Downloader

A CLI for searching, saving, and downloading satellite imagery from [ISRO's Bhoonidhi Earth Observation Portal](https://bhoonidhi.nrsc.gov.in/). Every command is also callable from a Python script.

[![PyPI version](https://img.shields.io/pypi/v/bhoonidhi-downloader.svg?logo=python&logoColor=white&label=PyPI&style=flat)](https://pypi.org/project/bhoonidhi-downloader/)
[:octicons-mark-github-16: View on GitHub](https://github.com/geovicco-dev/bhoonidhi-downloader){ .md-button }
[:material-language-python: PyPI](https://pypi.org/project/bhoonidhi-downloader/){ .md-button }

## What it does

- **Search by bounding box** — filter by satellite, sensor, and date range.
- **Named, persistent queries** — every search is saved under a short slug (`misty-falcon`), so you can come back to it later, refresh it for new scenes, or download from it without re-querying the portal.
- **Concurrent, verified downloads** — fetches multiple scenes in parallel, verifies each with a SHA256, and skips anything already downloaded.
- **Browse the archive** — list every satellite/sensor Bhoonidhi currently supports, live from the portal.
- **Session management** — log in once, refresh your token when it goes stale; no need to keep re-entering credentials.
- **Scriptable** — every command has a matching Python function, so you can call searches and downloads directly from a script instead of shelling out.

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
bhd query create 91.77 92 25.496 25.695 2025-12-01 2025-12-30 --sat Sentinel-2A --sen MSI

# 3. Download everything the query found
bhd query download misty-falcon --out ./downloads
```

`query create` prints the scenes it found in a table and tells you what slug it saved them under (here, `misty-falcon` — yours will be different). You don't have to download right away: come back anytime with `bhd query show misty-falcon`, or `bhd query refresh misty-falcon` to check for newly published scenes in the same area.

## Where to go next

<div class="grid cards" markdown>

- :material-code-tags: **[Examples](examples.md)**

    Worked walkthroughs of the CLI, including calling it from a script.

- :material-api: **[API Reference](api/index.md)**

    Class and function documentation generated from the source, for calling into the CLI's internals directly.

- :material-file-document-outline: **[Changelog](CHANGELOG.md)**

    What changed release to release.

</div>

## What's actually downloadable

Bhoonidhi's archive covers far more than what this tool can fetch directly. Every scene is searchable and shows up in results — but only scenes marked `OpenData_DirectDownload` (typically the more recent ones) can actually be pulled by `query download`. Anything priced or on-order shows up as metadata/planning-only for now, since there's no cart/order flow implemented yet.

The satellite/sensor list itself isn't hardcoded anywhere in this tool — `bhd archive list` fetches it live from the portal every time, so it's always current. Run it to see exactly what's searchable today rather than relying on a list here that would just go stale.

A couple of Bhoonidhi-specific quirks worth knowing about going in:

- **No resumable downloads.** The portal doesn't honor HTTP Range requests, so an interrupted download restarts from byte 0 rather than picking up where it left off. `query download` reports this explicitly (`↺ restarted from scratch`) when it happens.
- **Cold storage.** Scenes older than roughly a year often fail with a 404 error on direct download — Bhoonidhi's archiving policy isn't publicly documented, but this age threshold is a consistent pattern. The download report flags these as `cold_storage` rather than a generic failure. This CLI can only fetch `OpenData_DirectDownload` scenes; a 404'd scene can't be retrieved through it at all. You can request the scene directly on the [Bhoonidhi Browse & Order Portal](https://bhoonidhi.nrsc.gov.in/bhoonidhi/index.html#) — cart/order support is planned for this CLI but not yet implemented.
- **Already have it somewhere else?** `query download` checks if a scene's already downloaded and SHA-verified in a different folder before re-fetching it — if it finds one, it'll tell you and ask before wasting bandwidth. `--force` skips the check and downloads anyway.

## Limitations

- Search is bounding-box only — no point-coordinate or shapefile-based search yet.
- Only `OpenData_DirectDownload` scenes can be fetched directly; priced/on-order scenes show up in search results but are skipped on download (see above).
- No cart/order integration, so scenes that need to be requested first aren't reachable through this tool at all.

## License

[MIT](https://github.com/geovicco-dev/bhoonidhi-downloader/blob/main/LICENSE)
