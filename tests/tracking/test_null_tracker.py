"""Tests for NullTracker implementation."""

import pytest

from async_download_manager.tracking import BaseTracker, NullTracker


@pytest.fixture
def null_tracker():
    """Provide a NullTracker instance for testing."""
    return NullTracker()


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
