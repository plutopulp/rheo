"""Integration tests for manager-worker-tracker event wiring."""

import aiohttp
import pytest
from aioresponses import aioresponses

from rheo import DownloadManager, DownloadStatus
from rheo.tracking import NullTracker


class TestManagerTrackerWiring:
    """Test event wiring between manager, worker, and tracker."""

    @pytest.mark.asyncio
    async def test_manager_works_without_tracker(self, aio_client, mock_logger):
        """Test that manager works when no tracker provided."""
        async with DownloadManager(client=aio_client, logger=mock_logger) as manager:
            # Tracker is now auto-created, never None
            assert manager.tracker is not None
            assert manager._worker is not None

    @pytest.mark.asyncio
    async def test_worker_started_wires_to_tracker(
        self, manager_with_tracker, tmp_path
    ):
        """Test worker.started event updates tracker.started."""
        async with manager_with_tracker as manager:
            test_url = "https://example.com/file.txt"
            dest = tmp_path / "file.txt"

            with aioresponses() as mock:
                mock.get(test_url, status=200, body=b"test")
                await manager._worker.download(test_url, dest)

            # Tracker should have recorded the download
            info = manager.tracker.get_download_info(test_url)
            assert info is not None
            assert info.status == DownloadStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_worker_progress_wires_to_tracker(
        self, manager_with_tracker, tmp_path
    ):
        """Test worker.progress events update tracker.progress."""
        async with manager_with_tracker as manager:
            test_url = "https://example.com/file.txt"
            test_content = b"x" * 5000  # 5KB
            dest = tmp_path / "file.txt"

            with aioresponses() as mock:
                mock.get(test_url, status=200, body=test_content)
                await manager._worker.download(test_url, dest, chunk_size=1024)

            info = manager.tracker.get_download_info(test_url)
            assert info.bytes_downloaded == len(test_content)

    @pytest.mark.asyncio
    async def test_worker_completed_wires_to_tracker(
        self, manager_with_tracker, tmp_path
    ):
        """Test worker.completed event updates tracker.completed."""
        async with manager_with_tracker as manager:
            test_url = "https://example.com/file.txt"
            test_content = b"test content"
            dest = tmp_path / "file.txt"

            with aioresponses() as mock:
                mock.get(test_url, status=200, body=test_content)
                await manager._worker.download(test_url, dest)

            info = manager.tracker.get_download_info(test_url)
            assert info.status == DownloadStatus.COMPLETED
            assert info.total_bytes == len(test_content)

    @pytest.mark.asyncio
    async def test_worker_failed_wires_to_tracker(self, manager_with_tracker, tmp_path):
        """Test worker.failed event updates tracker.failed."""
        async with manager_with_tracker as manager:
            test_url = "https://example.com/file.txt"
            dest = tmp_path / "file.txt"

            with aioresponses() as mock:
                mock.get(test_url, status=404, body="Not Found")

                with pytest.raises(aiohttp.ClientResponseError):
                    await manager._worker.download(test_url, dest)

            info = manager.tracker.get_download_info(test_url)
            assert info is not None
            assert info.status == DownloadStatus.FAILED
            assert "404" in info.error or "ClientResponseError" in info.error

    @pytest.mark.asyncio
    async def test_custom_event_wiring_can_override_default(
        self, aio_client, tracker, mock_logger, mocker, tmp_path
    ):
        """Test that custom event wiring mapping can be provided."""
        custom_started_handler = mocker.AsyncMock()

        custom_wiring = {
            "worker.started": custom_started_handler,
        }

        async with DownloadManager(
            client=aio_client, tracker=tracker, logger=mock_logger
        ) as manager:
            # Override wiring with custom mapping
            manager._wire_worker_events(custom_wiring)

            test_url = "https://example.com/file.txt"
            dest = tmp_path / "file.txt"

            with aioresponses() as mock:
                mock.get(test_url, status=200, body=b"test")
                await manager._worker.download(test_url, dest)

            # Custom handler should have been called
            assert custom_started_handler.called


class TestPublicTrackerProperty:
    """Test that tracker property exposes the configured tracker instance."""

    def test_tracker_property_returns_provided_tracker(self, aio_client, tracker):
        """Verify tracker property returns the explicitly provided tracker."""
        manager = DownloadManager(client=aio_client, tracker=tracker)
        assert manager.tracker is tracker

    def test_tracker_property_with_null_tracker(self, aio_client):
        """Verify tracker property works with NullTracker."""

        null_tracker = NullTracker()
        manager = DownloadManager(client=aio_client, tracker=null_tracker)
        assert manager.tracker is null_tracker
