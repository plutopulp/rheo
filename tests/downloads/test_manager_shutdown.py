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
        # Note: Shutdown logs are now at DEBUG level
        log_messages = [call.args[0] for call in mock_logger.debug.call_args_list]

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


class TestShutdownMechanismInternals:
    """Test the internal mechanisms that make shutdown work correctly.

    These tests use custom manager implementations to demonstrate why
    specific implementation details (timeout and task_done) are critical.
    """

    class ManagerWithoutTimeout:
        """Custom manager that removes the timeout from process_queue.

        This demonstrates that without the timeout, workers block indefinitely
        on an empty queue and cannot respond to shutdown events.
        """

        def __init__(self, manager):
            """Wrap a real manager and override process_queue."""
            self._manager = manager
            # Expose necessary attributes
            self._shutdown_event = manager._shutdown_event
            self._tasks = manager._tasks
            self.queue = manager.queue
            self.worker = manager.worker
            self.download_dir = manager.download_dir
            self._logger = manager._logger

        async def start_workers(self):
            """Start workers using custom process_queue."""
            await self._manager.start_workers()

        async def stop_workers(self):
            """Stop workers."""
            await self._manager.stop_workers()

        async def shutdown(self, wait_for_current: bool = True):
            """Shutdown using manager's implementation."""
            await self._manager.shutdown(wait_for_current=wait_for_current)

        async def process_queue(self) -> None:
            """Process queue WITHOUT timeout to demonstrate the problem."""
            while not self._shutdown_event.is_set():
                file_config = None
                try:
                    # THIS IS THE PROBLEM: No timeout means we block forever
                    # on empty queue and can't check shutdown event
                    file_config = await self.queue.get_next()

                    # Check shutdown again before starting download
                    if self._shutdown_event.is_set():
                        await self.queue.add([file_config])
                        self.queue.task_done()
                        break

                    destination_path = file_config.get_destination_path(
                        self.download_dir
                    )
                    self._logger.debug(
                        f"Downloading {file_config.url} to {destination_path}"
                    )
                    await self.worker.download(file_config.url, destination_path)
                    self._logger.debug(
                        f"Downloaded {file_config.url} to {destination_path}"
                    )
                except asyncio.CancelledError:
                    self._logger.debug("Worker cancelled, stopping immediately")
                    raise
                except Exception as exc:
                    self._logger.error(f"Error processing queue: {exc}")
                finally:
                    if file_config is not None:
                        self.queue.task_done()

            self._logger.debug("Worker shutting down gracefully")

    class ManagerWithoutTaskDone:
        """Custom manager that skips task_done in the re-queue branch.

        This demonstrates that without task_done, queue.join() hangs because
        the internal unfinished task counter is never decremented.
        """

        def __init__(self, manager):
            """Wrap a real manager and override process_queue."""
            self._manager = manager
            # Expose necessary attributes
            self._shutdown_event = manager._shutdown_event
            self._tasks = manager._tasks
            self.queue = manager.queue
            self.worker = manager.worker
            self.download_dir = manager.download_dir
            self._logger = manager._logger

        async def start_workers(self):
            """Start workers using custom process_queue."""
            await self._manager.start_workers()

        async def stop_workers(self):
            """Stop workers."""
            await self._manager.stop_workers()

        async def shutdown(self, wait_for_current: bool = True):
            """Shutdown using manager's implementation."""
            await self._manager.shutdown(wait_for_current=wait_for_current)

        async def process_queue(self) -> None:
            """Process queue WITHOUT task_done in re-queue to demonstrate the problem."""
            while not self._shutdown_event.is_set():
                file_config = None
                got_item = False
                try:
                    file_config = await asyncio.wait_for(
                        self.queue.get_next(), timeout=1.0
                    )
                    got_item = True

                    # Check shutdown again before starting download
                    if self._shutdown_event.is_set():
                        # THIS IS THE PROBLEM: Re-queue without task_done
                        # leaves the queue's internal counter unbalanced
                        await self.queue.add([file_config])
                        # MISSING: self.queue.task_done()
                        break

                    destination_path = file_config.get_destination_path(
                        self.download_dir
                    )
                    self._logger.debug(
                        f"Downloading {file_config.url} to {destination_path}"
                    )
                    await self.worker.download(file_config.url, destination_path)
                    self._logger.debug(
                        f"Downloaded {file_config.url} to {destination_path}"
                    )
                except asyncio.TimeoutError:
                    continue
                except asyncio.CancelledError:
                    self._logger.debug("Worker cancelled, stopping immediately")
                    raise
                except Exception as exc:
                    self._logger.error(f"Error processing queue: {exc}")
                finally:
                    if file_config is not None and got_item:
                        self.queue.task_done()

            self._logger.debug("Worker shutting down gracefully")

    @pytest.mark.asyncio
    async def test_without_timeout_shutdown_fails_on_empty_queue(
        self, make_shutdown_manager
    ):
        """Demonstrate that without timeout, workers block indefinitely on empty queue.

        This test shows why the asyncio.wait_for timeout is necessary.
        Without it, a worker waiting on an empty queue cannot respond to
        the shutdown event.
        """
        # Create a real manager
        real_manager = make_shutdown_manager()

        # Wrap it with our custom implementation that has no timeout
        manager = self.ManagerWithoutTimeout(real_manager)

        # Manually create a task with the buggy process_queue
        # Don't add to manager._tasks to avoid shutdown cancelling it
        task = asyncio.create_task(manager.process_queue())

        # Give the worker time to enter the blocking get_next() call
        await asyncio.sleep(0.1)

        # Set shutdown event manually (since we're not using manager.shutdown())
        manager._shutdown_event.set()

        # Give it a moment to potentially notice the shutdown
        await asyncio.sleep(0.2)

        # Task should still be running (blocked on queue.get_next())
        # It can't check the shutdown event because it's stuck waiting
        assert not task.done()

        # Try to wait for the task with timeout - it should NOT complete
        with pytest.raises(asyncio.TimeoutError):
            # The worker is stuck in queue.get_next() and can't check
            # the shutdown event, so this will hang
            await asyncio.wait_for(task, timeout=0.5)

        # Verify shutdown event was set
        assert manager._shutdown_event.is_set()

        # Force cleanup by cancelling the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_without_task_done_queue_join_hangs(
        self, make_shutdown_manager, make_file_config, real_priority_queue
    ):
        """Demonstrate that without task_done, queue.join() hangs.

        This test shows why task_done() is necessary in the re-queue branch.
        When we get an item from the queue, the internal _unfinished_tasks
        counter is incremented. If we re-queue without calling task_done(),
        the counter stays unbalanced and queue.join() waits forever.
        """
        # Create a real manager
        real_manager = make_shutdown_manager()

        # Wrap it with our custom implementation that skips task_done
        manager = self.ManagerWithoutTaskDone(real_manager)

        # Add a file to the queue
        file_config = make_file_config()
        await manager.queue.add([file_config])

        # Manually create a task with the buggy process_queue
        task = asyncio.create_task(manager.process_queue())
        manager._tasks.append(task)

        # Immediately trigger shutdown (before download can start)
        # This will cause the re-queue branch to execute
        manager._shutdown_event.set()

        # Wait for re-queue to happen
        await asyncio.sleep(0.2)

        # Stop the worker task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # The item should be back in the queue
        assert not real_priority_queue.is_empty()

        # But queue.join() will HANG because task_done was never called
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(real_priority_queue.join(), timeout=0.5)

        # Control case: manually calling task_done fixes the queue state
        real_priority_queue.task_done()

        # Now join should complete immediately
        try:
            await asyncio.wait_for(real_priority_queue.join(), timeout=0.5)
        except asyncio.TimeoutError:
            pytest.fail("queue.join() hung even after task_done() - should not happen")
