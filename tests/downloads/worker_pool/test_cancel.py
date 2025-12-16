"""Tests for selective download cancellation."""

import asyncio
import typing as t

import pytest

from rheo.domain.cancellation import CancelledFrom
from rheo.domain.downloads import DownloadStatus
from rheo.domain.file_config import FileConfig
from rheo.downloads.worker_pool.pool import WorkerPool
from rheo.tracking import DownloadTracker

if t.TYPE_CHECKING:
    from tests.downloads.conftest import WorkerFactoryMaker


class TestTaskTracking:
    """Test download task tracking in pool."""

    @pytest.mark.asyncio
    async def test_active_download_tasks_empty_initially(
        self,
        make_worker_pool: t.Callable[..., WorkerPool],
    ) -> None:
        """Pool should have no active downloads before start."""
        pool = make_worker_pool()
        assert pool.active_download_tasks == {}

    @pytest.mark.asyncio
    async def test_active_download_task_lifecycle(
        self,
        mock_aio_client,
        make_worker_pool: t.Callable[..., WorkerPool],
        real_priority_queue,
        slow_download_mock,
        make_mock_worker_factory: "WorkerFactoryMaker",
    ) -> None:
        """Task should be tracked during download and cleared after completion."""
        download = slow_download_mock(download_time=0.2)
        worker_factory = make_mock_worker_factory(download_side_effect=download)
        pool = make_worker_pool(
            worker_factory=worker_factory,
            queue=real_priority_queue,
        )
        file_config = FileConfig(url="http://example.com/file.txt")
        await real_priority_queue.add([file_config])

        await pool.start(mock_aio_client)
        await asyncio.sleep(0.05)  # Let worker pick up item

        # Task should be tracked while in progress
        assert file_config.id in pool.active_download_tasks

        # Wait for completion
        await real_priority_queue.join()

        # Task should be cleared after completion
        assert file_config.id not in pool.active_download_tasks

        await pool.shutdown(wait_for_current=False)


class TestCooperativeCancellation:
    """Test cooperative cancellation for queued downloads."""

    @pytest.mark.asyncio
    async def test_cancelled_queued_download_skipped(
        self,
        mock_aio_client,
        make_worker_pool: t.Callable[..., WorkerPool],
        real_priority_queue,
        tracker: DownloadTracker,
    ) -> None:
        """Download in _cancelled_ids should be skipped when dequeued."""
        pool = make_worker_pool(queue=real_priority_queue)
        file_config = FileConfig(url="http://example.com/file.txt")
        await real_priority_queue.add([file_config])

        # Mark as cancelled before worker picks it up
        pool._cancelled_ids.add(file_config.id)

        await pool.start(mock_aio_client)
        await real_priority_queue.join()

        # Should be marked cancelled in tracker
        info = tracker.get_download_info(file_config.id)
        assert info is not None
        assert info.status == DownloadStatus.CANCELLED

        await pool.shutdown(wait_for_current=False)

    @pytest.mark.asyncio
    async def test_cancelled_queued_emits_event_with_queued_state(
        self,
        mock_aio_client,
        make_worker_pool: t.Callable[..., WorkerPool],
        real_priority_queue,
    ) -> None:
        """Cancelled queued download should emit event with cancelled_from=QUEUED."""
        pool = make_worker_pool(queue=real_priority_queue)
        file_config = FileConfig(url="http://example.com/file.txt")
        await real_priority_queue.add([file_config])

        events: list = []
        pool._emitter.on("download.cancelled", lambda e: events.append(e))

        pool._cancelled_ids.add(file_config.id)

        await pool.start(mock_aio_client)
        await real_priority_queue.join()

        assert len(events) == 1
        assert events[0].cancelled_from == CancelledFrom.QUEUED

        await pool.shutdown(wait_for_current=False)

    @pytest.mark.asyncio
    async def test_cancelled_id_removed_after_processing(
        self,
        mock_aio_client,
        make_worker_pool: t.Callable[..., WorkerPool],
        real_priority_queue,
    ) -> None:
        """Cancelled ID should be removed from set after being processed."""
        pool = make_worker_pool(queue=real_priority_queue)
        file_config = FileConfig(url="http://example.com/file.txt")
        await real_priority_queue.add([file_config])

        pool._cancelled_ids.add(file_config.id)

        await pool.start(mock_aio_client)
        await real_priority_queue.join()

        assert file_config.id not in pool._cancelled_ids

        await pool.shutdown(wait_for_current=False)
