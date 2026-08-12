"""A scrollable table viewer for result sets that don't fit on screen.

Printing every row at once pushes everything off the top of the terminal
and makes long lists hard to read. This viewer shows a fixed number of
rows and columns at a time, and you move around with the keyboard
instead of scrolling.

If the output isn't going to a real terminal (for example it's piped to
a file or another command), it just prints everything at once instead.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from rich.align import Align
from rich.console import Console, ConsoleRenderable, Group
from rich.live import Live
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

#: Rows of chrome around the table body: title, header, borders, status,
#: help line. Subtracted from terminal height to size the viewport.
_CHROME_ROWS = 10

#: Always-visible leading columns. Keeping the row number pinned means a
#: horizontal scroll never loses your place.
_PINNED = 1


@dataclass
class Column:
    """One column of the table."""

    header: str
    #: Called with (row, zero-based row index) and returns cell markup.
    render: Callable[[Any, int], str]
    style: str = ""
    width: int | None = None
    justify: str = "left"


@dataclass
class ViewerState:
    """Where the viewport currently sits."""

    row_offset: int = 0
    col_offset: int = 0
    rows_visible: int = 20
    #: Scrollable (non-pinned) columns that fit at the current width.
    cols_visible: int = 4

    total_rows: int = 0
    total_cols: int = 0

    def clamp(self) -> None:
        max_row = max(self.total_rows - self.rows_visible, 0)
        self.row_offset = max(0, min(self.row_offset, max_row))
        max_col = max(self.total_cols - _PINNED - self.cols_visible, 0)
        self.col_offset = max(0, min(self.col_offset, max_col))


# ---------------------------------------------------------------------------
# Key input
# ---------------------------------------------------------------------------


def _read_key() -> str:
    """Wait for one keypress and return a simple name for it.

    Arrow keys send multiple characters at once, so those get turned
    into readable names like "up" or "down" here.
    """
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch != "\x1b":
            return ch
        # Escape alone, or the start of a sequence — read the rest.
        seq = sys.stdin.read(2)
        return {
            "[A": "up",
            "[B": "down",
            "[C": "right",
            "[D": "left",
            "[5": "pageup",
            "[6": "pagedown",
            "[H": "home",
            "[F": "end",
        }.get(seq, "escape")
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _apply_key(key: str, state: ViewerState) -> bool:
    """Move the viewport based on a keypress. Returns False to quit."""
    page = max(state.rows_visible - 2, 1)
    half = max(state.rows_visible // 2, 1)

    if key in ("q", "escape", "\x03"):  # \x03 = Ctrl-C
        return False
    if key in ("j", "down"):
        state.row_offset += 1
    elif key in ("k", "up"):
        state.row_offset -= 1
    elif key in ("l", "right"):
        state.col_offset += 1
    elif key in ("h", "left"):
        state.col_offset -= 1
    elif key in ("f", "pagedown", " "):
        state.row_offset += page
    elif key in ("b", "pageup"):
        state.row_offset -= page
    elif key == "\x04":  # Ctrl-D
        state.row_offset += half
    elif key == "\x15":  # Ctrl-U
        state.row_offset -= half
    elif key in ("g", "home"):
        state.row_offset = 0
    elif key in ("G", "end"):
        state.row_offset = state.total_rows
    elif key == "0":
        state.col_offset = 0
    elif key == "$":
        state.col_offset = state.total_cols

    state.clamp()
    return True


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _fit_columns(console: Console, columns: list[Column], col_offset: int) -> int:
    """How many scrollable columns fit after the pinned ones."""
    budget = (console.width or 80) - 4  # borders and padding
    for col in columns[:_PINNED]:
        budget -= (col.width or len(col.header)) + 3

    fitted = 0
    for col in columns[_PINNED + col_offset :]:
        cost = (col.width or max(len(col.header), 12)) + 3
        if budget - cost < 0:
            break
        budget -= cost
        fitted += 1
    return max(fitted, 1)


def _build_table(
    rows: list[Any], columns: list[Column], state: ViewerState, title: str
) -> Table:
    visible = (
        columns[:_PINNED]
        + columns[
            _PINNED + state.col_offset : _PINNED + state.col_offset + state.cols_visible
        ]
    )

    table = Table(title=title, expand=False)
    for col in visible:
        table.add_column(
            col.header,
            style=col.style,
            no_wrap=True,
            overflow="ellipsis",
            max_width=col.width,
            justify=col.justify,
        )

    window = rows[state.row_offset : state.row_offset + state.rows_visible]
    for offset, row in enumerate(window):
        index = state.row_offset + offset
        table.add_row(*(col.render(row, index) for col in visible))
    return table


def _status_line(state: ViewerState) -> Text:
    first_row = state.row_offset + 1 if state.total_rows else 0
    last_row = min(state.row_offset + state.rows_visible, state.total_rows)
    first_col = state.col_offset + 1
    last_col = min(state.col_offset + state.cols_visible, state.total_cols - _PINNED)

    text = Text(justify="center")
    text.append(f"rows {first_row}-{last_row}/{state.total_rows}", style="bold cyan")
    text.append(
        f"   cols {first_col}-{last_col}/{state.total_cols - _PINNED} scrollable",
        style="bold magenta",
    )
    return text


#: (key, action) pairs shown in the nav-controls table, in display order.
_KEYMAP: list[tuple[str, str]] = [
    ("j / k", "scroll down / up"),
    ("h / l", "scroll columns left / right"),
    ("f / b", "page down / up"),
    ("g / G", "jump to top / end"),
    ("0 / $", "jump to first / last column"),
    ("q", "quit"),
]


def _nav_help() -> Table:
    """A centered table listing every key and what it does."""
    table = Table(title="Controls", show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", justify="right", style="bold yellow")
    table.add_column("Action", justify="left", style="dim")
    for key, action in _KEYMAP:
        table.add_row(key, action)
    return table


_HELP = Align.center(_nav_help())


def _render(
    rows: list[Any],
    columns: list[Column],
    state: ViewerState,
    title: str,
    footer: ConsoleRenderable | None,
) -> Group:
    items: list[Any] = [
        Align.center(_build_table(rows, columns, state, title)),
        _status_line(state),
        Rule(style="dim"),
        _HELP,
    ]
    if footer is not None:
        items.append(Rule(style="dim"))
        items.append(footer)
    return Group(*items)


def _footer_rows(console: Console, footer: ConsoleRenderable | None) -> int:
    """How many lines the controls table and footer take up together."""
    rows = 1 + len(console.render_lines(_HELP, console.options))
    if footer is not None:
        rows += 1 + len(console.render_lines(footer, console.options))
    return rows


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def show_table(
    console: Console,
    rows: list[Any],
    columns: list[Column],
    title: str,
    interactive: bool | None = None,
    truncate: bool = False,
    footer: ConsoleRenderable | None = None,
) -> None:
    """Show a table you can scroll through, when the terminal supports it.

    Set ``interactive`` to force scrolling on or off; leave it unset and
    it turns on automatically for a real terminal. ``footer`` is extra
    content (like a legend) shown below the table — it stays on screen
    the whole time you're scrolling, not just after you quit.
    """
    if not rows:
        console.print(f"[yellow]{title}: nothing to show.[/]")
        return

    if interactive is None:
        interactive = console.is_terminal and sys.stdin.isatty()

    if not interactive:
        _print_static(console, rows, columns, title, truncate=truncate, footer=footer)
        return

    footer_rows = _footer_rows(console, footer)
    state = ViewerState(total_rows=len(rows), total_cols=len(columns))
    state.rows_visible = max(
        (console.size.height or 24) - _CHROME_ROWS - footer_rows, 5
    )
    state.cols_visible = _fit_columns(console, columns, 0)
    state.clamp()

    try:
        with Live(
            _render(rows, columns, state, title, footer),
            console=console,
            auto_refresh=False,
            screen=True,  # alternate screen: leaves the scrollback untouched
        ) as live:
            while True:
                key = _read_key()
                if not _apply_key(key, state):
                    break
                # Recompute on every frame so a resize mid-session adapts.
                state.rows_visible = max(
                    (console.size.height or 24) - _CHROME_ROWS - footer_rows, 5
                )
                state.cols_visible = _fit_columns(console, columns, state.col_offset)
                state.clamp()
                live.update(_render(rows, columns, state, title, footer), refresh=True)
    except (OSError, ValueError):
        # No usable terminal after all (no controlling tty, closed stdin).
        _print_static(console, rows, columns, title, truncate=truncate, footer=footer)


def _print_static(
    console: Console,
    rows: list[Any],
    columns: list[Column],
    title: str,
    truncate: bool = False,
    footer: ConsoleRenderable | None = None,
) -> None:
    """Print every row and column at once, for when there's no live terminal.

    Long values are shown in full by default, wrapping onto extra lines,
    so a piped ``grep`` still sees the whole value. ``truncate`` switches
    to one line per row instead, which reads better as an on-screen
    summary.
    """
    table = Table(title=title)
    for col in columns:
        table.add_column(
            col.header,
            style=col.style,
            justify=col.justify,
            no_wrap=truncate,
            overflow="ellipsis" if truncate else "fold",
            max_width=col.width if truncate else None,
        )
    for index, row in enumerate(rows):
        table.add_row(*(col.render(row, index) for col in columns))
    console.print(Align.center(table))
    if footer is not None:
        console.print(Rule(style="dim"))
        console.print(footer)
