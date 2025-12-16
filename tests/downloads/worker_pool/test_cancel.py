"""Tests for selective download cancellation."""

import asyncio
import typing as t

import pytest

from rheo.domain.file_config import FileConfig
from rheo.downloads.worker_pool.pool import WorkerPool

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
