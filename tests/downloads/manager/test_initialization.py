"""Tests for DownloadManager context manager and initialization."""

import typing as t
from pathlib import Path

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses
from pytest_mock import MockerFixture

from rheo.domain.downloads import DownloadStats
from rheo.domain.exceptions import ManagerNotInitializedError, PendingDownloadsError
from rheo.domain.file_config import FileConfig, FileExistsStrategy
from rheo.downloads import (
    DownloadManager,
    DownloadWorker,
    PriorityDownloadQueue,
)
from rheo.events import BaseEmitter, EventEmitter, NullEmitter
from rheo.events.models import (
    DownloadCompletedEvent,
    DownloadQueuedEvent,
    DownloadStartedEvent,
)
from rheo.tracking import BaseTracker

if t.TYPE_CHECKING:
    from loguru import Logger


@pytest.fixture
def mock_tracker(mocker: MockerFixture, mock_emitter: BaseEmitter) -> BaseTracker:
    """Provide fully mocked DownloadTracker with spec and mock emitter."""
    mock = mocker.Mock(spec=BaseTracker)
    mock.emitter = mock_emitter
    return mock


class TestDownloadManagerInitialization:
    """Test DownloadManager initialization and basic setup."""

    def test_init_with_defaults(self, mock_logger):
        """Test manager initialization with default parameters."""
        manager = DownloadManager(logger=mock_logger)

        # Should have defaults set
        assert manager.timeout is None
        assert manager.max_concurrent == 3
        assert isinstance(manager.queue, PriorityDownloadQueue)
        assert manager._client is None
        assert (
            manager._worker_factory is DownloadWorker
        )  # Factory defaults to DownloadWorker
        assert not manager._owns_client

    def test_init_with_custom_params(self, mock_logger):
        """Test manager initialization with custom parameters."""
        custom_queue = PriorityDownloadQueue(logger=mock_logger)

        manager = DownloadManager(
            timeout=30.0, max_concurrent=5, queue=custom_queue, logger=mock_logger
        )

        assert manager.timeout == 30.0
        assert manager.max_concurrent == 5
        assert manager.queue is custom_queue

    def test_manager_creates_shared_emitter(self, mock_logger: "Logger"):
        """Manager should create a shared EventEmitter."""
        manager = DownloadManager(logger=mock_logger)

        assert manager._emitter is not None
        assert isinstance(manager._emitter, EventEmitter)
        assert manager.queue.emitter is manager._emitter

    def test_custom_emitter_is_used(
        self,
        mock_logger: "Logger",
        mock_emitter: BaseEmitter,
        mock_aio_client: ClientSession,
    ):
        """Custom emitter should be used when provided."""
        manager = DownloadManager(logger=mock_logger, emitter=mock_emitter)

        assert manager._emitter is mock_emitter
        assert manager.queue.emitter is mock_emitter
        worker = manager._worker_pool.create_worker(mock_aio_client)
        assert worker.emitter is mock_emitter

    def test_get_download_info_delegates_to_tracker(
        self, mock_logger, mock_tracker: BaseTracker
    ):
        """get_download_info should delegate to tracker."""
        manager = DownloadManager(logger=mock_logger, tracker=mock_tracker)
        mock_tracker.get_download_info.return_value = "test-info"

        result = manager.get_download_info("test-id")
        mock_tracker.get_download_info.assert_called_once_with("test-id")

        assert result == "test-info"

    def test_get_download_info_returns_none_when_not_found(
        self, mock_logger, mock_tracker: BaseTracker
    ):
        """get_download_info should return None when download not found."""
        manager = DownloadManager(logger=mock_logger, tracker=mock_tracker)
        mock_tracker.get_download_info.return_value = None

        assert manager.get_download_info("nonexistent") is None
        mock_tracker.get_download_info.assert_called_once_with("nonexistent")

    def test_stats_delegates_to_tracker(self, mock_logger, mock_tracker: BaseTracker):
        """stats property should delegate to tracker.get_stats()."""
        manager = DownloadManager(logger=mock_logger, tracker=mock_tracker)
        stats = DownloadStats(
            total=1, queued=1, in_progress=1, completed=1, failed=0, completed_bytes=100
        )
        mock_tracker.get_stats.return_value = stats

        result = manager.stats
        assert result == stats
        mock_tracker.get_stats.assert_called_once()

    def test_init_with_provided_client(self, aio_client, mock_logger):
        """Test manager initialization with provided client."""
        manager = DownloadManager(client=aio_client, logger=mock_logger)

        assert manager._client is aio_client
        assert not manager._owns_client  # We didn't create it

    def test_init_with_provided_worker_factory(self, aio_client, mock_logger):
        """Test manager initialization with provided worker factory."""

        def custom_factory(client, logger, emitter, **kwargs):
            return DownloadWorker(client, logger, emitter, **kwargs)

        manager = DownloadManager(worker_factory=custom_factory, logger=mock_logger)

        assert manager._worker_factory is custom_factory


