#!/usr/bin/env python3
"""
04_progress_display.py - Real-time progress with speed and ETA

Demonstrates:
- Event subscription with manager.on()
- DownloadProgressEvent with SpeedMetrics
- Live progress bar with percentage, speed, and ETA

Note: Requires internet connection to run
"""

import asyncio
import sys
from pathlib import Path

from rheo import DownloadManager
from rheo.domain import FileConfig, FileExistsStrategy
from rheo.events import DownloadCompletedEvent, DownloadEventType, DownloadProgressEvent


def format_bytes(value: int) -> str:
    """Format bytes as human-readable string."""
    amount = float(value)
    for unit in ["B", "KB", "MB", "GB"]:
        if amount < 1024:
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} TB"


def format_time(seconds: float | None) -> str:
    """Format seconds as mm:ss or --:--."""
    if seconds is None:
        return "--:--"
    mins, secs = divmod(int(seconds), 60)
    return f"{mins:02d}:{secs:02d}"


def on_progress(event: DownloadProgressEvent) -> None:
    """Handle progress events - update display."""
    pct = event.progress_percent or 0.0
    downloaded = format_bytes(event.bytes_downloaded)
    total = format_bytes(event.total_bytes) if event.total_bytes else "?"

    if event.speed:
        speed = format_bytes(int(event.speed.average_speed_bps)) + "/s"
        eta = format_time(event.speed.eta_seconds)
    else:
        speed = "-- KB/s"
        eta = "--:--"

    bar_width = 30
    filled = int(bar_width * pct / 100)
    bar = "█" * filled + "░" * (bar_width - filled)

    line = f"\r  [{bar}] {pct:5.1f}% | {downloaded}/{total} | {speed} | ETA: {eta}"
    sys.stdout.write(line)
    sys.stdout.flush()


def on_completed(event: DownloadCompletedEvent) -> None:
    """Handle completion - print final stats."""
    print()
    speed = format_bytes(int(event.average_speed_bps)) + "/s"
    print(f"  Completed in {event.elapsed_seconds:.1f}s (avg: {speed})")


async def main() -> None:
    """Download a file with live progress display."""
    print("Starting progress display example...")
    print("Downloading 10MB file with real-time progress\n")

    file = FileConfig(
        url="https://proof.ovh.net/files/10Mb.dat",
        filename="04-progress-10Mb.dat",
        destination_subdir="example_04",
    )

    async with DownloadManager(
        download_dir=Path("./downloads"),
        file_exists_strategy=FileExistsStrategy.OVERWRITE,
    ) as manager:
        manager.on(DownloadEventType.PROGRESS, on_progress)
        manager.on(DownloadEventType.COMPLETED, on_completed)

        await manager.add([file])
        await manager.wait_until_complete()

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
