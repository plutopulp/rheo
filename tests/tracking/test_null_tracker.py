"""Tests for NullTracker implementation."""

import pytest

from rheo.tracking import BaseTracker, NullTracker


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
    async def test_all_methods_do_nothing_without_error(
        self, null_tracker: NullTracker
    ):
        """Test that all tracker methods can be called without errors."""
        # Should not raise any exceptions
        await null_tracker._track_queued("id", "url", priority=1)
        await null_tracker._track_started("id", "url", total_bytes=100)
        await null_tracker._track_progress("id", "url", 50, 100)
        await null_tracker._track_completed("id", "url", 100, "/path")
        await null_tracker._track_failed("id", "url", Exception("test"))
        await null_tracker._track_skipped("id", "url", "reason", "/path")
        await null_tracker._track_cancelled("id", "url")
