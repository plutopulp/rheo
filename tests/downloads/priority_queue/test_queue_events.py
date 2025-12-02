"""Tests for queue event emission."""

import typing as t

import pytest

from rheo.domain.file_config import FileConfig
from rheo.downloads import PriorityDownloadQueue

from .conftest import MakeQueueFactory

if t.TYPE_CHECKING:
    from loguru import Logger


class TestQueueEventEmission:
    """Test queue event emission."""

    @pytest.mark.asyncio
    async def test_emits_queued_event_on_add(
        self, make_queue: MakeQueueFactory
    ) -> None:
        """Adding item should emit download.queued event."""
        queue, events = make_queue(capture_events=["download.queued"])
        config = FileConfig(url="https://example.com/file.txt", priority=5)

        await queue.add([config])

        assert len(events["download.queued"]) == 1
        event = events["download.queued"][0]
        assert event.download_id == config.id
        assert event.url == str(config.url)
        assert event.priority == 5
        assert event.event_type == "download.queued"

    @pytest.mark.asyncio
    async def test_emits_event_for_each_item(
        self, make_queue: MakeQueueFactory
    ) -> None:
        """Should emit one event per queued item."""
        queue, events = make_queue(capture_events=["download.queued"])
        configs = [FileConfig(url=f"https://example.com/file{i}.txt") for i in range(3)]

        await queue.add(configs)

        assert len(events["download.queued"]) == 3
        # Verify each event has correct download_id
        for i, event in enumerate(events["download.queued"]):
            assert event.download_id == configs[i].id

    @pytest.mark.asyncio
    async def test_no_event_for_duplicate(self, make_queue: MakeQueueFactory) -> None:
        """Duplicate items should not emit events."""
        queue, events = make_queue(capture_events=["download.queued"])
        config = FileConfig(url="https://example.com/file.txt")

        await queue.add([config])
        await queue.add([config])  # Duplicate

        assert len(events["download.queued"]) == 1  # Only first add emits

    @pytest.mark.asyncio
    async def test_no_emitter_uses_null_emitter(self, mock_logger: "Logger") -> None:
        """Queue without emitter should use NullEmitter and not fail."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        config = FileConfig(url="https://example.com/file.txt")

        # Should not raise - NullEmitter silently discards events
        await queue.add([config])

        assert queue.size() == 1
