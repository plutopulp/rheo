"""Tests for DownloadManager new download-centric API."""

import typing as t

import pytest

from rheo.domain.file_config import FileConfig
from rheo.downloads import DownloadManager, PriorityDownloadQueue

if t.TYPE_CHECKING:
    from loguru import Logger


class TestNewDownloadAPI:
    """Test new download-centric public API methods."""

    @pytest.mark.asyncio
    async def test_add_delegates_to_queue(
        self,
        mock_queue: PriorityDownloadQueue,
        make_file_config: t.Callable[..., FileConfig],
        mock_logger: "Logger",
    ):
        """Test that add() properly delegates to queue.add()."""
        manager = DownloadManager(queue=mock_queue, logger=mock_logger)

        file_configs = [make_file_config()]
        await manager.add(file_configs)

        # Verify delegation
        mock_queue.add.assert_called_once_with(file_configs)

    @pytest.mark.asyncio
    async def test_wait_until_complete_delegates_to_queue_join(
        self,
        mock_queue: PriorityDownloadQueue,
        mock_logger: "Logger",
    ):
        """Test that wait_until_complete() delegates to queue.join()."""
        manager = DownloadManager(queue=mock_queue, logger=mock_logger)

        await manager.wait_until_complete()

        # Verify delegation
        mock_queue.join.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_until_complete_with_timeout(
        self,
        mock_queue: PriorityDownloadQueue,
        mock_logger: "Logger",
        mocker,
    ):
        """Test that wait_until_complete() respects timeout parameter."""
        manager = DownloadManager(queue=mock_queue, logger=mock_logger)

        # Mock asyncio.wait_for to verify it's called with timeout
        mock_wait_for = mocker.patch("asyncio.wait_for", return_value=None)

        await manager.wait_until_complete(timeout=60.0)

        # Verify wait_for was called with queue.join() and timeout
        mock_wait_for.assert_called_once()
        call_args = mock_wait_for.call_args
        assert call_args[1]["timeout"] == 60.0

    @pytest.mark.asyncio
    async def test_multiple_add_wait_cycles_work(
        self,
        make_manager,
        make_file_configs,
        counting_download_mock,
    ):
        """Test that manager handles multiple add -> wait_until_complete cycles.

        Verifies that workers remain active after wait_until_complete() returns,
        allowing users to add more files and wait again without restarting.
        """
        download_mock = counting_download_mock(download_time=0.01)

        async with make_manager(
            max_workers=2, download_side_effect=download_mock
        ) as manager:
            # First batch
            batch1 = make_file_configs(count=2)
            await manager.add(batch1)
            await manager.wait_until_complete()
            assert download_mock.count["value"] == 2

            # Second batch - workers should still be running
            batch2 = make_file_configs(count=3)
            await manager.add(batch2)
            await manager.wait_until_complete()
            assert download_mock.count["value"] == 5

            # Third batch - still works!
            batch3 = make_file_configs(count=1)
            await manager.add(batch3)
            await manager.wait_until_complete()
            assert download_mock.count["value"] == 6

    @pytest.mark.asyncio
    async def test_cancel_all_delegates_to_pool_shutdown(
        self,
        mock_logger: "Logger",
        mock_worker_pool,
        mock_pool_factory,
    ):
        """Test that cancel_all() delegates to pool.shutdown()."""
        manager = DownloadManager(
            logger=mock_logger, worker_pool_factory=mock_pool_factory
        )

        await manager.cancel_all()

        # Verify delegation with default parameter
        mock_worker_pool.shutdown.assert_called_once_with(wait_for_current=False)

    @pytest.mark.asyncio
    async def test_cancel_all_with_wait_for_current(
        self,
        mock_logger: "Logger",
        mock_worker_pool,
        mock_pool_factory,
    ):
        """Test that cancel_all() respects wait_for_current parameter."""
        manager = DownloadManager(
            logger=mock_logger, worker_pool_factory=mock_pool_factory
        )

        await manager.cancel_all(wait_for_current=True)

        # Verify delegation with wait_for_current=True
        mock_worker_pool.shutdown.assert_called_once_with(wait_for_current=True)
