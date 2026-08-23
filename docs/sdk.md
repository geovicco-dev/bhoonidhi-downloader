# Python SDK

Everything the `bhd` command does is also callable from Python through a single
object, `BhoonidhiClient`. Use it to script searches, downloads, and cart
operations, or to wire Bhoonidhi into a data pipeline.

```python
from bhoonidhi_downloader.sdk import BhoonidhiClient

client = BhoonidhiClient()
client.login("my-username", "my-password")
```

One import, one client. Each command group is a namespace on the client:
`client.archive`, `client.query`, `client.cart`. The method names match the CLI
commands one-to-one.

## Install

```shell
pip install bhoonidhi-downloader
```

## Log in

```python
client = BhoonidhiClient()
client.login("my-username", "my-password")

client.is_authenticated   # True
client.whoami()           # "my-username"
```

If the portal emails a 6-digit OTP instead of returning a JWT immediately, pass
it (or a prompt callback) — the same second step the website uses:

```python
client.login("my-username", "my-password", otp="123456")
client.login("my-username", "my-password", otp_prompt=lambda msg: input("OTP: "))
```

A wrong or malformed code from `otp_prompt` doesn't fail outright — the same
callback is called again (with an updated message) against the mailed code,
for as many attempts as the portal itself allows, before `login` raises.
`otp` is checked once and raises immediately on rejection, since a fixed
string can't be corrected without someone to ask for a new one.

The client keeps the session in memory and also saves it to
`~/.bhoonidhi/session`, so a later `BhoonidhiClient()` in a new process picks it
up automatically — you don't have to log in every run.

```python
client = BhoonidhiClient()
if not client.is_authenticated:
    client.login("my-username", "my-password")
```

Keep credentials out of your source. Read them from the environment or a prompt:

```python
import os, getpass

client.login(
    os.environ["BHOONIDHI_USER"],
    os.environ.get("BHOONIDHI_PASS") or getpass.getpass(),
)
```

## Browse the archive

No login needed for the catalogue.

```python
records = client.archive.list()          # every satellite/sensor
client.archive.export("archive.json")    # write it to disk as JSON
client.archive.export("s2.json", sat="Sentinel-2A")   # one satellite
```

## Search and save a query

A search is saved under a short slug (like `misty-falcon`) so you can return to
it, refresh it, or download from it later. Give the area of interest as a
bounding box (`minx`/`maxx`/`miny`/`maxy`) or a point plus radius
(`lat`/`lon`/`radius_km`, default 10km, 1-100km) — one or the other, not both.

```python
from datetime import datetime

query = client.query.create(
    datetime(2025, 12, 1), datetime(2025, 12, 30),
    satellite="Sentinel-2A", sensor="MSI",
    minx=91.77, maxx=92.0, miny=25.496, maxy=25.695,
)

print(query.slug)              # "misty-falcon"
print(len(query.scenes))       # how many scenes matched
```

Or search around a point instead:

```python
query = client.query.create(
    datetime(2025, 12, 1), datetime(2025, 12, 30),
    satellite="Sentinel-2A", sensor="MSI",
    lat=25.58, lon=91.89, radius_km=15,
)
```

`create` returns `None` if nothing matched.

### Multiple missions or a single product

Pass `selections` instead of `satellite`/`sensor` to search several missions
in one call, or narrow to one product within a sensor. Each entry is a
`Selection(satellite, sensor=None, product=None)`; give one or the other, not
both.

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

Narrow further to a single product within a sensor:

```python
query = client.query.create(
    datetime(2025, 12, 1), datetime(2025, 12, 30),
    selections=[Selection(satellite="EOS-06", sensor="OCM(GAC)", product="L2C-Chlorophyll")],
    minx=74, maxx=80, miny=12, maxy=18,
)
```

An unknown satellite, sensor, or product is skipped with a warning instead of
failing the whole search; `client.archive.list()` (or `bhd archive list --sat
X`) shows valid names.

Work with saved queries:

```python
client.query.list()                    # all saved queries
client.query.show("misty-falcon")      # one query, with its scenes
client.query.rename("misty-falcon", name="Shillong winter")
client.query.fork("misty-falcon")      # clone under a new slug
client.query.rm("misty-falcon")        # delete
```

Check for newly published scenes in the same area without re-running the whole
search:

```python
query, added = client.query.refresh("misty-falcon")
print(f"{added} new scene(s)")         # added is None if already up to date
```

## Download

```python
outcomes = client.query.download("misty-falcon", "./downloads")

for o in outcomes:
    print(o.scene_id, o.status)        # "downloaded", "already_downloaded", ...
```

Priced and on-order scenes are skipped — those are ordered through the cart.
Files already present in the output folder are skipped unless you pass
`force=True`. Each download is verified with a SHA256.

Download specific scenes with `select` — a list of 1-based indices or scene IDs
from `query.show`:

```python
client.query.download("misty-falcon", "./downloads", select=[1, 3, 5])
```

Show progress as bytes arrive:

```python
def on_progress(scene_id, done, total):
    pct = f"{done / total * 100:3.0f}%" if total else "  ? "
    print(f"{pct}  {scene_id}")

client.query.download("misty-falcon", "./downloads", on_progress=on_progress)
```

## Stage scenes in the cart

Scenes you can't download directly — open scenes that aren't staged, on-order, or
priced — go into the Bhoonidhi cart. Finish the order in the Browse & Order
portal.

```python
added, failed, srt = client.cart.add("misty-falcon", select=[2, 4])

for scene, kind in added:
    print(scene["ID"], "->", kind)     # which cart it landed in
```

List what's staged — all three carts (direct, on-order, priced) in one list:

```python
items = client.cart.list()                       # added today
items = client.cart.list(last="1 week")          # added in the last 7 days
items = client.cart.list(filter_by="priced")     # only the priced cart
```

Cart items are filed by the date they were added, so `list()` with no dates
shows today only. Widen it with `last`, or `since` / `until`.

Remove staged rows:

```python
client.cart.rm(select=[1])                        # by cart row number
client.cart.rm("misty-falcon", select=[2, 4])     # by a query's scenes
```

## Handle errors

Every failure raises a subclass of `BhoonidhiError`, so one `except` catches
anything:

```python
from bhoonidhi_downloader.sdk import BhoonidhiClient, BhoonidhiError

try:
    client.query.download("misty-falcon", "./downloads")
except BhoonidhiError as e:
    print("something went wrong:", e)
```

Catch specific cases when you want to react differently:

```python
from bhoonidhi_downloader.exceptions import (
    BhoonidhiAuthError,        # not logged in, or credentials rejected
    BhoonidhiNotFoundError,    # unknown query slug or scene
    BhoonidhiValidationError,  # bad argument (empty login, bad filter value)
    BhoonidhiAPIError,         # the portal returned an error
)

try:
    client.query.download("typo-slug", "./downloads")
except BhoonidhiNotFoundError:
    print("no query by that name")
except BhoonidhiAuthError:
    client.login("my-username", "my-password")
```

## Runnable notebooks

Worked, runnable examples for each namespace — open them in Jupyter and run the
cells against your own session:

- [Auth](api/notebooks/auth.ipynb) — logging in and the session lifecycle
- [Archive](api/notebooks/archive.ipynb) — browsing and exporting the catalogue
- [Query](api/notebooks/query.ipynb) — search, saved queries, and downloads
- [Cart](api/notebooks/cart.ipynb) — staging, listing, and removing cart items

See the [API Reference](api/index.md) for every method, argument, and return
type.