class TestDownloadManagerEvents:
    """Test DownloadManager event subscription helpers."""

    @pytest.mark.asyncio
    async def test_on_subscribes_to_emitter(self, mock_logger: "Logger") -> None:
        """manager.on() should subscribe handler to emitter."""
        manager = DownloadManager(logger=mock_logger)
        events: list[dict[str, t.Any]] = []

        manager.on("download.completed", lambda e: events.append(e))

        event_data = DownloadCompletedEvent(
            download_id="test-id",
            url="https://example.com/file.txt",
            total_bytes=100,
            destination_path="test-path",
        )

        await manager._emitter.emit("download.completed", event_data)

        assert events == [event_data]

    @pytest.mark.asyncio
    async def test_subscription_unsubscribe(self, mock_logger: "Logger") -> None:
        """subscription.unsubscribe() should stop receiving events."""
        manager = DownloadManager(logger=mock_logger)
        events: list[dict[str, t.Any]] = []

        def handler(e: t.Any) -> None:
            events.append(e)

        subscription = manager.on("download.completed", handler)
        subscription.unsubscribe()
        event_data = DownloadCompletedEvent(
            download_id="test-id",
            url="https://example.com/file.txt",
            total_bytes=100,
            destination_path="test-path",
        )
        await manager._emitter.emit("download.completed", event_data)

        assert events == []

    @pytest.mark.asyncio
    async def test_wildcard_subscription(self, mock_logger: "Logger") -> None:
        """manager.on('*', ...) should receive all events."""
        manager = DownloadManager(logger=mock_logger)
        events: list[dict[str, t.Any]] = []

        manager.on("*", lambda e: events.append(e))
        started_event = DownloadStartedEvent(
            download_id="test-id", url="https://example.com/file.txt", total_bytes=100
        )
        completed_event = DownloadCompletedEvent(
            download_id="test-id",
            url="https://example.com/file.txt",
            total_bytes=100,
            destination_path="test-path",
        )
        queued_event = DownloadQueuedEvent(
            download_id="test-id", url="https://example.com/file.txt", priority=1
        )
        await manager._emitter.emit("download.queued", queued_event)
        await manager._emitter.emit("download.started", started_event)
        await manager._emitter.emit("download.completed", completed_event)

        assert events == [queued_event, started_event, completed_event]

    @pytest.mark.asyncio
    async def test_worker_factory_exception_propagates(
        self, mock_aio_client, mock_logger
    ):
        """Test that exceptions from worker factory are propagated."""

        def broken_factory(client, logger, emitter, **kwargs):
            raise ValueError("Factory initialization failed!")

        manager = DownloadManager(
            client=mock_aio_client,
            worker_factory=broken_factory,
            logger=mock_logger,
        )

        # Exception should propagate during context entry (start_workers)
        with pytest.raises(ValueError, match="Factory initialization failed"):
            async with manager:
                pass

    @pytest.mark.asyncio
    async def test_manager_handles_duplicate_downloads(self, mock_logger):
        """Test that adding same URL+destination twice only queues one download.

        Verifies that the manager properly delegates to the queue's deduplication
        logic, preventing duplicate downloads from being queued.
        """
        manager = DownloadManager(logger=mock_logger)
        file_config = FileConfig(url="https://example.com/file.txt")

        # Add same config twice
        await manager.add([file_config])
        await manager.add([file_config])

        # Should only have one item in queue (duplicate was skipped)
        assert manager.queue.size() == 1


