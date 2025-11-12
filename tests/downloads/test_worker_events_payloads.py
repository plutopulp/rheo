"""Tests for DownloadWorker event payload contents."""

import pytest
from aioresponses import aioresponses


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
