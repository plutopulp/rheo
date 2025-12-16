"""Integration tests for selective download cancellation."""

import asyncio
from pathlib import Path

import pytest
from aioresponses import CallbackResult, aioresponses

from rheo import DownloadManager, DownloadStatus
from rheo.domain import FileConfig
from rheo.domain.cancellation import CancelledFrom, CancelResult
from rheo.events.models import DownloadCancelledEvent


def slow_response(delay: float = 0.5, body: bytes = b"content"):
    """Create a callback that delays before returning response."""

    async def callback(url, **kwargs):
        await asyncio.sleep(delay)
        return CallbackResult(status=200, body=body)

    return callback


class TestCancelInProgress:
    """Integration tests for cancelling in-progress downloads."""

    @pytest.mark.asyncio
    async def test_cancel_in_progress_cleans_up_partial_file(
        self,
        tmp_path: Path,
        aio_client,
    ) -> None:
        """Cancelling mid-download should delete partial file."""
        with aioresponses() as mock:
            # Slow response to give time to cancel
            mock.get(
                "http://example.com/large.txt",
                callback=slow_response(delay=1.0, body=b"x" * 10000),
                repeat=True,
            )

            async with DownloadManager(
                client=aio_client,
                download_dir=tmp_path,
                max_concurrent=1,
            ) as manager:
                file_config = FileConfig(
                    url="http://example.com/large.txt", filename="large.txt"
                )
                await manager.add([file_config])
                await asyncio.sleep(0.1)  # Let download start
                expected_path = tmp_path / "large.txt"
                assert expected_path.exists()

                await manager.cancel(file_config.id)
                await asyncio.sleep(0.2)  # Let cleanup complete

                # Partial file should be cleaned up
                assert not expected_path.exists()

    @pytest.mark.asyncio
    async def test_cancel_in_progress_updates_tracker_status(
        self,
        tmp_path: Path,
        aio_client,
    ) -> None:
        """Cancelled download should show CANCELLED in tracker."""
        with aioresponses() as mock:
            mock.get(
                "http://example.com/file.txt",
                callback=slow_response(delay=1.0),
                repeat=True,
            )

            async with DownloadManager(
                client=aio_client,
                download_dir=tmp_path,
                max_concurrent=1,
            ) as manager:
                file_config = FileConfig(
                    url="http://example.com/file.txt", filename="file.txt"
                )
                await manager.add([file_config])
                await asyncio.sleep(0.1)
                expected_path = tmp_path / "file.txt"
                assert expected_path.exists()

                await manager.cancel(file_config.id)
                await asyncio.sleep(0.2)

                info = manager.get_download_info(file_config.id)
                assert info is not None
                assert info.status == DownloadStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_in_progress_emits_event_with_in_progress_state(
        self,
        tmp_path: Path,
        aio_client,
    ) -> None:
        """Cancelled in-progress download should emit event with
        cancelled_from=IN_PROGRESS."""
        events: list[DownloadCancelledEvent] = []

        with aioresponses() as mock:
            mock.get(
                "http://example.com/file.txt",
                callback=slow_response(delay=1.0),
                repeat=True,
            )

            async with DownloadManager(
                client=aio_client,
                download_dir=tmp_path,
                max_concurrent=1,
            ) as manager:
                manager.on("download.cancelled", lambda e: events.append(e))

                file_config = FileConfig(
                    url="http://example.com/file.txt", filename="file.txt"
                )
                await manager.add([file_config])
                await asyncio.sleep(0.1)

                await manager.cancel(file_config.id)
                await asyncio.sleep(0.2)

                assert len(events) == 1
                assert events[0].cancelled_from == CancelledFrom.IN_PROGRESS
                assert events[0].download_id == file_config.id


