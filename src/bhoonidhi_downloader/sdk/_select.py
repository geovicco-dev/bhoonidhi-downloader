"""Shared helpers: normalize typed SDK inputs into core-ready forms."""

from __future__ import annotations

from bhoonidhi_downloader.exceptions import BhoonidhiValidationError


def normalize_select(select: list[int | str] | None) -> list[str] | None:
    """Convert a typed ``select`` list into the string tokens the core expects.

    An ``int`` is a 1-based scene index; a ``str`` is a full scene ID. The
    comma-separated shorthand the CLI accepts (``"1,2,3"``) is deliberately
    rejected — an SDK caller passes real list elements (``[1, 2, 3]``), not
    one joined string.

    Raises:
        BhoonidhiValidationError: if an entry isn't a plain index or scene ID.
    """
    if select is None:
        return None

    tokens: list[str] = []
    for entry in select:
        if isinstance(entry, bool):
            # bool is an int subclass; a True/False index is never meant.
            raise BhoonidhiValidationError(f"Invalid select entry: {entry!r}")
        if isinstance(entry, int):
            tokens.append(str(entry))
        elif isinstance(entry, str) and entry.strip() and "," not in entry:
            tokens.append(entry.strip())
        else:
            raise BhoonidhiValidationError(
                f"Invalid select entry: {entry!r}. Pass a list of scene indices "
                "or scene IDs, e.g. select=[1, 2, 3], not a comma-joined string."
            )
    return tokens


def normalize_filter(filter_by: str | list[str] | None) -> list[str] | None:
    """Accept a single state or a list of states for a ``filter_by`` argument.

    A plain string (``"priced"``) is wrapped into a one-element list so it
    isn't walked character by character. A list passes straight through. The
    core parser handles casing, ``-``/``_``, and comma-separated values.
    """
    if filter_by is None:
        return None
    if isinstance(filter_by, str):
        return [filter_by]
    return list(filter_by)
