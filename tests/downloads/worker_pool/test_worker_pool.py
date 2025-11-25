"""Tests for the worker pool lifecycle and shutdown semantics."""

import asyncio
import typing as t
from pathlib import Path

import aiohttp
import pytest

from rheo.domain.exceptions import WorkerPoolAlreadyStartedError
from rheo.domain.file_config import FileConfig
from rheo.downloads.queue import PriorityDownloadQueue
from rheo.downloads.worker.worker import DownloadWorker
from rheo.downloads.worker_pool.pool import WorkerPool
from rheo.tracking.tracker import DownloadTracker
from tests.downloads.conftest import WorkerFactoryMaker

if t.TYPE_CHECKING:
    from loguru import Logger


@pytest.fixture
def make_worker_pool(
    tracker: "DownloadTracker",
    real_priority_queue: "PriorityDownloadQueue",
    mock_logger: "Logger",
    tmp_path: "Path",
) -> t.Callable[..., WorkerPool]:
    """Factory fixture to create WorkerPool instances with sensible defaults."""

    def _make_pool(
        worker_factory=None,
        max_workers: int = 1,
        queue=None,
        event_wiring=None,
    ) -> WorkerPool:
        return WorkerPool(
            queue=queue or real_priority_queue,
            worker_factory=worker_factory or DownloadWorker,
            tracker=tracker,
            logger=mock_logger,
            download_dir=tmp_path,
            max_workers=max_workers,
            event_wiring=event_wiring,
        )

    return _make_pool


class TestWorkerPoolInitialization:
    """Test WorkerPool initialization and basic setup."""

    def test_init_with_defaults(self, make_worker_pool: t.Callable[..., WorkerPool]):
        """Test pool initialization with default parameters."""
        pool = make_worker_pool()

        assert not pool.is_running
        assert len(pool.active_tasks) == 0

    def test_init_with_custom_max_workers(
        self, make_worker_pool: t.Callable[..., WorkerPool]
    ):
        """Test pool initialization with custom max_workers."""
        pool = make_worker_pool(max_workers=5)

        assert not pool.is_running
        assert len(pool.active_tasks) == 0


