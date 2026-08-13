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
it, refresh it, or download from it later.

```python
from datetime import datetime

query = client.query.create(
    91.77, 92.0, 25.496, 25.695,          # minx, maxx, miny, maxy
    datetime(2025, 12, 1), datetime(2025, 12, 30),
    satellite="Sentinel-2A", sensor="MSI",
)

print(query.slug)              # "misty-falcon"
print(len(query.scenes))       # how many scenes matched
```

`create` returns `None` if nothing matched.

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
