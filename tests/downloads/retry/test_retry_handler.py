"""Tests for retry handler with exponential backoff."""

import asyncio
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture

from rheo.domain.retry import RetryConfig, RetryPolicy
from rheo.downloads import ErrorCategoriser, RetryHandler
from rheo.downloads.retry.base import BaseRetryHandler
from rheo.events.base import BaseEmitter


@pytest.fixture
def default_retry_handler(mock_logger: Mock, mock_emitter: BaseEmitter) -> RetryHandler:
    """Provide a retry handler with default configuration."""
    config = RetryConfig(max_retries=3, base_delay=0.01, jitter=False)
    categoriser = ErrorCategoriser(RetryPolicy())
    return RetryHandler(config, mock_logger, mock_emitter, categoriser)


class TestRetryHandlerSuccessfulOperations:
    """Test retry handler with successful operations."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(
        self, default_retry_handler: BaseRetryHandler
    ) -> None:
        """No retry needed if operation succeeds on first attempt."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await default_retry_handler.execute_with_retry(
            operation, url="http://example.com/file.txt", download_id="test-id"
        )

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_success_after_retries(
        self, default_retry_handler: BaseRetryHandler
    ) -> None:
        """Operation succeeds after transient failures."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise asyncio.TimeoutError("Timeout")
            return "success"

        result = await default_retry_handler.execute_with_retry(
            operation, url="http://example.com/file.txt", download_id="test-id"
        )

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_returns_operation_result(
        self, default_retry_handler: BaseRetryHandler
    ) -> None:
        """Handler returns the operation's result value."""
        operation_result = {"data": "test", "count": 42}

        async def operation():
            return operation_result

        result = await default_retry_handler.execute_with_retry(
            operation, url="http://example.com/file.txt", download_id="test-id"
        )

        assert result == operation_result


