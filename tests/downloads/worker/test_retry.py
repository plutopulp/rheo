"""Tests for DownloadWorker retry integration."""

import asyncio
from pathlib import Path
from unittest.mock import Mock

import aiohttp
import pytest
from aioresponses import aioresponses
from attr import dataclass

from rheo.domain.retry import RetryConfig, RetryPolicy
from rheo.downloads import (
    DownloadWorker,
    ErrorCategoriser,
    NullRetryHandler,
    RetryHandler,
)
from rheo.downloads.worker.base import BaseWorker
from rheo.events.base import BaseEmitter


@pytest.fixture
def retry_config() -> RetryConfig:
    """Provide a retry config with fast retries for testing."""
    return RetryConfig(max_retries=2, base_delay=0.01, jitter=False)


@pytest.fixture
def retry_handler(
    mock_logger: Mock, mock_emitter: BaseEmitter, retry_config: RetryConfig
) -> RetryHandler:
    """Provide a RetryHandler for testing."""
    categoriser = ErrorCategoriser(retry_config.policy)
    return RetryHandler(
        config=retry_config,
        logger=mock_logger,
        emitter=mock_emitter,
        categoriser=categoriser,
    )


@pytest.fixture
def worker_with_retry(
    aio_client: Mock,
    mock_logger: Mock,
    mock_emitter: BaseEmitter,
    retry_handler: RetryHandler,
) -> DownloadWorker:
    """Provide a DownloadWorker with retry enabled."""
    return DownloadWorker(
        client=aio_client,
        logger=mock_logger,
        emitter=mock_emitter,
        retry_handler=retry_handler,
    )


@pytest.fixture
def worker_without_retry(
    aio_client: Mock, mock_logger: Mock, mock_emitter: BaseEmitter
) -> DownloadWorker:
    """Provide a DownloadWorker without retry (None)."""
    return DownloadWorker(
        client=aio_client,
        logger=mock_logger,
        emitter=mock_emitter,
        retry_handler=None,
    )


class TestWorkerRetryInitialization:
    """Test worker initialization with retry handler."""

    def test_init_with_retry_handler(
        self,
        aio_client: Mock,
        mock_logger: Mock,
        mock_emitter: BaseEmitter,
        retry_handler: RetryHandler,
    ) -> None:
        """Worker can be initialized with a retry handler."""
        worker = DownloadWorker(
            client=aio_client,
            logger=mock_logger,
            emitter=mock_emitter,
            retry_handler=retry_handler,
        )
        assert worker.retry_handler is retry_handler

    def test_init_without_retry_handler(
        self, aio_client: Mock, mock_logger: Mock, mock_emitter: BaseEmitter
    ) -> None:
        """Worker defaults to NullRetryHandler when None provided."""
        worker = DownloadWorker(
            client=aio_client,
            logger=mock_logger,
            emitter=mock_emitter,
            retry_handler=None,
        )
        assert isinstance(worker.retry_handler, NullRetryHandler)

    def test_init_with_default_retry_handler(
        self, aio_client: Mock, mock_logger: Mock
    ) -> None:
        """Worker uses NullRetryHandler by default."""
        worker = DownloadWorker(client=aio_client, logger=mock_logger)
        assert isinstance(worker.retry_handler, NullRetryHandler)


@dataclass
class DownloadTestData:
    """Test data container for download tests."""

    url: str
    content: bytes
    path: Path


@pytest.fixture
def test_data(tmp_path: Path) -> DownloadTestData:
    """Provide test data for download tests."""
    return DownloadTestData(
        url="https://example.com/file.txt",
        content=b"test content",
        path=tmp_path / "file.txt",
    )


