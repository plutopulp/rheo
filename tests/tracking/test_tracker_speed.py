"""Tests for DownloadTracker speed tracking functionality."""

import asyncio

import pytest

from rheo.domain.speed import SpeedMetrics
from rheo.tracking import DownloadTracker


class TestTrackerSpeedTracking:
    """Test tracker speed metric storage and retrieval."""

    @pytest.mark.asyncio
    async def test_track_progress_with_speed_stores_metrics(
        self, tracker: DownloadTracker
    ) -> None:
        """Test that _track_progress with speed stores speed metrics."""
        url = "https://example.com/file.txt"

        await tracker._track_started(url, url, total_bytes=10000)
        await tracker._track_progress(
            download_id=url,
            url=url,
            bytes_downloaded=1000,
            total_bytes=10000,
            speed=SpeedMetrics(
                current_speed_bps=1024.0,
                average_speed_bps=1000.0,
                eta_seconds=9.0,
                elapsed_seconds=1.0,
            ),
        )

        metrics = tracker.get_speed_metrics(url)
        assert metrics is not None
        assert metrics.current_speed_bps == 1024.0
        assert metrics.average_speed_bps == 1000.0
        assert metrics.eta_seconds == 9.0
        assert metrics.elapsed_seconds == 1.0

    @pytest.mark.asyncio
    async def test_track_progress_updates_existing_speed_metrics(
        self, tracker: DownloadTracker
    ) -> None:
        """Test that subsequent progress updates replace previous speed metrics."""
        url = "https://example.com/file.txt"

        await tracker._track_started(url, url, total_bytes=10000)

        # First update
        await tracker._track_progress(
            download_id=url,
            url=url,
            bytes_downloaded=1000,
            total_bytes=10000,
            speed=SpeedMetrics(
                current_speed_bps=1024.0,
                average_speed_bps=1000.0,
                eta_seconds=10.0,
                elapsed_seconds=1.0,
            ),
        )

        # Second update
        await tracker._track_progress(
            download_id=url,
            url=url,
            bytes_downloaded=2000,
            total_bytes=10000,
            speed=SpeedMetrics(
                current_speed_bps=2048.0,
                average_speed_bps=1500.0,
                eta_seconds=5.0,
                elapsed_seconds=2.0,
            ),
        )

        metrics = tracker.get_speed_metrics(url)
        assert metrics.current_speed_bps == 2048.0
        assert metrics.average_speed_bps == 1500.0
        assert metrics.eta_seconds == 5.0
        assert metrics.elapsed_seconds == 2.0

    @pytest.mark.asyncio
    async def test_get_speed_metrics_returns_none_for_unknown_url(
        self, tracker: DownloadTracker
    ) -> None:
        """Test that get_speed_metrics returns None for unknown URL."""
        metrics = tracker.get_speed_metrics("https://unknown.com/file.txt")
        assert metrics is None

    @pytest.mark.asyncio
    async def test_get_speed_metrics_returns_none_before_first_update(
        self, tracker: DownloadTracker
    ) -> None:
        """Test that get_speed_metrics returns None before any speed updates."""
        url = "https://example.com/file.txt"

        await tracker._track_started(url, url, total_bytes=10000)

        # No speed update yet
        metrics = tracker.get_speed_metrics(url)
        assert metrics is None

    @pytest.mark.asyncio
    async def test_track_progress_handles_none_eta(
        self, tracker: DownloadTracker
    ) -> None:
        """Test that _track_progress handles None ETA (unknown total size)."""
        url = "https://example.com/file.txt"

        await tracker._track_started(url, url)  # No total_bytes

        await tracker._track_progress(
            download_id=url,
            url=url,
            bytes_downloaded=1000,
            speed=SpeedMetrics(
                current_speed_bps=1024.0,
                average_speed_bps=1000.0,
                eta_seconds=None,  # Can't calculate ETA without total
                elapsed_seconds=1.0,
            ),
        )

        metrics = tracker.get_speed_metrics(url)
        assert metrics.eta_seconds is None

    @pytest.mark.asyncio
    async def test_track_progress_with_zero_speeds(
        self, tracker: DownloadTracker
    ) -> None:
        """Test that _track_progress handles zero speeds (first chunk)."""
        url = "https://example.com/file.txt"

        await tracker._track_started(url, url, total_bytes=10000)

        await tracker._track_progress(
            download_id=url,
            url=url,
            bytes_downloaded=100,
            total_bytes=10000,
            speed=SpeedMetrics(
                current_speed_bps=0.0,
                average_speed_bps=0.0,
                eta_seconds=None,
                elapsed_seconds=0.0,
            ),
        )

        metrics = tracker.get_speed_metrics(url)
        assert metrics.current_speed_bps == 0.0
        assert metrics.average_speed_bps == 0.0
        assert metrics.eta_seconds is None
        assert metrics.elapsed_seconds == 0.0

    @pytest.mark.asyncio
    async def test_track_progress_without_speed_does_not_clear_metrics(
        self, tracker: DownloadTracker
    ) -> None:
        """Test that progress without speed doesn't clear existing metrics."""
        url = "https://example.com/file.txt"

        await tracker._track_started(url, url, total_bytes=10000)
        await tracker._track_progress(
            download_id=url,
            url=url,
            bytes_downloaded=1000,
            total_bytes=10000,
            speed=SpeedMetrics(
                current_speed_bps=1024.0,
                average_speed_bps=1000.0,
                eta_seconds=9.0,
                elapsed_seconds=1.0,
            ),
        )

        # Update progress without speed
        await tracker._track_progress(url, url, bytes_downloaded=2000)

        # Speed metrics should still be available
        metrics = tracker.get_speed_metrics(url)
        assert metrics is not None
        assert metrics.current_speed_bps == 1024.0

    @pytest.mark.asyncio
    async def test_speed_metrics_cleared_on_completion(
        self, tracker: DownloadTracker
    ) -> None:
        """Test that transient speed metrics are cleared when download completes."""
        url = "https://example.com/file.txt"

        await tracker._track_started(url, url, total_bytes=10000)
        await tracker._track_progress(
            download_id=url,
            url=url,
            bytes_downloaded=5000,
            total_bytes=10000,
            speed=SpeedMetrics(
                current_speed_bps=1024.0,
                average_speed_bps=1000.0,
                eta_seconds=9.0,
                elapsed_seconds=10.0,
            ),
        )

        # Complete the download
        await tracker._track_completed(url, url, total_bytes=10000)

        # Transient speed metrics should be cleared
        metrics = tracker.get_speed_metrics(url)
        assert metrics is None

    @pytest.mark.asyncio
    async def test_average_speed_persisted_in_download_info_on_completion(
        self, tracker: DownloadTracker
    ) -> None:
        """Test that average speed is persisted in DownloadInfo when download
        completes."""
        url = "https://example.com/file.txt"

        await tracker._track_started(url, url, total_bytes=10000)
        await tracker._track_progress(
            download_id=url,
            url=url,
            bytes_downloaded=5000,
            total_bytes=10000,
            speed=SpeedMetrics(
                current_speed_bps=1024.0,
                average_speed_bps=1000.0,
                eta_seconds=9.0,
                elapsed_seconds=10.0,
            ),
        )

        # Complete the download
        await tracker._track_completed(url, url, total_bytes=10000)

        # Average speed should be persisted in DownloadInfo
        info = tracker.get_download_info(url)
        assert info is not None
        assert info.average_speed_bps == 1000.0

    @pytest.mark.asyncio
    async def test_speed_metrics_cleared_on_failure(
        self, tracker: DownloadTracker
    ) -> None:
        """Test that transient speed metrics are cleared when download fails."""
        url = "https://example.com/file.txt"

        await tracker._track_started(url, url, total_bytes=10000)
        await tracker._track_progress(
            download_id=url,
            url=url,
            bytes_downloaded=5000,
            total_bytes=10000,
            speed=SpeedMetrics(
                current_speed_bps=1024.0,
                average_speed_bps=1000.0,
                eta_seconds=9.0,
                elapsed_seconds=5.0,
            ),
        )

        # Fail the download
        await tracker._track_failed(url, url, ValueError("Network error"))

        # Transient speed metrics should be cleared
        metrics = tracker.get_speed_metrics(url)
        assert metrics is None

    @pytest.mark.asyncio
    async def test_average_speed_persisted_in_download_info_on_failure(
        self, tracker: DownloadTracker
    ) -> None:
        """Test that average speed is persisted in DownloadInfo when download fails."""
        url = "https://example.com/file.txt"

        await tracker._track_started(url, url, total_bytes=10000)
        await tracker._track_progress(
            download_id=url,
            url=url,
            bytes_downloaded=5000,
            total_bytes=10000,
            speed=SpeedMetrics(
                current_speed_bps=1024.0,
                average_speed_bps=900.0,
                eta_seconds=10.0,
                elapsed_seconds=5.0,
            ),
        )

        # Fail the download
        await tracker._track_failed(url, url, ValueError("Network error"))

        # Average speed should be persisted in DownloadInfo (useful for analysis)
        info = tracker.get_download_info(url)
        assert info is not None
        assert info.average_speed_bps == 900.0

    @pytest.mark.asyncio
    async def test_completion_without_speed_update_keeps_speed_none(
        self, tracker: DownloadTracker
    ) -> None:
        """Test that completing without speed updates leaves average_speed_bps as
        None."""
        url = "https://example.com/file.txt"

        await tracker._track_started(url, url, total_bytes=10000)
        # No speed update
        await tracker._track_completed(url, url, total_bytes=10000)

        info = tracker.get_download_info(url)
        assert info is not None
        assert info.average_speed_bps is None

    @pytest.mark.asyncio
    async def test_concurrent_progress_updates_are_thread_safe(
        self, tracker: DownloadTracker
    ) -> None:
        """Test that concurrent progress updates from multiple workers are safe."""
        url = "https://example.com/file.txt"
        await tracker._track_started(url, url, total_bytes=100000)

        # Simulate multiple concurrent progress updates with speed
        async def update_progress(bytes_val: int, speed_value: float) -> None:
            await tracker._track_progress(
                download_id=url,
                url=url,
                bytes_downloaded=bytes_val,
                total_bytes=100000,
                speed=SpeedMetrics(
                    current_speed_bps=speed_value,
                    average_speed_bps=speed_value * 0.9,
                    eta_seconds=100000 / speed_value if speed_value > 0 else None,
                    elapsed_seconds=10.0,
                ),
            )

        # Run concurrent updates
        await asyncio.gather(
            update_progress(1000, 1000.0),
            update_progress(2000, 2000.0),
            update_progress(3000, 3000.0),
            update_progress(4000, 4000.0),
            update_progress(5000, 5000.0),
        )

        # Should have one of the speeds (last write wins)
        metrics = tracker.get_speed_metrics(url)
        assert metrics is not None
        assert metrics.current_speed_bps in (1000.0, 2000.0, 3000.0, 4000.0, 5000.0)
