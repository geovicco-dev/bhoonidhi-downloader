# Errors

Every failure raises a subclass of `BhoonidhiError`, so a single `except
BhoonidhiError` catches anything the SDK can throw. Each subclass also keeps its
matching built-in base (`ValueError`, `LookupError`, `RuntimeError`), so
existing handlers for those still work.

```python
from bhoonidhi_downloader.sdk import BhoonidhiError

try:
    client.query.download("misty-falcon", "./downloads")
except BhoonidhiError as e:
    print("failed:", e)
```

| Exception | Raised when | Built-in base |
| --- | --- | --- |
| `BhoonidhiError` | Base class for all of the below | `Exception` |
| `BhoonidhiAuthError` | Not logged in, or credentials rejected | `Exception` |
| `BhoonidhiValidationError` | A bad argument (empty login, unknown filter, malformed `select`) | `ValueError` |
| `BhoonidhiNotFoundError` | An unknown query slug or scene | `LookupError` |
| `BhoonidhiAPIError` | The portal returned an error or an unexpected response | `RuntimeError` |

::: bhoonidhi_downloader.exceptions.BhoonidhiError

::: bhoonidhi_downloader.exceptions.BhoonidhiAuthError

::: bhoonidhi_downloader.exceptions.BhoonidhiValidationError

::: bhoonidhi_downloader.exceptions.BhoonidhiNotFoundError

::: bhoonidhi_downloader.exceptions.BhoonidhiAPIError
