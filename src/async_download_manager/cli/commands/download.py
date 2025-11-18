"""Download command implementation."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from pydantic import HttpUrl, ValidationError

from ...domain.downloads import DownloadStatus
from ...domain.file_config import FileConfig
from ...domain.hash_validation import HashConfig
from ...downloads import DownloadManager
from ...tracking.base import BaseTracker
from ..output.progress import (
    display_download_complete,
    display_download_error,
    display_download_start,
    display_validation_result,
)
from ..state import CLIState


def validate_url(url_str: str) -> HttpUrl:
    """Validate and convert a URL string to HttpUrl.

    Args:
        url_str: URL string to validate

    Returns:
        Validated HttpUrl object

    Raises:
        typer.Exit: If URL is invalid
    """
    try:
        return HttpUrl(url_str)
    except ValidationError as e:
        typer.secho(f"✗ Invalid URL: {url_str}", fg=typer.colors.RED)
        typer.secho(f"  {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


def validate_hash(hash_str: str) -> HashConfig:
    """Validate and parse hash string.

    Args:
        hash_str: Hash string in format 'algorithm:hash'

    Returns:
        Validated HashConfig object

    Raises:
        typer.Exit: If hash format is invalid or algorithm is unsupported
    """
    try:
        return HashConfig.from_checksum_string(hash_str)
    except ValueError as e:
        typer.secho(f"✗ Invalid hash: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)


async def download_file(
    url: HttpUrl,
    filename: Optional[str],
    hash_config: Optional[HashConfig],
    manager: DownloadManager,
    tracker: BaseTracker,
) -> None:
    """Core download logic with injected dependencies.

    Args:
        url: Pre-validated HTTP URL
        filename: Optional custom filename
        hash_config: Optional hash validation config
        manager: DownloadManager instance (already entered context)
        tracker: DownloadTracker instance

    Raises:
        typer.Exit: On download failure or validation error
    """
    display_download_start(str(url))

    # Create and queue download
    file_config = FileConfig(url=url, filename=filename, hash_config=hash_config)
    await manager.add_to_queue([file_config])
    await manager.queue.join()

    # Get download info - guard clause for missing info
    info = tracker.get_download_info(str(url))
    if not info:
        typer.secho("Warning: No download info available", fg=typer.colors.YELLOW)
        return

    # Guard clause - handle failure first
    if info.status == DownloadStatus.FAILED:
        error = Exception(info.error or "Unknown error")
        display_download_error(str(url), error)
        raise typer.Exit(code=1)

    # Guard clause - handle unexpected status
    if info.status != DownloadStatus.COMPLETED:
        typer.secho(
            f"Warning: Unexpected status: {info.status}", fg=typer.colors.YELLOW
        )
        return

    # Flat success path - no nesting
    display_download_complete(info)

    # Optional validation display
    if info.validation:
        display_validation_result(info)


def download(
    ctx: typer.Context,
    url: str = typer.Argument(..., help="URL to download"),
    output: Optional[Path] = typer.Option(
        None, "-o", "--output", help="Output directory"
    ),
    filename: Optional[str] = typer.Option(None, "--filename", help="Custom filename"),
    hash_str: Optional[str] = typer.Option(
        None, "--hash", help="Hash for validation (format: algorithm:hash)"
    ),
) -> None:
    """Download a file from a URL.

    Examples:
        adm download https://example.com/file.zip
        adm download https://example.com/file.zip -o /path/to/dir
        adm download https://example.com/file.zip --filename custom.zip
        adm download https://example.com/file.zip --hash sha256:abc123...
    """
    state: CLIState = ctx.obj

    # Validate inputs early at CLI boundary
    validated_url = validate_url(url)
    hash_config = validate_hash(hash_str) if hash_str else None

    # Determine output directory (manager will ensure it exists)
    output_dir = output if output else state.settings.download_dir

    # Create dependencies using factories
    tracker = state.create_tracker()

    # Run async download with proper error handling
    async def run() -> None:
        async with state.create_manager(
            download_dir=output_dir, tracker=tracker
        ) as manager:
            await download_file(validated_url, filename, hash_config, manager, tracker)

    try:
        asyncio.run(run())
    except typer.Exit:
        # Re-raise typer.Exit to preserve exit codes
        raise
    except Exception as e:
        typer.secho(f"Download failed: {e}", fg=typer.colors.RED)
        raise typer.Exit(code=1)
