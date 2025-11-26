"""Tests for DownloadTracker event handler execution behavior."""

import asyncio

import pytest

from rheo.domain.downloads import DownloadStatus
from rheo.tracking import DownloadTracker


class TestDownloadTrackerEventHandlers:
    """Test handler execution behavior."""

    @pytest.mark.asyncio
    async def test_sync_handler_executes_successfully(self, tracker: DownloadTracker):
        """Test that synchronous handlers execute successfully."""
        handler_called = []

        def sync_handler(event):
            handler_called.append("sync")

        tracker.on("tracker.queued", sync_handler)

        await tracker.track_queued(
            "https://example.com/file.txt", "https://example.com/file.txt"
        )

        assert handler_called == ["sync"]

    @pytest.mark.asyncio
    async def test_async_handler_executes_successfully(self, tracker: DownloadTracker):
        """Test that asynchronous handlers execute successfully."""
        handler_called = []

        async def async_handler(event):
            await asyncio.sleep(0.001)  # Simulate async work
            handler_called.append("async")

        tracker.on("tracker.queued", async_handler)

        await tracker.track_queued(
            "https://example.com/file.txt", "https://example.com/file.txt"
        )

        assert handler_called == ["async"]

    @pytest.mark.asyncio
    async def test_multiple_handlers_all_execute(self, tracker: DownloadTracker):
        """Test that all subscribed handlers execute."""
        handlers_called = []

        tracker.on("tracker.started", lambda e: handlers_called.append("handler1"))
        tracker.on("tracker.started", lambda e: handlers_called.append("handler2"))
        tracker.on("tracker.started", lambda e: handlers_called.append("handler3"))

        url = "https://example.com/file.txt"
        await tracker.track_started(url, url)

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
        await tracker.track_queued(
            "https://example.com/file.txt", "https://example.com/file.txt"
        )

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

        await tracker.track_queued(
            "https://example.com/file.txt", "https://example.com/file.txt"
        )

        # Both handlers should have been called
        assert "bad" in handlers_called
        assert "good" in handlers_called

    @pytest.mark.asyncio
    async def test_wildcard_handler_receives_all_events(self, tracker: DownloadTracker):
        """Test that wildcard '*' handler receives all event types."""
        events_received = []

        tracker.on("*", lambda e: events_received.append(e.event_type))

        await tracker.track_queued(
            "https://example.com/file.txt", "https://example.com/file.txt"
        )
        url = "https://example.com/file.txt"
        await tracker.track_started(url, url)
        await tracker.track_progress(url, url, 100)
        await tracker.track_completed(url, url, 100)

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

        await tracker.track_queued(
            "https://example.com/file.txt", "https://example.com/file.txt"
        )

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
        await tracker.track_queued(
            "https://example.com/file.txt", "https://example.com/file.txt"
        )

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
        await tracker.track_queued(
            "https://example.com/file.txt", "https://example.com/file.txt"
        )

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
        await tracker.track_queued(
            "https://example.com/file.txt", "https://example.com/file.txt"
        )

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
        await tracker.track_queued(
            "https://example.com/file.txt", "https://example.com/file.txt"
        )

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
