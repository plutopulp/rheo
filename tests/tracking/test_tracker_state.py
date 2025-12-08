"""Tests for DownloadTracker state management."""

import asyncio

import pytest

from rheo.domain.downloads import DownloadStatus
from rheo.tracking import DownloadTracker


class TestDownloadTrackerInitialization:
    """Test tracker initialization."""

    def test_init_creates_empty_tracker(self, tracker: DownloadTracker):
        """Test that tracker initializes with empty state."""
        assert tracker.get_all_downloads() == {}
        assert tracker.get_stats().total == 0


class TestDownloadTrackerStateUpdates:
    """Test state update methods."""

    @pytest.mark.asyncio
    async def test_track_queued_creates_new_download(self, tracker: DownloadTracker):
        """Test that track_queued creates DownloadInfo with QUEUED status."""
        url = "https://example.com/file.txt"
        download_id = url  # Use URL as ID for simplicity in tests

        await tracker.track_queued(download_id, url)

        info = tracker.get_download_info(download_id)
        assert info is not None
        assert info.url == url
        assert info.status == DownloadStatus.QUEUED
        assert info.bytes_downloaded == 0

    @pytest.mark.asyncio
    async def test_track_started_transitions_to_in_progress(
        self, tracker: DownloadTracker
    ):
        """Test that track_started updates status to IN_PROGRESS."""
        url = "https://example.com/file.txt"

        await tracker.track_queued(url, url)
        await tracker.track_started(url, url, total_bytes=1024)

        info = tracker.get_download_info(url)
        assert info.status == DownloadStatus.IN_PROGRESS
        assert info.total_bytes == 1024

    @pytest.mark.asyncio
    async def test_track_started_creates_if_not_exists(self, tracker: DownloadTracker):
        """Test that track_started can create DownloadInfo if it doesn't exist."""
        url = "https://example.com/file.txt"

        # Start without queuing first
        await tracker.track_started(url, url, total_bytes=2048)

        info = tracker.get_download_info(url)
        assert info is not None
        assert info.status == DownloadStatus.IN_PROGRESS
        assert info.total_bytes == 2048

    @pytest.mark.asyncio
    async def test_track_progress_updates_bytes_downloaded(
        self, tracker: DownloadTracker
    ):
        """Test that track_progress updates bytes_downloaded."""
        url = "https://example.com/file.txt"

        await tracker.track_started(url, url, total_bytes=1000)
        await tracker.track_progress(url, url, bytes_downloaded=250)

        info = tracker.get_download_info(url)
        assert info.bytes_downloaded == 250
        assert info.get_progress() == 0.25  # 250/1000

    @pytest.mark.asyncio
    async def test_track_progress_multiple_updates(self, tracker: DownloadTracker):
        """Test multiple progress updates."""
        url = "https://example.com/file.txt"

        await tracker.track_started(url, url, total_bytes=1000)
        await tracker.track_progress(url, url, bytes_downloaded=100)
        await tracker.track_progress(url, url, bytes_downloaded=500)
        await tracker.track_progress(url, url, bytes_downloaded=1000)

        info = tracker.get_download_info(url)
        assert info.bytes_downloaded == 1000
        assert info.get_progress() == 1.0

    @pytest.mark.asyncio
    async def test_track_progress_updates_total_bytes_if_provided(
        self, tracker: DownloadTracker
    ):
        """Test that track_progress can update total_bytes."""
        url = "https://example.com/file.txt"

        await tracker.track_started(url, url)
        await tracker.track_progress(url, url, bytes_downloaded=500, total_bytes=2000)

        info = tracker.get_download_info(url)
        assert info.bytes_downloaded == 500
        assert info.total_bytes == 2000
        assert info.get_progress() == 0.25

    @pytest.mark.asyncio
    async def test_track_progress_creates_if_not_exists(self, tracker: DownloadTracker):
        """Test that track_progress can create DownloadInfo if it doesn't exist."""
        url = "https://example.com/file.txt"

        # Update progress without starting first
        await tracker.track_progress(url, url, bytes_downloaded=100, total_bytes=1000)

        info = tracker.get_download_info(url)
        assert info is not None
        assert info.bytes_downloaded == 100
        assert info.total_bytes == 1000

    @pytest.mark.asyncio
    async def test_track_completed_sets_completed_status(
        self, tracker: DownloadTracker
    ):
        """Test that track_completed sets COMPLETED status."""
        url = "https://example.com/file.txt"

        await tracker.track_started(url, url, total_bytes=1024)
        await tracker.track_completed(
            url, url, total_bytes=1024, destination_path="/tmp/file.txt"
        )

        info = tracker.get_download_info(url)
        assert info.status == DownloadStatus.COMPLETED
        assert info.bytes_downloaded == 1024
        assert info.total_bytes == 1024
        assert info.destination_path == "/tmp/file.txt"
        assert info.is_terminal()

    @pytest.mark.asyncio
    async def test_track_completed_updates_bytes_and_total_bytes(
        self, tracker: DownloadTracker
    ):
        """Test that track_completed updates both bytes_downloaded and total_bytes."""
        url = "https://example.com/file.txt"

        await tracker.track_started(url, url)
        await tracker.track_completed(url, url, total_bytes=5000)

        info = tracker.get_download_info(url)
        assert info.bytes_downloaded == 5000
        assert info.total_bytes == 5000

    @pytest.mark.asyncio
    async def test_track_completed_creates_if_not_exists(
        self, tracker: DownloadTracker
    ):
        """Test that track_completed can create DownloadInfo if it doesn't exist."""
        url = "https://example.com/file.txt"

        await tracker.track_completed(url, url, total_bytes=1024)

        info = tracker.get_download_info(url)
        assert info is not None
        assert info.status == DownloadStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_track_failed_sets_failed_status_and_error(
        self, tracker: DownloadTracker
    ):
        """Test that track_failed sets FAILED status and error message."""
        url = "https://example.com/file.txt"
        error = ValueError("Connection failed")

        await tracker.track_started(url, url)
        await tracker.track_failed(url, url, error)

        info = tracker.get_download_info(url)
        assert info.status == DownloadStatus.FAILED
        assert info.error == "Connection failed"
        assert info.is_terminal()

    @pytest.mark.asyncio
    async def test_track_failed_creates_if_not_exists(self, tracker: DownloadTracker):
        """Test that track_failed can create DownloadInfo if it doesn't exist."""
        url = "https://example.com/file.txt"
        error = RuntimeError("Unexpected error")

        await tracker.track_failed(url, url, error)

        info = tracker.get_download_info(url)
        assert info is not None
        assert info.status == DownloadStatus.FAILED
        assert info.error == "Unexpected error"

    # Cleaner version of the test
    @pytest.mark.asyncio
    async def test_updating_one_download_leaves_others_unchanged(
        self, tracker: DownloadTracker
    ):
        """Test that updating one download doesn't affect others."""
        url1, url2 = "https://example.com/file1.txt", "https://example.com/file2.txt"

        # Set up two downloads
        await tracker.track_queued(url1, url1, priority=1)
        await tracker.track_started(url2, url2, total_bytes=1000)

        # Capture initial state of url1
        initial_info1 = tracker.get_download_info(url1)

        # Update url2 only
        await tracker.track_progress(url2, url2, bytes_downloaded=750)
        await tracker.track_completed(url2, url2, total_bytes=1000)

        # Verify url1 completely unchanged
        info1 = tracker.get_download_info(url1)
        assert info1 == initial_info1

    @pytest.mark.asyncio
    async def test_same_url_different_destinations_tracked_separately(
        self, tracker: DownloadTracker
    ):
        """Test same URL to different destinations tracked separately.

        This is the core bug fix - downloads keyed by (URL + destination),
        not just URL. Each download task is independent.
        """
        url = "https://example.com/file.txt"
        download_id_1 = "abc123"  # Represents URL + destination1
        download_id_2 = "def456"  # Represents URL + destination2

        # Track two downloads of same URL (different destinations)
        await tracker.track_queued(download_id_1, url, priority=1)
        await tracker.track_queued(download_id_2, url, priority=5)

        # Both should exist independently
        info1 = tracker.get_download_info(download_id_1)
        info2 = tracker.get_download_info(download_id_2)

        assert info1 is not None
        assert info2 is not None
        assert info1.id == download_id_1
        assert info2.id == download_id_2
        assert info1.url == url
        assert info2.url == url

        # Update one shouldn't affect the other
        await tracker.track_started(download_id_1, url, total_bytes=1024)
        await tracker.track_progress(
            download_id_2, url, bytes_downloaded=512, total_bytes=2048
        )

        info1 = tracker.get_download_info(download_id_1)
        info2 = tracker.get_download_info(download_id_2)

        assert info1.status == DownloadStatus.IN_PROGRESS
        assert info1.total_bytes == 1024
        assert info1.bytes_downloaded == 0

        assert info2.status == DownloadStatus.QUEUED  # Still queued, not started
        assert info2.total_bytes == 2048
        assert info2.bytes_downloaded == 512


