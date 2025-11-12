"""Tests for PriorityDownloadQueue."""

import asyncio

import pytest

from async_download_manager.domain.file_config import FileConfig
from async_download_manager.downloads import PriorityDownloadQueue


class TestPriorityDownloadQueueInitialization:
    """Test PriorityDownloadQueue initialization."""

    def test_init_with_default_logger(self):
        """Test queue initialization without explicit logger."""
        queue = PriorityDownloadQueue()

        assert queue is not None
        assert queue.is_empty()

    def test_init_with_custom_logger(self, mock_logger):
        """Test queue initialization with custom logger."""
        queue = PriorityDownloadQueue(logger=mock_logger)

        assert queue is not None
        assert queue.is_empty()

    def test_init_with_injected_queue(self, mock_logger):
        """Test queue initialization with injected asyncio.PriorityQueue."""
        custom_queue = asyncio.PriorityQueue()
        queue = PriorityDownloadQueue(queue=custom_queue, logger=mock_logger)

        assert queue is not None
        assert queue._queue is custom_queue
        assert queue.is_empty()

    @pytest.mark.asyncio
    async def test_injected_queue_is_used(self, mock_logger):
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
    async def test_add_single_file_config(self, mock_logger):
        """Test adding a single file config to the queue."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_config = FileConfig(url="https://example.com/file.txt", priority=3)

        await queue.add([file_config])

        assert not queue.is_empty()
        assert queue.size() == 1

    @pytest.mark.asyncio
    async def test_add_multiple_file_configs(self, mock_logger):
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
    async def test_add_empty_list(self, mock_logger):
        """Test adding an empty list does nothing."""
        queue = PriorityDownloadQueue(logger=mock_logger)

        await queue.add([])

        assert queue.is_empty()
        assert queue.size() == 0


class TestPriorityDownloadQueueRetrieval:
    """Test retrieving items from the queue."""

    @pytest.mark.asyncio
    async def test_get_next_returns_file_config(self, mock_logger):
        """Test that get_next returns a FileConfig object."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_config = FileConfig(url="https://example.com/file.txt", priority=3)
        await queue.add([file_config])

        retrieved = await queue.get_next()

        assert isinstance(retrieved, FileConfig)
        assert retrieved.url == "https://example.com/file.txt"
        assert retrieved.priority == 3

    @pytest.mark.asyncio
    async def test_get_next_respects_priority_ordering(self, mock_logger):
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
        assert first.url == "https://example.com/high.txt"
        assert first.priority == 5

        # Then medium priority
        second = await queue.get_next()
        assert second.url == "https://example.com/medium.txt"
        assert second.priority == 3

        # Finally low priority
        third = await queue.get_next()
        assert third.url == "https://example.com/low.txt"
        assert third.priority == 1

    @pytest.mark.asyncio
    async def test_get_next_with_same_priority(self, mock_logger):
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

        assert first.url == "https://example.com/first.txt"
        assert second.url == "https://example.com/second.txt"
        assert third.url == "https://example.com/third.txt"


class TestPriorityDownloadQueueTaskManagement:
    """Test task completion tracking."""

    @pytest.mark.asyncio
    async def test_task_done_marks_task_complete(self, mock_logger):
        """Test that task_done properly marks tasks as complete."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_config = FileConfig(url="https://example.com/file.txt")
        await queue.add([file_config])

        await queue.get_next()
        queue.task_done()

        # Should be able to join (wait for all tasks to complete)
        # This should complete immediately since we called task_done
        await asyncio.wait_for(queue.join(), timeout=1.0)


class TestPriorityDownloadQueueStatus:
    """Test queue status methods."""

    def test_is_empty_on_new_queue(self, mock_logger):
        """Test that new queue is empty."""
        queue = PriorityDownloadQueue(logger=mock_logger)

        assert queue.is_empty()

    @pytest.mark.asyncio
    async def test_is_empty_after_adding_items(self, mock_logger):
        """Test that queue is not empty after adding items."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_config = FileConfig(url="https://example.com/file.txt")

        await queue.add([file_config])

        assert not queue.is_empty()

    @pytest.mark.asyncio
    async def test_is_empty_after_retrieving_all_items(self, mock_logger):
        """Test that queue is empty after retrieving all items."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        file_config = FileConfig(url="https://example.com/file.txt")
        await queue.add([file_config])

        await queue.get_next()

        assert queue.is_empty()

    def test_size_on_new_queue(self, mock_logger):
        """Test that new queue has size 0."""
        queue = PriorityDownloadQueue(logger=mock_logger)

        assert queue.size() == 0

    @pytest.mark.asyncio
    async def test_size_after_adding_items(self, mock_logger):
        """Test that size reflects number of items added."""
        queue = PriorityDownloadQueue(logger=mock_logger)
        size = 5
        file_configs = [
            FileConfig(url=f"https://example.com/file{i}.txt") for i in range(size)
        ]

        await queue.add(file_configs)

        assert queue.size() == size

    @pytest.mark.asyncio
    async def test_size_decreases_after_retrieval(self, mock_logger):
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


class TestPriorityDownloadQueueEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_get_next_blocks_on_empty_queue(self, mock_logger):
        """Test that get_next blocks when queue is empty."""
        queue = PriorityDownloadQueue(logger=mock_logger)

        # This should timeout because queue is empty
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(queue.get_next(), timeout=0.1)

    @pytest.mark.asyncio
    async def test_multiple_adds_maintain_priority(self, mock_logger):
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