class TestCancelQueued:
    """Integration tests for cancelling queued downloads."""

    @pytest.mark.asyncio
    async def test_cancel_queued_never_starts_download(
        self,
        tmp_path: Path,
        aio_client,
    ) -> None:
        """Cancelled queued download should never emit started event."""
        started_ids: list[str] = []

        with aioresponses() as mock:
            # slow_file is slow so queued_file stays queued
            mock.get(
                "http://example.com/slow.txt",
                callback=slow_response(delay=0.5, body=b"content1"),
                repeat=True,
            )
            mock.get("http://example.com/queued.txt", body=b"content2", repeat=True)

            async with DownloadManager(
                client=aio_client,
                download_dir=tmp_path,
                max_concurrent=1,
            ) as manager:
                manager.on(
                    "download.started", lambda e: started_ids.append(e.download_id)
                )

                # slow_file added first - worker grabs it immediately, blocks on
                # slow HTTP
                slow_file = FileConfig(
                    url="http://example.com/slow.txt", filename="slow.txt"
                )
                # queued_file added second - stays in queue while worker is busy
                queued_file = FileConfig(
                    url="http://example.com/queued.txt", filename="queued.txt"
                )
                await manager.add([slow_file, queued_file])
                await asyncio.sleep(0.1)

                # Cancel queued_file while slow_file is downloading
                result = await manager.cancel(queued_file.id)
                assert result == CancelResult.CANCELLED

                await manager.wait_until_complete()

                # queued_file should never have started
                assert slow_file.id in started_ids
                assert queued_file.id not in started_ids

    @pytest.mark.asyncio
    async def test_cancel_queued_emits_event_with_queued_state(
        self,
        tmp_path: Path,
        aio_client,
    ) -> None:
        """Cancelled queued download should emit event with cancelled_from=QUEUED."""
        events: list[DownloadCancelledEvent] = []

        with aioresponses() as mock:
            # slow_file blocks worker so queued_file stays queued
            mock.get(
                "http://example.com/slow.txt",
                callback=slow_response(delay=0.5, body=b"content1"),
                repeat=True,
            )
            mock.get("http://example.com/queued.txt", body=b"content2", repeat=True)

            async with DownloadManager(
                client=aio_client,
                download_dir=tmp_path,
                max_concurrent=1,
            ) as manager:
                manager.on("download.cancelled", lambda e: events.append(e))

                # slow_file added first - worker grabs it, blocks on slow HTTP
                slow_file = FileConfig(
                    url="http://example.com/slow.txt", filename="slow.txt"
                )
                # queued_file added second - stays in queue
                queued_file = FileConfig(
                    url="http://example.com/queued.txt", filename="queued.txt"
                )
                await manager.add([slow_file, queued_file])
                await asyncio.sleep(0.1)

                await manager.cancel(queued_file.id)
                await manager.wait_until_complete()

                # Should have one cancelled event for queued_file
                cancelled_events = [
                    e for e in events if e.download_id == queued_file.id
                ]
                assert len(cancelled_events) == 1
                assert cancelled_events[0].cancelled_from == CancelledFrom.QUEUED


class TestCancelAndContinue:
    """Test that workers continue after cancellation."""

    @pytest.mark.asyncio
    async def test_workers_continue_after_cancel(
        self,
        tmp_path: Path,
        aio_client,
    ) -> None:
        """Cancelling one download should not affect others."""
        with aioresponses() as mock:
            # file1 is slow so file2 and file3 stay queued
            mock.get(
                "http://example.com/file1.txt",
                callback=slow_response(delay=0.3, body=b"content1"),
                repeat=True,
            )
            mock.get("http://example.com/file2.txt", body=b"content2", repeat=True)
            mock.get("http://example.com/file3.txt", body=b"content3", repeat=True)

            async with DownloadManager(
                client=aio_client,
                download_dir=tmp_path,
                max_concurrent=1,
            ) as manager:
                file1 = FileConfig(
                    url="http://example.com/file1.txt", filename="file1.txt"
                )
                file2 = FileConfig(
                    url="http://example.com/file2.txt", filename="file2.txt"
                )
                file3 = FileConfig(
                    url="http://example.com/file3.txt", filename="file3.txt"
                )
                await manager.add([file1, file2, file3])
                await asyncio.sleep(0.1)

                # Cancel file2 (queued)
                await manager.cancel(file2.id)

                await manager.wait_until_complete()

                # file1 and file3 should complete, file2 cancelled
                stats = manager.stats
                assert stats.completed == 2
                assert stats.cancelled == 1

    @pytest.mark.asyncio
    async def test_cancel_does_not_block_queue(
        self,
        tmp_path: Path,
        aio_client,
    ) -> None:
        """Cancelling should not cause queue deadlock."""
        with aioresponses() as mock:
            # First file is slow
            mock.get(
                "http://example.com/file0.txt",
                callback=slow_response(delay=0.2, body=b"content"),
                repeat=True,
            )
            for i in range(1, 5):
                mock.get(
                    f"http://example.com/file{i}.txt", body=b"content", repeat=True
                )

            async with DownloadManager(
                client=aio_client,
                download_dir=tmp_path,
                max_concurrent=2,
            ) as manager:
                files = [
                    FileConfig(
                        url=f"http://example.com/file{i}.txt", filename=f"file{i}.txt"
                    )
                    for i in range(5)
                ]
                await manager.add(files)
                await asyncio.sleep(0.1)

                # Cancel a couple of queued ones
                await manager.cancel(files[2].id)
                await manager.cancel(files[4].id)

                # Should complete without hanging
                await asyncio.wait_for(
                    manager.wait_until_complete(),
                    timeout=5.0,
                )

                stats = manager.stats
                assert stats.completed + stats.cancelled == 5


