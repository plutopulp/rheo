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

    files = [
        FileConfig(
            url="https://proof.ovh.net/files/1Mb.dat",
            filename="01-basic-1Mb.dat",
        )
    ]

    # Note: Duplicate downloads (same URL+destination) are automatically prevented.
    # If you add the same file twice, only one download will be queued.
    async with DownloadManager(download_dir=Path("./downloads")) as manager:
        await manager.add(files)
        await manager.wait_until_complete()

    print("Download complete. Files saved to ./downloads/")


if __name__ == "__main__":
    asyncio.run(main())
