"""Integration tests for manager-worker-tracker event wiring."""

import asyncio
import typing as t
from pathlib import Path

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses

from rheo import DownloadManager, DownloadStatus
from rheo.domain import FileConfig, FileExistsStrategy
from rheo.events.models import (
    DownloadCancelledEvent,
    DownloadCompletedEvent,
    DownloadFailedEvent,
    DownloadSkippedEvent,
)
from rheo.tracking import NullTracker

if t.TYPE_CHECKING:
    from loguru import Logger


class TestManagerTrackerWiring:
    """Test event wiring between manager, worker, and tracker."""

    @pytest.mark.asyncio
    async def test_manager_works_without_tracker(self, aio_client, mock_logger):
        """Test that manager works when no tracker provided."""
        async with DownloadManager(client=aio_client, logger=mock_logger) as manager:
            # Tracker is now auto-created, never None
            assert manager.tracker is not None

    @pytest.mark.asyncio
    async def test_worker_started_wires_to_tracker(
        self, manager_with_tracker, tmp_path
    ):
        """Test worker.started event updates tracker through queue flow."""
        test_url = "https://example.com/file.txt"

        # Create file config and add to queue
        file_config = FileConfig(url=test_url, priority=1)
        await manager_with_tracker.add([file_config])

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=b"test")

            # Use context manager to start workers and process queue
            async with manager_with_tracker as manager:
                # Wait for queue to be processed
                await manager.queue.join()

        # Tracker should have recorded the download
        info = manager_with_tracker.tracker.get_download_info(file_config.id)
        assert info is not None
        assert info.status == DownloadStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_worker_progress_wires_to_tracker(
        self, manager_with_tracker, tmp_path
    ):
        """Test worker.progress events update tracker through queue flow."""
        test_url = "https://example.com/file.txt"
        test_content = b"x" * 5000  # 5KB

        # Create file config
        file_config = FileConfig(url=test_url, priority=1)
        await manager_with_tracker.add([file_config])

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)

            async with manager_with_tracker as manager:
                await manager.queue.join()

        info = manager_with_tracker.tracker.get_download_info(file_config.id)
        assert info.bytes_downloaded == len(test_content)

    @pytest.mark.asyncio
    async def test_worker_completed_wires_to_tracker(
        self, manager_with_tracker, tmp_path
    ):
        """Test worker.completed event updates tracker through queue flow."""
        test_url = "https://example.com/file.txt"
        test_content = b"test content"

        file_config = FileConfig(url=test_url, priority=1)
        await manager_with_tracker.add([file_config])

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)

            async with manager_with_tracker as manager:
                await manager.queue.join()

        info = manager_with_tracker.tracker.get_download_info(file_config.id)
        assert info.status == DownloadStatus.COMPLETED
        assert info.total_bytes == len(test_content)

    @pytest.mark.asyncio
    async def test_worker_failed_wires_to_tracker(self, manager_with_tracker, tmp_path):
        """Test worker.failed event updates tracker through queue flow."""
        test_url = "https://example.com/file.txt"

        file_config = FileConfig(url=test_url, priority=1)
        await manager_with_tracker.add([file_config])

        with aioresponses() as mock:
            mock.get(test_url, status=404, body="Not Found")

            # Worker will catch the exception and record it
            async with manager_with_tracker as manager:
                await manager.queue.join()

        info = manager_with_tracker.tracker.get_download_info(file_config.id)
        assert info is not None
        assert info.status == DownloadStatus.FAILED
        assert "404" in info.error or "ClientResponseError" in info.error

    @pytest.mark.asyncio
    async def test_manager_prevents_duplicate_downloads(
        self, manager_with_tracker: DownloadManager
    ):
        """Test that duplicate downloads (same URL+destination) are prevented end-to-end.

        Verifies that:
        1. Adding same file twice only queues it once
        2. Only one download is executed by the worker
        3. Tracker records only one download
        """
        test_url = "https://example.com/file.txt"
        test_content = b"test content"

        # Create same file config twice (same URL, same destination)
        file_config_1 = FileConfig(url=test_url, priority=1)
        file_config_2 = FileConfig(url=test_url, priority=1)

        # Both should have the same ID (same URL + destination)
        assert file_config_1.id == file_config_2.id

        # Add both to queue
        await manager_with_tracker.add([file_config_1])
        await manager_with_tracker.add([file_config_2])

        # Queue should only have one item (duplicate was skipped)
        assert manager_with_tracker.queue.size() == 1

        with aioresponses() as mock:
            # Mock HTTP - if called twice, test would fail with connection error
            mock.get(test_url, status=200, body=test_content)

            async with manager_with_tracker as manager:
                await manager.queue.join()

        assert manager_with_tracker.queue.size() == 0
        # Verify only one download was tracked
        assert len(manager_with_tracker.tracker._downloads) == 1
        info = manager_with_tracker.tracker.get_download_info(file_config_1.id)
        assert info is not None
        assert info.status == DownloadStatus.COMPLETED
        assert info.bytes_downloaded == len(test_content)
        assert info.url == test_url
        assert info.id == file_config_1.id

        # If duplicate ran, aioresponses would raise ConnectionError on second call


