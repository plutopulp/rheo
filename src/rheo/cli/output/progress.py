"""Progress display functions for CLI.

Note: These functions are currently unused while event subscription
is being redesigned. They will be restored when the manager exposes
an event subscription interface.
"""

import typer

from ...events import (
    DownloadCompletedEvent,
    DownloadFailedEvent,
    DownloadStartedEvent,
    WorkerValidationCompletedEvent,
    WorkerValidationFailedEvent,
)


def display_download_started(event: DownloadStartedEvent) -> None:
    """Display download started message from event.

    Args:
        event: Download started event
    """
    typer.echo(f"Downloading: {event.url}")


def display_download_completed(event: DownloadCompletedEvent) -> None:
    """Display completion message from event.

    Args:
        event: Download completed event
    """
    typer.secho(f"✓ Downloaded: {event.url}", fg=typer.colors.GREEN)


def display_download_failed(event: DownloadFailedEvent) -> None:
    """Display error message from event.

    Args:
        event: Download failed event
    """
    typer.secho(f"✗ Failed: {event.url}", fg=typer.colors.RED)
    typer.secho(f"  Error: {event.error.message}", fg=typer.colors.RED)


def display_validation_completed(event: WorkerValidationCompletedEvent) -> None:
    """Display successful validation from event.

    Args:
        event: Validation completed event
    """
    typer.secho("✓ Hash validation passed", fg=typer.colors.GREEN)


def display_validation_failed(event: WorkerValidationFailedEvent) -> None:
    """Display failed validation from event.

    Args:
        event: Validation failed event
    """
    typer.secho("✗ Hash validation failed", fg=typer.colors.RED)
    if event.error_message:
        typer.secho(f"  {event.error_message}", fg=typer.colors.RED)
