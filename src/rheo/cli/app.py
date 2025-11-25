"""CLI application factory."""

from pathlib import Path
from typing import Optional

import typer

from ..config.settings import LogLevel, Settings, build_settings
from .commands import download
from .state import CLIState


def create_cli_app(
    settings: Settings | None = None, state: CLIState | None = None
) -> typer.Typer:
    """Create CLI application with optional settings or state override.

    Args:
        settings: Optional Settings override (ignored if state provided)
        state: Optional CLIState override for testing

    Returns:
        Configured Typer application with commands registered
    """
    app = typer.Typer(
        help="Rheo - Concurrent HTTP download orchestration with async I/O",
        name="rheo",
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
        # Use provided state if available (for testing)
        if state is not None:
            ctx.obj = state
        elif settings is not None:
            ctx.obj = CLIState(settings)
        else:
            resolved_settings = build_settings(
                download_dir=download_dir,
                max_concurrent=workers,
                log_level=LogLevel.DEBUG if verbose else None,
            )
            ctx.obj = CLIState(resolved_settings)

    # Register commands
    # Note: When we have 2+ command groups, migrate to sub-app pattern:
    #   app.add_typer(download_app, name="download")
    #   app.add_typer(config_app, name="config")
    # See: src/rheo/cli/commands/__init__.py for details
    app.command()(download)

    return app
