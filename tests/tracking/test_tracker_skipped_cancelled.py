"""Tests for skipped and cancelled tracking."""

import pytest

from rheo.domain.downloads import DownloadStatus
from rheo.tracking import DownloadTracker


class TestTrackerSkippedCancelled:
    """Test track_skipped and track_cancelled methods."""

    @pytest.mark.asyncio
    async def test_track_skipped_sets_status(self, tracker: DownloadTracker) -> None:
        """track_skipped sets status to SKIPPED."""
        await tracker._track_skipped("id", "http://x", "file_exists", "/path/to/file")
        info = tracker.get_download_info("id")

        assert info is not None
        assert info.status == DownloadStatus.SKIPPED
        assert info.destination_path == "/path/to/file"

    @pytest.mark.asyncio
    async def test_track_cancelled_sets_status(self, tracker: DownloadTracker) -> None:
        """track_cancelled sets status to CANCELLED."""
        await tracker._track_started("id", "http://x")
        await tracker._track_cancelled("id", "http://x")

        info = tracker.get_download_info("id")

        assert info is not None
        assert info.status == DownloadStatus.CANCELLED
