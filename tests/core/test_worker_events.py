"""Tests for DownloadWorker event emission."""

import aiohttp
import pytest
from aioresponses import aioresponses

from async_download_manager.core.events import (
    WorkerCompletedEvent,
    WorkerFailedEvent,
    WorkerProgressEvent,
    WorkerStartedEvent,
)
from async_download_manager.core.worker import DownloadWorker


class TestWorkerEventEmission:
    """Test that worker emits events during download lifecycle."""

    @pytest.mark.asyncio
    async def test_worker_has_emitter_attribute(self, test_worker):
        """Test that worker has an event emitter attribute."""
        assert hasattr(test_worker, "emitter")
        assert test_worker.emitter is not None

    @pytest.mark.asyncio
    async def test_worker_emits_started_event(self, test_worker, tmp_path):
        """Test that worker emits started event when download begins."""
        events_received = []
        test_worker.emitter.on("worker.started", lambda e: events_received.append(e))

        test_url = "https://example.com/file.txt"
        dest = tmp_path / "test_file.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=b"test content")
            await test_worker.download(test_url, dest)

        assert len(events_received) == 1
        assert isinstance(events_received[0], WorkerStartedEvent)
        assert events_received[0].url == test_url

    @pytest.mark.asyncio
    async def test_worker_emits_progress_after_each_chunk(self, test_worker, tmp_path):
        """Test that worker emits progress event after each chunk."""
        events_received = []
        test_worker.emitter.on("worker.progress", lambda e: events_received.append(e))

        test_url = "https://example.com/file.txt"
        # Create content that will be split into multiple chunks
        test_content = (
            b"a" * 5000
        )  # 5KB will be multiple chunks with default chunk size
        dest = tmp_path / "test_file.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)
            await test_worker.download(test_url, dest, chunk_size=1024)

        # Should have multiple progress events (at least 5 for 5KB with 1KB chunks)
        assert len(events_received) >= 5
        assert all(isinstance(e, WorkerProgressEvent) for e in events_received)

        # Verify bytes_downloaded is cumulative and reaches total
        assert events_received[-1].bytes_downloaded == len(test_content)

    @pytest.mark.asyncio
    async def test_worker_emits_progress_with_chunk_size(self, test_worker, tmp_path):
        """Test that progress events include chunk size."""
        events_received = []
        test_worker.emitter.on("worker.progress", lambda e: events_received.append(e))

        test_url = "https://example.com/file.txt"
        dest = tmp_path / "test_file.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=b"test_chunk_data")
            await test_worker.download(test_url, dest)

        # All chunks should have chunk_size > 0
        assert all(e.chunk_size > 0 for e in events_received)

    @pytest.mark.asyncio
    async def test_worker_emits_completed_event_on_success(self, test_worker, tmp_path):
        """Test that worker emits completed event on successful download."""
        events_received = []
        test_worker.emitter.on("worker.completed", lambda e: events_received.append(e))

        test_url = "https://example.com/file.txt"
        test_content = b"test_data"
        dest = tmp_path / "test_file.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)
            await test_worker.download(test_url, dest)

        assert len(events_received) == 1
        assert isinstance(events_received[0], WorkerCompletedEvent)
        assert events_received[0].url == test_url
        assert events_received[0].destination_path == str(dest)
        assert events_received[0].total_bytes == len(test_content)

    @pytest.mark.asyncio
    async def test_worker_emits_failed_event_on_error(self, test_worker, tmp_path):
        """Test that worker emits failed event when download fails."""
        events_received = []
        test_worker.emitter.on("worker.failed", lambda e: events_received.append(e))

        test_url = "https://example.com/file.txt"
        dest = tmp_path / "test_file.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=404, body="Not Found")

            with pytest.raises(aiohttp.ClientResponseError):
                await test_worker.download(test_url, dest)

        # Should have emitted failed event
        assert len(events_received) == 1
        assert isinstance(events_received[0], WorkerFailedEvent)
        assert events_received[0].url == test_url
        assert events_received[0].error_type == "ClientResponseError"

    @pytest.mark.asyncio
    async def test_worker_emits_failed_event_on_network_error(
        self, test_worker, tmp_path
    ):
        """Test that worker emits failed event on network errors."""
        events_received = []
        test_worker.emitter.on("worker.failed", lambda e: events_received.append(e))

        test_url = "https://example.com/file.txt"
        dest = tmp_path / "test_file.txt"

        with aioresponses() as mock:
            # Simulate a server error
            mock.get(test_url, status=500, body="Internal Server Error")

            with pytest.raises(aiohttp.ClientResponseError):
                await test_worker.download(test_url, dest)

        # Should have emitted failed event
        assert len(events_received) == 1
        assert isinstance(events_received[0], WorkerFailedEvent)
        assert events_received[0].error_type == "ClientResponseError"


class TestWorkerEventInjection:
    """Test that worker accepts emitter via dependency injection."""

    @pytest.mark.asyncio
    async def test_worker_accepts_emitter_in_constructor(
        self, aio_client, mock_logger, mocker
    ):
        """Test that worker can be initialized with a custom emitter."""
        mock_emitter = mocker.Mock()
        worker = DownloadWorker(aio_client, mock_logger, emitter=mock_emitter)

        assert worker.emitter is mock_emitter

    @pytest.mark.asyncio
    async def test_worker_creates_default_emitter_if_none_provided(
        self, aio_client, mock_logger
    ):
        """Test that worker creates default emitter if none provided."""
        worker = DownloadWorker(aio_client, mock_logger)

        assert hasattr(worker, "emitter")
        assert worker.emitter is not None


class TestWorkerEventPayloads:
    """Test worker event payload contents."""

    @pytest.mark.asyncio
    async def test_started_event_includes_total_bytes_if_available(
        self, test_worker, tmp_path
    ):
        """Test that started event includes content-length if available."""
        events_received = []
        test_worker.emitter.on("worker.started", lambda e: events_received.append(e))

        test_url = "https://example.com/file.txt"
        test_content = b"test content"
        dest = tmp_path / "test_file.txt"

        with aioresponses() as mock:
            mock.get(
                test_url,
                status=200,
                body=test_content,
                headers={"Content-Length": str(len(test_content))},
            )
            await test_worker.download(test_url, dest)

        # aioresponses should set content_length
        assert events_received[0].total_bytes is not None

    @pytest.mark.asyncio
    async def test_progress_event_includes_total_bytes_if_available(
        self, test_worker, tmp_path
    ):
        """Test that progress events include total_bytes if known."""
        events_received = []
        test_worker.emitter.on("worker.progress", lambda e: events_received.append(e))

        test_url = "https://example.com/file.txt"
        test_content = b"test content"
        dest = tmp_path / "test_file.txt"

        with aioresponses() as mock:
            mock.get(
                test_url,
                status=200,
                body=test_content,
                headers={"Content-Length": str(len(test_content))},
            )
            await test_worker.download(test_url, dest)

        # All progress events should have total_bytes
        assert all(e.total_bytes is not None for e in events_received)
