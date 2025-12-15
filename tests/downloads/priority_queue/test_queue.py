"""Tests for PriorityDownloadQueue."""

import asyncio
import typing as t
from unittest.mock import Mock

import pytest

from rheo.domain.file_config import FileConfig
from rheo.downloads import PriorityDownloadQueue

if t.TYPE_CHECKING:
    from loguru import Logger


class TestPriorityDownloadQueueInitialisation:
    """Test PriorityDownloadQueue initialisation."""

    def test_init_with_default_logger(self) -> None:
        """Test queue initialisation without explicit logger."""
        queue = PriorityDownloadQueue()

        assert queue is not None
        assert queue.is_empty()

    def test_init_with_custom_logger(self, mock_logger: "Logger") -> None:
        """Test queue initialisation with custom logger."""
        queue = PriorityDownloadQueue(logger=mock_logger)

        assert queue is not None
        assert queue.is_empty()

    def test_init_with_injected_queue(self, mock_logger: "Logger") -> None:
        """Test queue initialisation with injected asyncio.PriorityQueue."""
        custom_queue = asyncio.PriorityQueue()
        queue = PriorityDownloadQueue(queue=custom_queue, logger=mock_logger)

        assert queue is not None
        assert queue._queue is custom_queue
        assert queue.is_empty()

    @pytest.mark.asyncio
    async def test_injected_queue_is_used(self, mock_logger: "Logger") -> None:
        """Test that operations use the injected queue."""
        custom_queue = asyncio.PriorityQueue()
        queue = PriorityDownloadQueue(queue=custom_queue, logger=mock_logger)

        file_config = FileConfig(url="https://example.com/test.txt", priority=1)
        await queue.add([file_config])

        # Verify the custom queue has items
        assert custom_queue.qsize() == 1
        assert not queue.is_empty()


class TestPriorityDownloadQueueAddition:
    """Test adding items to the queue."""

    @pytest.mark.asyncio
    async def test_add_single_file_config(self, mock_logger: "Logger") -> None:
        """Test adding a single file config to the queue."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_config = FileConfig(url="https://example.com/file.txt", priority=3)

        await queue.add([file_config])

        assert not queue.is_empty()
        assert queue.size() == 1

    @pytest.mark.asyncio
    async def test_add_multiple_file_configs(self, mock_logger: "Logger") -> None:
        """Test adding multiple file configs to the queue."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_configs = [
            FileConfig(url="https://example.com/file1.txt", priority=1),
            FileConfig(url="https://example.com/file2.txt", priority=2),
            FileConfig(url="https://example.com/file3.txt", priority=3),
        ]

        await queue.add(file_configs)

        assert not queue.is_empty()
        assert queue.size() == 3

    @pytest.mark.asyncio
    async def test_add_empty_list(self, mock_logger: "Logger") -> None:
        """Test adding an empty list does nothing."""
        queue = PriorityDownloadQueue(logger=mock_logger)

        await queue.add([])

        assert queue.is_empty()
        assert queue.size() == 0


