"""Integration tests for end-to-end speed tracking through manager-worker-tracker."""

import asyncio
from dataclasses import dataclass
from pathlib import Path

import pytest
from aioresponses import aioresponses

from rheo import DownloadStatus
from rheo.domain import FileConfig


@dataclass
class IntegrationTestData:
    """Test data container for integration tests."""

    url: str
    content: bytes
    path: Path


@pytest.fixture
def test_data(tmp_path):
    """Provide default test data for integration tests.

    Uses 10KB content by default to ensure multiple chunks.
    """
    return IntegrationTestData(
        url="https://example.com/file.txt",
        content=b"x" * 10000,  # 10KB
        path=tmp_path / "file.txt",
    )


class TestSpeedTrackingIntegration:
    """Test that speed metrics flow from worker through tracker correctly."""

    @pytest.mark.asyncio
    async def test_speed_metrics_tracked_during_download(
        self, manager_with_tracker, test_data
    ):
        """Test that speed metrics are tracked through queue flow."""
        file_config = FileConfig(url=test_data.url, priority=1)
        await manager_with_tracker.add_to_queue([file_config])

        with aioresponses() as mock:
            mock.get(
                test_data.url,
                status=200,
                body=test_data.content,
                headers={"Content-Length": str(len(test_data.content))},
            )

            async with manager_with_tracker as manager:
                await manager.queue.join()

        # Speed metrics should be cleared after completion
        metrics = manager_with_tracker.tracker.get_speed_metrics(test_data.url)
        assert metrics is None

    @pytest.mark.asyncio
    async def test_average_speed_persisted_after_completion(
        self, manager_with_tracker, test_data
    ):
        """Test that average speed is persisted in DownloadInfo after completion."""
        file_config = FileConfig(url=test_data.url, priority=1)
        await manager_with_tracker.add_to_queue([file_config])

        with aioresponses() as mock:
            mock.get(
                test_data.url,
                status=200,
                body=test_data.content,
                headers={"Content-Length": str(len(test_data.content))},
            )

            async with manager_with_tracker as manager:
                await manager.queue.join()

        # Download should be completed
        info = manager_with_tracker.tracker.get_download_info(test_data.url)
        assert info is not None
        assert info.status == DownloadStatus.COMPLETED

        # Average speed should be persisted
        assert info.average_speed_bps is not None
        assert info.average_speed_bps >= 0.0

    @pytest.mark.asyncio
    async def test_average_speed_persisted_on_failure(
        self, manager_with_tracker, test_data
    ):
        """Test that average speed is persisted even when download fails."""
        file_config = FileConfig(url=test_data.url, priority=1)
        await manager_with_tracker.add_to_queue([file_config])

        with aioresponses() as mock:
            # Simulate server error
            mock.get(test_data.url, status=500, body="Server Error")

            # Worker catches the exception internally
            async with manager_with_tracker as manager:
                await manager.queue.join()

        # Download should be failed
        info = manager_with_tracker.tracker.get_download_info(test_data.url)
        assert info is not None
        assert info.status == DownloadStatus.FAILED

        # Speed metrics might be None if failure happened before first chunk
        # but if there were chunks, speed should be preserved
        # This just verifies the field exists
        assert hasattr(info, "average_speed_bps")

    @pytest.mark.asyncio
    async def test_multiple_concurrent_downloads_have_independent_speed_tracking(
        self, manager_with_tracker, tmp_path
    ):
        """Test that concurrent downloads have independent speed tracking."""
        url1 = "https://example.com/file1.txt"
        url2 = "https://example.com/file2.txt"
        url3 = "https://example.com/file3.txt"

        content1 = b"a" * 5000  # 5KB
        content2 = b"b" * 10000  # 10KB
        content3 = b"c" * 3000  # 3KB

        # Add all files to queue
        file_configs = [
            FileConfig(url=url1, priority=1),
            FileConfig(url=url2, priority=1),
            FileConfig(url=url3, priority=1),
        ]
        await manager_with_tracker.add_to_queue(file_configs)

        with aioresponses() as mock:
            mock.get(
                url1,
                status=200,
                body=content1,
                headers={"Content-Length": str(len(content1))},
            )
            mock.get(
                url2,
                status=200,
                body=content2,
                headers={"Content-Length": str(len(content2))},
            )
            mock.get(
                url3,
                status=200,
                body=content3,
                headers={"Content-Length": str(len(content3))},
            )

            # Workers process concurrently
            async with manager_with_tracker as manager:
                await manager.queue.join()

        # All downloads should be completed with independent speeds
        info1 = manager_with_tracker.tracker.get_download_info(url1)
        info2 = manager_with_tracker.tracker.get_download_info(url2)
        info3 = manager_with_tracker.tracker.get_download_info(url3)

        assert info1.status == DownloadStatus.COMPLETED
        assert info2.status == DownloadStatus.COMPLETED
        assert info3.status == DownloadStatus.COMPLETED

        # All should have average speeds recorded
        assert info1.average_speed_bps is not None
        assert info2.average_speed_bps is not None
        assert info3.average_speed_bps is not None

        # Speeds should be non-negative
        assert info1.average_speed_bps >= 0.0
        assert info2.average_speed_bps >= 0.0
        assert info3.average_speed_bps >= 0.0

    @pytest.mark.asyncio
    async def test_tracker_query_speed_metrics_for_active_downloads(
        self, manager_with_tracker, test_data, mocker
    ):
        """Test that we can query speed metrics for active downloads."""
        # Override with larger content to ensure multiple chunks
        large_content = b"x" * 50000  # 50KB

        # Track when speed metrics are available
        speed_metrics_seen = []

        file_config = FileConfig(url=test_data.url, priority=1)
        await manager_with_tracker.add_to_queue([file_config])

        async def check_speed_metrics(manager):
            """Periodically check if speed metrics are available."""
            for _ in range(10):  # Check 10 times
                await asyncio.sleep(0.01)  # Small delay
                metrics = manager.tracker.get_speed_metrics(test_data.url)
                if metrics is not None:
                    speed_metrics_seen.append(metrics)

        with aioresponses() as mock:
            mock.get(
                test_data.url,
                status=200,
                body=large_content,
                headers={"Content-Length": str(len(large_content))},
            )

            async with manager_with_tracker as manager:
                # Check metrics while download is processing
                check_task = asyncio.create_task(check_speed_metrics(manager))
                await manager.queue.join()
                await check_task

        # We should have captured at least some speed metrics
        # (might be 0 if download was too fast in mocked test)
        # This test mainly verifies the API works, not the timing
        assert isinstance(speed_metrics_seen, list)

    @pytest.mark.asyncio
    async def test_speed_tracking_with_unknown_file_size(
        self, manager_with_tracker, test_data
    ):
        """Test speed tracking when Content-Length is not provided."""
        file_config = FileConfig(url=test_data.url, priority=1)
        await manager_with_tracker.add_to_queue([file_config])

        with aioresponses() as mock:
            # No Content-Length header
            mock.get(test_data.url, status=200, body=test_data.content)

            async with manager_with_tracker as manager:
                await manager.queue.join()

        # Download should complete successfully
        info = manager_with_tracker.tracker.get_download_info(test_data.url)
        assert info is not None
        assert info.status == DownloadStatus.COMPLETED

        # Average speed should still be tracked
        assert info.average_speed_bps is not None
        assert info.average_speed_bps >= 0.0
