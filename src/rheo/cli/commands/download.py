"""Download command implementation."""

import asyncio
from pathlib import Path

import typer
from pydantic import HttpUrl, ValidationError

from ...domain.downloads import DownloadStatus
from ...domain.file_config import FileConfig
from ...domain.hash_validation import HashConfig
from ...downloads import DownloadManager
from ...tracking.base import BaseTracker
from ..output.progress import (
    on_completed,
    on_failed,
    on_progress,
    on_skipped,
    on_started,
    on_validating,
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
    filename: str | None,
    hash_config: HashConfig | None,
    manager: DownloadManager,
    tracker: BaseTracker,
) -> None:
    """Core download logic.

    Args:
        url: Pre-validated HTTP URL
        filename: Optional custom filename
        hash_config: Optional hash validation config
        manager: DownloadManager instance (already entered context)
        tracker: BaseTracker instance for state queries

    Raises:
        typer.Exit: On download failure
    """
    # Wire CLI handlers (subscriptions cleaned up in finally)
    subscriptions = [
        manager.on("download.started", on_started),
        manager.on("download.progress", on_progress),
        manager.on("download.completed", on_completed),
        manager.on("download.failed", on_failed),
        manager.on("download.validating", on_validating),
        manager.on("download.skipped", on_skipped),
    ]

    try:
        # Create and queue download
        file_config = FileConfig(url=url, filename=filename, hash_config=hash_config)
        await manager.add([file_config])
        await manager.queue.join()

        # Query final state to determine exit code
        info = tracker.get_download_info(file_config.id)
        if info and info.status == DownloadStatus.FAILED:
            raise typer.Exit(code=1)
    finally:
        for sub in subscriptions:
            sub.unsubscribe()


def download(
    ctx: typer.Context,
    url: str = typer.Argument(..., help="URL to download"),
    output: Path | None = typer.Option(None, "-o", "--output", help="Output directory"),
    filename: str | None = typer.Option(None, "--filename", help="Custom filename"),
    hash_str: str | None = typer.Option(
        None, "--hash", help="Hash for validation (format: algorithm:hash)"
    ),
) -> None:
    """Download a file from a URL.

    Examples:
        rheo download https://example.com/file.zip
        rheo download https://example.com/file.zip -o /path/to/dir
        rheo download https://example.com/file.zip --filename custom.zip
        rheo download https://example.com/file.zip --hash sha256:abc123...
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
