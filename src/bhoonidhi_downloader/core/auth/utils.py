"""Session file utilities."""

import json
import os
from pathlib import Path

SESSION_DIR = Path(os.path.expanduser("~")) / ".bhoonidhi"
SESSION_FILE = SESSION_DIR / "session"

_DEFAULT_SESSION = {
    "jwt": None,
    "userId": None,
    "user_email": None,
    "username": None,
    "sid": None,
    "scenes": [],
}


def save_session_info(session: dict) -> None:
    """Persist session info to ~/.bhoonidhi/session.

    The password is never written to disk. The file holds a live JWT, so
    it is created 0600 and the directory 0700 — without this it inherits
    the default umask (commonly 0644/0755), leaving the token readable by
    every other user on a shared machine.
    """
    SESSION_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    to_save = dict(session)
    to_save.pop("password", None)
    # Open with the restrictive mode in place from the start rather than
    # chmod-ing afterwards, which would leave a window where the token is
    # on disk world-readable.
    fd = os.open(SESSION_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(to_save, f)
    # The mode arguments above only apply when the path is created, so a
    # session file written by an earlier version keeps its old, looser
    # permissions forever. Tighten both explicitly on every save.
    os.chmod(SESSION_DIR, 0o700)
    os.chmod(SESSION_FILE, 0o600)


def load_session_info() -> dict:
    """Load session info from ~/.bhoonidhi/session, if present.

    Returns a dict with all values set to None if the file does not exist.
    """
    if SESSION_FILE.exists():
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    return dict(_DEFAULT_SESSION)


def clear_session_info() -> bool:
    """Remove the session file.

    Returns True if file was removed, False if it didn't exist.
    """
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()
        return True
    return False
