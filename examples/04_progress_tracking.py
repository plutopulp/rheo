#!/usr/bin/env python3
"""
04_progress_tracking.py - Real-time download monitoring

Demonstrates:
- Subscribing to tracker events for progress updates
- Real-time progress display with percentage, speed, and ETA
- Accessing speed metrics during downloads
- Getting overall download statistics
- Human-readable formatting for bytes, speeds, and time
"""

import asyncio
from pathlib import Path

from rheo import DownloadManager
from rheo.domain import FileConfig
from rheo.events import DownloadCompletedEvent, DownloadProgressEvent


def format_bytes(bytes_value: int) -> str:
    """Convert bytes to human-readable format (KB, MB, GB).

    Args:
        bytes_value: Number of bytes to format

    Returns:
        Formatted string like "1.5 MB" or "500 KB"
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_value < 1024:
            # Use integer for bytes, float for others
            if unit == "B":
                return f"{bytes_value} {unit}"
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024
    return f"{bytes_value:.1f} PB"


def format_speed(bytes_per_sec: float) -> str:
    """Convert bytes/sec to human-readable speed (KB/s, MB/s).

    Args:
        bytes_per_sec: Speed in bytes per second

    Returns:
        Formatted string like "2.4 MB/s" or "500 KB/s"
    """
    for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
        if bytes_per_sec < 1024:
            if unit == "B/s":
                return f"{bytes_per_sec:.0f} {unit}"
            return f"{bytes_per_sec:.1f} {unit}"
        bytes_per_sec /= 1024
    return f"{bytes_per_sec:.1f} TB/s"


def format_eta(seconds: float | None) -> str:
    """Format ETA as human-readable time.

    Args:
        seconds: Time in seconds, or None if unknown

    Returns:
        Formatted string like "3m 45s" or "12s" or "unknown"
    """
    if seconds is None:
        return "unknown"

    if seconds < 1:
        return "<1s"
    elif seconds < 60:
        return f"{int(seconds)}s"
    else:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"


async def main() -> None:
    """Download a large file with real-time progress tracking."""
    print("Real-time Progress Tracking\n")

    # Define file to download
    files = [
        FileConfig(
            url="https://proof.ovh.net/files/100Mb.dat",
            filename="04-progress-100Mb.dat",
            destination_subdir="example_04",
            description="100MB file",
        ),
    ]

    async with DownloadManager(
        max_concurrent=3,
        download_dir=Path("./downloads"),
    ) as manager:

        # Event handlers defined inside the context to access manager via closure.
        # If defining handlers outside, pass manager as a parameter to your callback.

        # Progress handler - called for each progress update
        def on_progress(event: DownloadProgressEvent) -> None:
            """Show real-time progress with speed and ETA."""
            # Get speed metrics from tracker
            speed_metrics = manager.tracker.get_speed_metrics(event.download_id)

            # Format progress
            filename = event.url.split("/")[-1]
            progress_pct = event.progress_percent
            downloaded = format_bytes(event.bytes_downloaded)
            total = format_bytes(event.total_bytes) if event.total_bytes else "?"

            # Format speed and ETA
            speed = (
                format_speed(speed_metrics.average_speed_bps) if speed_metrics else "?"
            )
            eta = format_eta(speed_metrics.eta_seconds) if speed_metrics else "?"

            print(
                f"\t{filename:15s} {progress_pct:5.1f}% | "
                f"{downloaded:>10s}/{total:<10s} | "
                f"{speed:>10s} | ETA: {eta:>6s}",
                flush=True,
            )

        # Completion handler
        def on_completed(event: DownloadCompletedEvent) -> None:
            """Print completion message."""
            filename = event.url.split("/")[-1]
            size = format_bytes(event.total_bytes)
            print(f"{filename} completed ({size})")

        # Subscribe to events
        manager.tracker.on("tracker.progress", on_progress)
        manager.tracker.on("tracker.completed", on_completed)

        print("Downloading 100MB file with real-time progress...\n")
        print(
            f"\t{'File':<15s} {'Progress':>6s} | {'Downloaded/Total':^23s} | "
            f"{'Speed':>10s} | {'ETA':>10s}"
        )

        # Add all downloads
        await manager.add(files)

        # Wait for completion
        await manager.wait_until_complete()

        # Show final statistics
        stats = manager.tracker.get_stats()
        print("\nFinal Statistics:")
        print(f"\tTotal downloads: {stats.total}")
        print(f"\tCompleted: {stats.completed}")
        print(f"\tFailed: {stats.failed}")
        print(f"\tTotal data: {format_bytes(stats.completed_bytes)}")

        print("\nDownload completed")
        print(f"\tFile saved to: {manager.download_dir.absolute()}")


if __name__ == "__main__":
    asyncio.run(main())