class TestDownloadTrackerQueries:
    """Test query methods."""

    @pytest.mark.asyncio
    async def test_get_download_info_returns_none_for_unknown_url(
        self, tracker: DownloadTracker
    ):
        """Test that get_download_info returns None for unknown URL."""

        info = tracker.get_download_info("https://unknown.com/file.txt")
        assert info is None

    @pytest.mark.asyncio
    async def test_get_download_info_returns_correct_info(
        self, tracker: DownloadTracker
    ):
        """Test that get_download_info returns correct DownloadInfo."""
        url = "https://example.com/file.txt"

        await tracker.track_queued(url, url)

        info = tracker.get_download_info(url)
        assert info is not None
        assert info.url == url
        assert info.status == DownloadStatus.QUEUED

    @pytest.mark.asyncio
    async def test_get_all_downloads_returns_all_tracked(
        self, tracker: DownloadTracker
    ):
        """Test that get_all_downloads returns all downloads."""

        await tracker.track_queued(
            "https://example.com/file1.txt", "https://example.com/file1.txt"
        )
        await tracker.track_queued(
            "https://example.com/file2.txt", "https://example.com/file2.txt"
        )
        await tracker.track_queued(
            "https://example.com/file3.txt", "https://example.com/file3.txt"
        )

        all_downloads = tracker.get_all_downloads()
        assert len(all_downloads) == 3
        assert "https://example.com/file1.txt" in all_downloads
        assert "https://example.com/file2.txt" in all_downloads
        assert "https://example.com/file3.txt" in all_downloads

    @pytest.mark.asyncio
    async def test_get_all_downloads_returns_copy(self, tracker: DownloadTracker):
        """Test that get_all_downloads returns a copy, not reference."""
        url = "https://example.com/file.txt"

        await tracker.track_queued(url, url)

        all_downloads = tracker.get_all_downloads()
        # Modify the returned dict
        all_downloads.clear()

        # Original should be unchanged
        assert tracker.get_download_info(url) is not None

    @pytest.mark.asyncio
    async def test_get_active_downloads_returns_only_in_progress(
        self, tracker: DownloadTracker
    ):
        """Test that get_active_downloads returns only IN_PROGRESS downloads."""

        await tracker.track_queued(
            "https://example.com/file1.txt", "https://example.com/file1.txt"
        )
        await tracker.track_started(
            "https://example.com/file2.txt", "https://example.com/file2.txt"
        )
        await tracker.track_started(
            "https://example.com/file3.txt", "https://example.com/file3.txt"
        )
        await tracker.track_completed(
            "https://example.com/file4.txt",
            "https://example.com/file4.txt",
            total_bytes=100,
        )

        active = tracker.get_active_downloads()
        assert len(active) == 2
        assert "https://example.com/file2.txt" in active
        assert "https://example.com/file3.txt" in active

    @pytest.mark.asyncio
    async def test_get_active_downloads_excludes_non_in_progress(
        self, tracker: DownloadTracker
    ):
        """Test that get_active_downloads excludes QUEUED, COMPLETED, FAILED."""

        await tracker.track_queued(
            "https://example.com/queued.txt", "https://example.com/queued.txt"
        )
        await tracker.track_started(
            "https://example.com/active.txt", "https://example.com/active.txt"
        )
        await tracker.track_completed(
            "https://example.com/completed.txt",
            "https://example.com/completed.txt",
            total_bytes=100,
        )
        await tracker.track_failed(
            "https://example.com/failed.txt",
            "https://example.com/failed.txt",
            ValueError("Error"),
        )

        active = tracker.get_active_downloads()
        assert len(active) == 1
        assert "https://example.com/active.txt" in active

    @pytest.mark.asyncio
    async def test_get_stats_returns_accurate_total_count(
        self, tracker: DownloadTracker
    ):
        """Test that get_stats returns accurate total count."""

        await tracker.track_queued(
            "https://example.com/file1.txt", "https://example.com/file1.txt"
        )
        await tracker.track_queued(
            "https://example.com/file2.txt", "https://example.com/file2.txt"
        )
        await tracker.track_started(
            "https://example.com/file3.txt", "https://example.com/file3.txt"
        )

        stats = tracker.get_stats()
        assert stats.total == 3

    @pytest.mark.asyncio
    async def test_get_stats_returns_correct_counts_by_status(
        self, tracker: DownloadTracker
    ):
        """Test that get_stats returns correct counts by status."""

        # Queue 2
        await tracker.track_queued(
            "https://example.com/file1.txt", "https://example.com/file1.txt"
        )
        await tracker.track_queued(
            "https://example.com/file2.txt", "https://example.com/file2.txt"
        )

        # Start 2
        await tracker.track_started(
            "https://example.com/file3.txt", "https://example.com/file3.txt"
        )
        await tracker.track_started(
            "https://example.com/file4.txt", "https://example.com/file4.txt"
        )

        # Complete 1
        await tracker.track_completed(
            "https://example.com/file5.txt",
            "https://example.com/file5.txt",
            total_bytes=1024,
        )

        # Fail 1
        await tracker.track_failed(
            "https://example.com/file6.txt",
            "https://example.com/file6.txt",
            ValueError("Error"),
        )

        stats = tracker.get_stats()
        assert stats.total == 6
        assert stats.queued == 2
        assert stats.in_progress == 2
        assert stats.completed == 1
        assert stats.failed == 1

    @pytest.mark.asyncio
    async def test_get_stats_calculates_completed_bytes_correctly(
        self, tracker: DownloadTracker
    ):
        """Test that get_stats calculates completed_bytes correctly."""

        await tracker.track_completed(
            "https://example.com/file1.txt",
            "https://example.com/file1.txt",
            total_bytes=1024,
        )
        await tracker.track_completed(
            "https://example.com/file2.txt",
            "https://example.com/file2.txt",
            total_bytes=2048,
        )
        await tracker.track_completed(
            "https://example.com/file3.txt",
            "https://example.com/file3.txt",
            total_bytes=512,
        )
        # In progress shouldn't count
        await tracker.track_started(
            "https://example.com/file4.txt",
            "https://example.com/file4.txt",
            total_bytes=5000,
        )

        stats = tracker.get_stats()
        assert stats.completed_bytes == 3584  # 1024 + 2048 + 512


