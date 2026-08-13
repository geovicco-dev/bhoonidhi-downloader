class BhoonidhiError(Exception):
    """Base class for every error this package raises.

    Catch this to handle any Bhoonidhi failure in one place. The
    subclasses below also keep their matching built-in base (``ValueError``,
    ``LookupError``, ...) so existing ``except ValueError`` style handlers
    keep working.
    """


class BhoonidhiAuthError(BhoonidhiError):
    """Raised when authentication or session validation against Bhoonidhi fails."""


class BhoonidhiAPIError(BhoonidhiError, RuntimeError):
    """Raised when a Bhoonidhi API request fails or returns an unexpected payload."""


class BhoonidhiValidationError(BhoonidhiError, ValueError):
    """Raised when a satellite/sensor combination or other input is invalid."""


class BhoonidhiNotFoundError(BhoonidhiError, LookupError):
    """Raised when a requested scene or record cannot be found."""
