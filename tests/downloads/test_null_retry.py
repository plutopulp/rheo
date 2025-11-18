"""Tests for NullRetryHandler."""

import pytest

from rheo.downloads import NullRetryHandler


@pytest.fixture
def null_retry_handler():
    """Provide a NullRetryHandler instance for testing."""
    return NullRetryHandler()


class TestNullRetryHandler:
    """Test NullRetryHandler null object implementation."""

    @pytest.mark.asyncio
    async def test_executes_operation_without_retry(self, null_retry_handler):
        """NullRetryHandler executes operation directly without retry."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            return "result"

        result = await null_retry_handler.execute_with_retry(
            operation, url="http://example.com/file.txt"
        )

        assert result == "result"
        assert call_count == 1  # Called only once, no retry

    @pytest.mark.asyncio
    async def test_propagates_exceptions(self, null_retry_handler):
        """NullRetryHandler propagates exceptions without retry."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            await null_retry_handler.execute_with_retry(
                operation, url="http://example.com/file.txt"
            )

        assert call_count == 1  # Called only once, no retry on error

    @pytest.mark.asyncio
    async def test_ignores_max_retries_parameter(self, null_retry_handler):
        """NullRetryHandler ignores max_retries parameter."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First call fails")
            return "success"

        # Even with max_retries specified, should not retry
        with pytest.raises(ValueError, match="First call fails"):
            await null_retry_handler.execute_with_retry(
                operation, url="http://example.com/file.txt", max_retries=5
            )

        assert call_count == 1  # No retry even with max_retries

    @pytest.mark.asyncio
    async def test_returns_any_type(self, null_retry_handler):
        """NullRetryHandler can return any type."""

        async def string_operation():
            return "string result"

        async def int_operation():
            return 42

        async def dict_operation():
            return {"key": "value"}

        assert (
            await null_retry_handler.execute_with_retry(string_operation, "")
            == "string result"
        )
        assert await null_retry_handler.execute_with_retry(int_operation, "") == 42
        assert await null_retry_handler.execute_with_retry(dict_operation, "") == {
            "key": "value"
        }
