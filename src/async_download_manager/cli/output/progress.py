"""Progress display functions for CLI."""

import typer

from ...domain.downloads import DownloadInfo
from ...domain.hash_validation import ValidationStatus


def display_download_start(url: str) -> None:
    """Display download started message."""
    typer.echo(f"Downloading: {url}")


def display_download_complete(info: DownloadInfo) -> None:
    """Display completion message."""
    typer.secho(f"✓ Downloaded: {info.url}", fg=typer.colors.GREEN)


def display_download_error(url: str, error: Exception) -> None:
    """Display error message."""
    typer.secho(f"✗ Failed: {url}", fg=typer.colors.RED)
    typer.secho(f"  Error: {error}", fg=typer.colors.RED)


def display_validation_result(info: DownloadInfo) -> None:
    """Display hash validation result."""
    if not info.validation:
        return

    if info.validation.status == ValidationStatus.SUCCEEDED:
        typer.secho("✓ Hash validation passed", fg=typer.colors.GREEN)
    elif info.validation.status == ValidationStatus.FAILED:
        typer.secho("✗ Hash validation failed", fg=typer.colors.RED)
        if info.validation.error:
            typer.secho(f"  {info.validation.error}", fg=typer.colors.RED)
