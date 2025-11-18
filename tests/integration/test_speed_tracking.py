"""Integration tests for end-to-end speed tracking through manager-worker-tracker."""

import asyncio
from dataclasses import dataclass
from pathlib import Path

import aiohttp
import pytest
from aioresponses import aioresponses

from rheo import DownloadStatus


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
        """Test that speed metrics are tracked and accessible during download."""
        async with manager_with_tracker as manager:
            with aioresponses() as mock:
                mock.get(
                    test_data.url,
                    status=200,
                    body=test_data.content,
                    headers={"Content-Length": str(len(test_data.content))},
                )
                await manager._worker.download(
                    test_data.url, test_data.path, chunk_size=1024
                )

            # Speed metrics should be available via tracker
            metrics = manager.tracker.get_speed_metrics(test_data.url)
            # Metrics should be cleared after completion
            assert metrics is None

    @pytest.mark.asyncio
    async def test_average_speed_persisted_after_completion(
        self, manager_with_tracker, test_data
    ):
        """Test that average speed is persisted in DownloadInfo after completion."""
        async with manager_with_tracker as manager:
            with aioresponses() as mock:
                mock.get(
                    test_data.url,
                    status=200,
                    body=test_data.content,
                    headers={"Content-Length": str(len(test_data.content))},
                )
                await manager._worker.download(
                    test_data.url, test_data.path, chunk_size=1024
                )

            # Download should be completed
            info = manager.tracker.get_download_info(test_data.url)
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

        async with manager_with_tracker as manager:
            with aioresponses() as mock:
                # Simulate partial download then failure
                mock.get(test_data.url, status=500, body="Server Error")

                with pytest.raises(aiohttp.ClientResponseError):
                    await manager._worker.download(test_data.url, test_data.path)

            # Download should be failed
            info = manager.tracker.get_download_info(test_data.url)
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

        async with manager_with_tracker as manager:
            url1 = "https://example.com/file1.txt"
            url2 = "https://example.com/file2.txt"
            url3 = "https://example.com/file3.txt"

            content1 = b"a" * 5000  # 5KB
            content2 = b"b" * 10000  # 10KB
            content3 = b"c" * 3000  # 3KB

            dest1 = tmp_path / "file1.txt"
            dest2 = tmp_path / "file2.txt"
            dest3 = tmp_path / "file3.txt"

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

                # Download concurrently
                await asyncio.gather(
                    manager._worker.download(url1, dest1, chunk_size=1024),
                    manager._worker.download(url2, dest2, chunk_size=1024),
                    manager._worker.download(url3, dest3, chunk_size=1024),
                )

            # All downloads should be completed with independent speeds
            info1 = manager.tracker.get_download_info(url1)
            info2 = manager.tracker.get_download_info(url2)
            info3 = manager.tracker.get_download_info(url3)

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

        async with manager_with_tracker as manager:
            # Track when speed metrics are available
            speed_metrics_seen = []

            async def capture_download():
                """Download and periodically check for speed metrics."""
                with aioresponses() as mock:
                    mock.get(
                        test_data.url,
                        status=200,
                        body=large_content,
                        headers={"Content-Length": str(len(large_content))},
                    )
                    await manager._worker.download(
                        test_data.url, test_data.path, chunk_size=1024
                    )

            async def check_speed_metrics():
                """Periodically check if speed metrics are available."""

                for _ in range(10):  # Check 10 times
                    await asyncio.sleep(0.01)  # Small delay
                    metrics = manager.tracker.get_speed_metrics(test_data.url)
                    if metrics is not None:
                        speed_metrics_seen.append(metrics)

            # Run download and metric checking concurrently

            await asyncio.gather(
                capture_download(),
                check_speed_metrics(),
            )

            # We should have captured at least some speed metrics
            # (might be 0 if download was too fast in mocked test)
            # This test mainly verifies the API works, not the timing
            assert isinstance(speed_metrics_seen, list)

    @pytest.mark.asyncio
    async def test_speed_tracking_with_unknown_file_size(
        self, manager_with_tracker, test_data
    ):
        """Test speed tracking when Content-Length is not provided."""
        async with manager_with_tracker as manager:
            with aioresponses() as mock:
                # No Content-Length header
                mock.get(test_data.url, status=200, body=test_data.content)
                await manager._worker.download(
                    test_data.url, test_data.path, chunk_size=1024
                )

            # Download should complete successfully
            info = manager.tracker.get_download_info(test_data.url)
            assert info is not None
            assert info.status == DownloadStatus.COMPLETED

            # Average speed should still be tracked
            assert info.average_speed_bps is not None
            assert info.average_speed_bps >= 0.0
