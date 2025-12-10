#!/usr/bin/env python3
"""
05_event_logging.py - Event lifecycle debugger

Demonstrates:
- Wildcard subscription with manager.on("*", handler)
- Full download lifecycle: queued -> started -> progress -> completed
- Event model structure and fields

Note: Requires internet connection to run
"""


import asyncio
from datetime import datetime
from pathlib import Path

from rheo import DownloadManager
from rheo.domain import FileConfig, FileExistsStrategy
from rheo.events import DownloadEvent


def on_any_event(event: DownloadEvent) -> None:
    """Log any download event with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    event_type = event.event_type

    detail = ""
    if event_type == "download.queued":
        detail = f"priority={event.priority}"
    elif event_type == "download.started":
        size = f"{event.total_bytes:,}" if event.total_bytes else "unknown"
        detail = f"size={size} bytes"
    elif event_type == "download.progress":
        pct = f"{event.progress_percent:.1f}%" if event.progress_percent else "?"
        detail = f"{event.bytes_downloaded:,} bytes ({pct})"
    elif event_type == "download.completed":
        detail = f"{event.total_bytes:,} bytes in {event.elapsed_seconds:.2f}s"
    elif event_type == "download.failed":
        detail = f"error={event.error.exc_type}"
    elif event_type == "download.skipped":
        detail = f"reason={event.reason}"

    short_id = event.download_id[:8] + "..."
    print(f"[{ts}] {event_type:<20} | {short_id} | {detail}")


async def main() -> None:
    """Download files while logging all events."""
    print("Starting event logging example...")
    print("This shows the full download lifecycle via events\n")
    print("-" * 70)

    files = [
        FileConfig(
            url="https://proof.ovh.net/files/1Mb.dat",
            filename="05-event-1Mb.dat",
            destination_subdir="example_05",
            priority=2,
        ),
        FileConfig(
            url="https://proof.ovh.net/files/1Mb.dat",
            filename="05-event-1Mb-copy.dat",
            destination_subdir="example_05",
            priority=1,
        ),
    ]

    async with DownloadManager(
        download_dir=Path("./downloads"),
        max_concurrent=1,
        file_exists_strategy=FileExistsStrategy.OVERWRITE,
    ) as manager:
        manager.on("*", on_any_event)

        await manager.add(files)
        await manager.wait_until_complete()

    print("-" * 70)
    print(
        "\nDone! Each download follows: queued -> started -> progress... -> completed"
    )


if __name__ == "__main__":
    asyncio.run(main())
