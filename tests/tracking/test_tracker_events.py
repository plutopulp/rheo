"""Tests for DownloadTracker event subscription and emission."""

import pytest

from rheo.domain.downloads import DownloadStatus
from rheo.events import (
    DownloadCompletedEvent,
    DownloadFailedEvent,
    DownloadProgressEvent,
    DownloadQueuedEvent,
    DownloadStartedEvent,
)
from rheo.tracking import DownloadTracker


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
        assert events_received[0].download_id == "https://example.com/file.txt"
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
        assert events_received[0].download_id == "https://example.com/file.txt"
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
        assert events_received[0].download_id == "https://example.com/file.txt"
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
        assert events_received[0].download_id == "https://example.com/file.txt"
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
        assert events_received[0].download_id == "https://example.com/file.txt"
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
