# Query

Reachable as `client.query`. Run searches and manage saved queries. `create`,
`refresh`, and `download` reach the portal; the rest work on the local query
store.

```python
from datetime import datetime

query = client.query.create(
    datetime(2025, 12, 1), datetime(2025, 12, 30),
    satellite="Sentinel-2A", sensor="MSI",
    minx=91.77, maxx=92.0, miny=25.496, maxy=25.695,
)
client.query.download(query.slug, "./downloads")
```

::: bhoonidhi_downloader.sdk.query.QueryNamespace
    options:
      members:
        - create
        - list
        - show
        - rename
        - fork
        - refresh
        - rm
        - download

## Download result

`download` returns a list of `DownloadOutcome`, one per scene.

::: bhoonidhi_downloader.core.download.client.DownloadOutcome