class TestWorkerRetryOnTransientErrors:
    """Test retry behavior on transient errors."""

    @pytest.mark.asyncio
    async def test_retries_on_500_error(
        self,
        worker_with_retry: BaseWorker,
        test_data: DownloadTestData,
        mock_emitter: Mock,
    ) -> None:
        """Worker retries on transient 500 Internal Server Error."""

        with aioresponses() as mock:
            # First attempt fails with 500, second succeeds
            mock.get(test_data.url, status=500)
            mock.get(test_data.url, status=200, body=test_data.content)

            await worker_with_retry.download(
                test_data.url, test_data.path, download_id="test-id"
            )

        # File should exist with correct content
        assert test_data.path.exists()
        assert test_data.path.read_bytes() == test_data.content

        # Should have emitted retry events
        retry_events = [
            call
            for call in mock_emitter.emit.call_args_list
            if call[0][0] == "worker.retry"
        ]
        assert len(retry_events) >= 1

    @pytest.mark.asyncio
    async def test_retries_on_timeout(
        self, worker_with_retry: BaseWorker, test_data: DownloadTestData
    ) -> None:
        """Worker retries on timeout errors."""
        with aioresponses() as mock:
            # First attempt times out, second succeeds
            mock.get(test_data.url, exception=asyncio.TimeoutError())
            mock.get(test_data.url, status=200, body=test_data.content)

            await worker_with_retry.download(
                test_data.url, test_data.path, download_id="test-id"
            )

        assert test_data.path.exists()
        assert test_data.path.read_bytes() == test_data.content

    @pytest.mark.asyncio
    async def test_retries_on_connection_error(
        self, worker_with_retry: BaseWorker, test_data: DownloadTestData
    ) -> None:
        """Worker retries on connection errors."""
        with aioresponses() as mock:
            # First attempt connection error, second succeeds
            # Use ClientOSError as it's easier to instantiate for testing
            mock.get(
                test_data.url, exception=aiohttp.ClientOSError("Connection failed")
            )
            mock.get(test_data.url, status=200, body=test_data.content)

            await worker_with_retry.download(
                test_data.url, test_data.path, download_id="test-id"
            )

    @pytest.mark.asyncio
    async def test_fails_after_max_retries(
        self, worker_with_retry: BaseWorker, test_data: DownloadTestData
    ) -> None:
        """Worker fails after exhausting all retries."""
        with aioresponses() as mock:
            # All attempts fail with 500
            mock.get(test_data.url, status=500, repeat=True)

            with pytest.raises(aiohttp.ClientResponseError):
                await worker_with_retry.download(
                    test_data.url, test_data.path, download_id="test-id"
                )

        # File should not exist (cleaned up)
        assert not test_data.path.exists()


class TestWorkerRetryOnPermanentErrors:
    """Test that permanent errors are not retried."""

    @pytest.mark.asyncio
    async def test_no_retry_on_404(
        self, worker_with_retry: BaseWorker, test_data: DownloadTestData
    ) -> None:
        """Worker does not retry on 404 Not Found (permanent error)."""

        with aioresponses() as mock:
            mock.get(test_data.url, status=404)

            with pytest.raises(aiohttp.ClientResponseError):
                await worker_with_retry.download(
                    test_data.url, test_data.path, download_id="test-id"
                )

        assert not test_data.path.exists()

    @pytest.mark.asyncio
    async def test_no_retry_on_403(
        self, worker_with_retry: BaseWorker, test_data: DownloadTestData
    ) -> None:
        """Worker does not retry on 403 Forbidden (permanent error)."""
        with aioresponses() as mock:
            mock.get(test_data.url, status=403)

            with pytest.raises(aiohttp.ClientResponseError):
                await worker_with_retry.download(
                    test_data.url, test_data.path, download_id="test-id"
                )

        assert not test_data.path.exists()

    @pytest.mark.asyncio
    async def test_no_retry_on_file_not_found_error(
        self, worker_with_retry: BaseWorker, test_data: DownloadTestData
    ) -> None:
        """Worker does not retry on filesystem errors like FileNotFoundError."""
        # Use a path with non-existent parent directory
        test_data.path = test_data.path.parent / "nonexistent" / "path" / "file.txt"
        with aioresponses() as mock:
            mock.get(test_data.url, status=200, body=b"test")

            with pytest.raises(FileNotFoundError):
                await worker_with_retry.download(
                    test_data.url, test_data.path, download_id="test-id"
                )


class TestWorkerWithoutRetry:
    """Test worker behavior when retry is disabled."""

    @pytest.mark.asyncio
    async def test_no_retry_when_disabled(
        self, worker_without_retry: BaseWorker, test_data: DownloadTestData
    ) -> None:
        """Worker fails immediately when retry is disabled."""

        with aioresponses() as mock:
            mock.get(test_data.url, status=500)

            with pytest.raises(aiohttp.ClientResponseError):
                await worker_without_retry.download(
                    test_data.url, test_data.path, download_id="test-id"
                )

        assert not test_data.path.exists()

    @pytest.mark.asyncio
    async def test_success_without_retry(
        self, worker_without_retry: BaseWorker, test_data: DownloadTestData
    ) -> None:
        """Worker can still succeed when retry is disabled."""

        with aioresponses() as mock:
            mock.get(test_data.url, status=200, body=test_data.content)

            await worker_without_retry.download(
                test_data.url, test_data.path, download_id="test-id"
            )

        assert test_data.path.exists()
        assert test_data.path.read_bytes() == test_data.content


