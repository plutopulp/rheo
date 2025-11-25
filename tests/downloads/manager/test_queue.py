"""Tests for DownloadManager queue integration."""

import typing as t

import pytest

from rheo.domain.file_config import FileConfig
from rheo.downloads import DownloadManager, PriorityDownloadQueue

if t.TYPE_CHECKING:
    from loguru import Logger


class TestDownloadManagerQueueIntegration:
    """Unit tests for DownloadManager queue integration.

    These tests focus on manager orchestration logic using mocked dependencies.
    """

    @pytest.mark.asyncio
    async def test_add_to_queue_delegates_to_queue(
        self,
        mock_queue: PriorityDownloadQueue,
        make_file_config: t.Callable[..., FileConfig],
        mock_logger: "Logger",
    ):
        """Test that add_to_queue properly delegates to queue.add()."""
        manager = DownloadManager(queue=mock_queue, logger=mock_logger)

        file_configs = [make_file_config()]
        await manager.add_to_queue(file_configs)

        # Verify delegation
        mock_queue.add.assert_called_once_with(file_configs)

    @pytest.mark.asyncio
    async def test_manager_accepts_custom_queue(self, mock_logger: "Logger"):
        """Test that manager accepts and uses a custom PriorityDownloadQueue."""
        custom_queue = PriorityDownloadQueue(logger=mock_logger)
        manager = DownloadManager(queue=custom_queue, logger=mock_logger)

        assert manager.queue is custom_queue
