# Examples

Two ways to use this tool: the CLI (`bhd`), or importing `bhoonidhi_downloader.core` directly in a script. Both call the same underlying functions — nothing is CLI-only.

## CLI walkthrough

### 1. Authenticate

```console
$ bhd auth login
Username: myuser
Password:
✓ Logged in as myuser
```

Omit `--username`/`--password` and you'll be prompted. Pass them directly for non-interactive use:

```console
$ bhd auth login --username myuser --password ${BHOONIDHI_PASSWORD}
```

Check your session anytime with `bhd auth status`, or find out who's currently logged in with `bhd auth whoami`.

### 2. See what's searchable

```console
$ bhd archive list --sat Sentinel-2A
```

This hits the portal live (and caches the result), so it always reflects what's currently available — no hardcoded satellite list to go stale.

### 3. Search a bounding box and save it as a query

```console
$ bhd query create 91.77 92 25.496 25.695 2025-12-01 2025-12-30 --sat Sentinel-2A --sen MSI
```

Arguments are `minx maxx miny maxy start_date end_date` (dates as `YYYY-MM-DD`). The results print as a table, and the query is saved under an auto-generated slug like `misty-falcon` — that's what you'll use to refer to it going forward.

### 4. Come back to it later

```console
$ bhd query show misty-falcon        # redisplay the saved scenes
$ bhd query refresh misty-falcon     # check for newly published scenes in the same AOI
```

`refresh` doesn't re-run the full search — it only looks for scenes newer than what's already saved, so it's cheap to run repeatedly.

### 5. Download

```console
$ bhd query download misty-falcon --out ./downloads
```

Downloads run concurrently (`--parallel`, default 4), each file is SHA256-verified after the fact, and anything already present in `--out` is skipped unless you pass `--force`. If your session's gone stale, `query download` re-authenticates automatically rather than failing outright.

To grab specific scenes instead of the whole query, use `--select` with the 1-based index or scene ID shown by `query show`:

```console
$ bhd query download misty-falcon --out ./downloads --select 1,3,5
```

Not sure what a run will do first? `--dry-run` shows the same table without fetching anything or needing a session:

```console
$ bhd query download misty-falcon --out ./downloads --dry-run
```

### 6. Stage what you can't download directly

`query download` only fetches scenes marked `Ready`. For everything else — open scenes that aren't staged, on-order, or priced — add them to the Bhoonidhi cart and finish the order in the Browse & Order portal:

```console
$ bhd cart add misty-falcon --select 2,4      # stage specific scenes
$ bhd cart list                                # see everything staged
$ bhd cart rm --select 1                        # remove a staged row by its number
```

Each scene is routed automatically to the portal's direct-download, on-order, or priced cart based on its access type — a query mixing all three works in one command. `bhd cart list` merges all three carts into one table: each row shows which cart it's in and whether it's ready or archived, its satellite and sensor, the date it was added, and whether the order has been placed, alongside Metadata and Quick View links. Because the portal files items by the date they were added, `cart list` with no options shows today only; use `--last "1 week"` (or `--since`/`--until`) to see scenes staged on earlier days.

`--filter ready|archived|onorder|priced` narrows either `query show` or `cart list`/`cart rm` to one or more states — comma-separated or repeatable — using the same words shown in the Availability/Cart columns:

```console
$ bhd query show misty-falcon --filter ready       # only what's downloadable now
$ bhd cart list --filter priced                    # only the priced cart
```

## Calling it from a script

Every CLI command is a thin wrapper around a plain Python function — nothing about the underlying logic depends on being invoked from a terminal. If you're scripting a bulk ingestion pipeline or wiring this into a notebook, call into `bhoonidhi_downloader.core` directly instead of shelling out:

```python
from datetime import datetime

from bhoonidhi_downloader.core.archive import ArchiveManager
from bhoonidhi_downloader.core.query.command import run_query_create, run_query_download
from bhoonidhi_downloader.logger import get_console

console = get_console()

# Browse the archive programmatically
manifest = ArchiveManager().build_manifest()
print(manifest["Sentinel-2A"].keys())  # -> dict_keys(['MSI'])

# Search + save a query (same thing `bhd query create` does)
query = run_query_create(
    console,
    minx=91.77,
    maxx=92,
    miny=25.496,
    maxy=25.695,
    start_date=datetime(2025, 12, 1),
    end_date=datetime(2025, 12, 30),
    satellite="Sentinel-2A",
    sensor="MSI",
)

# Download everything it found
run_query_download(console, slug=query.slug, out="./downloads")
```

Command handlers live under `core/<domain>/command.py` (`auth`, `archive`, `search`, `query`, `download`, `cart`) — each one takes a `rich.console.Console` (get one via `bhoonidhi_downloader.logger.get_console()`) and returns plain data (a `QuerySchema`, a list of scenes, a bool) rather than printing-and-exiting like a CLI would. The `render.py` modules alongside them turn that data into the tables you see on screen — skip them entirely and just work with the returned objects if you're scripting.

See the [API Reference](api/index.md) for the full set of classes and functions this exposes.

### Authenticating without the CLI

```python
from bhoonidhi_downloader.core.auth.client import AuthManager
from bhoonidhi_downloader.schemas import SessionSchema

auth = AuthManager(cfg=SessionSchema(username="myuser", password="mypassword"))
session = auth.login()
print(session.jwt)  # use this token for authenticated requests
```

### Exporting the archive to JSON

```python
from bhoonidhi_downloader.core.archive import ArchiveManager

am = ArchiveManager()
data = am.parse(satellite_filter="ResourceSat-2A")  # omit for the full archive

import json
from pathlib import Path

Path("archive.json").write_text(json.dumps(data, indent=2))
```
