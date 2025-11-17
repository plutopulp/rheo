"""CLI application factory."""

from pathlib import Path
from typing import Optional

import typer

from ..config.settings import LogLevel, Settings, build_settings
from .state import CLIState


def create_cli_app(settings: Settings | None = None) -> typer.Typer:
    """Create CLI application with optional settings override.

    Args:
        settings: Optional Settings override for testing

    Returns:
        Configured Typer application with commands registered
    """
    app = typer.Typer(
        name="adm",
        help="Async Download Manager - Concurrent HTTP downloads with progress tracking",
        no_args_is_help=True,
    )

    @app.callback()
    def setup(
        ctx: typer.Context,
        download_dir: Optional[Path] = typer.Option(
            None,
            "--download-dir",
            "-d",
            help="Directory to save downloads",
        ),
        workers: Optional[int] = typer.Option(
            None,
            "--workers",
            "-w",
            help="Number of concurrent workers",
            min=1,
        ),
        verbose: bool = typer.Option(
            False,
            "--verbose",
            "-v",
            help="Enable verbose output (DEBUG logging)",
        ),
    ) -> None:
        """Global options available to all commands."""
        if settings is not None:
            resolved_settings = settings
        else:
            resolved_settings = build_settings(
                download_dir=download_dir,
                max_workers=workers,
                log_level=LogLevel.DEBUG if verbose else None,
            )

        state = CLIState(resolved_settings)
        ctx.obj = state

    # Commands will be registered here later
    return app
