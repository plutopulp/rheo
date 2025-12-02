"""Fixtures for priority queue tests."""

import typing as t

import pytest

from rheo.downloads import PriorityDownloadQueue
from rheo.events import EventEmitter

if t.TYPE_CHECKING:
    from loguru import Logger


# Type alias for the make_queue factory fixture
MakeQueueFactory = t.Callable[..., tuple[PriorityDownloadQueue, dict[str, list[t.Any]]]]


@pytest.fixture
def event_emitter(mock_logger: "Logger") -> EventEmitter:
    """EventEmitter with mock logger to suppress log output in tests."""
    return EventEmitter(mock_logger)


@pytest.fixture
def make_queue(mock_logger: "Logger", event_emitter: EventEmitter) -> MakeQueueFactory:
    """Factory for creating queue with optional event capture.

    Returns:
        Factory function that returns (queue, captured_events_dict)

    Example:
        queue, events = make_queue(capture_events=["download.queued"])
        await queue.add([config])
        assert len(events["download.queued"]) == 1
    """

    def _make_queue(
        capture_events: list[str] | None = None,
    ) -> tuple[PriorityDownloadQueue, dict[str, list[t.Any]]]:
        captured: dict[str, list[t.Any]] = {}

        if capture_events:
            for event_type in capture_events:
                captured[event_type] = []
                # Capture event_type in closure to avoid late binding
                event_emitter.on(
                    event_type, lambda e, et=event_type: captured[et].append(e)
                )

        queue = PriorityDownloadQueue(logger=mock_logger, emitter=event_emitter)
        return queue, captured

    return _make_queue
