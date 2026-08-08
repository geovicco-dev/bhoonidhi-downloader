class BhoonidhiAuthError(Exception):
    """Raised when authentication or session validation against Bhoonidhi fails."""


class BhoonidhiAPIError(RuntimeError):
    """Raised when a Bhoonidhi API request fails or returns an unexpected payload."""


class BhoonidhiValidationError(ValueError):
    """Raised when a satellite/sensor combination or other input is invalid."""


class BhoonidhiNotFoundError(LookupError):
    """Raised when a requested scene or record cannot be found."""