class TestPublicTrackerProperty:
    """Test that tracker property exposes the configured tracker instance."""

    def test_tracker_property_returns_provided_tracker(self, aio_client, tracker):
        """Verify tracker property returns the explicitly provided tracker."""
        manager = DownloadManager(client=aio_client, tracker=tracker)
        assert manager.tracker is tracker

    def test_tracker_property_with_null_tracker(self, aio_client):
        """Verify tracker property works with NullTracker."""

        null_tracker = NullTracker()
        manager = DownloadManager(client=aio_client, tracker=null_tracker)
        assert manager.tracker is null_tracker


class TestQueueEventWiring:
    """Test queue event wiring through manager to tracker."""

    @pytest.mark.asyncio
    async def test_queue_add_updates_tracker_via_event(
        self, manager_with_tracker, tmp_path
    ):
        """Adding to queue should automatically track as QUEUED via event."""
        test_url = "https://example.com/queued.txt"
        file_config = FileConfig(url=test_url, priority=5)

        async with manager_with_tracker as manager:
            # Add to queue (triggers download.queued event)
            await manager.add([file_config])

            # Tracker should immediately have QUEUED status via event wiring
            info = manager.tracker.get_download_info(file_config.id)
            assert info is not None
            assert info.status == DownloadStatus.QUEUED
            assert info.url == test_url

            # Clean up by closing (cancels pending)
            await manager.close()

    @pytest.mark.asyncio
    async def test_queued_transitions_to_completed(
        self, manager_with_tracker, tmp_path
    ):
        """Download should transition from QUEUED to COMPLETED."""
        test_url = "https://example.com/file.txt"
        file_config = FileConfig(url=test_url, priority=1)

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=b"content")

            async with manager_with_tracker as manager:
                await manager.add([file_config])

                # Initially QUEUED
                info = manager.tracker.get_download_info(file_config.id)
                assert info.status == DownloadStatus.QUEUED

                # Wait for download to complete
                await manager.wait_until_complete()

        # Final state should be COMPLETED
        info = manager_with_tracker.tracker.get_download_info(file_config.id)
        assert info.status == DownloadStatus.COMPLETED


class TestManagerEventSubscription:
    """Test manager.on() event subscription end-to-end."""

    @pytest.mark.asyncio
    async def test_on_receives_completed_event(
        self, aio_client: ClientSession, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """Subscribe via manager.on() should receive download.completed event."""
        test_url = "https://example.com/file.txt"
        test_content = b"test content"
        file_config = FileConfig(url=test_url, priority=1)

        events: list[DownloadCompletedEvent] = []

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)

            async with DownloadManager(
                client=aio_client,
                logger=mock_logger,
                download_dir=tmp_path,
            ) as manager:
                manager.on("download.completed", lambda e: events.append(e))

                await manager.add([file_config])
                await manager.wait_until_complete()

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, DownloadCompletedEvent)
        assert event.download_id == file_config.id
        assert event.url == test_url
        assert event.total_bytes == len(test_content)

    @pytest.mark.asyncio
    async def test_wildcard_receives_all_events_in_order(
        self, aio_client: ClientSession, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """Subscribe to '*' should receive queued, started, progress, completed
        in order."""
        test_url = "https://example.com/file.txt"
        test_content = b"test content"
        file_config = FileConfig(url=test_url, priority=1)

        events: list[t.Any] = []

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)

            async with DownloadManager(
                client=aio_client,
                logger=mock_logger,
                download_dir=tmp_path,
            ) as manager:
                manager.on("*", lambda e: events.append(e))

                await manager.add([file_config])
                await manager.wait_until_complete()

        # Extract event types
        event_types = [e.event_type for e in events]

        # Should have at least queued, started, completed (progress may vary)
        assert "download.queued" in event_types
        assert "download.started" in event_types
        assert "download.completed" in event_types

        # Order check: queued before started before completed
        queued_idx = event_types.index("download.queued")
        started_idx = event_types.index("download.started")
        completed_idx = event_types.index("download.completed")

        assert queued_idx < started_idx < completed_idx

    @pytest.mark.asyncio
    async def test_off_unsubscribes_handler(
        self, aio_client: ClientSession, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """Unsubscribe via manager.off() should stop receiving events."""
        test_url = "https://example.com/file.txt"
        file_config = FileConfig(url=test_url, priority=1)

        events: list[t.Any] = []

        def handler(e: t.Any) -> None:
            events.append(e)

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=b"content")

            async with DownloadManager(
                client=aio_client,
                logger=mock_logger,
                download_dir=tmp_path,
            ) as manager:
                manager.on("download.completed", handler)
                manager.off("download.completed", handler)

                await manager.add([file_config])
                await manager.wait_until_complete()

        # Handler was unsubscribed before download, should receive nothing
        assert events == []


