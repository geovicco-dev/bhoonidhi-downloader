# Archive

Reachable as `client.archive`. Browse and export the portal's satellite and
sensor catalogue. No login required.

```python
records = client.archive.list()
client.archive.export("archive.json")
```

::: bhoonidhi_downloader.sdk.archive.ArchiveNamespace
    options:
      members:
        - list
        - export
