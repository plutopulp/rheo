"""Tests for null object implementations of tracker and emitter."""

from typing import Any

import pytest

from async_download_manager.events import BaseEmitter
from async_download_manager.tracking import BaseTracker


class TestNullTracker:
    """Test NullTracker implementation."""

    @pytest.mark.asyncio
    async def test_null_tracker_implements_base_tracker(self, null_tracker):
        """Test that NullTracker inherits from BaseTracker."""
        assert isinstance(null_tracker, BaseTracker)

    @pytest.mark.asyncio
    async def test_all_methods_do_nothing_without_error(self, null_tracker):
        """Test that all tracker methods can be called without errors."""
        # Should not raise any exceptions
        await null_tracker.track_queued("url", priority=1)
        await null_tracker.track_started("url", total_bytes=100)
        await null_tracker.track_progress("url", 50, 100)
        await null_tracker.track_completed("url", 100, "/path")
        await null_tracker.track_failed("url", Exception("test"))


class TestNullEmitter:
    """Test NullEmitter implementation."""

    @pytest.mark.asyncio
    async def test_null_emitter_implements_base_emitter(self, null_emitter):
        """Test that NullEmitter inherits from BaseEmitter."""
        assert isinstance(null_emitter, BaseEmitter)

    @pytest.mark.asyncio
    async def test_all_methods_do_nothing_without_error(self, null_emitter):
        """Test that all emitter methods can be called without errors."""

        def handler(_: Any) -> None:
            pass

        # Should not raise any exceptions
        null_emitter.on("event", handler)
        await null_emitter.emit("event", {"data": "test"})
        null_emitter.off("event", handler)
