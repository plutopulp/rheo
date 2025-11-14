"""Tests for DownloadWorker event emission during download lifecycle."""

from dataclasses import dataclass
from pathlib import Path

import aiohttp
import pytest
from aioresponses import aioresponses

from async_download_manager.events import (
    WorkerCompletedEvent,
    WorkerFailedEvent,
    WorkerProgressEvent,
    WorkerStartedEvent,
)


@dataclass
class EventTestData:
    """Test data container for event emission tests."""

    url: str
    content: bytes
    path: Path


@pytest.fixture
def test_data(tmp_path):
    """Provide default test data for event emission tests."""
    return EventTestData(
        url="https://example.com/file.txt",
        content=b"test content",
        path=tmp_path / "test_file.txt",
    )


class TestWorkerEventEmission:
    """Test that worker emits events during download lifecycle."""

    @pytest.mark.asyncio
    async def test_worker_has_emitter_attribute(self, test_worker):
        """Test that worker has an event emitter attribute."""
        assert hasattr(test_worker, "emitter")
        assert test_worker.emitter is not None

    @pytest.mark.asyncio
    async def test_worker_emits_started_event(self, test_worker, test_data):
        """Test that worker emits started event when download begins."""
        events_received = []
        test_worker.emitter.on("worker.started", lambda e: events_received.append(e))

        with aioresponses() as mock:
            mock.get(test_data.url, status=200, body=test_data.content)
            await test_worker.download(test_data.url, test_data.path)

        assert len(events_received) == 1
        assert isinstance(events_received[0], WorkerStartedEvent)
        assert events_received[0].url == test_data.url

    @pytest.mark.asyncio
    async def test_worker_emits_progress_after_each_chunk(self, test_worker, test_data):
        """Test that worker emits progress event after each chunk."""
        events_received = []
        test_worker.emitter.on("worker.progress", lambda e: events_received.append(e))

        # Create content that will be split into multiple chunks
        content = b"a" * 5000  # 5KB will be multiple chunks with 1KB chunk size

        with aioresponses() as mock:
            mock.get(test_data.url, status=200, body=content)
            await test_worker.download(test_data.url, test_data.path, chunk_size=1024)

        # Should have multiple progress events (at least 5 for 5KB with 1KB chunks)
        assert len(events_received) >= 5
        assert all(isinstance(e, WorkerProgressEvent) for e in events_received)

        # Verify bytes_downloaded is cumulative and reaches total
        assert events_received[-1].bytes_downloaded == len(content)

    @pytest.mark.asyncio
    async def test_worker_emits_progress_with_chunk_size(self, test_worker, test_data):
        """Test that progress events include chunk size."""
        events_received = []
        test_worker.emitter.on("worker.progress", lambda e: events_received.append(e))

        with aioresponses() as mock:
            mock.get(test_data.url, status=200, body=b"test_chunk_data")
            await test_worker.download(test_data.url, test_data.path)

        # All chunks should have chunk_size > 0
        assert all(e.chunk_size > 0 for e in events_received)

    @pytest.mark.asyncio
    async def test_worker_emits_completed_event_on_success(
        self, test_worker, test_data
    ):
        """Test that worker emits completed event on successful download."""
        events_received = []
        test_worker.emitter.on("worker.completed", lambda e: events_received.append(e))

        with aioresponses() as mock:
            mock.get(test_data.url, status=200, body=test_data.content)
            await test_worker.download(test_data.url, test_data.path)

        assert len(events_received) == 1
        assert isinstance(events_received[0], WorkerCompletedEvent)
        assert events_received[0].url == test_data.url
        assert events_received[0].destination_path == str(test_data.path)
        assert events_received[0].total_bytes == len(test_data.content)

    @pytest.mark.asyncio
    async def test_worker_emits_failed_event_on_error(self, test_worker, test_data):
        """Test that worker emits failed event when download fails."""
        events_received = []
        test_worker.emitter.on("worker.failed", lambda e: events_received.append(e))

        with aioresponses() as mock:
            mock.get(test_data.url, status=404, body="Not Found")

            with pytest.raises(aiohttp.ClientResponseError):
                await test_worker.download(test_data.url, test_data.path)

        # Should have emitted failed event
        assert len(events_received) == 1
        assert isinstance(events_received[0], WorkerFailedEvent)
        assert events_received[0].url == test_data.url
        assert events_received[0].error_type == "ClientResponseError"

    @pytest.mark.asyncio
    async def test_worker_emits_failed_event_on_network_error(
        self, test_worker, test_data
    ):
        """Test that worker emits failed event on network errors."""
        events_received = []
        test_worker.emitter.on("worker.failed", lambda e: events_received.append(e))

        with aioresponses() as mock:
            # Simulate a server error
            mock.get(test_data.url, status=500, body="Internal Server Error")

            with pytest.raises(aiohttp.ClientResponseError):
                await test_worker.download(test_data.url, test_data.path)

        # Should have emitted failed event
        assert len(events_received) == 1
        assert isinstance(events_received[0], WorkerFailedEvent)
        assert events_received[0].error_type == "ClientResponseError"
