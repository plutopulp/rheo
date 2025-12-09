"""Progress display functions for CLI.

Provides event handlers for real-time download progress display.
Handlers are designed to be wired to manager.on() for event subscription.
"""

import sys

import typer

from ...events import (
    DownloadCompletedEvent,
    DownloadFailedEvent,
    DownloadProgressEvent,
    DownloadSkippedEvent,
    DownloadStartedEvent,
    DownloadValidatingEvent,
)

# Formatting Utils


def format_bytes(b: int | float) -> str:
    """Format bytes as human-readable string (e.g., '1.5 MB')."""
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"


def format_time(seconds: float | None) -> str:
    """Format seconds as mm:ss or --:-- if unknown."""
    if seconds is None:
        return "--:--"
    mins, secs = divmod(int(seconds), 60)
    return f"{mins:02d}:{secs:02d}"


def build_progress_bar(percent: float, width: int = 30) -> str:
    """Build a text progress bar.

    Args:
        percent: Progress percentage (0-100)
        width: Bar width in characters

    Returns:
        Progress bar string like "[████████░░░░░░░░░░░░░░░░░░░░░░]"
    """
    filled = int(width * percent / 100)
    return "█" * filled + "░" * (width - filled)


# Event Handlers


def on_started(event: DownloadStartedEvent) -> None:
    """Handle download.started - show initial message."""
    size_str = format_bytes(event.total_bytes) if event.total_bytes else "unknown size"
    typer.echo(f"Downloading: {event.url} ({size_str})")


def on_progress(event: DownloadProgressEvent) -> None:
    """Handle download.progress - update progress bar inline."""
    pct = event.progress_percent or 0
    downloaded = format_bytes(event.bytes_downloaded)
    total = format_bytes(event.total_bytes) if event.total_bytes else "?"

    # Speed and ETA from embedded metrics
    if event.speed:
        speed = format_bytes(event.speed.average_speed_bps) + "/s"
        eta = format_time(event.speed.eta_seconds)
    else:
        speed = "-- KB/s"
        eta = "--:--"

    # Build progress line
    bar = build_progress_bar(pct)
    line = (
        f"\r\033[K  [{bar}] {pct:5.1f}% | {downloaded}/{total} | {speed} | ETA: {eta}"
    )

    # Overwrite current line
    sys.stdout.write(line)
    sys.stdout.flush()


def on_completed(event: DownloadCompletedEvent) -> None:
    """Handle download.completed - show success with stats."""
    # Newline after progress bar
    typer.echo()

    # Show validation result if present
    if event.validation:
        if event.validation.is_valid:
            typer.secho("  ✓ Hash validation passed", fg=typer.colors.GREEN)
        else:
            # Shouldn't happen (validation failure → download.failed), but handle it
            typer.secho("  ✗ Hash validation failed", fg=typer.colors.RED)

    # Final success message
    speed = format_bytes(event.average_speed_bps) + "/s"
    typer.secho(
        f"✓ Downloaded in {event.elapsed_seconds:.1f}s (avg: {speed})",
        fg=typer.colors.GREEN,
    )
    typer.echo(f"  → {event.destination_path}")


def on_failed(event: DownloadFailedEvent) -> None:
    """Handle download.failed - show error details."""
    # Newline after progress bar (if any)
    typer.echo()

    # Show validation failure details if present
    if event.validation and not event.validation.is_valid:
        typer.secho("✗ Hash validation failed", fg=typer.colors.RED)
        typer.secho(
            f"  Expected:   {event.validation.expected_hash}", fg=typer.colors.RED
        )
        typer.secho(
            f"  Calculated: {event.validation.calculated_hash}", fg=typer.colors.RED
        )
    else:
        typer.secho(f"✗ Download failed: {event.error.message}", fg=typer.colors.RED)


def on_validating(event: DownloadValidatingEvent) -> None:
    """Handle download.validating - show validation started."""
    # Newline after progress bar
    typer.echo()
    typer.echo(f"  Validating with {event.algorithm.value}...")


def on_skipped(event: DownloadSkippedEvent) -> None:
    """Handle download.skipped - show skip reason."""
    typer.secho(f"⊘ Skipped: {event.reason}", fg=typer.colors.YELLOW)
    if event.destination_path:
        typer.echo(f"  → {event.destination_path}")
