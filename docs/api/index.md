# API Reference

The public Python API is the [`bhoonidhi_downloader.sdk`](../sdk.md) package. It
centres on one class, `BhoonidhiClient`, whose command groups are exposed as
namespaces.

| Page | Reachable as | Covers |
| --- | --- | --- |
| [Client](client.md) | `BhoonidhiClient` | Log in, session state, and the entry point to every namespace |
| [Archive](archive.md) | `client.archive` | Browse and export the satellite/sensor catalogue |
| [Query](query.md) | `client.query` | Saved searches: create, list, show, rename, fork, refresh, delete, download |
| [Cart](cart.md) | `client.cart` | Stage, list, and remove scenes in the Bhoonidhi cart |
| [Errors](errors.md) | `bhoonidhi_downloader.exceptions` | The exception hierarchy every method raises |
| [Data models](schemas.md) | `bhoonidhi_downloader.schemas` | The Pydantic models returned by the methods above |

Start with the [SDK guide](../sdk.md) for a task-by-task walkthrough; the pages
here are the exhaustive reference generated from the source.

```python
from bhoonidhi_downloader.sdk import BhoonidhiClient

client = BhoonidhiClient()
client.login("my-username", "my-password")
```
