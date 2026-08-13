# Client

`BhoonidhiClient` is the entry point to the SDK. It holds the portal session and
exposes each command group as a namespace: `client.archive`, `client.query`,
`client.cart`.

```python
from bhoonidhi_downloader.sdk import BhoonidhiClient

client = BhoonidhiClient()
client.login("my-username", "my-password")
```

::: bhoonidhi_downloader.sdk.client.BhoonidhiClient
    options:
      members:
        - login
        - logout
        - whoami
        - status
        - refresh
        - is_authenticated
        - account
        - require_account
