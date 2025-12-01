"""Tests for DownloadWorker cancellation behavior."""

import asyncio
import typing as t
from pathlib import Path

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses

from rheo.downloads import DownloadWorker

if t.TYPE_CHECKING:
    from loguru import Logger


@pytest.fixture
def cancellable_worker(
    aio_client: ClientSession,
    mock_logger: "Logger",
) -> tuple[DownloadWorker, asyncio.Event]:
    """Worker configured for cancellation testing.

    Returns:
        (worker, download_started_event) - The worker has _write_chunk_to_file
        patched to set the event and add a small delay, creating a window
        for cancellation during chunk writes.
    """
    worker = DownloadWorker(client=aio_client, logger=mock_logger)
    download_started = asyncio.Event()

    original_write = worker._write_chunk_to_file

    async def write_with_signal(chunk, file_handle):
        download_started.set()
        await asyncio.sleep(0.01)
        await original_write(chunk, file_handle)

    worker._write_chunk_to_file = write_with_signal

    return worker, download_started


class TestDownloadWorkerCancellation:
    """Test cancellation cleanup behavior."""

    @pytest.mark.asyncio
    async def test_cancellation_cleans_up_partial_file(
        self,
        cancellable_worker: tuple[DownloadWorker, asyncio.Event],
        tmp_path: Path,
    ):
        """Cancelling a download should remove the partial file from disk.

        This test verifies that when a download is cancelled mid-stream,
        the partial file is cleaned up rather than left corrupted on disk.
        """
        worker, download_started = cancellable_worker
        test_url = "https://example.com/large-file.dat"
        temp_file = tmp_path / "partial.dat"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=b"x" * 10000)

            download_task = asyncio.create_task(
                worker.download(test_url, temp_file, download_id="cancel-test")
            )

            await asyncio.wait_for(download_started.wait(), timeout=2.0)
            download_task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await download_task

        # KEY ASSERTION: Partial file should be cleaned up
        assert (
            not temp_file.exists()
        ), "Partial file should be removed after cancellation"

    @pytest.mark.asyncio
    async def test_cancellation_reraises_cancelled_error(
        self,
        cancellable_worker: tuple[DownloadWorker, asyncio.Event],
        tmp_path: Path,
    ):
        """CancelledError should be re-raised after cleanup.

        This ensures proper cancellation propagation through the task hierarchy.
        """
        worker, download_started = cancellable_worker
        test_url = "https://example.com/file.dat"
        temp_file = tmp_path / "test.dat"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=b"x" * 1000)

            download_task = asyncio.create_task(
                worker.download(test_url, temp_file, download_id="cancel-test")
            )

            await asyncio.wait_for(download_started.wait(), timeout=2.0)
            download_task.cancel()

            # Should raise CancelledError, not swallow it
            with pytest.raises(asyncio.CancelledError):
                await download_task
