#!/usr/bin/env python3
"""
02_multiple_with_priority.py - Multiple downloads with priority queue

Demonstrates: Priority-based concurrent downloads
Note: Requires internet connection to run
"""
import asyncio
from pathlib import Path

from rheo import DownloadManager
from rheo.domain import FileConfig


async def main() -> None:
    """Download multiple files with different priorities."""
    print("Starting priority download example...")
    print("Downloading 5 files with different priorities (3=high, 2=medium, 1=low)\n")

    # Create files with different priorities
    # Higher priority numbers download first
    files = [
        FileConfig(
            url="https://proof.ovh.net/files/100Mb.dat",
            priority=1,
            description="Low priority - 100MB file",
        ),
        FileConfig(
            url="https://proof.ovh.net/files/1Mb.dat",
            priority=3,
            description="High priority - 1MB file",
        ),
        FileConfig(
            url="https://proof.ovh.net/files/10Mb.dat",
            priority=2,
            description="Medium priority - 10MB file",
        ),
        FileConfig(
            url="https://proof.ovh.net/files/100Mb.dat",
            priority=1,
            description="Low priority - 100MB file (second)",
        ),
        FileConfig(
            url="https://proof.ovh.net/files/1Mb.dat",
            priority=1,
            description="Low priority - 1MB file (waits despite being small)",
        ),
    ]

    # Print queue order
    print("Files queued in this order:")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f.description} (priority: {f.priority})")

    print("\nExpected download order (by priority):")
    sorted_files = sorted(files, key=lambda f: f.priority, reverse=True)
    for i, f in enumerate(sorted_files, 1):
        print(f"  {i}. {f.description}")

    max_workers = 3
    print(f"\nStarting downloads with {max_workers} concurrent workers...\n")

    async with DownloadManager(
        download_dir=Path("./downloads"),
        max_workers=max_workers,
    ) as manager:
        await manager.add_to_queue(files)
        await manager.queue.join()

    print("\nAll downloads complete. Files saved to ./downloads/")


if __name__ == "__main__":
    asyncio.run(main())
