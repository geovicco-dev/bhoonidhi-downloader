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

    The password is never written to disk.
    """
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    to_save = dict(session)
    to_save.pop("password", None)
    with open(SESSION_FILE, "w") as f:
        json.dump(to_save, f)


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
