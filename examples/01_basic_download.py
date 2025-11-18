#!/usr/bin/env python3
"""
01_basic_download.py - Simplest possible download

Demonstrates: Basic DownloadManager usage with default settings
Note: Requires internet connection to run
"""
import asyncio
from pathlib import Path

from rheo import DownloadManager
from rheo.domain import FileConfig


async def main() -> None:
    """Download a single file to ./downloads directory."""
    print("Starting basic download example...")

    files = [FileConfig(url="https://httpbin.org/bytes/1024")]

    async with DownloadManager(download_dir=Path("./downloads")) as manager:
        await manager.add_to_queue(files)
        await manager.queue.join()

    print("✓ Download complete! Check ./downloads/")


if __name__ == "__main__":
    asyncio.run(main())
