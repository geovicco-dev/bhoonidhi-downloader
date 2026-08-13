"""The Bhoonidhi Python SDK — a scripting entry point, separate from the CLI.

Everything a script needs comes from this one namespace:

    from bhoonidhi_downloader.sdk import BhoonidhiClient, BhoonidhiError
"""

from bhoonidhi_downloader.exceptions import (
    BhoonidhiAPIError,
    BhoonidhiAuthError,
    BhoonidhiError,
    BhoonidhiNotFoundError,
    BhoonidhiValidationError,
)
from bhoonidhi_downloader.sdk.client import BhoonidhiClient

__all__ = [
    "BhoonidhiClient",
    "BhoonidhiError",
    "BhoonidhiAuthError",
    "BhoonidhiAPIError",
    "BhoonidhiValidationError",
    "BhoonidhiNotFoundError",
]
