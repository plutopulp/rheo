"""Integration tests for manager-level retry configuration."""

from pathlib import Path
from unittest.mock import Mock

import pytest
from aioresponses import CallbackResult, aioresponses

from rheo import DownloadManager, DownloadStatus
from rheo.domain import FileConfig
from rheo.domain.retry import RetryConfig, RetryPolicy
from rheo.downloads.retry import RetryHandler
from rheo.events import DownloadEventType


def transient_then_success(fail_count: int, body: bytes = b"content"):
    """Create callback that fails N times with 500, then succeeds."""
    attempts = {"count": 0}

    async def callback(url, **kwargs):
        attempts["count"] += 1
        if attempts["count"] <= fail_count:
            return CallbackResult(
                status=500, body=b"Server Error", reason="Internal Server Error"
            )
        return CallbackResult(status=200, body=body, reason="OK")

    return callback, attempts


def always_fail():
    """Create callback that always fails with 500."""
    attempts = {"count": 0}

    async def callback(url, **kwargs):
        attempts["count"] += 1
        return CallbackResult(
            status=500, body=b"Server Error", reason="Internal Server Error"
        )

    return callback, attempts


class TestManagerWithRetryHandler:
    """Test manager with retry handler retries transient errors."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "max_retries,fail_count",
        [
            (1, 1),  # 1 retry, fail once -> succeed on retry
            (2, 2),  # 2 retries, fail twice -> succeed on 2nd retry
            (3, 1),  # 3 retries, fail once -> succeed on 1st retry
        ],
    )
    async def test_retries_transient_errors_and_succeeds(
        self,
        tmp_path: Path,
        aio_client,
        max_retries: int,
        fail_count: int,
        mock_logger: Mock,
    ) -> None:
        """Manager with retry handler retries on transient errors."""
        callback, attempts = transient_then_success(fail_count)
        retry_events: list = []

        handler = RetryHandler(
            RetryConfig(
                max_retries=max_retries,
                base_delay=0.01,
                jitter=False,
            )
        )

        with aioresponses() as mock:
            mock.get("http://example.com/file.txt", callback=callback, repeat=True)

            async with DownloadManager(
                client=aio_client,
                download_dir=tmp_path,
                retry_handler=handler,
                logger=mock_logger,
            ) as manager:
                path = tmp_path / "file.txt"
                assert not path.exists()
                manager.on(
                    DownloadEventType.RETRYING,
                    lambda e: retry_events.append(e),
                )

                file_config = FileConfig(
                    url="http://example.com/file.txt",
                    filename="file.txt",
                )
                await manager.add([file_config])
                await manager.wait_until_complete()
                assert path.exists()

                info = manager.get_download_info(file_config.id)
                assert info is not None
                assert info.status == DownloadStatus.COMPLETED

        # Verify retry count via both callback execution and events
        assert attempts["count"] == fail_count + 1  # fails + 1 success
        assert len(retry_events) == fail_count

    @pytest.mark.asyncio
    async def test_fails_after_max_retries_exhausted(
        self,
        tmp_path: Path,
        aio_client,
        mock_logger: Mock,
    ) -> None:
        """Manager fails download after all retries exhausted."""
        max_retries = 2
        callback, attempts = always_fail()

        handler = RetryHandler(
            RetryConfig(
                max_retries=max_retries,
                base_delay=0.01,
                jitter=False,
            )
        )

        with aioresponses() as mock:
            mock.get("http://example.com/file.txt", callback=callback, repeat=True)

            async with DownloadManager(
                client=aio_client,
                download_dir=tmp_path,
                retry_handler=handler,
                logger=mock_logger,
            ) as manager:
                path = tmp_path / "file.txt"
                assert not path.exists()

                file_config = FileConfig(
                    url="http://example.com/file.txt",
                    filename="file.txt",
                )
                await manager.add([file_config])
                await manager.wait_until_complete()

                # File should not exist since download failed
                assert not path.exists()

                info = manager.get_download_info(file_config.id)
                assert info is not None
                assert info.status == DownloadStatus.FAILED

        # Verify callback was called exactly max_retries + 1 times (initial + retries)
        assert attempts["count"] == max_retries + 1


class TestManagerWithoutRetryHandler:
    """Test manager without retry handler fails immediately."""

    @pytest.mark.asyncio
    async def test_no_retry_with_default_handler(
        self,
        tmp_path: Path,
        aio_client,
        mock_logger: Mock,
    ) -> None:
        """Manager without retry handler fails immediately on error."""
        callback, attempts = always_fail()
        retry_events: list = []

        with aioresponses() as mock:
            mock.get("http://example.com/file.txt", callback=callback, repeat=True)

            async with DownloadManager(
                client=aio_client,
                download_dir=tmp_path,
                logger=mock_logger,
                # No retry_handler - uses NullRetryHandler
            ) as manager:
                manager.on(
                    DownloadEventType.RETRYING,
                    lambda e: retry_events.append(e),
                )
                path = tmp_path / "file.txt"
                assert not path.exists()

                file_config = FileConfig(
                    url="http://example.com/file.txt",
                    filename="file.txt",
                )
                await manager.add([file_config])
                await manager.wait_until_complete()

                # File should not exist since download failed
                assert not path.exists()

                info = manager.get_download_info(file_config.id)
                assert info is not None
                assert info.status == DownloadStatus.FAILED

        # No retry events should be emitted
        assert len(retry_events) == 0
        # Callback should only be called once (no retries)
        assert attempts["count"] == 1


class TestManagerWithCustomRetryPolicy:
    """Test manager with custom retry policy."""

    @pytest.mark.asyncio
    async def test_custom_policy_treats_404_as_transient(
        self,
        tmp_path: Path,
        aio_client,
        mock_logger: Mock,
    ) -> None:
        """Custom policy can treat normally-permanent errors as transient."""
        attempts = {"count": 0}

        async def callback_404(url, **kwargs):
            attempts["count"] += 1
            if attempts["count"] <= 1:
                return CallbackResult(status=404, body=b"Not Found", reason="Not Found")
            return CallbackResult(status=200, body=b"content", reason="OK")

        custom_policy = RetryPolicy(
            transient_status_codes=frozenset({404, 500, 502, 503}),
            permanent_status_codes=frozenset({400, 401, 403}),
        )
        handler = RetryHandler(
            RetryConfig(
                max_retries=2,
                base_delay=0.01,
                jitter=False,
                policy=custom_policy,
            )
        )

        with aioresponses() as mock:
            mock.get("http://example.com/file.txt", callback=callback_404, repeat=True)

            async with DownloadManager(
                client=aio_client,
                download_dir=tmp_path,
                retry_handler=handler,
                logger=mock_logger,
            ) as manager:
                path = tmp_path / "file.txt"
                assert not path.exists()

                file_config = FileConfig(
                    url="http://example.com/file.txt",
                    filename="file.txt",
                )
                await manager.add([file_config])
                await manager.wait_until_complete()

                assert path.exists()

                info = manager.get_download_info(file_config.id)
                assert info is not None
                assert info.status == DownloadStatus.COMPLETED

        # 1 fail + 1 success
        assert attempts["count"] == 2


class TestRetryEventsFlowThroughManager:
    """Test retry events are accessible via manager.on()."""

    @pytest.mark.asyncio
    async def test_retry_event_payload(
        self,
        tmp_path: Path,
        aio_client,
        mock_logger: Mock,
    ) -> None:
        """Retry events contain expected payload fields."""
        callback, attempts = transient_then_success(fail_count=1)
        retry_events: list = []

        handler = RetryHandler(
            RetryConfig(
                max_retries=3,
                base_delay=0.05,
                jitter=False,
            )
        )

        with aioresponses() as mock:
            mock.get("http://example.com/file.txt", callback=callback, repeat=True)

            async with DownloadManager(
                client=aio_client,
                download_dir=tmp_path,
                retry_handler=handler,
                logger=mock_logger,
            ) as manager:
                manager.on(DownloadEventType.RETRYING, lambda e: retry_events.append(e))

                path = tmp_path / "file.txt"
                assert not path.exists()

                file_config = FileConfig(
                    url="http://example.com/file.txt",
                    filename="file.txt",
                )
                await manager.add([file_config])
                await manager.wait_until_complete()

                assert path.exists()

        assert len(retry_events) == 1
        event = retry_events[0]
        assert event.url == "http://example.com/file.txt"
        assert event.retry == 1  # First retry
        assert event.max_retries == 3
        assert event.delay_seconds == 0.05
        assert event.error is not None
        # Verify callback execution count
        assert attempts["count"] == 2  # 1 fail + 1 success
