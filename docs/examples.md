# Examples

Two ways to use this tool: the CLI (`bhd`), or the [Python SDK](sdk.md). Both call the same underlying code — nothing is CLI-only.

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
$ bhd query create 2025-12-01 2025-12-30 --sat Sentinel-2A:MSI --minx 91.77 --maxx 92 --miny 25.496 --maxy 25.695
```

Arguments are `start_date end_date` (dates as `YYYY-MM-DD`), with the area of interest given as a bounding box (`--minx --maxx --miny --maxy`) or a point plus radius (`--lat --lon --radius`, radius defaults to 10km and must be 1-100km) — give one or the other, not both:

```console
$ bhd query create 2025-12-01 2025-12-30 --sat Sentinel-2A:MSI --lat 25.58 --lon 91.89 --radius 15
```

The results print as a table, and the query is saved under an auto-generated slug like `misty-falcon` — that's what you'll use to refer to it going forward.

### 3b. Multiple missions or a single product

`--sat` is repeatable and accepts `SAT[:SEN[:PROD]]` — combine several missions in one search, or narrow to one product within a sensor:

```console
$ bhd query create 2025-12-01 2025-12-30 --sat ResourceSat-2A:LISS3 --sat CartoSat-3 --minx 91.77 --maxx 92 --miny 25.496 --maxy 25.695
```

```console
$ bhd query create 2025-12-01 2025-12-30 --sat "EOS-06:OCM(GAC):L2C-Chlorophyll" --minx 74 --maxx 80 --miny 12 --maxy 18
```

Quote a `--sat` value containing parentheses, like `OCM(GAC)` above, so the shell passes it through intact. An unknown satellite, sensor, or product is skipped with a warning rather than failing the whole search — run `bhd archive list --sat X` first to see what's valid under a satellite.

### 3c. Search without saving

Every search is saved by default under a slug. When you just want the scene list — a one-off check, or a scripted/multi-worker run where saved query files would pile up on disk and diverge per worker — add `--no-save`:

```console
$ bhd query create 2025-12-01 2025-12-30 --sat Sentinel-2A:MSI --minx 91.77 --maxx 92 --miny 25.496 --maxy 25.695 --no-save
```

The scenes print exactly as usual, but nothing is written under `~/.bhoonidhi/queries/` and no slug is generated — so there's no `query show`/`refresh` to come back to. The SDK equivalent is `client.query.create(..., save=False)`, which still returns the `QuerySchema` with its scenes populated.

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

Or search around a point instead of a bounding box:

```python
query = client.query.create(
    datetime(2025, 12, 1), datetime(2025, 12, 30),
    satellite="Sentinel-2A", sensor="MSI",
    lat=25.58, lon=91.89, radius_km=15,
)
```

Combine several missions or narrow to a single product with `selections`:

```python
from bhoonidhi_downloader.sdk import Selection

query = client.query.create(
    datetime(2025, 12, 1), datetime(2025, 12, 30),
    selections=[
        Selection(satellite="ResourceSat-2A", sensor="LISS3"),
        Selection(satellite="CartoSat-3"),
    ],
    minx=91.77, maxx=92.0, miny=25.496, maxy=25.695,
)
```

See the [Python SDK guide](sdk.md) for the full walkthrough and the
[API Reference](api/index.md) for every method and return type.