class TestCancelAlreadyTerminal:
    """Test cancelling downloads that already finished."""

    @pytest.mark.asyncio
    async def test_cancel_completed_returns_already_terminal(
        self,
        tmp_path: Path,
        aio_client,
    ) -> None:
        """Cancelling completed download returns ALREADY_TERMINAL."""
        with aioresponses() as mock:
            mock.get("http://example.com/file.txt", body=b"content")

            async with DownloadManager(
                client=aio_client,
                download_dir=tmp_path,
                max_concurrent=1,
            ) as manager:
                file_config = FileConfig(
                    url="http://example.com/file.txt", filename="file.txt"
                )
                await manager.add([file_config])
                await manager.wait_until_complete()

                result = await manager.cancel(file_config.id)

                assert result == CancelResult.ALREADY_TERMINAL

    @pytest.mark.asyncio
    async def test_cancel_completed_does_not_delete_file(
        self,
        tmp_path: Path,
        aio_client,
    ) -> None:
        """Cancelling completed download should NOT delete the file."""
        with aioresponses() as mock:
            mock.get("https://example.com/file.txt", body=b"downloaded content")

            async with DownloadManager(
                client=aio_client,
                download_dir=tmp_path,
                max_concurrent=1,
            ) as manager:
                expected_path = tmp_path / "file.txt"
                assert not expected_path.exists()
                file_config = FileConfig(
                    url="https://example.com/file.txt",
                    filename="file.txt",
                )
                await manager.add([file_config])
                await manager.wait_until_complete()

                # Verify file was actually created by download
                assert expected_path.exists(), "File should exist after download"
                original_content = expected_path.read_bytes()

                await manager.cancel(file_config.id)

                # File should still exist after cancel
                assert expected_path.exists()
                assert expected_path.read_bytes() == original_content


class TestCancelEventSubscription:
    """Test that cancel events work with manager subscriptions."""

    @pytest.mark.asyncio
    async def test_subscriber_receives_cancel_event(
        self,
        tmp_path: Path,
        aio_client,
    ) -> None:
        """External subscribers should receive cancel events."""
        received_events: list[DownloadCancelledEvent] = []

        with aioresponses() as mock:
            # Slow response so we have time to cancel
            mock.get(
                "http://example.com/file.txt",
                callback=slow_response(delay=0.5),
                repeat=True,
            )

            async with DownloadManager(
                client=aio_client,
                download_dir=tmp_path,
                max_concurrent=1,
            ) as manager:
                # Subscribe before adding downloads
                manager.on("download.cancelled", lambda e: received_events.append(e))

                file_config = FileConfig(
                    url="http://example.com/file.txt", filename="file.txt"
                )
                await manager.add([file_config])
                await asyncio.sleep(0.1)

                await manager.cancel(file_config.id)
                await asyncio.sleep(0.2)

                assert len(received_events) == 1
                event = received_events[0]
                assert event.download_id == file_config.id
                assert event.url == str(file_config.url)
                assert event.cancelled_from in (
                    CancelledFrom.QUEUED,
                    CancelledFrom.IN_PROGRESS,
                )

                await manager.close()
