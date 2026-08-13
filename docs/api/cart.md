# Cart

Reachable as `client.cart`. Stage scenes into the Bhoonidhi cart, list what's
staged, and remove items. All three reach the portal and need a login.

```python
added, failed, srt = client.cart.add("misty-falcon", select=[2, 4])
client.cart.list(filter_by="priced")
client.cart.rm(select=[1])
```

::: bhoonidhi_downloader.sdk.cart.CartNamespace
    options:
      members:
        - add
        - list
        - rm

## Cart kinds

`add` and `rm` report which of the portal's three carts each scene landed in,
as a `CartKind`.

::: bhoonidhi_downloader.core.cart.utils.CartKind
