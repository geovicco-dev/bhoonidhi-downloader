from __future__ import annotations

import importlib.metadata
import sys

import typer

from bhoonidhi_downloader.cli.archive import archive_app
from bhoonidhi_downloader.cli.auth import auth_app
from bhoonidhi_downloader.cli.cart import cart_app
from bhoonidhi_downloader.cli.query import query_app


def _get_version() -> str:
    try:
        return importlib.metadata.version("bhoonidhi-downloader")
    except importlib.metadata.PackageNotFoundError:
        return "unknown (not installed)"


def _main_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


app = typer.Typer(
    name="bhoonidhi-downloader",
    help=(
        "Search, save, and download satellite imagery from ISRO's "
        "Bhoonidhi Earth Observation portal.\n\n"
        "A typical session: authenticate once, search an area and date "
        "range, then download or stage what you find.\n\n"
        "  bhd auth login\n"
        "  bhd query create 2026-01-01 2026-01-31 --sat ResourceSat-2A:LISS3 "
        "--minx 91.7 --maxx 92.0 --miny 25.5 --maxy 25.7\n"
        "  bhd query download <slug> --out ./scenes\n\n"
        "Run 'bhd COMMAND --help' for a command's full options and examples."
    ),
    callback=_main_callback,
    invoke_without_command=True,
    pretty_exceptions_enable=False,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_short=False,
    add_completion=False,
    no_args_is_help=False,
)

# Register subcommand groups
app.add_typer(auth_app, name="auth")
app.add_typer(archive_app, name="archive")
app.add_typer(query_app, name="query")
app.add_typer(cart_app, name="cart")


@app.command()
def version() -> None:
    """Package version."""
    typer.echo(f"bhoonidhi-downloader {_get_version()}")


if __name__ == "__main__":
    if "--version" in sys.argv or "-V" in sys.argv:
        typer.echo(f"bhoonidhi-downloader {_get_version()}")
        raise SystemExit(0)
    app()
