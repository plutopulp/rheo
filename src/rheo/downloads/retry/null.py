"""Null Object implementation for retry handler."""

import typing as t

from .base import BaseRetryHandler

T = t.TypeVar("T")


class NullRetryHandler(BaseRetryHandler):
    """No-op retry handler that executes operations without retrying.

    This is the default retry handler when no retry logic is desired.
    It follows the Null Object pattern, allowing the worker to always
    have a retry handler without needing None checks.
    """

    async def execute_with_retry(
        self,
        operation: t.Callable[[], t.Awaitable[T]],
        url: str,
        download_id: str,
        max_retries: int | None = None,
    ) -> T:
        """Execute operation directly without retry logic.

        Args:
            operation: The async callable to execute.
            url: The URL (ignored by null handler).
            download_id: Unique identifier (ignored by null handler).
            max_retries: Max retries override (ignored by null handler).

        Returns:
            The result of the operation.

        Raises:
            Exception: Any exception raised by the operation.
        """
        return await operation()
