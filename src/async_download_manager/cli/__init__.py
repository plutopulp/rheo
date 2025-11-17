"""CLI module - Typer-based command-line interface."""

from .app import create_cli_app

__all__ = ["create_cli_app", "cli"]


def cli() -> None:
    """Run the CLI application."""
    app = create_cli_app()
    app()
