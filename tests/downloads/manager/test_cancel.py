"""Unit tests for DownloadManager.cancel() method."""

import typing as t
from unittest.mock import Mock

import pytest

from rheo.domain.cancellation import CancelResult
from rheo.domain.downloads import DownloadInfo, DownloadStatus
from rheo.downloads.manager import DownloadManager
from rheo.downloads.worker_pool.factory import WorkerPoolFactory

if t.TYPE_CHECKING:
    from loguru import Logger

    from rheo.tracking import DownloadTracker


class TestManagerCancel:
    """Unit tests for manager.cancel() logic.

    These tests mock the pool and tracker to test the CancelResult mapping:
    - Pool returns True → CANCELLED
    - Pool returns False + tracker has terminal → ALREADY_TERMINAL
    - Pool returns False + tracker has no info → NOT_FOUND
    """

    @pytest.mark.asyncio
    async def test_cancel_returns_cancelled_when_pool_cancels(
        self,
        mock_worker_pool: Mock,
        mock_pool_factory: WorkerPoolFactory,
        tracker: "DownloadTracker",
        mock_logger: "Logger",
    ) -> None:
        """Returns CANCELLED when pool.cancel() returns True."""
        mock_worker_pool.cancel.return_value = True

        manager = DownloadManager(
            worker_pool_factory=mock_pool_factory,
            tracker=tracker,
            logger=mock_logger,
        )

        result = await manager.cancel("some-id")

        assert result == CancelResult.CANCELLED
        mock_worker_pool.cancel.assert_called_once_with("some-id")

    @pytest.mark.asyncio
    async def test_cancel_returns_already_terminal_when_completed(
        self,
        mock_worker_pool: Mock,
        mock_pool_factory: WorkerPoolFactory,
        tracker: "DownloadTracker",
        mock_logger: "Logger",
    ) -> None:
        """Returns ALREADY_TERMINAL when pool says no but tracker has completed."""
        mock_worker_pool.cancel.return_value = False

        # Set up tracker with completed download
        tracker._downloads["completed-id"] = DownloadInfo(
            id="completed-id",
            url="http://example.com/file.txt",
            status=DownloadStatus.COMPLETED,
        )

        manager = DownloadManager(
            worker_pool_factory=mock_pool_factory,
            tracker=tracker,
            logger=mock_logger,
        )

        result = await manager.cancel("completed-id")

        assert result == CancelResult.ALREADY_TERMINAL

    @pytest.mark.asyncio
    async def test_cancel_returns_already_terminal_when_failed(
        self,
        mock_worker_pool: Mock,
        mock_pool_factory: WorkerPoolFactory,
        tracker: "DownloadTracker",
        mock_logger: "Logger",
    ) -> None:
        """Returns ALREADY_TERMINAL when pool says no but tracker has failed."""
        mock_worker_pool.cancel.return_value = False

        tracker._downloads["failed-id"] = DownloadInfo(
            id="failed-id",
            url="http://example.com/file.txt",
            status=DownloadStatus.FAILED,
        )

        manager = DownloadManager(
            worker_pool_factory=mock_pool_factory,
            tracker=tracker,
            logger=mock_logger,
        )

        result = await manager.cancel("failed-id")

        assert result == CancelResult.ALREADY_TERMINAL

    @pytest.mark.asyncio
    async def test_cancel_returns_not_found_when_unknown(
        self,
        mock_worker_pool: Mock,
        mock_pool_factory: WorkerPoolFactory,
        tracker: "DownloadTracker",
        mock_logger: "Logger",
    ) -> None:
        """Returns NOT_FOUND when pool says no and tracker has no record."""
        mock_worker_pool.cancel.return_value = False

        manager = DownloadManager(
            worker_pool_factory=mock_pool_factory,
            tracker=tracker,
            logger=mock_logger,
        )

        result = await manager.cancel("unknown-id")

        assert result == CancelResult.NOT_FOUND
