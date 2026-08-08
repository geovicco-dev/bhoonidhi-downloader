import logging

from rich.console import Console
from rich.highlighter import ReprHighlighter
from rich.logging import RichHandler
from rich.theme import Theme

CUSTOM_THEME = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "success": "bold green",
        "progress": "blue",
        "highlight": "bold yellow",
        "dim": "dim white",
        "operation": "bold cyan",
        "filename": "yellow",
        "path": "dim blue",
    }
)


def get_console() -> Console:
    return Console(
        theme=CUSTOM_THEME,
        highlighter=ReprHighlighter(),
        force_terminal=True,
        legacy_windows=False,
        log_time=True,
        log_path=True,
        log_time_format="[%H:%M:%S]",
        color_system="truecolor",
    )


class CustomRichHandler(RichHandler):
    """Custom RichHandler to format log levels with emojis and colors."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            console=get_console(),  # ty:ignore[parameter-already-assigned]
            markup=True,
            rich_tracebacks=True,
            show_time=True,
            show_level=False,
            show_path=True,
            enable_link_path=False,
        )

    def format(self, record):
        if record.levelname == "WARNING":
            record.msg = f"[warning]⚠️ {record.msg}[/warning]"
        elif record.levelname == "ERROR":
            record.msg = f"[error]❌ {record.msg}[/error]"
        elif "✓" in str(record.msg):
            record.msg = f"[success]{record.msg}[/success]"
        return super().format(record)


def get_logger(name: str = "bhoonidhi") -> logging.Logger:
    """Get a logger instance with a shared RichHandler configuration."""
    logger = logging.getLogger(name)
    if not logger.hasHandlers():
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            datefmt="[%Y-%m-%d %H:%M:%S]",
            handlers=[CustomRichHandler(level=logging.INFO)],
            force=True,
        )
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