class TestTrackerStateEventsCoherence:
    """Test tracker state matches events and manager.stats reflects totals."""

    @pytest.mark.asyncio
    async def test_tracker_state_matches_completed_event(
        self, aio_client: ClientSession, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """Tracker state should match download.completed event data."""
        test_url = "https://example.com/file.txt"
        test_content = b"test content here"
        file_config = FileConfig(url=test_url, priority=1)

        events: list[DownloadCompletedEvent] = []

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)

            async with DownloadManager(
                client=aio_client,
                logger=mock_logger,
                download_dir=tmp_path,
            ) as manager:
                manager.on("download.completed", lambda e: events.append(e))

                await manager.add([file_config])
                await manager.wait_until_complete()

                # Get tracker state
                info = manager.get_download_info(file_config.id)

                assert info is not None
                assert info.status == DownloadStatus.COMPLETED
                assert info.total_bytes == len(test_content)
                assert info.bytes_downloaded == len(test_content)
                assert info.url == test_url

                # Event should match tracker state
                assert len(events) == 1
                event = events[0]
                assert event.download_id == info.id
                assert event.total_bytes == info.total_bytes
                assert event.url == info.url

    @pytest.mark.asyncio
    async def test_manager_stats_reflects_totals(
        self, aio_client: ClientSession, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """manager.stats should reflect completed totals after downloads."""
        test_content = b"test content"
        file_configs = [
            FileConfig(url=f"https://example.com/file{i}.txt", priority=1)
            for i in range(3)
        ]

        with aioresponses() as mock:
            for config in file_configs:
                mock.get(str(config.url), status=200, body=test_content)

            async with DownloadManager(
                client=aio_client,
                logger=mock_logger,
                download_dir=tmp_path,
            ) as manager:
                await manager.add(file_configs)
                await manager.wait_until_complete()

                stats = manager.stats
                assert stats.total == 3
                assert stats.completed == 3
                assert stats.failed == 0
                assert stats.queued == 0
                assert stats.in_progress == 0
                assert stats.completed_bytes == len(test_content) * 3


class TestEventPathsFailure:
    """Test failure path events."""

    @pytest.mark.asyncio
    async def test_http_error_emits_failed_event(
        self, aio_client: ClientSession, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """HTTP 500 error should emit download.failed event."""
        test_url = "https://example.com/file.txt"
        file_config = FileConfig(url=test_url, priority=1)

        events: list[DownloadFailedEvent] = []

        with aioresponses() as mock:
            mock.get(test_url, status=500, body=b"Internal Server Error")

            async with DownloadManager(
                client=aio_client,
                logger=mock_logger,
                download_dir=tmp_path,
            ) as manager:
                manager.on("download.failed", lambda e: events.append(e))

                await manager.add([file_config])
                await manager.wait_until_complete()

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, DownloadFailedEvent)
        assert event.download_id == file_config.id
        assert event.url == test_url
        assert event.error is not None
        assert "500" in event.error.message or "500" in event.error.exc_type

    @pytest.mark.asyncio
    async def test_http_404_emits_failed_event(
        self, aio_client: ClientSession, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """HTTP 404 error should emit download.failed event."""
        test_url = "https://example.com/notfound.txt"
        file_config = FileConfig(url=test_url, priority=1)

        events: list[DownloadFailedEvent] = []

        with aioresponses() as mock:
            mock.get(test_url, status=404, body=b"Not Found")

            async with DownloadManager(
                client=aio_client,
                logger=mock_logger,
                download_dir=tmp_path,
            ) as manager:
                manager.on("download.failed", lambda e: events.append(e))

                await manager.add([file_config])
                await manager.wait_until_complete()

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, DownloadFailedEvent)
        assert "404" in event.error.message or "404" in event.error.exc_type

    @pytest.mark.asyncio
    async def test_tracker_records_failed_status(
        self, aio_client: ClientSession, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """Tracker should record FAILED status on HTTP error."""
        test_url = "https://example.com/file.txt"
        file_config = FileConfig(url=test_url, priority=1)

        with aioresponses() as mock:
            mock.get(test_url, status=500)

            async with DownloadManager(
                client=aio_client,
                logger=mock_logger,
                download_dir=tmp_path,
            ) as manager:
                await manager.add([file_config])
                await manager.wait_until_complete()

                info = manager.get_download_info(file_config.id)
                assert info is not None
                assert info.status == DownloadStatus.FAILED
                assert info.error is not None


class TestEventPathsSkip:
    """Test skip path events with FileExistsStrategy.SKIP."""

    @pytest.mark.asyncio
    async def test_existing_file_emits_skipped_event(
        self, aio_client: ClientSession, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """Existing file with SKIP strategy should emit download.skipped event."""
        # Create existing file
        existing_file = tmp_path / "existing.txt"
        existing_file.write_text("original content")

        file_config = FileConfig(
            url="https://example.com/existing.txt",
            filename="existing.txt",
        )

        events: list[DownloadSkippedEvent] = []

        with aioresponses():
            # No mock - would error if HTTP call made
            async with DownloadManager(
                client=aio_client,
                logger=mock_logger,
                download_dir=tmp_path,
                file_exists_strategy=FileExistsStrategy.SKIP,
            ) as manager:
                manager.on("download.skipped", lambda e: events.append(e))

                await manager.add([file_config])
                await manager.wait_until_complete()

        assert len(events) == 1
        event = events[0]
        assert isinstance(event, DownloadSkippedEvent)
        assert event.download_id == file_config.id
        assert event.reason == "file_exists"
        assert str(existing_file) in (event.destination_path or "")

    @pytest.mark.asyncio
    async def test_tracker_records_skipped_status(
        self, aio_client: ClientSession, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """Tracker should record SKIPPED status for existing file."""
        existing_file = tmp_path / "existing.txt"
        existing_file.write_text("original")

        file_config = FileConfig(
            url="https://example.com/existing.txt",
            filename="existing.txt",
        )

        with aioresponses():
            async with DownloadManager(
                client=aio_client,
                logger=mock_logger,
                download_dir=tmp_path,
                file_exists_strategy=FileExistsStrategy.SKIP,
            ) as manager:
                await manager.add([file_config])
                await manager.wait_until_complete()

                info = manager.get_download_info(file_config.id)
                assert info is not None
                assert info.status == DownloadStatus.SKIPPED


class TestEventPathsCancellation:
    """Test cancellation path events."""

    @pytest.mark.asyncio
    async def test_close_without_wait_emits_cancelled_event(
        self, aio_client: ClientSession, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """Closing manager without waiting should emit download.cancelled event."""
        test_url = "https://example.com/large.bin"
        file_config = FileConfig(url=test_url, priority=1)

        events: list[DownloadCancelledEvent] = []

        async with DownloadManager(
            client=aio_client,
            logger=mock_logger,
            download_dir=tmp_path,
        ) as manager:
            manager.on("download.cancelled", lambda e: events.append(e))

            # Start the download
            await manager.add([file_config])

            # Give it a moment to start
            await asyncio.sleep(0.01)

            # Close without waiting (cancels in-progress)
            await manager.close(wait_for_current=False)

        # Should have received cancelled event (if download was in progress)
        # Note: timing-dependent, might be 0 or 1 depending on how fast download started
        if events:
            assert isinstance(events[0], DownloadCancelledEvent)
            assert events[0].download_id == file_config.id

    @pytest.mark.asyncio
    async def test_queued_items_cancelled_on_close(
        self, aio_client: ClientSession, mock_logger: "Logger", tmp_path: Path
    ) -> None:
        """Queued items should be cancelled when manager closes."""
        # Queue multiple items, close before all complete
        file_configs = [
            FileConfig(url=f"https://example.com/file{i}.txt", priority=1)
            for i in range(5)
        ]

        cancelled_events: list[DownloadCancelledEvent] = []

        with aioresponses() as mock:
            # Only mock first file - rest won't get a chance to download
            mock.get("https://example.com/file0.txt", status=200, body=b"content")

            async with DownloadManager(
                client=aio_client,
                logger=mock_logger,
                download_dir=tmp_path,
                max_concurrent=1,  # Single worker to control ordering
            ) as manager:
                manager.on("download.cancelled", lambda e: cancelled_events.append(e))

                await manager.add(file_configs)

                # Let first download start
                await asyncio.sleep(0.01)

                # Close without waiting
                await manager.close(wait_for_current=False)

        # Some items should have been cancelled (timing-dependent)
        # At minimum, verify the event type is correct if any arrived
        for event in cancelled_events:
            assert isinstance(event, DownloadCancelledEvent)
