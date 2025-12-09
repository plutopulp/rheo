#!/usr/bin/env python3
"""
06_batch_summary.py - Batch download with summary report

Demonstrates:
- Downloading multiple files in batch
- Using manager.stats for aggregate statistics
- Using manager.get_download_info() for per-file details
- Building a summary report after completion

Note: Requires internet connection to run
"""


import asyncio
from pathlib import Path

from rheo import DownloadManager, DownloadStatus
from rheo.domain import FileConfig, FileExistsStrategy, HashConfig


def format_bytes(value: int) -> str:
    """Format bytes as human-readable string."""
    amount = float(value)
    for unit in ["B", "KB", "MB"]:
        if amount < 1024:
            return f"{amount:.1f} {unit}"
        amount /= 1024
    return f"{amount:.1f} GB"


async def main() -> None:
    """Download batch of files and print summary."""
    print("Starting batch summary example...")
    print("Downloading 4 files (mix of success and failure)\n")

    files = [
        FileConfig(
            url="https://proof.ovh.net/files/1Mb.dat",
            filename="06-batch-1.dat",
            destination_subdir="example_06",
            description="File 1 (1MB)",
        ),
        FileConfig(
            url="https://proof.ovh.net/files/1Mb.dat",
            filename="06-batch-2.dat",
            destination_subdir="example_06",
            description="File 2 (1MB)",
        ),
        FileConfig(
            url="https://proof.ovh.net/files/1Mb.dat",
            filename="06-batch-3.dat",
            destination_subdir="example_06",
            description="File 3 (1MB)",
        ),
        FileConfig(
            url="https://proof.ovh.net/files/1Mb.dat",
            filename="06-batch-4-bad-hash.dat",
            destination_subdir="example_06",
            description="File 4 (bad hash - will fail)",
            hash_config=HashConfig(algorithm="sha256", expected_hash="0" * 64),
        ),
    ]

    async with DownloadManager(
        download_dir=Path("./downloads"),
        max_concurrent=2,
        file_exists_strategy=FileExistsStrategy.OVERWRITE,
    ) as manager:
        await manager.add(files)
        await manager.wait_until_complete()

        stats = manager.stats
        print("=" * 50)
        print("BATCH SUMMARY")
        print("=" * 50)
        print(f"Total:     {stats.total}")
        print(f"Completed: {stats.completed}")
        print(f"Failed:    {stats.failed}")
        print(f"Bytes:     {format_bytes(stats.completed_bytes)}")
        print()

        print("PER-FILE RESULTS")
        print("-" * 50)
        for file_config in files:
            info = manager.get_download_info(file_config.id)
            status_icon = "✓" if info.status == DownloadStatus.COMPLETED else "✗"
            print(f"{status_icon} {file_config.description}")
            print(f"\tStatus: {info.status.value}")
            if info.status == DownloadStatus.COMPLETED:
                speed = format_bytes(int(info.average_speed_bps or 0)) + "/s"
                print(f"\tSize: {format_bytes(info.bytes_downloaded)} @ {speed}")
            elif info.error:
                error_line = info.error.split("\n")[0][:50]
                print(f"\tError: {error_line}")
            print()

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