class TestPriorityDownloadQueueRetrieval:
    """Test retrieving items from the queue."""

    @pytest.mark.asyncio
    async def test_get_next_returns_file_config(self, mock_logger: "Logger") -> None:
        """Test that get_next returns a FileConfig object."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_config = FileConfig(url="https://example.com/file.txt", priority=3)
        await queue.add([file_config])

        retrieved = await queue.get_next()

        assert isinstance(retrieved, FileConfig)
        assert str(retrieved.url) == "https://example.com/file.txt"
        assert retrieved.priority == 3

    @pytest.mark.asyncio
    async def test_get_next_respects_priority_ordering(
        self, mock_logger: "Logger"
    ) -> None:
        """Test that higher priority items are returned first."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_configs = [
            FileConfig(url="https://example.com/low.txt", priority=1),
            FileConfig(url="https://example.com/high.txt", priority=5),
            FileConfig(url="https://example.com/medium.txt", priority=3),
        ]
        await queue.add(file_configs)

        # Should get high priority first
        first = await queue.get_next()
        assert str(first.url) == "https://example.com/high.txt"
        assert first.priority == 5

        # Then medium priority
        second = await queue.get_next()
        assert str(second.url) == "https://example.com/medium.txt"
        assert second.priority == 3

        # Finally low priority
        third = await queue.get_next()
        assert str(third.url) == "https://example.com/low.txt"
        assert third.priority == 1

    @pytest.mark.asyncio
    async def test_get_next_with_same_priority(self, mock_logger: "Logger") -> None:
        """Test that items with same priority maintain FIFO order."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_configs = [
            FileConfig(url="https://example.com/first.txt", priority=3),
            FileConfig(url="https://example.com/second.txt", priority=3),
            FileConfig(url="https://example.com/third.txt", priority=3),
        ]
        await queue.add(file_configs)

        # Should maintain insertion order for same priority
        first = await queue.get_next()
        second = await queue.get_next()
        third = await queue.get_next()

        assert str(first.url) == "https://example.com/first.txt"
        assert str(second.url) == "https://example.com/second.txt"
        assert str(third.url) == "https://example.com/third.txt"


class TestPriorityDownloadQueueTaskManagement:
    """Test task completion tracking."""

    @pytest.mark.asyncio
    async def test_task_done_marks_task_complete(self, mock_logger: "Logger") -> None:
        """Test that task_done properly marks tasks as complete."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_config = FileConfig(url="https://example.com/file.txt")
        await queue.add([file_config])

        retrieved = await queue.get_next()
        queue.task_done(retrieved.id)

        # Should be able to join (wait for all tasks to complete)
        # This should complete immediately since we called task_done
        await asyncio.wait_for(queue.join(), timeout=1.0)

    @pytest.mark.asyncio
    async def test_task_done_with_untracked_id_raises_error(
        self, mock_logger: "Logger"
    ) -> None:
        """Calling task_done with an ID that was never queued should raise KeyError."""
        queue = PriorityDownloadQueue(logger=mock_logger)

        # Try to mark done an ID that was never queued
        with pytest.raises(KeyError):
            queue.task_done("never-queued-id")

    @pytest.mark.asyncio
    async def test_task_done_twice_raises_error(self, mock_logger: "Logger") -> None:
        """Calling task_done twice for the same ID should raise KeyError."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_config = FileConfig(url="https://example.com/file.txt")
        await queue.add([file_config])

        retrieved = await queue.get_next()
        queue.task_done(retrieved.id)

        # Calling task_done again with the same ID should raise KeyError
        with pytest.raises(KeyError):
            queue.task_done(retrieved.id)


class TestPriorityDownloadQueueStatus:
    """Test queue status methods."""

    def test_is_empty_on_new_queue(self, mock_logger: "Logger") -> None:
        """Test that new queue is empty."""
        queue = PriorityDownloadQueue(logger=mock_logger)

        assert queue.is_empty()

    @pytest.mark.asyncio
    async def test_is_empty_after_adding_items(self, mock_logger: "Logger") -> None:
        """Test that queue is not empty after adding items."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_config = FileConfig(url="https://example.com/file.txt")

        await queue.add([file_config])

        assert not queue.is_empty()

    @pytest.mark.asyncio
    async def test_is_empty_after_retrieving_all_items(
        self, mock_logger: "Logger"
    ) -> None:
        """Test that queue is empty after retrieving all items."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_config = FileConfig(url="https://example.com/file.txt")
        await queue.add([file_config])

        await queue.get_next()

        assert queue.is_empty()

    def test_size_on_new_queue(self, mock_logger: "Logger") -> None:
        """Test that new queue has size 0."""
        queue = PriorityDownloadQueue(logger=mock_logger)

        assert queue.size() == 0

    @pytest.mark.asyncio
    async def test_size_after_adding_items(self, mock_logger: "Logger") -> None:
        """Test that size reflects number of items added."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        size = 5
        file_configs = [
            FileConfig(url=f"https://example.com/file{i}.txt") for i in range(size)
        ]

        await queue.add(file_configs)

        assert queue.size() == size

    @pytest.mark.asyncio
    async def test_size_decreases_after_retrieval(self, mock_logger: "Logger") -> None:
        """Test that size decreases as items are retrieved."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        size = 3
        file_configs = [
            FileConfig(url=f"https://example.com/file{i}.txt") for i in range(size)
        ]
        await queue.add(file_configs)

        for i in range(size):
            assert queue.size() == size - i
            await queue.get_next()
        assert queue.is_empty()


class TestQueueDeduplication:
    """Test queue deduplication based on download_id."""

    @pytest.mark.asyncio
    async def test_duplicate_detection_same_url_same_destination(
        self, mock_logger: "Logger"
    ) -> None:
        """Adding same URL+destination twice should skip the duplicate."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_config = FileConfig(
            url="https://example.com/file.txt", destination_subdir="downloads"
        )

        # Add same config twice
        await queue.add([file_config])
        await queue.add([file_config])

        # Should only have one item (duplicate was skipped)
        assert queue.size() == 1
        item = await queue.get_next()
        assert item.id == file_config.id

    @pytest.mark.asyncio
    async def test_allows_same_url_different_destinations(
        self, mock_logger: "Logger"
    ) -> None:
        """Same URL to different destinations should both be queued."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        config1 = FileConfig(
            url="https://example.com/file.txt", destination_subdir="dir1"
        )
        config2 = FileConfig(
            url="https://example.com/file.txt", destination_subdir="dir2"
        )

        await queue.add([config1, config2])

        # Should have both items (different download_ids)
        assert queue.size() == 2
        retrieved_1 = await queue.get_next()
        retrieved_2 = await queue.get_next()
        assert retrieved_1.id == config1.id
        assert retrieved_2.id == config2.id
        # For good measure, check they are different
        assert retrieved_1.id != retrieved_2.id

    @pytest.mark.asyncio
    async def test_task_done_removes_from_duplicate_tracking(
        self, mock_logger: "Logger"
    ) -> None:
        """Calling task_done should allow re-adding the same download."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_config = FileConfig(url="https://example.com/file.txt")

        # Add config
        await queue.add([file_config])
        assert queue.size() == 1

        # Try to add duplicate (should be skipped)
        await queue.add([file_config])
        assert queue.size() == 1

        # Process the item
        retrieved = await queue.get_next()
        queue.task_done(retrieved.id)

        # Now we should be able to add it again
        await queue.add([file_config])
        assert queue.size() == 1

    @pytest.mark.asyncio
    async def test_multiple_duplicates_all_skipped(self, mock_logger: "Logger") -> None:
        """Multiple attempts to add same download should all be skipped."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_config = FileConfig(url="https://example.com/file.txt")

        # Add same config multiple times
        for _ in range(4):
            await queue.add([file_config])

        # Should only have one item (duplicate was skipped)
        assert queue.size() == 1
        item = await queue.get_next()
        assert item.id == file_config.id

    @pytest.mark.asyncio
    async def test_duplicate_logs_warning(self, mock_logger: Mock) -> None:
        """Duplicate downloads should log a warning message."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_config = FileConfig(url="https://example.com/file.txt")

        # Add once (should succeed)
        await queue.add([file_config])

        # Add duplicate (should log warning)
        await queue.add([file_config])

        # Verify warning was logged
        mock_logger.warning.assert_called_once()
        expected_warning_msg = (
            f"Skipping duplicate download: {file_config.url} "
            f"(already queued with ID {file_config.id}...)"
        )
        warning_msg = mock_logger.warning.call_args[0][0]
        assert expected_warning_msg == warning_msg