class TestWorkerRetryEvents:
    """Test retry event emission."""

    @pytest.mark.asyncio
    async def test_emits_retry_events(
        self,
        worker_with_retry: BaseWorker,
        test_data: DownloadTestData,
        mock_emitter: Mock,
    ) -> None:
        """Worker emits retry events during retries."""

        with aioresponses() as mock:
            # Fail once, then succeed
            mock.get(test_data.url, status=500)
            mock.get(test_data.url, status=200, body=test_data.content)

            await worker_with_retry.download(
                test_data.url, test_data.path, download_id="test-id"
            )

        # Check retry events were emitted
        retry_events = [
            call
            for call in mock_emitter.emit.call_args_list
            if call[0][0] == "worker.retry"
        ]
        assert len(retry_events) == 1

        # Verify retry event payload
        retry_event = retry_events[0][0][1]
        assert retry_event.url == test_data.url
        assert retry_event.attempt == 1
        assert retry_event.max_retries == 2


class TestWorkerRetryWithCustomPolicy:
    """Test worker with custom retry policies."""

    @pytest.mark.asyncio
    async def test_custom_policy_treats_404_as_transient(
        self,
        aio_client: Mock,
        mock_logger: Mock,
        mock_emitter: BaseEmitter,
        test_data: DownloadTestData,
    ) -> None:
        """Worker can use custom policy to retry normally permanent errors."""
        # Custom policy that treats 404 as transient
        custom_policy = RetryPolicy(
            transient_status_codes=frozenset({404, 500}),
            permanent_status_codes=frozenset(),
        )
        custom_config = RetryConfig(
            max_retries=2, base_delay=0.01, jitter=False, policy=custom_policy
        )

        # Create custom retry handler with custom policy
        custom_categoriser = ErrorCategoriser(custom_policy)
        custom_retry_handler = RetryHandler(
            config=custom_config,
            logger=mock_logger,
            emitter=mock_emitter,
            categoriser=custom_categoriser,
        )

        worker = DownloadWorker(
            client=aio_client,
            logger=mock_logger,
            emitter=mock_emitter,
            retry_handler=custom_retry_handler,
        )

        with aioresponses() as mock:
            # 404 then success
            mock.get(test_data.url, status=404)
            mock.get(test_data.url, status=200, body=test_data.content)

            await worker.download(test_data.url, test_data.path, download_id="test-id")

        assert test_data.path.exists()
        assert test_data.path.read_bytes() == test_data.content

    @pytest.mark.asyncio
    async def test_retry_uses_fresh_speed_calculator(
        self,
        worker_with_real_events: BaseWorker,
        tmp_path: Path,
        test_data: DownloadTestData,
    ) -> None:
        """Test that each retry attempt gets a fresh SpeedCalculator with clean state.

        Bug: When a download is retried, the same SpeedCalculator instance is reused,
        retaining stale state (_chunks, _start_time, _last_time, _last_bytes) from
        the failed attempt. This causes corrupted speed metrics on retry.

        Expected: Each retry attempt should get a fresh calculator or reset the
        existing one.
        """
        test_data.content = b"a" * 5000  # 5KB for multiple chunks
        # Collect speed events to verify calculator state
        speed_events = []
        worker_with_real_events.emitter.on(
            "worker.speed_updated", lambda e: speed_events.append(e)
        )

        with aioresponses() as mock:
            # First attempt: fails immediately (transient error - no chunks)
            mock.get(test_data.url, status=503, body="Service Unavailable")
            # Second attempt: succeeds with full download
            mock.get(
                test_data.url,
                status=200,
                body=test_data.content,
                headers={"Content-Length": str(len(test_data.content))},
            )

            await worker_with_real_events.download(
                test_data.url, test_data.path, download_id="test-id", chunk_size=1024
            )

        # Verify file was successfully downloaded
        assert test_data.path.exists()
        assert test_data.path.read_bytes() == test_data.content

        # Verify we got speed events (should be from successful attempt only)
        assert len(speed_events) > 0

        # Critical check: First speed event of successful attempt should have
        # elapsed_seconds starting near 0, not continuing from failed attempt
        # If calculator was reused, elapsed_seconds would be much higher
        first_speed_event = speed_events[0]

        # First event should have very small elapsed time (< 1 second typically)
        # If calculator state was stale, this would be much larger
        assert first_speed_event.elapsed_seconds < 1.0, (
            f"Speed calculator appears to have stale state from failed attempt. "
            f"First event elapsed_seconds: {first_speed_event.elapsed_seconds}"
        )
