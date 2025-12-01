"""Tests for DownloadManager graceful shutdown behavior."""

import asyncio

import pytest


class TestBasicShutdownBehavior:
    """Test basic shutdown functionality at the manager level."""

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
        await manager.add([make_file_config()])
        await manager.open()

        # Wait for download to start
        await asyncio.wait_for(mock_download.started.wait(), timeout=1.0)

        # Call shutdown with wait_for_current=True
        await manager.close(wait_for_current=True)

        # Verify download was completed
        assert mock_download.completed.is_set()

        # Verify worker.download was called
        mock_worker.download.assert_called_once()


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
        await manager.add(make_file_configs(count=10))

        # Start workers
        await manager.open()

        # Let some downloads happen
        await asyncio.sleep(0.15)

        # Trigger shutdown
        await manager.close(wait_for_current=True)

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
        await manager.open()

        # Let it wait on empty queue for a bit
        await asyncio.sleep(0.5)

        # Shutdown should work even with empty queue
        await manager.close(wait_for_current=True)

        # Verify no downloads were attempted
        mock_worker.download.assert_not_called()


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
        await manager.add([make_file_config()])
        await manager.open()

        # Wait for download to start
        await asyncio.wait_for(mock_download.started.wait(), timeout=1.0)

        # Call shutdown with wait_for_current=False
        await manager.close(wait_for_current=False)

        # Verify download was NOT completed (cancelled)
        assert not mock_download.completed.is_set()

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
        await manager.add(make_file_configs(count=5))

        # Start workers
        await manager.open()

        # Let one download start
        await asyncio.sleep(0.05)

        # Immediate shutdown
        await manager.close(wait_for_current=False)

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

        manager = make_shutdown_manager(max_concurrent=3)

        # Add files
        await manager.add(make_file_configs(count=10))

        # Start workers
        await manager.open()

        # Let some downloads happen
        await asyncio.sleep(0.1)

        # Shutdown
        await manager.close(wait_for_current=True)

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

        manager = make_shutdown_manager(max_concurrent=5)

        # Add many files
        await manager.add(make_file_configs(count=20))

        # Start workers
        await manager.open()

        # Let downloads start
        await asyncio.sleep(0.15)

        # Shutdown
        await manager.close(wait_for_current=True)

        # Not all 20 should have been processed
        assert mock_download.count["value"] < 20

        # But some should have been
        assert mock_download.count["value"] > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_shutdown_with_empty_queue(self, make_shutdown_manager):
        """No items in queue, call shutdown(), verify clean exit."""
        manager = make_shutdown_manager(max_concurrent=2)

        # Start workers with empty queue
        await manager.open()

        # Shutdown immediately
        await manager.close(wait_for_current=True)

        # Should complete cleanly without errors

    @pytest.mark.asyncio
    async def test_repeated_shutdown_calls_are_idempotent(self, make_shutdown_manager):
        """Call shutdown() multiple times, verify no errors."""
        manager = make_shutdown_manager()

        # Start workers
        await manager.open()

        # Call shutdown multiple times
        for _ in range(3):
            await manager.close(wait_for_current=True)

        # Should complete without errors