class TestRetryHandlerPermanentErrors:
    """Test retry handler with permanent errors."""

    @pytest.mark.asyncio
    async def test_no_retry_on_permanent_error(
        self, default_retry_handler: BaseRetryHandler
    ) -> None:
        """Does not retry permanent errors."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            raise PermissionError("Permission denied")

        with pytest.raises(PermissionError, match="Permission denied"):
            await default_retry_handler.execute_with_retry(
                operation, url="http://example.com/file.txt", download_id="test-id"
            )

        assert call_count == 1  # Only tried once

    @pytest.mark.asyncio
    async def test_permanent_error_logged(
        self, mock_logger: Mock, default_retry_handler: BaseRetryHandler
    ) -> None:
        """Permanent errors are logged but not retried."""

        async def operation():
            raise FileNotFoundError("File not found")

        with pytest.raises(FileNotFoundError):
            await default_retry_handler.execute_with_retry(
                operation, url="http://example.com/file.txt", download_id="test-id"
            )

        # Should log the non-transient error
        mock_logger.debug.assert_called_once()
        assert "Non-transient" in mock_logger.debug.call_args[0][0]


class TestRetryHandlerTransientErrors:
    """Test retry handler with transient errors."""

    @pytest.mark.asyncio
    async def test_retries_transient_errors(
        self, default_retry_handler: BaseRetryHandler
    ) -> None:
        """Retries on transient errors up to max_retries."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            raise asyncio.TimeoutError("Always times out")

        with pytest.raises(asyncio.TimeoutError):
            await default_retry_handler.execute_with_retry(
                operation, url="http://example.com/file.txt", download_id="test-id"
            )

        # Should try: 1 initial + 3 retries = 4 total
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_respects_max_retries_override(
        self, default_retry_handler: BaseRetryHandler
    ) -> None:
        """Respects per-call max_retries override."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            raise asyncio.TimeoutError("Always times out")

        with pytest.raises(asyncio.TimeoutError):
            await default_retry_handler.execute_with_retry(
                operation,
                url="http://example.com/file.txt",
                download_id="test-id",
                max_retries=1,
            )

        # Should try: 1 initial + 1 retry = 2 total
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_waits_between_retries(
        self, default_retry_handler: BaseRetryHandler, mocker: MockerFixture
    ) -> None:
        """Waits with exponential backoff between retries."""
        sleep_spy = mocker.spy(asyncio, "sleep")
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise asyncio.TimeoutError("Timeout")
            return "success"

        await default_retry_handler.execute_with_retry(
            operation, url="http://example.com/file.txt", download_id="test-id"
        )

        # Should have called sleep twice (between attempts 1-2 and 2-3)
        assert sleep_spy.call_count == 2
        # Delays should be exponential: 0.01, 0.02 (base_delay * 2^attempt)
        assert sleep_spy.call_args_list[0][0][0] == 0.01
        assert sleep_spy.call_args_list[1][0][0] == 0.02


class TestRetryHandlerEventEmission:
    """Test retry handler event emission."""

    @pytest.mark.asyncio
    async def test_emits_retry_event(
        self, mock_logger: Mock, mock_emitter: BaseEmitter
    ) -> None:
        """Emits retry event on transient errors."""
        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        categoriser = ErrorCategoriser(RetryPolicy())
        handler = RetryHandler(config, mock_logger, mock_emitter, categoriser)

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise asyncio.TimeoutError("Timeout")
            return "success"

        await handler.execute_with_retry(
            operation, url="http://example.com/file.txt", download_id="test-id"
        )

        # Should have emitted one retry event
        mock_emitter.emit.assert_called_once()
        event_name, event = mock_emitter.emit.call_args[0]

        assert event_name == "download.retrying"
        assert event.url == "http://example.com/file.txt"
        assert event.retry == 1  # First retry (after first attempt failed)
        assert event.max_retries == 2  # Matches config
        assert "Timeout" in event.error.message
        assert event.delay_seconds == 0.01

    @pytest.mark.asyncio
    async def test_no_events_on_first_success(
        self, mock_emitter: BaseEmitter, default_retry_handler: BaseRetryHandler
    ) -> None:
        """Does not emit events if operation succeeds immediately."""

        async def operation():
            return "success"

        await default_retry_handler.execute_with_retry(
            operation, url="http://example.com/file.txt", download_id="test-id"
        )

        mock_emitter.emit.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_events_on_permanent_error(
        self, mock_emitter: BaseEmitter, default_retry_handler: BaseRetryHandler
    ) -> None:
        """Does not emit retry events for permanent errors."""

        async def operation():
            raise PermissionError("Permission denied")

        with pytest.raises(PermissionError):
            await default_retry_handler.execute_with_retry(
                operation, url="http://example.com/file.txt", download_id="test-id"
            )

        mock_emitter.emit.assert_not_called()


class TestRetryHandlerLogging:
    """Test retry handler logging behaviour."""

    @pytest.mark.asyncio
    async def test_logs_retry_attempts(
        self, mock_logger: Mock, mock_emitter: BaseEmitter
    ) -> None:
        """Logs warning messages for retry attempts."""
        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        categoriser = ErrorCategoriser(RetryPolicy())
        handler = RetryHandler(config, mock_logger, mock_emitter, categoriser)

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise asyncio.TimeoutError("Timeout")
            return "success"

        await handler.execute_with_retry(
            operation, url="http://example.com/file.txt", download_id="test-id"
        )

        # Should have logged retry warning
        mock_logger.warning.assert_called_once()
        log_message = mock_logger.warning.call_args[0][0]
        assert "Retrying download" in log_message
        assert "attempt 2/3" in log_message
        assert "http://example.com/file.txt" in log_message

    @pytest.mark.asyncio
    async def test_logs_final_failure(
        self, mock_logger: Mock, mock_emitter: BaseEmitter
    ) -> None:
        """Logs error when all retries exhausted."""
        config = RetryConfig(max_retries=1, base_delay=0.01, jitter=False)
        categoriser = ErrorCategoriser(RetryPolicy())
        handler = RetryHandler(config, mock_logger, mock_emitter, categoriser)

        async def operation():
            raise asyncio.TimeoutError("Always fails")

        with pytest.raises(asyncio.TimeoutError):
            await handler.execute_with_retry(
                operation, url="http://example.com/file.txt", download_id="test-id"
            )

        # Should have logged error
        mock_logger.error.assert_called_once()
        log_message = mock_logger.error.call_args[0][0]
        assert "failed after 1 retries" in log_message
        assert "http://example.com/file.txt" in log_message


class TestRetryHandlerCategoriserIntegration:
    """Test retry handler integration with categoriser."""

    @pytest.mark.asyncio
    async def test_uses_injected_categoriser(
        self, mock_logger: Mock, mock_emitter: BaseEmitter
    ) -> None:
        """Uses the injected categoriser for error classification."""
        # Create a custom categoriser that always returns TRANSIENT
        custom_policy = RetryPolicy(retry_unknown_errors=True)
        custom_categoriser = ErrorCategoriser(custom_policy)

        config = RetryConfig(max_retries=2, base_delay=0.01, jitter=False)
        handler = RetryHandler(config, mock_logger, mock_emitter, custom_categoriser)

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # ValueError is normally UNKNOWN, but our policy retries unknown errors
                raise ValueError("Custom error")
            return "success"

        # With default policy (retry_unknown_errors=False), this would fail immediately
        # With custom policy (retry_unknown_errors=True), it should retry
        result = await handler.execute_with_retry(
            operation, url="http://example.com/file.txt", download_id="test-id"
        )

        assert result == "success"
        assert call_count == 2  # Retried once
