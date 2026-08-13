"""The public entry point for using Bhoonidhi from Python.

``BhoonidhiClient`` is the one object a script needs. It holds the session,
so callers never load a token from disk or pass a JWT around by hand:

    from bhoonidhi_downloader.sdk import BhoonidhiClient

    client = BhoonidhiClient()
    client.login("my-user", "my-pass")
    if client.is_authenticated:
        ...

Everything it exposes mirrors the ``bhd`` CLI one-to-one, so the command
you'd type is the method you'd call.
"""

from bhoonidhi_downloader.core.auth import command as _auth
from bhoonidhi_downloader.core.auth.utils import load_session_info
from bhoonidhi_downloader.schemas import SessionSchema
from bhoonidhi_downloader.sdk.archive import ArchiveNamespace
from bhoonidhi_downloader.sdk.cart import CartNamespace
from bhoonidhi_downloader.sdk.query import QueryNamespace


class BhoonidhiClient:
    """A logged-in (or about-to-log-in) handle on the Bhoonidhi portal.

    The session is cached in memory. Pass an existing ``SessionSchema`` to
    reuse one, or leave it out and the saved session at
    ``~/.bhoonidhi/session`` is picked up the first time it's needed.
    """

    def __init__(self, session: SessionSchema | None = None) -> None:
        self._session = session
        self.archive = ArchiveNamespace()
        self.query = QueryNamespace(self)
        self.cart = CartNamespace(self)

    @property
    def account(self) -> SessionSchema | None:
        """The active session record, loaded from disk on first use if unset."""
        if self._session is None:
            data = load_session_info()
            if data.get("jwt"):
                self._session = SessionSchema(**data)
        return self._session

    @property
    def is_authenticated(self) -> bool:
        """True when a session with a token is held."""
        account = self.account
        return bool(account and account.jwt)

    def login(self, username: str, password: str, save: bool = True) -> SessionSchema:
        """Authenticate and remember the session.

        Mirrors ``bhd auth login``. The password is used only for this call
        and never stored on the client. Raises a
        :class:`~bhoonidhi_downloader.exceptions.BhoonidhiError` if the
        credentials are empty or rejected.
        """
        self._session = _auth.run_login(username, password, save=save)
        return self._session

    def logout(self) -> bool:
        """Forget the session, in memory and on disk.

        Mirrors ``bhd auth logout``. Returns True if a saved session was
        removed, False if there was nothing to remove.
        """
        self._session = None
        return _auth.run_logout()

    def whoami(self) -> str | None:
        """Return the logged-in username, or None. Mirrors ``bhd auth whoami``."""
        return _auth.run_whoami()

    def status(self) -> tuple[SessionSchema, bool] | None:
        """Return the saved session and whether its token still validates.

        Mirrors ``bhd auth status``. Returns None when there's no session
        to check.
        """
        return _auth.run_status()

    def refresh(self) -> SessionSchema | None:
        """Renew the current token without re-entering the password.

        Mirrors ``bhd auth refresh``. Updates the held session on success.
        Returns None when there's no session to refresh, and raises a
        :class:`~bhoonidhi_downloader.exceptions.BhoonidhiError` if the
        portal rejects the refresh.
        """
        session = _auth.run_refresh()
        if session is not None:
            self._session = session
        return session
