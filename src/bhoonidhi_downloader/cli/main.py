from __future__ import annotations

import importlib.metadata
import sys

import typer

from bhoonidhi_downloader.cli.archive import archive_app
from bhoonidhi_downloader.cli.auth import auth_app
from bhoonidhi_downloader.cli.query import query_app


def _get_version() -> str:
    try:
        return importlib.metadata.version("bhoonidhi-downloader")
    except importlib.metadata.PackageNotFoundError:
        return "0.2.0rc1 (development)"


def _main_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


app = typer.Typer(
    name="bhoonidhi-downloader",
    help="Search, save, and download satellite imagery from the Bhoonidhi Earth Observation portal.",
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


### CLI COMMANDS ####


@app.command()
def version() -> None:
    """Package version."""
    typer.echo(f"bhoonidhi-downloader {_get_version()}")


if __name__ == "__main__":
    if "--version" in sys.argv or "-V" in sys.argv:
        typer.echo(f"bhoonidhi-downloader {_get_version()}")
        raise SystemExit(0)
    app()
