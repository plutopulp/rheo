"""Tests for DownloadTracker event payload contents."""

from datetime import datetime

import pytest

from async_download_manager.tracking import DownloadTracker


class TestDownloadTrackerEventPayloads:
    """Test event payload contents."""

    @pytest.mark.asyncio
    async def test_download_queued_event_contains_priority(
        self, tracker: DownloadTracker
    ):
        """Test that DownloadQueuedEvent contains priority information."""

        events_received = []

        tracker.on("tracker.queued", lambda e: events_received.append(e))

        await tracker.track_queued("https://example.com/file.txt", priority=5)

        assert events_received[0].priority == 5

    @pytest.mark.asyncio
    async def test_download_progress_event_calculates_percent(
        self, tracker: DownloadTracker
    ):
        """Test that DownloadProgressEvent calculates progress_percent correctly."""

        events_received = []

        tracker.on("tracker.progress", lambda e: events_received.append(e))

        await tracker.track_progress(
            "https://example.com/file.txt", bytes_downloaded=250, total_bytes=1000
        )

        event = events_received[0]
        assert event.progress_fraction == 0.25
        assert event.progress_percent == 25.0

    @pytest.mark.asyncio
    async def test_download_completed_event_includes_destination(
        self, tracker: DownloadTracker
    ):
        """Test that DownloadCompletedEvent includes destination_path."""

        events_received = []

        tracker.on("tracker.completed", lambda e: events_received.append(e))

        await tracker.track_completed(
            "https://example.com/file.txt",
            total_bytes=1024,
            destination_path="/tmp/file.txt",
        )

        assert events_received[0].destination_path == "/tmp/file.txt"

    @pytest.mark.asyncio
    async def test_event_contains_timestamp(self, tracker: DownloadTracker):
        """Test that all events contain a timestamp."""

        events_received = []

        tracker.on("tracker.queued", lambda e: events_received.append(e))

        before = datetime.now()
        await tracker.track_queued("https://example.com/file.txt")
        after = datetime.now()

        event = events_received[0]
        assert before <= event.timestamp <= after
