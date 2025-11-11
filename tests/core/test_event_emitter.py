"""Tests for EventEmitter class."""

import pytest

from async_download_manager.events import EventEmitter


@pytest.fixture
def test_emitter(mock_logger):
    return EventEmitter(logger=mock_logger)


class TestEventEmitterSubscription:
    """Test event subscription and unsubscription."""

    def test_on_registers_handler(self, test_emitter):
        """Test that on() registers a handler for an event type."""
        handler_called = []

        def handler(event):
            handler_called.append(event)

        test_emitter.on("test.event", handler)

        assert "test.event" in test_emitter._handlers
        assert handler in test_emitter._handlers["test.event"]

    def test_multiple_handlers_can_subscribe(self, test_emitter):
        """Test that multiple handlers can subscribe to same event."""

        def handler1(event):
            pass

        def handler2(event):
            pass

        test_emitter.on("test.event", handler1)
        test_emitter.on("test.event", handler2)

        assert len(test_emitter._handlers["test.event"]) == 2
        assert handler1 in test_emitter._handlers["test.event"]
        assert handler2 in test_emitter._handlers["test.event"]

    def test_off_removes_handler(self, test_emitter):
        """Test that off() removes a handler."""

        def handler(event):
            pass

        test_emitter.on("test.event", handler)
        test_emitter.off("test.event", handler)

        assert handler not in test_emitter._handlers.get("test.event", [])

    def test_off_handles_non_existent_handler_gracefully(self, test_emitter):
        """Test that off() handles removing non-existent handler without error."""

        def handler(event):
            pass

        # Should not raise
        test_emitter.off("test.event", handler)

        # Verify warning was logged
        warning_msg = f"Handler {handler} not found for event test.event"
        test_emitter._logger.warning.assert_called_once_with(warning_msg)


class TestEventEmitterSyncHandlers:
    """Test synchronous handler execution."""

    @pytest.mark.asyncio
    async def test_sync_handler_executes(self, test_emitter):
        """Test that synchronous handlers execute successfully."""
        handler_called = []

        def handler(event):
            handler_called.append(event)

        test_emitter.on("test.event", handler)

        test_data = {"key": "value"}
        await test_emitter.emit("test.event", test_data)

        assert len(handler_called) == 1
        assert handler_called[0] == test_data

    @pytest.mark.asyncio
    async def test_multiple_sync_handlers_execute(self, test_emitter):
        """Test that all sync handlers execute."""
        handlers_called = []

        def handler1(event):
            handlers_called.append("handler1")

        def handler2(event):
            handlers_called.append("handler2")

        test_emitter.on("test.event", handler1)
        test_emitter.on("test.event", handler2)

        await test_emitter.emit("test.event", {})

        assert len(handlers_called) == 2
        assert "handler1" in handlers_called
        assert "handler2" in handlers_called

    @pytest.mark.asyncio
    async def test_sync_handler_exception_does_not_break_emission(self, test_emitter):
        """Test that exceptions in sync handlers don't prevent other handlers."""
        handlers_called = []

        def bad_handler(event):
            handlers_called.append("bad")
            raise ValueError("Handler error")

        def good_handler(event):
            handlers_called.append("good")

        test_emitter.on("test.event", bad_handler)
        test_emitter.on("test.event", good_handler)

        await test_emitter.emit("test.event", {})

        # Both handlers should have been called
        assert "bad" in handlers_called
        assert "good" in handlers_called

        # Exception should have been logged
        test_emitter._logger.exception.assert_called_once()