class TestDownloadTrackerThreadSafety:
    """Test concurrent access with asyncio locks."""

    @pytest.mark.asyncio
    async def test_concurrent_updates_are_thread_safe(self, tracker: DownloadTracker):
        """Test that concurrent updates don't corrupt state."""

        url = "https://example.com/file.txt"

        # Simulate multiple workers updating progress concurrently
        async def update_progress(bytes_count):
            await tracker.track_progress(url, url, bytes_downloaded=bytes_count)

        # Start with a download
        await tracker.track_started(url, url, total_bytes=1000)

        # Update progress from multiple "workers" concurrently
        await asyncio.gather(
            update_progress(100),
            update_progress(200),
            update_progress(300),
            update_progress(400),
            update_progress(500),
        )

        # Last update should win (one of the values)
        info = tracker.get_download_info(url)
        assert info.bytes_downloaded in (100, 200, 300, 400, 500)

    @pytest.mark.asyncio
    async def test_multiple_urls_updated_concurrently(self, tracker: DownloadTracker):
        """Test that multiple workers can update different URLs simultaneously."""

        async def download_file(url, size):
            await tracker.track_started(url, url, total_bytes=size)
            await tracker.track_progress(url, url, bytes_downloaded=size // 2)
            await tracker.track_completed(url, url, total_bytes=size)

        # Download multiple files concurrently
        await asyncio.gather(
            download_file("https://example.com/file1.txt", 1000),
            download_file("https://example.com/file2.txt", 2000),
            download_file("https://example.com/file3.txt", 3000),
        )

        # Verify all completed successfully
        assert tracker.get_stats().completed == 3

    @pytest.mark.asyncio
    async def test_lock_prevents_race_conditions(self, tracker: DownloadTracker):
        """Test that lock prevents race conditions on same URL."""

        url = "https://example.com/file.txt"

        await tracker.track_started(url, url, total_bytes=1000)

        # Rapidly update progress many times
        async def rapid_updates():
            for i in range(10):
                await tracker.track_progress(url, url, bytes_downloaded=i * 100)

        # Multiple workers doing rapid updates
        await asyncio.gather(
            rapid_updates(),
            rapid_updates(),
            rapid_updates(),
        )

        # State should still be valid (not corrupted)
        info = tracker.get_download_info(url)
        assert info is not None
        assert info.total_bytes == 1000
        assert 0 <= info.bytes_downloaded <= 1000
