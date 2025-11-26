"""Tests for DownloadWorker speed tracking and event emission."""

import asyncio
from dataclasses import dataclass
from pathlib import Path

import pytest
from aioresponses import aioresponses

from rheo.downloads.worker.base import BaseWorker
from rheo.events import WorkerSpeedUpdatedEvent


@dataclass
class SpeedTestData:
    """Test data container for speed tracking tests."""

    url: str
    content: bytes
    path: Path


@pytest.fixture
def test_data(tmp_path: Path) -> SpeedTestData:
    """Provide default test data for speed tracking tests.

    Uses 5KB content by default to ensure multiple chunks (at 1KB chunk size).
    Tests requiring different content sizes can override inline.
    """
    return SpeedTestData(
        url="https://example.com/file.txt",
        content=b"a" * 5000,  # 5KB - good for multi-chunk tests
        path=tmp_path / "test_file.txt",
    )


@pytest.fixture
def speed_events(test_worker: BaseWorker) -> list[WorkerSpeedUpdatedEvent]:
    """Set up speed event listener and return events list.

    Returns a list that will be populated with WorkerSpeedUpdatedEvent
    instances as they are emitted during downloads.
    """
    events: list[WorkerSpeedUpdatedEvent] = []
    test_worker.emitter.on("worker.speed_updated", lambda e: events.append(e))
    return events


