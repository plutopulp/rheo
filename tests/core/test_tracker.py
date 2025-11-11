"""Tests for DownloadTracker - Phase 1: State tracking only."""

import asyncio
from datetime import datetime

import pytest

from async_download_manager.domain.downloads import DownloadStatus
from async_download_manager.events import (
    DownloadCompletedEvent,
    DownloadFailedEvent,
    DownloadProgressEvent,
    DownloadQueuedEvent,
    DownloadStartedEvent,
)
from async_download_manager.tracking import DownloadTracker


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

        await tracker.track_queued(url)

        info = tracker.get_download_info(url)
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

        await tracker.track_queued(url)
        await tracker.track_started(url, total_bytes=1024)

        info = tracker.get_download_info(url)
        assert info.status == DownloadStatus.IN_PROGRESS
        assert info.total_bytes == 1024

    @pytest.mark.asyncio
    async def test_track_started_creates_if_not_exists(self, tracker: DownloadTracker):
        """Test that track_started can create DownloadInfo if it doesn't exist."""
        url = "https://example.com/file.txt"

        # Start without queuing first
        await tracker.track_started(url, total_bytes=2048)

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

        await tracker.track_started(url, total_bytes=1000)
        await tracker.track_progress(url, bytes_downloaded=250)

        info = tracker.get_download_info(url)
        assert info.bytes_downloaded == 250
        assert info.get_progress() == 0.25  # 250/1000

    @pytest.mark.asyncio
    async def test_track_progress_multiple_updates(self, tracker: DownloadTracker):
        """Test multiple progress updates."""
        url = "https://example.com/file.txt"

        await tracker.track_started(url, total_bytes=1000)
        await tracker.track_progress(url, bytes_downloaded=100)
        await tracker.track_progress(url, bytes_downloaded=500)
        await tracker.track_progress(url, bytes_downloaded=1000)

        info = tracker.get_download_info(url)
        assert info.bytes_downloaded == 1000
        assert info.get_progress() == 1.0

    @pytest.mark.asyncio
    async def test_track_progress_updates_total_bytes_if_provided(
        self, tracker: DownloadTracker
    ):
        """Test that track_progress can update total_bytes."""
        url = "https://example.com/file.txt"

        await tracker.track_started(url)
        await tracker.track_progress(url, bytes_downloaded=500, total_bytes=2000)

        info = tracker.get_download_info(url)
        assert info.bytes_downloaded == 500
        assert info.total_bytes == 2000
        assert info.get_progress() == 0.25

    @pytest.mark.asyncio
    async def test_track_progress_creates_if_not_exists(self, tracker: DownloadTracker):
        """Test that track_progress can create DownloadInfo if it doesn't exist."""
        url = "https://example.com/file.txt"

        # Update progress without starting first
        await tracker.track_progress(url, bytes_downloaded=100, total_bytes=1000)

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

        await tracker.track_started(url, total_bytes=1024)
        await tracker.track_completed(url, total_bytes=1024)

        info = tracker.get_download_info(url)
        assert info.status == DownloadStatus.COMPLETED
        assert info.bytes_downloaded == 1024
        assert info.total_bytes == 1024
        assert info.is_terminal()

    @pytest.mark.asyncio
    async def test_track_completed_updates_bytes_and_total_bytes(
        self, tracker: DownloadTracker
    ):
        """Test that track_completed updates both bytes_downloaded and total_bytes."""
        url = "https://example.com/file.txt"

        await tracker.track_started(url)
        await tracker.track_completed(url, total_bytes=5000)

        info = tracker.get_download_info(url)
        assert info.bytes_downloaded == 5000
        assert info.total_bytes == 5000

    @pytest.mark.asyncio
    async def test_track_completed_creates_if_not_exists(
        self, tracker: DownloadTracker
    ):
        """Test that track_completed can create DownloadInfo if it doesn't exist."""
        url = "https://example.com/file.txt"

        await tracker.track_completed(url, total_bytes=1024)

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

        await tracker.track_started(url)
        await tracker.track_failed(url, error)

        info = tracker.get_download_info(url)
        assert info.status == DownloadStatus.FAILED
        assert info.error == "Connection failed"
        assert info.is_terminal()

    @pytest.mark.asyncio
    async def test_track_failed_creates_if_not_exists(self, tracker: DownloadTracker):
        """Test that track_failed can create DownloadInfo if it doesn't exist."""
        url = "https://example.com/file.txt"
        error = RuntimeError("Unexpected error")

        await tracker.track_failed(url, error)

        info = tracker.get_download_info(url)
        assert info is not None
        assert info.status == DownloadStatus.FAILED
        assert info.error == "Unexpected error"


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

        await tracker.track_queued(url)

        info = tracker.get_download_info(url)
        assert info is not None
        assert info.url == url
        assert info.status == DownloadStatus.QUEUED

    @pytest.mark.asyncio
    async def test_get_all_downloads_returns_all_tracked(
        self, tracker: DownloadTracker
    ):
        """Test that get_all_downloads returns all downloads."""

        await tracker.track_queued("https://example.com/file1.txt")
        await tracker.track_queued("https://example.com/file2.txt")
        await tracker.track_queued("https://example.com/file3.txt")

        all_downloads = tracker.get_all_downloads()
        assert len(all_downloads) == 3
        assert "https://example.com/file1.txt" in all_downloads
        assert "https://example.com/file2.txt" in all_downloads
        assert "https://example.com/file3.txt" in all_downloads

    @pytest.mark.asyncio
    async def test_get_all_downloads_returns_copy(self, tracker: DownloadTracker):
        """Test that get_all_downloads returns a copy, not reference."""
        url = "https://example.com/file.txt"

        await tracker.track_queued(url)

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

        await tracker.track_queued("https://example.com/file1.txt")
        await tracker.track_started("https://example.com/file2.txt")
        await tracker.track_started("https://example.com/file3.txt")
        await tracker.track_completed("https://example.com/file4.txt", total_bytes=100)

        active = tracker.get_active_downloads()
        assert len(active) == 2
        assert "https://example.com/file2.txt" in active
        assert "https://example.com/file3.txt" in active

    @pytest.mark.asyncio
    async def test_get_active_downloads_excludes_non_in_progress(
        self, tracker: DownloadTracker
    ):
        """Test that get_active_downloads excludes QUEUED, COMPLETED, FAILED."""

        await tracker.track_queued("https://example.com/queued.txt")
        await tracker.track_started("https://example.com/active.txt")
        await tracker.track_completed(
            "https://example.com/completed.txt", total_bytes=100
        )
        await tracker.track_failed(
            "https://example.com/failed.txt", ValueError("Error")
        )

        active = tracker.get_active_downloads()
        assert len(active) == 1
        assert "https://example.com/active.txt" in active

    @pytest.mark.asyncio
    async def test_get_stats_returns_accurate_total_count(
        self, tracker: DownloadTracker
    ):
        """Test that get_stats returns accurate total count."""

        await tracker.track_queued("https://example.com/file1.txt")
        await tracker.track_queued("https://example.com/file2.txt")
        await tracker.track_started("https://example.com/file3.txt")

        stats = tracker.get_stats()
        assert stats.total == 3

    @pytest.mark.asyncio
    async def test_get_stats_returns_correct_counts_by_status(
        self, tracker: DownloadTracker
    ):
        """Test that get_stats returns correct counts by status."""

        # Queue 2
        await tracker.track_queued("https://example.com/file1.txt")
        await tracker.track_queued("https://example.com/file2.txt")

        # Start 2
        await tracker.track_started("https://example.com/file3.txt")
        await tracker.track_started("https://example.com/file4.txt")

        # Complete 1
        await tracker.track_completed("https://example.com/file5.txt", total_bytes=1024)

        # Fail 1
        await tracker.track_failed("https://example.com/file6.txt", ValueError("Error"))

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

        await tracker.track_completed("https://example.com/file1.txt", total_bytes=1024)
        await tracker.track_completed("https://example.com/file2.txt", total_bytes=2048)
        await tracker.track_completed("https://example.com/file3.txt", total_bytes=512)
        # In progress shouldn't count
        await tracker.track_started("https://example.com/file4.txt", total_bytes=5000)

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
            await tracker.track_progress(url, bytes_downloaded=bytes_count)

        # Start with a download
        await tracker.track_started(url, total_bytes=1000)

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
            await tracker.track_started(url, total_bytes=size)
            await tracker.track_progress(url, bytes_downloaded=size // 2)
            await tracker.track_completed(url, total_bytes=size)

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

        await tracker.track_started(url, total_bytes=1000)

        # Rapidly update progress many times
        async def rapid_updates():
            for i in range(10):
                await tracker.track_progress(url, bytes_downloaded=i * 100)

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


class TestDownloadTrackerEventSubscription:
    """Test event subscription methods."""

    def test_tracker_accepts_emitter_in_constructor(self, mock_logger, mocker):
        """Test that tracker can be initialized with a custom emitter."""
        mock_emitter = mocker.Mock()
        tracker = DownloadTracker(logger=mock_logger, emitter=mock_emitter)

        assert tracker._emitter is mock_emitter

    def test_tracker_creates_default_emitter_if_none_provided(self, mock_logger):
        """Test that tracker creates default emitter if none provided."""
        tracker = DownloadTracker(logger=mock_logger)

        assert hasattr(tracker, "_emitter")
        assert tracker._emitter is not None

    def test_on_registers_handler_for_event_type(self, tracker: DownloadTracker):
        """Test that on() registers a handler for an event type."""
        handler_called = []

        def handler(event):
            handler_called.append(event)

        tracker.on("tracker.queued", handler)

        # Handler is registered (we'll test emission in next test class)
        assert "tracker.queued" in tracker._emitter._handlers
        assert handler in tracker._emitter._handlers["tracker.queued"]

    def test_multiple_handlers_can_subscribe_to_same_event(
        self, tracker: DownloadTracker
    ):
        """Test that multiple handlers can subscribe to the same event."""

        def handler1(event):
            pass

        def handler2(event):
            pass

        tracker.on("tracker.started", handler1)
        tracker.on("tracker.started", handler2)

        assert len(tracker._emitter._handlers["tracker.started"]) == 2
        assert handler1 in tracker._emitter._handlers["tracker.started"]
        assert handler2 in tracker._emitter._handlers["tracker.started"]

    def test_off_removes_handler(self, tracker: DownloadTracker):
        """Test that off() removes a handler."""

        def handler(event):
            pass

        tracker.on("tracker.progress", handler)
        tracker.off("tracker.progress", handler)

        assert handler not in tracker._emitter._handlers.get("tracker.progress", [])

    def test_off_handles_removing_non_existent_handler_gracefully(
        self, tracker: DownloadTracker
    ):
        """Test that off() handles removing a non-existent handler without error."""

        def handler(event):
            pass

        # Should not raise an error
        tracker.off("tracker.completed", handler)

        # check that a warning is logged (message format changed in EventEmitter)
        warning_msg = f"Handler {handler} not found for event tracker.completed"
        tracker._logger.warning.assert_called_once_with(warning_msg)

    def test_wildcard_handler_registration(self, tracker: DownloadTracker):
        """Test that wildcard '*' handler can be registered."""

        def handler(event):
            pass

        tracker.on("*", handler)

        assert "*" in tracker._emitter._handlers
        assert handler in tracker._emitter._handlers["*"]


class TestDownloadTrackerEventEmission:
    """Test event emission during state changes."""

    @pytest.mark.asyncio
    async def test_track_queued_emits_event(self, tracker: DownloadTracker):
        """Test that track_queued emits DownloadQueuedEvent."""
        events_received = []

        def handler(event):
            events_received.append(event)

        tracker.on("tracker.queued", handler)

        await tracker.track_queued("https://example.com/file.txt")

        assert len(events_received) == 1
        assert isinstance(events_received[0], DownloadQueuedEvent)
        assert events_received[0].url == "https://example.com/file.txt"

    @pytest.mark.asyncio
    async def test_track_started_emits_event(self, tracker: DownloadTracker):
        """Test that track_started emits DownloadStartedEvent."""
        events_received = []

        def handler(event):
            events_received.append(event)

        tracker.on("tracker.started", handler)

        await tracker.track_started("https://example.com/file.txt", total_bytes=1024)

        assert len(events_received) == 1
        assert isinstance(events_received[0], DownloadStartedEvent)
        assert events_received[0].url == "https://example.com/file.txt"
        assert events_received[0].total_bytes == 1024

    @pytest.mark.asyncio
    async def test_track_progress_emits_event(self, tracker: DownloadTracker):
        """Test that track_progress emits DownloadProgressEvent."""
        events_received = []

        def handler(event):
            events_received.append(event)

        tracker.on("tracker.progress", handler)

        await tracker.track_progress(
            "https://example.com/file.txt", bytes_downloaded=512, total_bytes=1024
        )

        assert len(events_received) == 1
        assert isinstance(events_received[0], DownloadProgressEvent)
        assert events_received[0].url == "https://example.com/file.txt"
        assert events_received[0].bytes_downloaded == 512
        assert events_received[0].total_bytes == 1024

    @pytest.mark.asyncio
    async def test_track_completed_emits_event(self, tracker: DownloadTracker):
        """Test that track_completed emits DownloadCompletedEvent."""
        events_received = []

        def handler(event):
            events_received.append(event)

        tracker.on("tracker.completed", handler)

        await tracker.track_completed("https://example.com/file.txt", total_bytes=1024)

        assert len(events_received) == 1
        assert isinstance(events_received[0], DownloadCompletedEvent)
        assert events_received[0].url == "https://example.com/file.txt"
        assert events_received[0].total_bytes == 1024

    @pytest.mark.asyncio
    async def test_track_failed_emits_event(self, tracker: DownloadTracker):
        """Test that track_failed emits DownloadFailedEvent."""
        events_received = []

        def handler(event):
            events_received.append(event)

        tracker.on("tracker.failed", handler)

        error = ValueError("Connection failed")
        await tracker.track_failed("https://example.com/file.txt", error)

        assert len(events_received) == 1
        assert isinstance(events_received[0], DownloadFailedEvent)
        assert events_received[0].url == "https://example.com/file.txt"
        assert events_received[0].error_message == "Connection failed"
        assert events_received[0].error_type == "ValueError"

    @pytest.mark.asyncio
    async def test_events_emitted_after_state_update(self, tracker: DownloadTracker):
        """Test that events are emitted after state is updated, not before."""
        state_when_handler_called = []

        def handler(event):
            # Capture state when handler is called
            info = tracker.get_download_info(event.url)
            state_when_handler_called.append(info.status if info else None)

        tracker.on("tracker.started", handler)

        await tracker.track_started("https://example.com/file.txt")

        # Handler should see the updated state
        assert len(state_when_handler_called) == 1
        assert state_when_handler_called[0] == DownloadStatus.IN_PROGRESS


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
        assert hasattr(event, "timestamp")
        assert before <= event.timestamp <= after


class TestDownloadTrackerEventHandlers:
    """Test handler execution behavior."""

    @pytest.mark.asyncio
    async def test_sync_handler_executes_successfully(self, tracker: DownloadTracker):
        """Test that synchronous handlers execute successfully."""
        handler_called = []

        def sync_handler(event):
            handler_called.append("sync")

        tracker.on("tracker.queued", sync_handler)

        await tracker.track_queued("https://example.com/file.txt")

        assert handler_called == ["sync"]

    @pytest.mark.asyncio
    async def test_async_handler_executes_successfully(self, tracker: DownloadTracker):
        """Test that asynchronous handlers execute successfully."""
        handler_called = []

        async def async_handler(event):
            await asyncio.sleep(0.001)  # Simulate async work
            handler_called.append("async")

        tracker.on("tracker.queued", async_handler)

        await tracker.track_queued("https://example.com/file.txt")

        assert handler_called == ["async"]

    @pytest.mark.asyncio
    async def test_multiple_handlers_all_execute(self, tracker: DownloadTracker):
        """Test that all subscribed handlers execute."""
        handlers_called = []

        tracker.on("tracker.started", lambda e: handlers_called.append("handler1"))
        tracker.on("tracker.started", lambda e: handlers_called.append("handler2"))
        tracker.on("tracker.started", lambda e: handlers_called.append("handler3"))

        await tracker.track_started("https://example.com/file.txt")

        assert len(handlers_called) == 3
        assert "handler1" in handlers_called
        assert "handler2" in handlers_called
        assert "handler3" in handlers_called

    @pytest.mark.asyncio
    async def test_handler_exception_does_not_break_tracking(
        self, tracker: DownloadTracker
    ):
        """Test that exceptions in handlers don't prevent state updates."""

        def bad_handler(event):
            raise ValueError("Handler error")

        tracker.on("tracker.queued", bad_handler)

        # Should not raise, tracking should continue
        await tracker.track_queued("https://example.com/file.txt")

        # State should still be updated
        info = tracker.get_download_info("https://example.com/file.txt")
        assert info is not None
        assert info.status == DownloadStatus.QUEUED

    @pytest.mark.asyncio
    async def test_handler_exception_does_not_prevent_other_handlers(
        self, tracker: DownloadTracker
    ):
        """Test that exceptions in one handler don't prevent others from running."""
        handlers_called = []

        def bad_handler(event):
            handlers_called.append("bad")
            raise ValueError("Handler error")

        def good_handler(event):
            handlers_called.append("good")

        tracker.on("tracker.queued", bad_handler)
        tracker.on("tracker.queued", good_handler)

        await tracker.track_queued("https://example.com/file.txt")

        # Both handlers should have been called
        assert "bad" in handlers_called
        assert "good" in handlers_called

    @pytest.mark.asyncio
    async def test_wildcard_handler_receives_all_events(self, tracker: DownloadTracker):
        """Test that wildcard '*' handler receives all event types."""
        events_received = []

        tracker.on("*", lambda e: events_received.append(e.event_type))

        await tracker.track_queued("https://example.com/file.txt")
        await tracker.track_started("https://example.com/file.txt")
        await tracker.track_progress("https://example.com/file.txt", 100)
        await tracker.track_completed("https://example.com/file.txt", 100)

        assert "tracker.queued" in events_received
        assert "tracker.started" in events_received
        assert "tracker.progress" in events_received
        assert "tracker.completed" in events_received

    @pytest.mark.asyncio
    async def test_specific_and_wildcard_handlers_both_fire(
        self, tracker: DownloadTracker
    ):
        """Test that both specific and wildcard handlers receive events."""
        specific_called = []
        wildcard_called = []

        tracker.on("tracker.queued", lambda e: specific_called.append(e))
        tracker.on("*", lambda e: wildcard_called.append(e))

        await tracker.track_queued("https://example.com/file.txt")

        assert len(specific_called) == 1
        assert len(wildcard_called) == 1

    @pytest.mark.asyncio
    async def test_handler_exception_logs_with_traceback(
        self, tracker: DownloadTracker
    ):
        """Test that handler exceptions are logged with full traceback."""

        def bad_handler(event):
            raise ValueError("Test exception in handler")

        tracker.on("tracker.queued", bad_handler)

        # Should not raise
        await tracker.track_queued("https://example.com/file.txt")

        # Logger.exception should have been called
        tracker._logger.exception.assert_called_once()
        call_args = tracker._logger.exception.call_args[0][0]
        assert "tracker.queued" in call_args
        assert "Error in event handler" in call_args

    @pytest.mark.asyncio
    async def test_tracker_logs_initialization_when_logger_provided(
        self, mock_logger, tracker: DownloadTracker
    ):
        """Test that tracker logs debug message on initialization."""
        # Create tracker with logger

        # Should have logged initialization
        tracker._logger.debug.assert_called_once_with("DownloadTracker initialized")
        assert tracker._logger is mock_logger

    @pytest.mark.asyncio
    async def test_handler_exception_does_not_break_state_tracking(
        self, tracker: DownloadTracker
    ):
        """Test that handler exceptions don't prevent state updates with
        default logger."""
        # Should not raise - uses default logger

        def bad_handler(event):
            raise ValueError("Test exception")

        tracker.on("tracker.queued", bad_handler)

        # Should not raise even though handler fails
        await tracker.track_queued("https://example.com/file.txt")

        # State should still be updated despite handler exception
        info = tracker.get_download_info("https://example.com/file.txt")
        assert info is not None
        assert info.status == DownloadStatus.QUEUED

    @pytest.mark.asyncio
    async def test_async_handler_exception_logs_with_traceback(
        self, tracker: DownloadTracker
    ):
        """Test that async handler exceptions are logged with full traceback."""

        async def bad_async_handler(event):
            raise ValueError("Test exception in async handler")

        tracker.on("tracker.queued", bad_async_handler)

        # Should not raise
        await tracker.track_queued("https://example.com/file.txt")

        # Logger.opt().error() should have been called for async handler
        tracker._logger.opt.assert_called_once()
        # Verify the exception info was passed to opt()
        opt_call_kwargs = tracker._logger.opt.call_args[1]
        assert "exception" in opt_call_kwargs
        exception_tuple = opt_call_kwargs["exception"]
        assert exception_tuple[0] == ValueError
        assert isinstance(exception_tuple[1], ValueError)

        # Verify error() was called on the returned opt() object
        tracker._logger.opt.return_value.error.assert_called_once()
        error_message = tracker._logger.opt.return_value.error.call_args[0][0]
        assert "async handler" in error_message
        assert "tracker.queued" in error_message

    @pytest.mark.asyncio
    async def test_mixed_sync_async_handler_exceptions_all_logged(
        self, tracker: DownloadTracker
    ):
        """Test that both sync and async handler exceptions are logged."""

        def bad_sync_handler(event):
            raise ValueError("Sync handler error")

        async def bad_async_handler(event):
            raise RuntimeError("Async handler error")

        tracker.on("tracker.queued", bad_sync_handler)
        tracker.on("tracker.queued", bad_async_handler)

        # Should not raise
        await tracker.track_queued("https://example.com/file.txt")

        # Sync handler should call logger.exception() once
        assert tracker._logger.exception.call_count == 1

        # Async handler should call logger.opt().error() once
        assert tracker._logger.opt.call_count == 1
        tracker._logger.opt.return_value.error.assert_called_once()

        # Verify the async exception info was passed to opt()
        opt_call_kwargs = tracker._logger.opt.call_args[1]
        assert "exception" in opt_call_kwargs
        exception_tuple = opt_call_kwargs["exception"]
        assert exception_tuple[0] == RuntimeError
        assert isinstance(exception_tuple[1], RuntimeError)
