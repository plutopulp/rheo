"""Base interface for retry handlers."""

from abc import ABC, abstractmethod
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


class BaseRetryHandler(ABC):
    """Abstract base class for retry handlers.

    This interface defines the contract for retry handlers, allowing
    different retry strategies (e.g., exponential backoff, no retry)
    to be used interchangeably via dependency injection.
    """

    @abstractmethod
    async def execute_with_retry(
        self,
        operation: Callable[[], Awaitable[T]],
        url: str,
        max_retries: int | None = None,
    ) -> T:
        """Execute an async operation with retry logic.

        Args:
            operation: The async callable to execute.
            url: The URL associated with the operation, for logging and events.
            max_retries: Optional override for max retries (implementation-specific).

        Returns:
            The result of the operation.

        Raises:
            Exception: The last exception if all retries fail or on a permanent error.
        """
        pass