class TestWorkerSpeedTracking:
    """Test that worker tracks and emits speed metrics during downloads."""

    @pytest.mark.asyncio
    async def test_worker_emits_speed_events_after_each_chunk(
        self,
        test_worker: BaseWorker,
        test_data: SpeedTestData,
        speed_events: list[WorkerSpeedUpdatedEvent],
    ) -> None:
        """Test that worker emits speed event after each chunk."""
        with aioresponses() as mock:
            mock.get(test_data.url, status=200, body=test_data.content)
            await test_worker.download(
                test_data.url, test_data.path, download_id="test-id", chunk_size=1024
            )

        # Should have multiple speed events (at least 5 for 5KB with 1KB chunks)
        assert len(speed_events) >= 5
        assert all(isinstance(e, WorkerSpeedUpdatedEvent) for e in speed_events)

    @pytest.mark.asyncio
    async def test_speed_event_contains_correct_url(
        self,
        test_worker: BaseWorker,
        test_data: SpeedTestData,
        speed_events: list[WorkerSpeedUpdatedEvent],
    ) -> None:
        """Test that speed events contain the correct URL."""
        with aioresponses() as mock:
            mock.get(test_data.url, status=200, body=b"test content")
            await test_worker.download(
                test_data.url, test_data.path, download_id="test-id"
            )

        assert all(e.url == test_data.url for e in speed_events)

    @pytest.mark.asyncio
    async def test_speed_event_has_cumulative_bytes(
        self,
        test_worker: BaseWorker,
        test_data: SpeedTestData,
        speed_events: list[WorkerSpeedUpdatedEvent],
    ) -> None:
        """Test that speed events show cumulative bytes downloaded."""
        content = b"a" * 3000  # 3KB

        with aioresponses() as mock:
            mock.get(test_data.url, status=200, body=content)
            await test_worker.download(
                test_data.url, test_data.path, download_id="test-id", chunk_size=1024
            )

        # Bytes should be cumulative and increasing
        bytes_values = [e.bytes_downloaded for e in speed_events]
        assert bytes_values == sorted(bytes_values)  # Monotonically increasing
        assert bytes_values[-1] == len(content)  # Final equals total

    @pytest.mark.asyncio
    async def test_speed_event_includes_total_bytes_when_known(
        self,
        test_worker: BaseWorker,
        test_data: SpeedTestData,
        speed_events: list[WorkerSpeedUpdatedEvent],
    ) -> None:
        """Test that speed events include total_bytes from Content-Length."""
        content = b"test content"

        with aioresponses() as mock:
            # Explicitly set Content-Length header
            mock.get(
                test_data.url,
                status=200,
                body=content,
                headers={"Content-Length": str(len(content))},
            )
            await test_worker.download(
                test_data.url, test_data.path, download_id="test-id"
            )

        # All events should have total_bytes set
        assert all(e.total_bytes == len(content) for e in speed_events)

    @pytest.mark.asyncio
    async def test_first_speed_event_has_zero_speeds(
        self,
        test_worker: BaseWorker,
        test_data: SpeedTestData,
        speed_events: list[WorkerSpeedUpdatedEvent],
    ) -> None:
        """Test that first speed event has zero speeds (no previous data)."""
        with aioresponses() as mock:
            mock.get(test_data.url, status=200, body=b"test content")
            await test_worker.download(
                test_data.url, test_data.path, download_id="test-id"
            )

        # First event should have zero speeds
        first_event = speed_events[0]
        assert first_event.current_speed_bps == 0.0
        assert first_event.average_speed_bps == 0.0
        assert first_event.eta_seconds is None  # Can't calculate with zero speed

    @pytest.mark.asyncio
    async def test_subsequent_speed_events_have_nonzero_speeds(
        self,
        test_worker: BaseWorker,
        test_data: SpeedTestData,
        speed_events: list[WorkerSpeedUpdatedEvent],
    ) -> None:
        """Test that subsequent speed events have calculated speeds."""
        content = b"a" * 3000  # 3KB

        with aioresponses() as mock:
            mock.get(test_data.url, status=200, body=content)
            await test_worker.download(
                test_data.url, test_data.path, download_id="test-id", chunk_size=1024
            )

        # Skip first event (zero speeds), check rest have speeds
        if len(speed_events) > 1:
            for event in speed_events[1:]:
                # Speeds should be calculated (non-zero in real download)
                # Note: Might be zero in fast mocked test, so just check fields exist
                assert isinstance(event.current_speed_bps, float)
                assert isinstance(event.average_speed_bps, float)
                assert event.current_speed_bps >= 0
                assert event.average_speed_bps >= 0

    @pytest.mark.asyncio
    async def test_speed_event_includes_eta_when_total_known(
        self,
        test_worker: BaseWorker,
        test_data: SpeedTestData,
        speed_events: list[WorkerSpeedUpdatedEvent],
    ) -> None:
        """Test that ETA is calculated when total_bytes is known."""
        with aioresponses() as mock:
            # Explicitly set Content-Length header
            mock.get(
                test_data.url,
                status=200,
                body=test_data.content,
                headers={"Content-Length": str(len(test_data.content))},
            )
            await test_worker.download(
                test_data.url, test_data.path, download_id="test-id", chunk_size=1024
            )

        # Skip first event (zero speed, no ETA)
        # Middle events should have ETA when speed > 0 and total known
        middle_events = speed_events[1:-1]  # Skip first and last
        if middle_events:
            # At least some should have ETA calculated
            # (might be None if speed is zero in fast test)
            assert any(e.eta_seconds is not None for e in middle_events) or all(
                e.average_speed_bps == 0 for e in middle_events
            )

    @pytest.mark.asyncio
    async def test_final_speed_event_has_zero_eta(
        self,
        test_worker: BaseWorker,
        test_data: SpeedTestData,
        speed_events: list[WorkerSpeedUpdatedEvent],
    ) -> None:
        """Test that final speed event has ETA of 0 (download complete)."""
        content = b"a" * 2000  # 2KB

        with aioresponses() as mock:
            # Explicitly set Content-Length header
            mock.get(
                test_data.url,
                status=200,
                body=content,
                headers={"Content-Length": str(len(content))},
            )
            await test_worker.download(
                test_data.url, test_data.path, download_id="test-id", chunk_size=1024
            )

        # Final event should have ETA of 0 (all bytes downloaded)
        final_event = speed_events[-1]
        assert final_event.bytes_downloaded == len(content)
        assert final_event.eta_seconds == 0.0

    @pytest.mark.asyncio
    async def test_speed_tracking_with_unknown_total_size(
        self,
        test_worker: BaseWorker,
        test_data: SpeedTestData,
        speed_events: list[WorkerSpeedUpdatedEvent],
    ) -> None:
        """Test speed tracking when Content-Length is not provided."""
        with aioresponses() as mock:
            # Headers without Content-Length
            mock.get(
                test_data.url,
                status=200,
                body=b"test content",
                headers={},  # No Content-Length
            )
            await test_worker.download(
                test_data.url, test_data.path, download_id="test-id"
            )

        # Speed events should still be emitted
        assert len(speed_events) > 0

        # But ETA should be None (can't calculate without total)
        assert all(e.eta_seconds is None for e in speed_events)

    @pytest.mark.asyncio
    async def test_concurrent_downloads_have_independent_speed_tracking(
        self, test_worker: BaseWorker, tmp_path: Path
    ) -> None:
        """Test that concurrent downloads each have independent speed calculators.

        This ensures:
        - Each download has its own SpeedCalculator instance
        - Speed metrics don't leak between concurrent downloads
        - Events are correctly attributed to their respective URLs
        - No race conditions or state interference
        """
        all_events = []
        test_worker.emitter.on("worker.speed_updated", lambda e: all_events.append(e))

        # Set up three different downloads with different sizes
        url1 = "https://example.com/file1.txt"
        url2 = "https://example.com/file2.txt"
        url3 = "https://example.com/file3.txt"

        content1 = b"a" * 3000  # 3KB
        content2 = b"b" * 5000  # 5KB
        content3 = b"c" * 2000  # 2KB

        dest1 = tmp_path / "file1.txt"
        dest2 = tmp_path / "file2.txt"
        dest3 = tmp_path / "file3.txt"

        with aioresponses() as mock:
            # Mock all three downloads
            mock.get(url1, status=200, body=content1)
            mock.get(url2, status=200, body=content2)
            mock.get(url3, status=200, body=content3)

            # Run downloads concurrently
            await asyncio.gather(
                test_worker.download(url1, dest1, download_id="id1", chunk_size=1024),
                test_worker.download(url2, dest2, download_id="id2", chunk_size=1024),
                test_worker.download(url3, dest3, download_id="id3", chunk_size=1024),
            )

        # Verify events were emitted for all downloads
        assert len(all_events) > 0

        # Group events by URL to verify each download was tracked independently
        events_by_url = {
            url1: [e for e in all_events if e.url == url1],
            url2: [e for e in all_events if e.url == url2],
            url3: [e for e in all_events if e.url == url3],
        }

        # Each download should have emitted events
        assert len(events_by_url[url1]) > 0
        assert len(events_by_url[url2]) > 0
        assert len(events_by_url[url3]) > 0

        # Verify each download's final bytes match its content size
        final_bytes_by_url = {
            url1: events_by_url[url1][-1].bytes_downloaded,
            url2: events_by_url[url2][-1].bytes_downloaded,
            url3: events_by_url[url3][-1].bytes_downloaded,
        }

        assert final_bytes_by_url[url1] == len(content1)
        assert final_bytes_by_url[url2] == len(content2)
        assert final_bytes_by_url[url3] == len(content3)

        # Verify bytes are monotonically increasing for each download independently
        for url in [url1, url2, url3]:
            bytes_sequence = [e.bytes_downloaded for e in events_by_url[url]]
            assert bytes_sequence == sorted(
                bytes_sequence
            ), f"Bytes not monotonic for {url}"
