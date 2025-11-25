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


class TestManualLifecycle:
    """Test manual lifecycle management with open() and close()."""

    @pytest.mark.asyncio
    async def test_open_initialises_manager(
        self,
        mock_logger: "Logger",
        mock_worker_pool,
        mock_pool_factory,
        tmp_path,
    ):
        """Test that open() creates client and starts workers."""
        manager = DownloadManager(
            logger=mock_logger,
            worker_pool_factory=mock_pool_factory,
            download_dir=tmp_path,
        )

        await manager.open()

        # Should have created client
        assert manager._client is not None
        assert manager._owns_client is True

        # Should have started workers
        mock_worker_pool.start.assert_called_once()

        # Cleanup
        await manager.close()

    @pytest.mark.asyncio
    async def test_close_cleans_up(
        self,
        mock_logger: "Logger",
        mock_worker_pool,
        mock_pool_factory,
        tmp_path,
    ):
        """Test that close() stops workers and closes client."""
        manager = DownloadManager(
            logger=mock_logger,
            worker_pool_factory=mock_pool_factory,
            download_dir=tmp_path,
        )

        await manager.open()
        client = manager._client

        await manager.close()

        # Should have stopped workers
        mock_worker_pool.stop.assert_called_once()

        # Should have closed client (if we owned it)
        assert client.closed

    @pytest.mark.asyncio
    async def test_close_with_wait_for_current(
        self,
        mock_logger: "Logger",
        mock_worker_pool,
        mock_pool_factory,
        tmp_path,
    ):
        """Test that close() respects wait_for_current parameter."""
        manager = DownloadManager(
            logger=mock_logger,
            worker_pool_factory=mock_pool_factory,
            download_dir=tmp_path,
        )

        await manager.open()
        await manager.close(wait_for_current=True)

        # Should call shutdown instead of stop when wait_for_current=True
        mock_worker_pool.shutdown.assert_called_once_with(wait_for_current=True)

    @pytest.mark.asyncio
    async def test_manual_lifecycle_without_context_manager(
        self,
        make_manager,
        make_file_configs,
        counting_download_mock,
    ):
        """Test using manager with manual open/close instead of context manager."""
        download_mock = counting_download_mock(download_time=0.01)
        manager = make_manager(max_workers=2, download_side_effect=download_mock)

        # Use manual lifecycle
        await manager.open()

        try:
            # Add and wait for downloads
            batch1 = make_file_configs(count=2)
            await manager.add(batch1)
            await manager.wait_until_complete()
            assert download_mock.count["value"] == 2

            # Can add more
            batch2 = make_file_configs(count=1)
            await manager.add(batch2)
            await manager.wait_until_complete()
            assert download_mock.count["value"] == 3
        finally:
            await manager.close()


class TestIsActiveProperty:
    """Test is_active property for manager state."""

    @pytest.mark.asyncio
    async def test_is_active_false_before_open(self, mock_logger: "Logger", tmp_path):
        """Test that is_active is False before open() is called."""
        manager = DownloadManager(logger=mock_logger, download_dir=tmp_path)

        assert manager.is_active is False

    @pytest.mark.asyncio
    async def test_is_active_true_after_open(
        self, mock_logger: "Logger", mock_worker_pool, mock_pool_factory, tmp_path
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
        self, mock_logger: "Logger", mock_worker_pool, mock_pool_factory, tmp_path
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
        manager = make_manager(max_workers=1, download_side_effect=download_mock)

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
