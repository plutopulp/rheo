"""Base interface for retry handlers."""

import typing as t
from abc import ABC, abstractmethod

T = t.TypeVar("T")


class BaseRetryHandler(ABC):
    """Abstract base class for retry handlers.

    This interface defines the contract for retry handlers, allowing
    different retry strategies (e.g., exponential backoff, no retry)
    to be used interchangeably via dependency injection.
    """

    @abstractmethod
    async def execute_with_retry(
        self,
        operation: t.Callable[[], t.Awaitable[T]],
        url: str,
        download_id: str,
        max_retries: int | None = None,
    ) -> T:
        """Execute an async operation with retry logic.

        Args:
            operation: The async callable to execute.
            url: The URL associated with the operation, for logging and events.
            download_id: Unique identifier for the download task.
            max_retries: Optional override for max retries (implementation-specific).

        Returns:
            The result of the operation.

        Raises:
            Exception: The last exception if all retries fail or on a permanent error.
        """