class TestWorkerPoolLifecycle:
    """Test worker pool start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_sets_running_state(
        self,
        mock_aio_client: aiohttp.ClientSession,
        make_worker_pool: t.Callable[..., WorkerPool],
    ):
        """Pool should set is_running to True after start."""
        pool = make_worker_pool()

        await pool.start(mock_aio_client)
        assert pool.is_running

        await pool.stop()

    @pytest.mark.asyncio
    async def test_start_creates_worker_tasks(
        self,
        mock_aio_client: aiohttp.ClientSession,
        make_worker_pool: t.Callable[..., WorkerPool],
    ):
        """Pool should create max_workers tasks on start."""
        pool = make_worker_pool(max_workers=3)

        await pool.start(mock_aio_client)
        await asyncio.sleep(0.01)

        assert len(pool.active_tasks) == 3
        await pool.stop()

    @pytest.mark.asyncio
    async def test_start_twice_raises_error(
        self,
        mock_aio_client: aiohttp.ClientSession,
        make_worker_pool: t.Callable[..., WorkerPool],
    ):
        """Starting an already-running pool should raise
        WorkerPoolAlreadyStartedError."""
        pool = make_worker_pool()

        await pool.start(mock_aio_client)

        with pytest.raises(WorkerPoolAlreadyStartedError, match="already started"):
            await pool.start(mock_aio_client)

        await pool.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_running_state(
        self,
        mock_aio_client: aiohttp.ClientSession,
        make_worker_pool: t.Callable[..., WorkerPool],
    ):
        """Pool should set is_running to False after stop."""
        pool = make_worker_pool()

        await pool.start(mock_aio_client)
        assert pool.is_running

        await pool.stop()
        assert not pool.is_running

    @pytest.mark.asyncio
    async def test_stop_clears_tasks(
        self,
        mock_aio_client: aiohttp.ClientSession,
        make_worker_pool: t.Callable[..., WorkerPool],
    ):
        """Pool should clear task list after stop."""
        pool = make_worker_pool(max_workers=3)

        await pool.start(mock_aio_client)
        assert len(pool.active_tasks) == 3

        await pool.stop()
        assert len(pool.active_tasks) == 0


class TestWorkerPoolIsolation:
    """Test that workers are properly isolated from each other."""

    @pytest.mark.asyncio
    async def test_start_creates_isolated_workers(
        self,
        mock_aio_client: aiohttp.ClientSession,
        isolated_mock_worker_factory: t.Any,
        make_worker_pool: t.Callable[..., WorkerPool],
    ):
        """Each worker task should have its own worker + emitter instance."""
        pool = make_worker_pool(
            worker_factory=isolated_mock_worker_factory,
            max_workers=3,
        )

        await pool.start(mock_aio_client)
        await asyncio.sleep(0.01)

        created_workers = isolated_mock_worker_factory.created_mocks
        assert len(created_workers) == 3
        emitter_ids = {id(worker.emitter) for worker in created_workers}
        assert len(emitter_ids) == 3, "Expected unique emitter per worker"

        await pool.stop()


class TestWorkerPoolShutdown:
    """Test shutdown behavior with graceful vs immediate modes."""

    @pytest.mark.asyncio
    async def test_shutdown_waits_for_inflight_download(
        self,
        mock_aio_client: "aiohttp.ClientSession",
        make_worker_pool: t.Callable[..., WorkerPool],
        slow_download_mock: t.Callable[[float], t.Any],
        make_file_config: t.Callable[..., "FileConfig"],
        real_priority_queue: "PriorityDownloadQueue",
        make_mock_worker_factory: WorkerFactoryMaker,
    ):
        """wait_for_current=True should allow active downloads to complete."""
        await real_priority_queue.add([make_file_config()])
        download = slow_download_mock(download_time=0.05)

        worker_factory = make_mock_worker_factory(download_side_effect=download)
        pool = make_worker_pool(worker_factory=worker_factory)

        await pool.start(mock_aio_client)
        await asyncio.wait_for(download.started.wait(), timeout=1.0)

        await pool.shutdown(wait_for_current=True)

        assert download.completed.is_set()
        assert not pool.is_running

    @pytest.mark.asyncio
    async def test_shutdown_without_wait_cancels_download(
        self,
        mock_aio_client: "aiohttp.ClientSession",
        make_worker_pool: t.Callable[..., WorkerPool],
        slow_download_mock: t.Callable[[float], t.Any],
        make_file_config: t.Callable[..., "FileConfig"],
        real_priority_queue: "PriorityDownloadQueue",
        make_mock_worker_factory: WorkerFactoryMaker,
    ):
        """wait_for_current=False should cancel in-flight downloads."""
        await real_priority_queue.add([make_file_config()])
        download = slow_download_mock(download_time=100.0)  # Long running

        worker_factory = make_mock_worker_factory(download_side_effect=download)
        pool = make_worker_pool(worker_factory=worker_factory)

        await pool.start(mock_aio_client)
        await asyncio.wait_for(download.started.wait(), timeout=1.0)

        await pool.shutdown(wait_for_current=False)

        assert not download.completed.is_set()
        assert not pool.is_running

    @pytest.mark.asyncio
    async def test_request_shutdown_requeues_item_before_download(
        self,
        mock_aio_client: "aiohttp.ClientSession",
        make_worker_pool: t.Callable[..., WorkerPool],
        make_file_config: t.Callable[..., "FileConfig"],
        real_priority_queue: "PriorityDownloadQueue",
        make_mock_worker_factory: WorkerFactoryMaker,
    ):
        """If shutdown is requested before download starts, item is re-queued."""
        file_config = make_file_config()
        await real_priority_queue.add([file_config])

        worker_factory = make_mock_worker_factory()
        pool = make_worker_pool(worker_factory=worker_factory)

        await pool.start(mock_aio_client)
        pool.request_shutdown()

        await asyncio.sleep(0.1)
        await pool.stop()

        assert not real_priority_queue.is_empty()

    @pytest.mark.asyncio
    async def test_shutdown_with_empty_queue(
        self,
        mock_aio_client: aiohttp.ClientSession,
        make_worker_pool: t.Callable[..., WorkerPool],
    ):
        """No items in queue, call shutdown(), verify clean exit."""
        pool = make_worker_pool(max_workers=2)

        await pool.start(mock_aio_client)
        await pool.shutdown(wait_for_current=True)

        assert len(pool.active_tasks) == 0
        assert not pool.is_running

    @pytest.mark.asyncio
    async def test_repeated_shutdown_calls_are_idempotent(
        self,
        mock_aio_client: aiohttp.ClientSession,
        make_worker_pool: t.Callable[..., WorkerPool],
    ):
        """Call shutdown() multiple times, verify no errors."""
        pool = make_worker_pool()

        await pool.start(mock_aio_client)

        # Call shutdown multiple times
        for _ in range(3):
            await pool.shutdown(wait_for_current=True)

        assert not pool.is_running
        assert len(pool.active_tasks) == 0

    @pytest.mark.asyncio
    async def test_request_shutdown_is_idempotent(
        self,
        mock_aio_client: aiohttp.ClientSession,
        make_worker_pool: t.Callable[..., WorkerPool],
    ):
        """request_shutdown() can be called multiple times safely."""
        pool = make_worker_pool()

        await pool.start(mock_aio_client)

        # Call multiple times
        pool.request_shutdown()
        pool.request_shutdown()
        pool.request_shutdown()

        await pool.stop()
        assert not pool.is_running

    @pytest.mark.asyncio
    async def test_shutdown_logs_appropriately(
        self,
        mock_aio_client: aiohttp.ClientSession,
        make_worker_pool: t.Callable[..., WorkerPool],
        mock_logger: t.Any,
    ):
        """Verify workers log 'shutting down gracefully' on clean exit."""
        pool = make_worker_pool()

        await pool.start(mock_aio_client)
        await pool.shutdown(wait_for_current=True)

        log_messages = [call.args[0] for call in mock_logger.debug.call_args_list]
        assert any("Worker shutting down gracefully" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_shutdown_race_condition_prevents_download(
        self,
        mock_aio_client: aiohttp.ClientSession,
        make_worker_pool: t.Callable[..., WorkerPool],
        make_file_config: t.Callable[..., FileConfig],
        real_priority_queue: PriorityDownloadQueue,
        make_mock_worker_factory: WorkerFactoryMaker,
        mocker: t.Any,
    ) -> None:
        """Shutdown triggered between queue retrieval and download start should prevent
        download.

        Simulates a race condition where shutdown is requested exactly after an item is
        retrieved from the queue but before the worker checks the shutdown flag.
        """
        file_config = make_file_config()

        # Track if download was called
        download_called = asyncio.Event()

        async def mock_download_tracking(*args, **kwargs):
            download_called.set()

        # Create pool with tracking worker
        worker_factory = make_mock_worker_factory(
            download_side_effect=mock_download_tracking
        )
        pool = make_worker_pool(worker_factory=worker_factory)

        # Patch get_destination_path to trigger shutdown during path resolution
        # This happens inside _process_queue after get_next() but before the
        # shutdown check
        original_method = type(file_config).get_destination_path

        def patched_get_destination_path(self, download_dir, create_dirs=True):
            pool.request_shutdown()
            return original_method(self, download_dir, create_dirs)

        mocker.patch.object(
            type(file_config),
            "get_destination_path",
            patched_get_destination_path,
        )

        await real_priority_queue.add([file_config])
        await pool.start(mock_aio_client)

        # Wait briefly for processing
        await asyncio.sleep(0.1)
        await pool.stop()

        # Download should NOT have been called because shutdown was triggered
        # before the worker's final check
        assert not download_called.is_set()

    @pytest.mark.asyncio
    async def test_shutdown_handles_failed_tasks(
        self,
        mock_aio_client: aiohttp.ClientSession,
        make_worker_pool: t.Callable[..., WorkerPool],
    ):
        """Shutdown should complete cleanly even if worker tasks raised exceptions."""
        pool = make_worker_pool()

        # Manually inject a failing task into the pool's task list
        async def failing_task():
            raise ValueError("Task blew up")

        task = asyncio.create_task(failing_task())
        pool._worker_tasks.append(task)
        pool._is_running = True  # Simulate running

        # Shutdown should wait for it and handle exception
        await pool.shutdown(wait_for_current=True)

        assert len(pool.active_tasks) == 0
        assert not pool.is_running
        # Task should be done (and raised)
        assert task.done()
        with pytest.raises(ValueError):
            await task


class TestWorkerPoolQueueProcessing:
    """Test successful queue processing and error handling."""

    @pytest.mark.asyncio
    async def test_process_queue_consumes_items(
        self,
        mock_aio_client: aiohttp.ClientSession,
        make_worker_pool: t.Callable[..., WorkerPool],
        make_file_config: t.Callable[..., FileConfig],
        real_priority_queue: PriorityDownloadQueue,
        make_mock_worker_factory: WorkerFactoryMaker,
    ):
        """Worker should consume items and call task_done()."""
        # Setup worker that just completes immediately
        worker_factory = make_mock_worker_factory()
        pool = make_worker_pool(worker_factory=worker_factory)

        # Add item
        await real_priority_queue.add([make_file_config()])
        assert real_priority_queue.size() == 1

        await pool.start(mock_aio_client)

        # Wait for queue to be empty and processed
        # If task_done() is not called, join() will hang
        await asyncio.wait_for(real_priority_queue.join(), timeout=1.0)

        await pool.stop()
        assert real_priority_queue.is_empty()

    @pytest.mark.asyncio
    async def test_multiple_workers_process_concurrently(
        self,
        mock_aio_client: aiohttp.ClientSession,
        make_worker_pool: t.Callable[..., WorkerPool],
        make_file_configs: t.Callable[..., list[FileConfig]],
        real_priority_queue: PriorityDownloadQueue,
        make_mock_worker_factory: WorkerFactoryMaker,
    ):
        """Multiple workers should process items in parallel."""

        # Setup worker that sleeps
        async def slow_download(*args, **kwargs):
            await asyncio.sleep(0.1)

        worker_factory = make_mock_worker_factory(download_side_effect=slow_download)
        # 3 workers
        pool = make_worker_pool(max_workers=3, worker_factory=worker_factory)

        # Add 3 items
        items = make_file_configs(count=3)
        await real_priority_queue.add(items)

        start_time = asyncio.get_running_loop().time()
        await pool.start(mock_aio_client)

        await asyncio.wait_for(real_priority_queue.join(), timeout=1.0)
        end_time = asyncio.get_running_loop().time()

        await pool.stop()

        # Should take roughly 0.1s, definitely less than 0.25s (if serial would be 0.3s)
        duration = end_time - start_time
        assert duration < 0.25, f"Expected parallel processing, took {duration:.2f}s"

    @pytest.mark.asyncio
    async def test_worker_continues_after_download_error(
        self,
        mock_aio_client: aiohttp.ClientSession,
        make_worker_pool: t.Callable[..., WorkerPool],
        make_file_configs: t.Callable[..., list[FileConfig]],
        real_priority_queue: PriorityDownloadQueue,
        make_mock_worker_factory: WorkerFactoryMaker,
        mock_logger: t.Any,
    ):
        """Worker loop should continue processing items after a download exception."""
        # Setup worker that fails on first call, succeeds on others
        call_count = 0

        async def failing_download(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("Download failed!")
            # Success
            return None

        worker_factory = make_mock_worker_factory(download_side_effect=failing_download)
        pool = make_worker_pool(worker_factory=worker_factory)

        # Add 2 items
        items = make_file_configs(count=2)
        await real_priority_queue.add(items)

        await pool.start(mock_aio_client)

        # Should process both items (one fail, one success)
        await asyncio.wait_for(real_priority_queue.join(), timeout=1.0)

        await pool.stop()

        # Verify error was logged
        log_messages = [call.args[0] for call in mock_logger.error.call_args_list]
        assert any("Download failed" in msg for msg in log_messages)
