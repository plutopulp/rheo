"""Tests for DownloadWorker event payload contents."""

from dataclasses import dataclass
from pathlib import Path

import pytest
from aioresponses import aioresponses


@dataclass
class PayloadTestData:
    """Test data container for event payload tests."""

    url: str
    content: bytes
    path: Path


@pytest.fixture
def test_data(tmp_path):
    """Provide default test data for event payload tests."""
    return PayloadTestData(
        url="https://example.com/file.txt",
        content=b"test content",
        path=tmp_path / "test_file.txt",
    )


class TestWorkerEventPayloads:
    """Test download event payload contents."""

    @pytest.mark.asyncio
    async def test_started_event_includes_total_bytes_if_available(
        self, test_worker, test_data
    ):
        """Test that started event includes content-length if available."""
        events_received = []
        test_worker.emitter.on("download.started", lambda e: events_received.append(e))

        with aioresponses() as mock:
            mock.get(
                test_data.url,
                status=200,
                body=test_data.content,
                headers={"Content-Length": str(len(test_data.content))},
            )
            await test_worker.download(
                test_data.url, test_data.path, download_id="test-id-123"
            )

        # aioresponses should set content_length
        assert events_received[0].total_bytes is not None
        assert events_received[0].download_id == "test-id-123"

    @pytest.mark.asyncio
    async def test_progress_event_includes_total_bytes_if_available(
        self, test_worker, test_data
    ):
        """Test that progress events include total_bytes if known."""
        events_received = []
        test_worker.emitter.on("download.progress", lambda e: events_received.append(e))

        with aioresponses() as mock:
            mock.get(
                test_data.url,
                status=200,
                body=test_data.content,
                headers={"Content-Length": str(len(test_data.content))},
            )
            await test_worker.download(
                test_data.url, test_data.path, download_id="test-id-456"
            )

        # All progress events should have total_bytes and download_id
        assert all(e.total_bytes is not None for e in events_received)
        assert all(e.download_id == "test-id-456" for e in events_received)