class TestDownloadManagerContextManager:
    """Test DownloadManager context manager behavior."""

    @pytest.mark.asyncio
    async def test_context_manager_creates_client(self, mock_logger):
        """Test that context manager creates client when none provided."""
        async with DownloadManager(logger=mock_logger) as ctx:
            # Should have created a client
            assert ctx._client is not None
            assert isinstance(ctx._client, ClientSession)
            assert ctx._owns_client

            # Workers are created per-task, not during context entry
            assert ctx._worker_factory is DownloadWorker

    @pytest.mark.asyncio
    async def test_context_manager_uses_provided_client(self, aio_client, mock_logger):
        """Test that context manager uses provided client."""

        async with DownloadManager(client=aio_client, logger=mock_logger) as ctx:
            # Should use provided client
            assert ctx._client is aio_client
            assert not ctx._owns_client

    @pytest.mark.asyncio
    async def test_context_manager_uses_provided_worker_factory(
        self, aio_client, mock_logger
    ):
        """Test that context manager uses provided worker factory."""

        def custom_factory(client, logger, emitter, **kwargs):
            return DownloadWorker(client, logger, emitter, **kwargs)

        async with DownloadManager(
            client=aio_client, worker_factory=custom_factory, logger=mock_logger
        ) as ctx:
            # Should use provided factory
            assert ctx._worker_factory is custom_factory
            assert ctx._client is aio_client

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self, mock_logger):
        """Test that context manager properly cleans up resources."""

        async with DownloadManager(logger=mock_logger) as ctx:
            client = ctx._client
            assert not client.closed

        # Client should be closed after exiting context
        assert client.closed

    @pytest.mark.asyncio
    async def test_context_manager_no_cleanup_external_client(
        self, aio_client, mock_logger
    ):
        """Test that external clients are not closed on exit."""

        async with DownloadManager(client=aio_client, logger=mock_logger):
            assert not aio_client.closed

        # External client should remain open
        assert not aio_client.closed

    @pytest.mark.asyncio
    async def test_context_manager_creates_download_directory(
        self, mock_logger, tmp_path
    ):
        """Test that context manager creates download directory if it doesn't exist."""
        download_dir = tmp_path / "nested" / "download" / "path"
        assert not download_dir.exists()

        async with DownloadManager(
            download_dir=download_dir, logger=mock_logger
        ) as manager:
            # Directory should be created
            assert download_dir.exists()
            assert download_dir.is_dir()
            assert manager.download_dir == download_dir

    @pytest.mark.asyncio
    async def test_context_manager_handles_existing_directory(
        self, mock_logger, tmp_path
    ):
        """Test that context manager handles existing directories gracefully."""
        download_dir = tmp_path / "existing"
        download_dir.mkdir()
        assert download_dir.exists()

        async with DownloadManager(
            download_dir=download_dir, logger=mock_logger
        ) as manager:
            # Directory should still exist and be usable
            assert download_dir.exists()
            assert download_dir.is_dir()
            assert manager.download_dir == download_dir


class TestDownloadManagerProperties:
    """Test DownloadManager property access and error handling."""

    def test_client_property_before_context(self, mock_logger):
        """Test accessing client property before entering context manager."""
        manager = DownloadManager(logger=mock_logger)

        with pytest.raises(ManagerNotInitializedError):
            _ = manager.client

    def test_client_property_with_provided_client(self, aio_client, mock_logger):
        """Test accessing client property when client was provided."""
        manager = DownloadManager(client=aio_client, logger=mock_logger)

        # Should work even before context manager
        assert manager.client is aio_client

    @pytest.mark.asyncio
    async def test_client_property_after_context_entry(self, mock_logger):
        """Test that client property works correctly after entering context."""

        async with DownloadManager(logger=mock_logger) as manager:
            # Client property should work
            client = manager.client

            assert isinstance(client, ClientSession)

    @pytest.mark.asyncio
    async def test_is_active_false_before_open(self, mock_logger, tmp_path):
        """Test that is_active is False before open() is called."""
        manager = DownloadManager(logger=mock_logger, download_dir=tmp_path)

        assert manager.is_active is False

    @pytest.mark.asyncio
    async def test_is_active_true_after_open(
        self, mock_logger, mock_worker_pool, mock_pool_factory, tmp_path
    ):
        """Test that is_active is True after open() is called."""
        manager = DownloadManager(
            logger=mock_logger,
            worker_pool_factory=mock_pool_factory,
            download_dir=tmp_path,
        )

        await manager.open()

        assert manager.is_active is True

        await manager.close()

    @pytest.mark.asyncio
    async def test_is_active_false_after_close(
        self, mock_logger, mock_worker_pool, mock_pool_factory, tmp_path
    ):
        """Test that is_active is False after close() is called."""
        manager = DownloadManager(
            logger=mock_logger,
            worker_pool_factory=mock_pool_factory,
            download_dir=tmp_path,
        )

        await manager.open()
        assert manager.is_active is True

        await manager.close()
        assert manager.is_active is False

    @pytest.mark.asyncio
    async def test_is_active_lifecycle_with_context_manager(
        self, make_manager, make_file_configs, counting_download_mock
    ):
        """Test is_active property throughout context manager lifecycle."""
        download_mock = counting_download_mock(download_time=0.01)
        manager = make_manager(max_concurrent=1, download_side_effect=download_mock)

        # Before entering context
        assert manager.is_active is False

        async with manager:
            # Inside context - should be active
            assert manager.is_active is True

            # Still active while processing
            await manager.add(make_file_configs(count=1))
            assert manager.is_active is True

            await manager.wait_until_complete()
            assert manager.is_active is True

        assert manager.is_active is False


