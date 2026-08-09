# API Reference

Every CLI command in `bhd` is backed by a plain Python function or class under `bhoonidhi_downloader.core` — this section documents those directly from their source docstrings, for anyone scripting against the SDK instead of shelling out.

The package is organized by domain, matching the CLI's command groups:

| Module | Backs CLI group | Covers |
| --- | --- | --- |
| [Auth](auth.md) | `bhd auth` | Login, session validation, token refresh |
| [Archive](archive.md) | `bhd archive` | Fetching/caching the satellite & sensor catalog |
| [Search](search.md) | *(used by `bhd query create`)* | Querying the Bhoonidhi STAC-like search endpoint |
| [Query](query.md) | `bhd query` | Saved queries: create, list, refresh, fork, download |
| [Download](download.md) | *(used by `bhd query download`)* | Concurrent, verified scene downloads |
| [Schemas](schemas.md) | — | Pydantic models shared across all of the above |

## Two layers per domain

Most domains split into two layers you can use independently:

- **Client classes** (`ArchiveManager`, `AuthManager`, `SearchManager`, `DownloadManager`) — the actual HTTP/IO logic, no console output. Use these if you want full control.
- **Command functions** (`run_query_create`, `run_archive_list`, etc.) — what the CLI itself calls. These take a `rich.console.Console` and handle the table/status rendering seen on screen, but return plain data (a `QuerySchema`, a list of scenes, a bool) rather than printing-and-exiting. Reuse these directly if you just want the CLI's exact behavior without invoking a subprocess.

See [Examples](../examples.md) for both in action.
