"""Tests for Subscription class."""

import typing as t

from rheo.events.base import BaseEmitter
from rheo.events.subscription import Subscription


class TestSubscription:
    """Test Subscription unsubscribe behaviour."""

    def test_unsubscribe_calls_emitter_off(self, mock_emitter: BaseEmitter) -> None:
        """unsubscribe() should call emitter.off() with original event/handler."""
        handler: t.Callable[[t.Any], None] = lambda e: None

        sub = Subscription(mock_emitter, "download.completed", handler)
        sub.unsubscribe()

        mock_emitter.off.assert_called_once_with("download.completed", handler)

    def test_unsubscribe_is_idempotent(self, mock_emitter: BaseEmitter) -> None:
        """Multiple unsubscribe() calls should only call off() once."""
        handler: t.Callable[[t.Any], None] = lambda e: None

        sub = Subscription(mock_emitter, "download.completed", handler)
        sub.unsubscribe()
        sub.unsubscribe()
        sub.unsubscribe()

        assert mock_emitter.off.call_count == 1

    def test_is_active_reflects_state(self, mock_emitter: BaseEmitter) -> None:
        """is_active should be True initially, False after unsubscribe."""
        handler: t.Callable[[t.Any], None] = lambda e: None

        sub = Subscription(mock_emitter, "download.completed", handler)

        assert sub.is_active is True
        sub.unsubscribe()
        assert sub.is_active is False