class TestEventEmitterAsyncHandlers:
    """Test asynchronous handler execution."""

    @pytest.mark.asyncio
    async def test_async_handler_executes(self, test_emitter):
        """Test that async handlers execute successfully."""
        handler_called = []

        async def handler(event):
            handler_called.append(event)

        test_emitter.on("test.event", handler)

        test_data = {"key": "value"}
        await test_emitter.emit("test.event", test_data)

        assert len(handler_called) == 1
        assert handler_called[0] == test_data

    @pytest.mark.asyncio
    async def test_multiple_async_handlers_execute(self, test_emitter):
        """Test that all async handlers execute."""
        handlers_called = []

        async def handler1(event):
            handlers_called.append("handler1")

        async def handler2(event):
            handlers_called.append("handler2")

        test_emitter.on("test.event", handler1)
        test_emitter.on("test.event", handler2)

        await test_emitter.emit("test.event", {})

        assert len(handlers_called) == 2
        assert "handler1" in handlers_called
        assert "handler2" in handlers_called

    @pytest.mark.asyncio
    async def test_async_handler_exception_logs_with_traceback(self, test_emitter):
        """Test that async handler exceptions are logged with traceback."""

        async def bad_handler(event):
            raise ValueError("Async handler error")

        test_emitter.on("test.event", bad_handler)

        await test_emitter.emit("test.event", {})

        # Logger.opt().error() should have been called
        test_emitter._logger.opt.assert_called_once()
        opt_call_kwargs = test_emitter._logger.opt.call_args[1]
        assert "exception" in opt_call_kwargs

    @pytest.mark.asyncio
    async def test_async_handler_exception_does_not_prevent_others(self, test_emitter):
        """Test that async handler exceptions don't prevent other handlers."""
        handlers_called = []

        async def bad_handler(event):
            handlers_called.append("bad")
            raise RuntimeError("Async error")

        async def good_handler(event):
            handlers_called.append("good")

        test_emitter.on("test.event", bad_handler)
        test_emitter.on("test.event", good_handler)

        await test_emitter.emit("test.event", {})

        # Both handlers should have been called
        assert "bad" in handlers_called
        assert "good" in handlers_called


class TestEventEmitterMixedHandlers:
    """Test mixed sync and async handler execution."""

    @pytest.mark.asyncio
    async def test_mixed_sync_and_async_handlers_execute(self, test_emitter):
        """Test that both sync and async handlers execute."""
        handlers_called = []

        def sync_handler(event):
            handlers_called.append("sync")

        async def async_handler(event):
            handlers_called.append("async")

        test_emitter.on("test.event", sync_handler)
        test_emitter.on("test.event", async_handler)

        await test_emitter.emit("test.event", {})

        assert len(handlers_called) == 2
        assert "sync" in handlers_called
        assert "async" in handlers_called

    @pytest.mark.asyncio
    async def test_mixed_handler_exceptions_all_logged(self, test_emitter):
        """Test that both sync and async exceptions are logged."""

        def bad_sync(event):
            raise ValueError("Sync error")

        async def bad_async(event):
            raise RuntimeError("Async error")

        test_emitter.on("test.event", bad_sync)
        test_emitter.on("test.event", bad_async)

        await test_emitter.emit("test.event", {})

        # Sync handler exception logged
        assert test_emitter._logger.exception.call_count == 1

        # Async handler exception logged
        assert test_emitter._logger.opt.call_count == 1


class TestEventEmitterEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_emit_with_no_handlers(self, test_emitter):
        """Test emitting event with no subscribers."""

        # Should not raise
        await test_emitter.emit("nonexistent.event", {})

    @pytest.mark.asyncio
    async def test_handler_can_modify_event_data(self, test_emitter):
        """Test that handlers receive event data correctly."""
        received_data = []

        def handler(event):
            received_data.append(event)

        test_emitter.on("test.event", handler)

        test_data = {"mutable": [1, 2, 3]}
        await test_emitter.emit("test.event", test_data)

        assert received_data[0] is test_data

    def test_emitter_without_logger_works(self):
        """Test that emitter works with default logger."""
        # Should not raise
        emitter = EventEmitter()

        def handler(event):
            pass

        emitter.on("test.event", handler)
        assert "test.event" in emitter._handlers
