"""Tests for DownloadManager graceful shutdown behavior."""

import asyncio

import pytest


class TestBasicShutdownBehavior:
    """Test basic shutdown functionality and event initialization."""

    @pytest.mark.asyncio
    async def test_shutdown_event_initialized(self, make_shutdown_manager):
        """Verify _shutdown_event exists and is not set after init."""
        manager = make_shutdown_manager()

        assert hasattr(manager, "_shutdown_event")
        assert isinstance(manager._shutdown_event, asyncio.Event)
        assert not manager._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_shutdown_sets_event(self, make_shutdown_manager):
        """Call shutdown(), verify event is set."""
        manager = make_shutdown_manager()

        # Start workers (they'll be waiting on empty queue)
        await manager.start_workers()

        # Verify event not set before shutdown
        assert not manager._shutdown_event.is_set()

        # Call shutdown
        await manager.shutdown()

        # Verify event is now set
        assert manager._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_shutdown_with_wait_completes_current_download(
        self, make_shutdown_manager, mock_worker, make_file_config, slow_download_mock
    ):
        """Mock download in progress, call shutdown(wait_for_current=True),
        verify download completes before workers stop."""
        mock_download = slow_download_mock()
        mock_worker.download.side_effect = mock_download

        manager = make_shutdown_manager()

        # Add a file and start workers
        await manager.add_to_queue([make_file_config()])
        await manager.start_workers()

        # Wait for download to start
        await asyncio.wait_for(mock_download.started.wait(), timeout=1.0)

        # Call shutdown with wait_for_current=True
        await manager.shutdown(wait_for_current=True)

        # Verify download was completed
        assert mock_download.completed.is_set()

        # Verify worker.download was called
        mock_worker.download.assert_called_once()

        # Verify tasks are cleared
        assert len(manager._tasks) == 0


class TestProcessQueueShutdown:
    """Test process_queue behavior with shutdown event."""

    @pytest.mark.asyncio
    async def test_process_queue_stops_when_shutdown_event_set(
        self,
        make_shutdown_manager,
        mock_worker,
        make_file_configs,
        counting_download_mock,
    ):
        """Add items to queue, start worker, set shutdown event,
        verify worker exits gracefully."""
        mock_download = counting_download_mock()
        mock_worker.download.side_effect = mock_download

        manager = make_shutdown_manager()

        # Add multiple files
        await manager.add_to_queue(make_file_configs(count=10))

        # Start workers
        await manager.start_workers()

        # Let some downloads happen
        await asyncio.sleep(0.15)

        # Trigger shutdown
        await manager.shutdown(wait_for_current=True)

        # Should have processed at least one download
        assert mock_download.count["value"] > 0

        # Should have stopped before processing all 10
        assert mock_download.count["value"] < 10

    @pytest.mark.asyncio
    async def test_process_queue_handles_timeout_and_checks_shutdown(
        self, make_shutdown_manager, mock_worker
    ):
        """Mock empty queue (timeout), verify loop continues checking
        shutdown event."""
        manager = make_shutdown_manager()

        # Start workers with empty queue
        await manager.start_workers()

        # Let it wait on empty queue for a bit
        await asyncio.sleep(0.5)

        # Shutdown should work even with empty queue
        await manager.shutdown(wait_for_current=True)

        # Verify tasks are cleared
        assert len(manager._tasks) == 0

        # Verify no downloads were attempted
        mock_worker.download.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_queue_requeues_item_if_shutdown_during_get(
        self, make_shutdown_manager, make_file_config, real_priority_queue
    ):
        """Shutdown while item is retrieved but before download starts,
        verify item put back in queue."""
        manager = make_shutdown_manager()

        # Add a file
        file_config = make_file_config()
        await manager.add_to_queue([file_config])

        # Start workers
        await manager.start_workers()

        # Immediately trigger shutdown (before download can start)
        manager._shutdown_event.set()

        # Wait a moment for processing
        await asyncio.sleep(0.1)

        # Stop workers properly
        await manager.stop_workers()

        # The item should have been put back in the queue
        # Check queue is not empty
        assert not real_priority_queue.is_empty()


