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
    ):
        """start_workers should call pool.start()."""
        manager = DownloadManager(
            logger=mock_logger,
            worker_pool_factory=mock_pool_factory,
            client=mock_aio_client,
        )

        await manager.open()

        mock_worker_pool.start.assert_called_once_with(mock_aio_client)

    @pytest.mark.asyncio
    async def test_stop_workers_delegates_to_pool(
        self,
        mock_logger: "Logger",
        mock_worker_pool: Mock,
        mock_pool_factory: WorkerPoolFactory,
        mock_aio_client: aiohttp.ClientSession,
    ):
        """stop_workers should call pool.stop()."""
        manager = DownloadManager(
            logger=mock_logger,
            worker_pool_factory=mock_pool_factory,
            client=mock_aio_client,
        )

        await manager.close()

        mock_worker_pool.stop.assert_called_once()
