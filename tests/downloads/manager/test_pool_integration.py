"""Tests for DownloadManager integration with WorkerPool."""

import typing as t
from unittest.mock import Mock

import aiohttp
import pytest

from rheo.downloads.manager import DownloadManager
from rheo.downloads.worker_pool.factory import WorkerPoolFactory

if t.TYPE_CHECKING:
    from loguru import Logger


class TestDownloadManagerPoolIntegration:
    """Test that DownloadManager correctly delegates to WorkerPool."""

    def test_init_creates_default_pool(self, mock_logger: "Logger"):
        """Manager should create a default WorkerPool if none provided."""
        manager = DownloadManager(logger=mock_logger)

        assert manager._worker_pool is not None

    def test_init_uses_injected_pool_factory(
        self,
        mock_logger: "Logger",
        mock_worker_pool: Mock,
        mock_pool_factory: WorkerPoolFactory,
    ):
        """Manager should use injected worker pool factory."""
        manager = DownloadManager(
            logger=mock_logger, worker_pool_factory=mock_pool_factory
        )

        assert manager._worker_pool is mock_worker_pool

    @pytest.mark.asyncio
    async def test_start_workers_delegates_to_pool(
        self,
        mock_logger: "Logger",
        mock_worker_pool: Mock,
        mock_pool_factory: WorkerPoolFactory,
        mock_aio_client: aiohttp.ClientSession,
        tmp_path,
    ):
        """open() should create client and call pool.start() with correct client."""
        manager = DownloadManager(
            logger=mock_logger,
            worker_pool_factory=mock_pool_factory,
            client=mock_aio_client,
            download_dir=tmp_path,
        )

        await manager.open()

        # Should have started workers with the client
        mock_worker_pool.start.assert_called_once_with(mock_aio_client)

        # Cleanup
        await manager.close()

    @pytest.mark.asyncio
    async def test_close_delegates_to_pool_shutdown(
        self,
        mock_logger: "Logger",
        mock_worker_pool: Mock,
        mock_pool_factory: WorkerPoolFactory,
        tmp_path,
    ):
        """close() should call pool.shutdown() and clean up client."""
        manager = DownloadManager(
            logger=mock_logger,
            worker_pool_factory=mock_pool_factory,
            download_dir=tmp_path,
        )

        await manager.open()
        client = manager._client

        await manager.close()

        # Should have called shutdown with default wait_for_current=False
        mock_worker_pool.shutdown.assert_called_once_with(wait_for_current=False)

        # Should have closed client (if we owned it)
        assert client.closed

    @pytest.mark.asyncio
    async def test_close_with_wait_for_current(
        self,
        mock_logger: "Logger",
        mock_worker_pool: Mock,
        mock_pool_factory: WorkerPoolFactory,
        tmp_path,
    ):
        """close() should call shutdown when wait_for_current=True."""
        manager = DownloadManager(
            logger=mock_logger,
            worker_pool_factory=mock_pool_factory,
            download_dir=tmp_path,
        )

        await manager.open()
        await manager.close(wait_for_current=True)

        # Should call shutdown instead of stop when wait_for_current=True
        mock_worker_pool.shutdown.assert_called_once_with(wait_for_current=True)