class TestImmediateCancellation:
    """Test immediate cancellation without waiting for current downloads."""

    @pytest.mark.asyncio
    async def test_shutdown_without_wait_cancels_immediately(
        self, make_shutdown_manager, mock_worker, make_file_config, slow_download_mock
    ):
        """Mock long download, call shutdown(wait_for_current=False),
        verify immediate cancellation via stop_workers()."""
        mock_download = slow_download_mock(download_time=10.0)
        mock_worker.download.side_effect = mock_download

        manager = make_shutdown_manager()

        # Add a file and start workers
        await manager.add_to_queue([make_file_config()])
        await manager.start_workers()

        # Wait for download to start
        await asyncio.wait_for(mock_download.started.wait(), timeout=1.0)

        # Call shutdown with wait_for_current=False
        await manager.shutdown(wait_for_current=False)

        # Verify download was NOT completed (cancelled)
        assert not mock_download.completed.is_set()

        # Verify tasks are cleared
        assert len(manager._tasks) == 0

    @pytest.mark.asyncio
    async def test_shutdown_without_wait_does_not_complete_download(
        self,
        make_shutdown_manager,
        mock_worker,
        make_file_configs,
        counting_download_mock,
    ):
        """Verify download is interrupted when wait_for_current=False."""
        mock_download = counting_download_mock(download_time=1.0)
        mock_worker.download.side_effect = mock_download

        manager = make_shutdown_manager()

        # Add multiple files
        await manager.add_to_queue(make_file_configs(count=5))

        # Start workers
        await manager.start_workers()

        # Let one download start
        await asyncio.sleep(0.05)

        # Immediate shutdown
        await manager.shutdown(wait_for_current=False)

        # Should have started at most 1 download
        assert mock_download.count["value"] <= 1


class TestMultipleWorkersShutdown:
    """Test shutdown behavior with multiple concurrent workers."""

    @pytest.mark.asyncio
    async def test_shutdown_stops_all_workers_gracefully(
        self,
        make_shutdown_manager,
        mock_worker,
        make_file_configs,
        counting_download_mock,
    ):
        """Multiple workers active, call shutdown(), verify all workers stop."""
        mock_download = counting_download_mock()
        mock_worker.download.side_effect = mock_download

        manager = make_shutdown_manager(max_workers=3)

        # Add files
        await manager.add_to_queue(make_file_configs(count=10))

        # Start workers
        await manager.start_workers()

        # Verify we have 3 workers
        assert len(manager._tasks) == 3

        # Let some downloads happen
        await asyncio.sleep(0.1)

        # Shutdown
        await manager.shutdown(wait_for_current=True)

        # All tasks should be cleared
        assert len(manager._tasks) == 0

        # Some downloads should have happened
        assert mock_download.count["value"] > 0

    @pytest.mark.asyncio
    async def test_multiple_workers_respect_shutdown_event(
        self,
        make_shutdown_manager,
        mock_worker,
        make_file_configs,
        counting_download_mock,
    ):
        """Add many items, multiple workers, shutdown mid-processing,
        verify all workers stop."""
        mock_download = counting_download_mock()
        mock_worker.download.side_effect = mock_download

        manager = make_shutdown_manager(max_workers=5)

        # Add many files
        await manager.add_to_queue(make_file_configs(count=20))

        # Start workers
        await manager.start_workers()

        # Let downloads start
        await asyncio.sleep(0.15)

        # Shutdown
        await manager.shutdown(wait_for_current=True)

        # Not all 20 should have been processed
        assert mock_download.count["value"] < 20

        # But some should have been
        assert mock_download.count["value"] > 0

        # All tasks cleared
        assert len(manager._tasks) == 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_shutdown_with_empty_queue(self, make_shutdown_manager):
        """No items in queue, call shutdown(), verify clean exit."""
        manager = make_shutdown_manager(max_workers=2)

        # Start workers with empty queue
        await manager.start_workers()

        # Shutdown immediately
        await manager.shutdown(wait_for_current=True)

        # Should complete cleanly
        assert len(manager._tasks) == 0
        assert manager._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_shutdown_logs_appropriately(
        self, make_shutdown_manager, mock_logger
    ):
        """Verify shutdown logs 'initiating shutdown' and workers log
        'shutting down gracefully'."""
        manager = make_shutdown_manager()

        # Start workers
        await manager.start_workers()

        # Shutdown
        await manager.shutdown(wait_for_current=True)

        # Check logs for shutdown messages
        # Note: mock_logger.info is called with formatted strings
        log_messages = [call.args[0] for call in mock_logger.info.call_args_list]

        # Should have "Initiating shutdown" message
        assert any("Initiating shutdown" in msg for msg in log_messages)

        # Should have "Worker shutting down gracefully" message
        assert any("Worker shutting down gracefully" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_repeated_shutdown_calls_are_idempotent(self, make_shutdown_manager):
        """Call shutdown() multiple times, verify no errors."""
        manager = make_shutdown_manager()

        # Start workers
        await manager.start_workers()

        # Call shutdown multiple times
        for _ in range(3):
            await manager.shutdown(wait_for_current=True)

        # Should complete without errors
        assert manager._shutdown_event.is_set()
        assert len(manager._tasks) == 0
