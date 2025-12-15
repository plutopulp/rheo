"""Throughput benchmark scenarios."""

import asyncio
from pathlib import Path

from rheo.domain.file_config import FileConfig, FileExistsStrategy
from rheo.downloads import DownloadManager


def test_throughput_10_files_1mb(
    benchmark, benchmark_server: str, benchmark_download_dir: Path
) -> None:
    """Benchmark downloading 10 x 1MB files with 4 concurrent workers."""
    file_size = 1_000_000
    file_count = 10
    max_concurrent = 4

    async def download_batch() -> None:
        files = [
            FileConfig(
                url=f"{benchmark_server}/file/{file_size}",
                filename=f"file_{i}.bin",
            )
            for i in range(file_count)
        ]
        async with DownloadManager(
            max_concurrent=max_concurrent,
            download_dir=benchmark_download_dir,
            file_exists_strategy=FileExistsStrategy.OVERWRITE,
        ) as manager:
            await manager.add(files)
            await manager.wait_until_complete()

    def run_downloads() -> None:
        asyncio.run(download_batch())

    benchmark(run_downloads)