class TestQueuePendingCount:
    """Test pending_count property."""

    @pytest.mark.asyncio
    async def test_pending_count_initially_zero(self, mock_logger: "Logger") -> None:
        """Empty queue should have zero pending count."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        assert queue.pending_count == 0

    @pytest.mark.asyncio
    async def test_pending_count_increases_on_add(self, mock_logger: "Logger") -> None:
        """Adding items should increase pending count."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        configs = [FileConfig(url=f"https://example.com/file{i}.txt") for i in range(3)]
        await queue.add(configs)
        assert queue.pending_count == 3

    @pytest.mark.asyncio
    async def test_pending_count_decreases_on_task_done(
        self, mock_logger: "Logger"
    ) -> None:
        """Completing tasks should decrease pending count."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        config = FileConfig(url="https://example.com/file.txt")
        await queue.add([config])
        assert queue.pending_count == 1

        await queue.get_next()
        queue.task_done(config.id)
        assert queue.pending_count == 0

    @pytest.mark.asyncio
    async def test_pending_includes_in_progress_downloads(
        self, mock_logger: "Logger"
    ) -> None:
        """Pending count includes items being downloaded (retrieved but not done)."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        config = FileConfig(url="https://example.com/file.txt")
        await queue.add([config])

        await queue.get_next()  # Item retrieved, download "in progress"
        # Still pending because task_done not called yet
        assert queue.pending_count == 1


class TestPriorityDownloadQueueEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_get_next_blocks_on_empty_queue(self, mock_logger: "Logger") -> None:
        """Test that get_next blocks when queue is empty."""
        queue = PriorityDownloadQueue(logger=mock_logger)

        # This should timeout because queue is empty
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(queue.get_next(), timeout=0.1)

    @pytest.mark.asyncio
    async def test_multiple_adds_maintain_priority(self, mock_logger: "Logger") -> None:
        """Test that multiple add calls maintain overall priority ordering."""
        queue = PriorityDownloadQueue(logger=mock_logger)

        # Add low priority items
        await queue.add([FileConfig(url="https://example.com/low.txt", priority=1)])

        # Add high priority items
        await queue.add([FileConfig(url="https://example.com/high.txt", priority=5)])

        # Add medium priority items
        await queue.add([FileConfig(url="https://example.com/medium.txt", priority=3)])

        # Should still respect priority across all adds
        first = await queue.get_next()
        assert first.priority == 5

        second = await queue.get_next()
        assert second.priority == 3

        third = await queue.get_next()
        assert third.priority == 1
