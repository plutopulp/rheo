"""Integration tests for manager-worker-tracker event wiring."""

import pytest
from aioresponses import aioresponses

from rheo import DownloadManager, DownloadStatus
from rheo.domain import FileConfig
from rheo.tracking import NullTracker


class TestManagerTrackerWiring:
    """Test event wiring between manager, worker, and tracker."""

    @pytest.mark.asyncio
    async def test_manager_works_without_tracker(self, aio_client, mock_logger):
        """Test that manager works when no tracker provided."""
        async with DownloadManager(client=aio_client, logger=mock_logger) as manager:
            # Tracker is now auto-created, never None
            assert manager.tracker is not None

    @pytest.mark.asyncio
    async def test_worker_started_wires_to_tracker(
        self, manager_with_tracker, tmp_path
    ):
        """Test worker.started event updates tracker through queue flow."""
        test_url = "https://example.com/file.txt"

        # Create file config and add to queue
        file_config = FileConfig(url=test_url, priority=1)
        await manager_with_tracker.add([file_config])

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=b"test")

            # Use context manager to start workers and process queue
            async with manager_with_tracker as manager:
                # Wait for queue to be processed
                await manager.queue.join()

        # Tracker should have recorded the download
        info = manager_with_tracker.tracker.get_download_info(file_config.id)
        assert info is not None
        assert info.status == DownloadStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_worker_progress_wires_to_tracker(
        self, manager_with_tracker, tmp_path
    ):
        """Test worker.progress events update tracker through queue flow."""
        test_url = "https://example.com/file.txt"
        test_content = b"x" * 5000  # 5KB

        # Create file config
        file_config = FileConfig(url=test_url, priority=1)
        await manager_with_tracker.add([file_config])

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)

            async with manager_with_tracker as manager:
                await manager.queue.join()

        info = manager_with_tracker.tracker.get_download_info(file_config.id)
        assert info.bytes_downloaded == len(test_content)

    @pytest.mark.asyncio
    async def test_worker_completed_wires_to_tracker(
        self, manager_with_tracker, tmp_path
    ):
        """Test worker.completed event updates tracker through queue flow."""
        test_url = "https://example.com/file.txt"
        test_content = b"test content"

        file_config = FileConfig(url=test_url, priority=1)
        await manager_with_tracker.add([file_config])

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)

            async with manager_with_tracker as manager:
                await manager.queue.join()

        info = manager_with_tracker.tracker.get_download_info(file_config.id)
        assert info.status == DownloadStatus.COMPLETED
        assert info.total_bytes == len(test_content)

    @pytest.mark.asyncio
    async def test_worker_failed_wires_to_tracker(self, manager_with_tracker, tmp_path):
        """Test worker.failed event updates tracker through queue flow."""
        test_url = "https://example.com/file.txt"

        file_config = FileConfig(url=test_url, priority=1)
        await manager_with_tracker.add([file_config])

        with aioresponses() as mock:
            mock.get(test_url, status=404, body="Not Found")

            # Worker will catch the exception and record it
            async with manager_with_tracker as manager:
                await manager.queue.join()

        info = manager_with_tracker.tracker.get_download_info(file_config.id)
        assert info is not None
        assert info.status == DownloadStatus.FAILED
        assert "404" in info.error or "ClientResponseError" in info.error

    @pytest.mark.asyncio
    async def test_manager_prevents_duplicate_downloads(
        self, manager_with_tracker: DownloadManager
    ):
        """Test that duplicate downloads (same URL+destination) are prevented end-to-end.

        Verifies that:
        1. Adding same file twice only queues it once
        2. Only one download is executed by the worker
        3. Tracker records only one download
        """
        test_url = "https://example.com/file.txt"
        test_content = b"test content"

        # Create same file config twice (same URL, same destination)
        file_config_1 = FileConfig(url=test_url, priority=1)
        file_config_2 = FileConfig(url=test_url, priority=1)

        # Both should have the same ID (same URL + destination)
        assert file_config_1.id == file_config_2.id

        # Add both to queue
        await manager_with_tracker.add([file_config_1])
        await manager_with_tracker.add([file_config_2])

        # Queue should only have one item (duplicate was skipped)
        assert manager_with_tracker.queue.size() == 1

        with aioresponses() as mock:
            # Mock HTTP - if called twice, test would fail with connection error
            mock.get(test_url, status=200, body=test_content)

            async with manager_with_tracker as manager:
                await manager.queue.join()

        assert manager_with_tracker.queue.size() == 0
        # Verify only one download was tracked
        assert len(manager_with_tracker.tracker._downloads) == 1
        info = manager_with_tracker.tracker.get_download_info(file_config_1.id)
        assert info is not None
        assert info.status == DownloadStatus.COMPLETED
        assert info.bytes_downloaded == len(test_content)
        assert info.url == test_url
        assert info.id == file_config_1.id

        # If duplicate ran, aioresponses would raise ConnectionError on second call


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
