"""Retry handler with exponential backoff."""

import asyncio
from typing import TYPE_CHECKING, Awaitable, Callable, TypeVar

from ..domain.exceptions import RetryError
from ..domain.retry import ErrorCategory, RetryConfig
from ..events import EventEmitter, WorkerRetryEvent
from .error_categoriser import ErrorCategoriser

if TYPE_CHECKING:
    import loguru

T = TypeVar("T")


class RetryHandler:
    """Handles retry logic with exponential backoff."""

    def __init__(
        self,
        config: RetryConfig,
        logger: "loguru.Logger",
        emitter: EventEmitter | None,
        categoriser: ErrorCategoriser,
    ) -> None:
        """
        Initialise retry handler.

        Args:
            config: Retry configuration
            logger: Logger for retry messages
            emitter: Event emitter for retry events (optional)
            categoriser: Error categoriser for classifying exceptions
        """
        self.config = config
        self.logger = logger
        self.emitter = emitter
        self.categoriser = categoriser

    async def execute_with_retry(
        self,
        operation: Callable[[], Awaitable[T]],
        url: str,
        max_retries: int | None = None,
    ) -> T:
        """
        Execute async operation with retry on transient errors.

        Args:
            operation: Async callable to execute
            url: URL being processed (for logging/events)
            max_retries: Override config max_retries (optional)

        Returns:
            Result of the operation

        Raises:
            Exception: The last exception if all retries fail on transient errors,
                      or immediately on permanent errors
        """
        effective_max_retries = (
            max_retries if max_retries is not None else self.config.max_retries
        )

        last_exception = None

        for attempt in range(effective_max_retries + 1):
            try:
                return await operation()

            except Exception as e:
                last_exception = e
                category = self.categoriser.categorise(e)

                # Don't retry permanent or unknown errors
                if category != ErrorCategory.TRANSIENT:
                    self.logger.debug(
                        (
                            f"Non-transient error ({category.value}), "
                            f"not retrying {url}: {e}"
                        )
                    )
                    raise

                # Check if we have retries left
                if attempt >= effective_max_retries:
                    self.logger.error(
                        f"Download failed after {effective_max_retries} retries: {url}"
                    )
                    raise

                # Calculate backoff delay
                delay = self.config.calculate_delay(attempt)

                # Emit retry event
                if self.emitter:
                    await self.emitter.emit(
                        "worker.retry",
                        WorkerRetryEvent(
                            url=url,
                            attempt=attempt + 1,
                            max_retries=effective_max_retries,
                            error_message=str(e),
                            retry_delay=delay,
                        ),
                    )

                self.logger.warning(
                    f"Retrying download (attempt {attempt + 2}/"
                    f"{effective_max_retries + 1}) in {delay:.2f}s: {url}"
                )

                # Wait before retry
                await asyncio.sleep(delay)

        # Should never reach here, but handle edge case
        if last_exception:
            raise last_exception

        # Type checker satisfaction: this line is unreachable
        raise RetryError("Retry loop completed without returning or raising")
