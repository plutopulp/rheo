"""Retry handler with exponential backoff."""

import asyncio
import typing as t

from ...domain.exceptions import RetryError
from ...domain.retry import ErrorCategory, RetryConfig
from ...events import DownloadRetryingEvent, ErrorInfo, EventEmitter
from ...infrastructure.logging import get_logger
from .base import BaseRetryHandler
from .categoriser import ErrorCategoriser

if t.TYPE_CHECKING:
    import loguru

T = t.TypeVar("T")


class RetryHandler(BaseRetryHandler):
    """Handles retry logic with exponential backoff."""

    def __init__(
        self,
        config: RetryConfig,
        logger: "loguru.Logger" = get_logger(__name__),
        emitter: EventEmitter | None = None,
        categoriser: ErrorCategoriser | None = None,
    ) -> None:
        """
        Initialise retry handler.

        Args:
            config: Retry configuration
            logger: Logger for recording retry events
            emitter: Event emitter for broadcasting retry events.
                    If None, a new EventEmitter will be created.
            categoriser: Error categoriser to determine if errors are transient.
                        If None, a default ErrorCategoriser with the config's
                        policy will be created.
        """
        self.config = config
        self.logger = logger
        self.emitter = emitter if emitter is not None else EventEmitter(logger)
        self.categoriser = (
            categoriser if categoriser is not None else ErrorCategoriser(config.policy)
        )

    async def execute_with_retry(
        self,
        operation: t.Callable[[], t.Awaitable[T]],
        url: str,
        download_id: str,
        max_retries: int | None = None,
    ) -> T:
        """
        Execute async operation with retry on transient errors.

        Args:
            operation: Async callable to execute
            url: URL being processed (for logging/events)
            download_id: Unique identifier for the download task
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

                # Emit retry event with structured error info
                # attempt=0 is first try; if it fails, we're about to do retry 1
                retry_number = attempt + 1
                if self.emitter:
                    await self.emitter.emit(
                        "download.retrying",
                        DownloadRetryingEvent(
                            download_id=download_id,
                            url=url,
                            retry=retry_number,
                            max_retries=effective_max_retries,
                            delay_seconds=delay,
                            error=ErrorInfo.from_exception(e),
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