class TestDownloadManagerPendingDownloadsCheck:
    """Test PendingDownloadsError behavior on context manager exit."""

    @pytest.mark.asyncio
    async def test_raises_error_when_exiting_with_pending_downloads(
        self, mock_logger: "Logger"
    ) -> None:
        """Should raise PendingDownloadsError if exiting with work left."""
        with pytest.raises(PendingDownloadsError) as exc_info:
            async with DownloadManager(logger=mock_logger) as manager:
                await manager.add([FileConfig(url="https://example.com/file.txt")])
                # Exit without wait_until_complete() or close()

        assert exc_info.value.pending_count == 1

    @pytest.mark.asyncio
    async def test_no_error_when_wait_until_complete_called(
        self, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """Should not raise if wait_until_complete() was called."""
        with aioresponses() as mock:
            mock.get("https://example.com/file.txt", body=b"content")

            async with DownloadManager(
                logger=mock_logger, download_dir=tmp_path
            ) as manager:
                await manager.add([FileConfig(url="https://example.com/file.txt")])
                await manager.wait_until_complete()
        # No exception raised

    @pytest.mark.asyncio
    async def test_no_error_when_close_called_explicitly(
        self, mock_logger: "Logger"
    ) -> None:
        """Should not raise if close() was called explicitly."""
        async with DownloadManager(logger=mock_logger) as manager:
            await manager.add([FileConfig(url="https://example.com/file.txt")])
            await manager.close()  # Explicit cancellation
        # No exception raised

    @pytest.mark.asyncio
    async def test_does_not_mask_existing_exception(
        self, mock_logger: "Logger"
    ) -> None:
        """Should not raise PendingDownloadsError if already handling exception."""
        with pytest.raises(ValueError, match="original error"):
            async with DownloadManager(logger=mock_logger) as manager:
                await manager.add([FileConfig(url="https://example.com/file.txt")])
                raise ValueError("original error")
        # ValueError propagates, not PendingDownloadsError

    @pytest.mark.asyncio
    async def test_resources_cleaned_up_before_raising(
        self, mock_logger: "Logger"
    ) -> None:
        """Should close resources even when raising PendingDownloadsError."""
        manager = DownloadManager(logger=mock_logger)
        try:
            async with manager:
                await manager.add([FileConfig(url="https://example.com/file.txt")])
        except PendingDownloadsError:
            pass

        assert not manager.is_active  # Pool stopped
        assert manager._client is None or manager._client.closed  # Client cleaned up


class TestDownloadManagerFileExistsStrategy:
    """Test DownloadManager file_exists_strategy configuration."""

    def test_default_strategy_is_skip(self, mock_logger: "Logger") -> None:
        """Manager should default to SKIP strategy."""
        manager = DownloadManager(logger=mock_logger)
        assert manager.file_exists_strategy == FileExistsStrategy.SKIP

    def test_custom_strategy_can_be_set(self, mock_logger: "Logger") -> None:
        """Manager should accept custom strategy."""
        manager = DownloadManager(
            logger=mock_logger,
            file_exists_strategy=FileExistsStrategy.OVERWRITE,
        )
        assert manager.file_exists_strategy == FileExistsStrategy.OVERWRITE


class TestDownloadManagerQueueEmitter:
    """Test queue emitter wiring in DownloadManager."""

    def test_default_queue_uses_event_emitter(self, mock_logger: "Logger") -> None:
        """Manager's default queue should use EventEmitter for automatic tracking."""

        manager = DownloadManager(logger=mock_logger)
        assert isinstance(manager.queue.emitter, EventEmitter)

    def test_custom_queue_with_null_emitter_disables_events(
        self, mock_logger: "Logger"
    ) -> None:
        """Passing queue with NullEmitter disables queue events."""

        # Create queue with NullEmitter to disable events
        custom_queue = PriorityDownloadQueue(
            logger=mock_logger
        )  # Defaults to NullEmitter

        manager = DownloadManager(logger=mock_logger, queue=custom_queue)

        assert isinstance(manager.queue.emitter, NullEmitter)

    def test_custom_queue_with_emitter_is_used(self, mock_logger: "Logger") -> None:
        """Manager should use custom queue's emitter."""

        # Create queue with custom emitter
        custom_emitter = EventEmitter(mock_logger)
        custom_queue = PriorityDownloadQueue(logger=mock_logger, emitter=custom_emitter)

        manager = DownloadManager(logger=mock_logger, queue=custom_queue)

        # Queue's emitter should be used
        assert manager.queue.emitter is custom_emitter

    @pytest.mark.asyncio
    async def test_queue_wired_to_tracker_on_open(
        self, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """Manager.open() should wire queue events to tracker."""

        custom_emitter = EventEmitter(mock_logger)
        manager = DownloadManager(
            logger=mock_logger,
            download_dir=tmp_path,
            queue=PriorityDownloadQueue(logger=mock_logger, emitter=custom_emitter),
        )

        await manager.open()

        # Queue's emitter should have download.queued handler
        assert "download.queued" in custom_emitter._handlers
        assert len(custom_emitter._handlers["download.queued"]) == 1

        await manager.close()
