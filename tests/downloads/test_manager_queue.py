"""Tests for DownloadManager queue integration."""

import asyncio

import pytest

from async_download_manager.downloads import DownloadManager, PriorityDownloadQueue


class TestDownloadManagerQueueIntegration:
    """Unit tests for DownloadManager queue integration.

    These tests focus on manager orchestration logic using mocked dependencies.
    """

    @pytest.mark.asyncio
    async def test_add_to_queue_delegates_to_queue(
        self, mock_queue, make_file_config, mock_logger
    ):
        """Test that add_to_queue properly delegates to queue.add()."""
        manager = DownloadManager(queue=mock_queue, logger=mock_logger)

        file_configs = [make_file_config()]
        await manager.add_to_queue(file_configs)

        # Verify delegation
        mock_queue.add.assert_called_once_with(file_configs)

    @pytest.mark.asyncio
    async def test_manager_accepts_custom_queue(self, mock_logger):
        """Test that manager accepts and uses a custom PriorityDownloadQueue."""
        custom_queue = PriorityDownloadQueue(logger=mock_logger)
        manager = DownloadManager(queue=custom_queue, logger=mock_logger)

        assert manager.queue is custom_queue

    @pytest.mark.asyncio
    async def test_process_queue_uses_queue_get_next(
        self, mock_manager_dependencies, make_file_config, mock_logger, tmp_path
    ):
        """Test that process_queue delegates to queue.get_next() and
        worker.download()."""
        # Customize queue behavior for this test
        mock_manager_dependencies["queue"].get_next.side_effect = [
            make_file_config(),
            asyncio.CancelledError(),
        ]

        manager = DownloadManager(
            **mock_manager_dependencies,
            download_dir=tmp_path,
            logger=mock_logger,
        )

        # Process queue (will stop after one iteration due to CancelledError)
        try:
            await manager.process_queue()
        except asyncio.CancelledError:
            pass

        # Verify queue.get_next was called
        assert mock_manager_dependencies["queue"].get_next.call_count >= 1

        # Verify worker.download was called with correct URL
        mock_manager_dependencies["worker"].download.assert_called_once()
        call_args = mock_manager_dependencies["worker"].download.call_args[0]
        assert call_args[0] == "https://example.com/test.txt"

        # Verify task_done was called
        mock_manager_dependencies["queue"].task_done.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_queue_calls_task_done_on_success(
        self, mock_manager_dependencies, make_file_config, mock_logger, tmp_path
    ):
        """Test that process_queue calls task_done after successful download."""
        # Customize queue behavior for this test
        mock_manager_dependencies["queue"].get_next.side_effect = [
            make_file_config(),
            asyncio.CancelledError(),
        ]

        manager = DownloadManager(
            **mock_manager_dependencies,
            download_dir=tmp_path,
            logger=mock_logger,
        )

        try:
            await manager.process_queue()
        except asyncio.CancelledError:
            pass

        # Verify task_done was called after processing
        mock_manager_dependencies["queue"].task_done.assert_called_once()

    @pytest.mark.asyncio
    async def test_multiple_workers_process_concurrent_downloads(
        self,
        mock_aio_client,
        mock_worker,
        real_priority_queue,
        make_file_configs,
        mock_logger,
        tmp_path,
    ):
        """Test that multiple workers can process downloads concurrently."""
        download_count = 0

        async def slow_download(*args, **kwargs):
            nonlocal download_count
            download_count += 1
            await asyncio.sleep(0.05)  # Simulate slow download

        mock_worker.download.side_effect = slow_download

        manager = DownloadManager(
            client=mock_aio_client,
            worker=mock_worker,
            queue=real_priority_queue,
            max_workers=3,
            download_dir=tmp_path,
            logger=mock_logger,
        )

        # Add multiple files to the queue
        file_configs = make_file_configs(count=5)
        await manager.add_to_queue(file_configs)

        # Start workers
        await manager.start_workers()

        # Wait for processing
        await asyncio.sleep(0.3)

        # Stop workers
        await manager.stop_workers()

        # Should have processed multiple files concurrently
        assert download_count > 1

    @pytest.mark.asyncio
    async def test_stop_workers_waits_for_completion(
        self,
        mock_aio_client,
        mock_worker,
        real_priority_queue,
        make_file_config,
        mock_logger,
        tmp_path,
    ):
        """Test that stop_workers() waits for all tasks to complete before returning.

        This test verifies the fix for the race condition where stop_workers() would
        return before tasks were fully cleaned up, potentially causing issues when
        the client is closed in __aexit__.
        """
        # Track task lifecycle
        download_started = asyncio.Event()
        download_in_progress = asyncio.Event()
        cleanup_completed = asyncio.Event()

        async def blocking_download(*args, **kwargs):
            download_started.set()
            download_in_progress.set()
            try:
                # Simulate long-running download
                await asyncio.sleep(10)  # Would block forever if not cancelled
            except asyncio.CancelledError:
                # Simulate cleanup work
                await asyncio.sleep(0.1)
                cleanup_completed.set()
                raise

        mock_worker.download.side_effect = blocking_download

        manager = DownloadManager(
            client=mock_aio_client,
            worker=mock_worker,
            queue=real_priority_queue,
            max_workers=1,
            download_dir=tmp_path,
            logger=mock_logger,
        )

        # Add a file and start workers
        await manager.add_to_queue([make_file_config()])
        await manager.start_workers()

        # Wait for download to start
        await asyncio.wait_for(download_started.wait(), timeout=1.0)
        assert download_in_progress.is_set()

        # Stop workers should wait for cleanup to complete
        await manager.stop_workers()

        # Verify cleanup was completed before stop_workers returned
        assert cleanup_completed.is_set()

        # Verify tasks list was cleared
        assert len(manager._tasks) == 0
