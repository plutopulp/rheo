"""HTTP download worker with error handling and cleanup.

This module provides a DownloadWorker class that handles streaming downloads
with proper error handling, partial file cleanup, and logging.
"""

import asyncio
import time
import typing as t
from pathlib import Path

import aiofiles
import aiofiles.os
import aiohttp
from aiofiles.threadpool.binary import AsyncBufferedIOBase

from ...domain.exceptions import HashMismatchError
from ...domain.hash_validation import HashConfig
from ...domain.speed import SpeedCalculator
from ...events import (
    BaseEmitter,
    EventEmitter,
    WorkerCompletedEvent,
    WorkerFailedEvent,
    WorkerProgressEvent,
    WorkerSpeedUpdatedEvent,
    WorkerStartedEvent,
    WorkerValidationCompletedEvent,
    WorkerValidationFailedEvent,
    WorkerValidationStartedEvent,
)
from ...infrastructure.logging import get_logger
from ..retry.base import BaseRetryHandler
from ..retry.null import NullRetryHandler
from ..validation.base import BaseFileValidator
from ..validation.validator import FileValidator
from .base import BaseWorker

if t.TYPE_CHECKING:
    import loguru

# Type alias for all exceptions that can occur during downloads
DownloadException = (
    aiohttp.ClientError
    | aiohttp.ClientConnectorError
    | aiohttp.ClientOSError
    | aiohttp.ClientSSLError
    | aiohttp.ClientResponseError
    | aiohttp.ClientPayloadError
    | asyncio.TimeoutError
    | FileNotFoundError
    | PermissionError
    | OSError
    | Exception  # Generic fallback
)


class DownloadWorker(BaseWorker):
    """Handles HTTP streaming downloads with comprehensive error handling.

    This class provides file downloading with the following features:
    - Streaming downloads for memory efficiency
    - Automatic partial file cleanup on errors
    - Comprehensive error handling and logging
    - Configurable chunk sizes and timeouts
    - HTTP status code validation
    - Real-time speed tracking and ETA estimation

    Implementation Decisions:
    - Uses dependency injection for client, logger and emitter to enable easy testing
        and configuration
    - Cleans up partial files on any error to avoid corrupted downloads
    - Re-raises exceptions after logging to allow caller-specific error handling
    - Uses aiohttp's raise_for_status() for consistent HTTP error handling

    TODO: Performance Optimization
        High-frequency events (progress, speed_updated) are emitted on every chunk
        even when no listeners are subscribed. Consider adding emitter.has_listeners()
        check before event creation to reduce overhead when events aren't needed.
    """

    def __init__(
        self,
        client: aiohttp.ClientSession,
        logger: "loguru.Logger" = get_logger(__name__),
        emitter: BaseEmitter | None = None,
        retry_handler: BaseRetryHandler | None = None,
        validator: BaseFileValidator | None = None,
        speed_window_seconds: float = 5.0,
    ) -> None:
        """Initialize the download worker.

        Args:
            client: Configured aiohttp ClientSession for making HTTP requests
            logger: Logger instance for recording download events and errors
            emitter: Event emitter for broadcasting worker lifecycle events.
                    If None, a new EventEmitter will be created.
            retry_handler: Retry handler for automatic retry with exponential backoff.
                          If None, a NullRetryHandler is used (no retries).
            validator: File validator for post-download hash verification.
                      If None, a FileValidator is used.
            speed_window_seconds: Time window in seconds for moving average speed
                                calculation. Shorter windows react faster to speed
                                changes; longer windows provide smoother averages.
        """
        self.client = client
        self.logger = logger
        # TODO: Consider NullEmitter as default for less overhead in standalone use.
        # When implementing manager facade, evaluate: NullEmitter() vs
        # EventEmitter(logger). NullEmitter avoids dict lookups/iteration, EventEmitter
        # enables direct worker usage with events.
        self._emitter = emitter or EventEmitter(logger)
        self.retry_handler = retry_handler or NullRetryHandler()
        self._validator = validator or FileValidator()
        self._speed_window_seconds = speed_window_seconds

    @property
    def emitter(self) -> BaseEmitter:
        """Event emitter for broadcasting worker events."""
        return self._emitter

    async def _write_chunk_to_file(
        self, chunk: bytes, file_handle: AsyncBufferedIOBase
    ) -> None:
        """Write a data chunk to the output file asynchronously.

        This method provides an extension point for chunk processing.
        Future enhancements could include:
        - Progress callbacks
        - Chunk validation
        - Compression
        - Custom data transformations

        Args:
            chunk: Binary data chunk to write
            file_handle: Async file handle (aiofiles) to write to
        """
        await file_handle.write(chunk)

    def _log_and_categorize_error(
        self,
        exception: DownloadException,
        url: str,
    ) -> None:
        """Log download errors with appropriate categorisation.

        Categorises exceptions by type to provide meaningful error messages.
        This helps with debugging and monitoring by making error patterns clear.

        Args:
            exception: The exception that occurred during download
            url: The URL that was being downloaded when the error occurred
        """
        match exception:
            # Network connection errors - issues establishing connection
            case aiohttp.ClientConnectorError():
                error_category = "Failed to connect to"
            case aiohttp.ClientOSError():
                error_category = "Network error connecting to"
            case aiohttp.ClientSSLError():
                error_category = "SSL/TLS error connecting to"

            # HTTP response errors - server responded but with error
            case aiohttp.ClientResponseError():
                error_category = f"HTTP {exception.status} error from"
            case aiohttp.ClientPayloadError():
                error_category = "Invalid response payload from"

            # Timeout errors - operation took too long
            case asyncio.TimeoutError():
                error_category = "Timeout downloading from"

            # File system errors - issues writing to disk
            case FileNotFoundError():
                error_category = "Could not create file for downloading from"
            case PermissionError():
                error_category = "Permission denied writing file from"
            case OSError():
                error_category = "File system error downloading from"

            # Generic fallback - unexpected errors
            case Exception():
                error_category = "Unexpected error downloading from"
                # Log exception type for debugging unexpected errors
                self.logger.debug(
                    f"Uncaught exception of type {type(exception).__name__}: {exception}"
                )

        # Format and log the error message
        error_message = f"{error_category} {url}: {exception}"
        self.logger.error(error_message)

    async def download(
        self,
        url: str,
        destination_path: Path,
        download_id: str,
        *,
        chunk_size: int = 1024,
        timeout: float | None = None,
        speed_calculator: SpeedCalculator | None = None,
        hash_config: HashConfig | None = None,
    ) -> None:
        """Download a file from URL to local path with error handling and retry support.

        This method streams the download in chunks for memory efficiency and provides
        error handling with automatic cleanup of partial files. If retry is enabled,
        transient errors will be retried with exponential backoff. If hash_config is
        provided, validates the downloaded file after completion.

        Implementation decisions:
        - Uses streaming to handle large files without loading into memory
        - Validates HTTP status codes using raise_for_status()
        - Cleans up partial files on any error to prevent corruption
        - Re-raises exceptions after logging to allow caller-specific handling
        - Uses asyncio.Timeout for consistent timeout behavior
        - Wraps download in retry handler if configured
        - Performs hash validation after download if hash_config provided

        Args:
            url: HTTP/HTTPS URL to download from
            destination_path: Local filesystem path to save the file
            download_id: Unique identifier for this download task
            chunk_size: Size of data chunks to read/write (default: 1024 bytes)
            timeout: Maximum time to wait for the entire download (None = no timeout)
            speed_calculator: Speed calculator for tracking download speed and ETA.
                            If None, creates a new calculator with configured window.
                            Provide custom implementation for alternative speed tracking.
            hash_config: Optional hash configuration for post-download validation.
                        If provided, validates file hash matches expected value.

        Raises:
            aiohttp.ClientError: For network/HTTP related errors
            asyncio.TimeoutError: If download exceeds timeout
            OSError: For filesystem errors (FileNotFoundError, PermissionError, etc.)
            HashMismatchError: If hash validation fails

        Example:
            ```python
            async with aiohttp.ClientSession() as session:
                worker = DownloadWorker(session, logger)
                await worker.download(
                    "https://example.com/file.zip",
                    Path("./file.zip"),
                    download_id="abc123"
                )
            ```
        """
        # Always use retry handler (NullRetryHandler if no retries configured)
        # Note: SpeedCalculator is created inside _download_with_cleanup to ensure
        # each retry attempt gets a fresh calculator with clean state
        await self.retry_handler.execute_with_retry(
            operation=lambda: self._download_with_cleanup(
                url,
                destination_path,
                download_id,
                chunk_size,
                timeout,
                speed_calculator,
                hash_config,
            ),
            url=url,
            download_id=download_id,
        )

    async def _download_with_cleanup(
        self,
        url: str,
        destination_path: Path,
        download_id: str,
        chunk_size: int,
        timeout: float | None,
        speed_calculator: SpeedCalculator | None,
        hash_config: HashConfig | None,
    ) -> None:
        """Internal download implementation with error handling and cleanup.

        This is the core download logic that gets wrapped by the retry handler.
        Creates a fresh SpeedCalculator for each retry attempt to avoid stale state.

        Args:
            url: HTTP/HTTPS URL to download from
            destination_path: Local filesystem path to save the file
            download_id: Unique identifier for this download task
            chunk_size: Size of data chunks to read/write
            timeout: Maximum time to wait for the entire download
            speed_calculator: Optional speed calculator. If None, creates a fresh one
                            with configured window. Creating fresh instances ensures
                            retry attempts don't inherit stale state from failed
                            attempts.
            hash_config: Optional hash configuration for post-download validation.
        """
        self.logger.debug(f"Starting download: {url} -> {destination_path}")

        # Create fresh calculator for this attempt (ensures clean state on retry)
        calc = speed_calculator or SpeedCalculator(
            window_seconds=self._speed_window_seconds
        )

        bytes_downloaded = 0

        try:
            # Open destination file for binary writing (async to avoid blocking)
            async with aiofiles.open(destination_path, "wb") as file_handle:
                # Create HTTP request with timeout context
                async with self.client.get(url) as response, asyncio.Timeout(timeout):
                    # Validate HTTP status - raises ClientResponseError for 4xx/5xx
                    response.raise_for_status()

                    # Get total bytes if available from Content-Length header
                    total_bytes = response.content_length

                    # Emit started event
                    await self.emitter.emit(
                        "worker.started",
                        WorkerStartedEvent(
                            download_id=download_id, url=url, total_bytes=total_bytes
                        ),
                    )

                    # Stream download in chunks for memory efficiency
                    async for chunk in response.content.iter_chunked(chunk_size):
                        await self._write_chunk_to_file(chunk, file_handle)
                        bytes_downloaded += len(chunk)

                        # Calculate speed metrics
                        speed_metrics = calc.record_chunk(
                            chunk_bytes=len(chunk),
                            bytes_downloaded=bytes_downloaded,
                            total_bytes=total_bytes,
                            current_time=time.monotonic(),
                        )

                        # Emit progress event after each chunk
                        await self.emitter.emit(
                            "worker.progress",
                            WorkerProgressEvent(
                                download_id=download_id,
                                url=url,
                                chunk_size=len(chunk),
                                bytes_downloaded=bytes_downloaded,
                                total_bytes=total_bytes,
                            ),
                        )

                        # Emit speed event after each chunk
                        await self.emitter.emit(
                            "worker.speed_updated",
                            WorkerSpeedUpdatedEvent(
                                download_id=download_id,
                                url=url,
                                current_speed_bps=speed_metrics.current_speed_bps,
                                average_speed_bps=speed_metrics.average_speed_bps,
                                eta_seconds=speed_metrics.eta_seconds,
                                elapsed_seconds=speed_metrics.elapsed_seconds,
                                bytes_downloaded=bytes_downloaded,
                                total_bytes=total_bytes,
                            ),
                        )

            self.logger.debug(f"Download completed successfully: {destination_path}")

            # Validate hash if configured
            if hash_config is not None:
                await self._validate_download(
                    url, destination_path, download_id, hash_config
                )

            # Emit completed event
            await self.emitter.emit(
                "worker.completed",
                WorkerCompletedEvent(
                    download_id=download_id,
                    url=url,
                    destination_path=str(destination_path),
                    total_bytes=bytes_downloaded,
                ),
            )

        except asyncio.CancelledError:
            # CancelledError is a BaseException (not Exception), so needs explicit
            # handling. We clean up but don't emit worker.failed, e.g. cancellation
            # is not a failure.
            await self._cleanup_partial_file(destination_path)
            self.logger.debug(f"Download cancelled, cleaned up: {destination_path}")
            # Must re-raise to propagate cancellation through task hierarchy
            raise

        except Exception as download_error:
            # Clean up partial file to prevent corruption
            await self._cleanup_partial_file(destination_path)

            # Log the error with appropriate categorization
            self._log_and_categorize_error(download_error, url)

            # Emit failed event
            await self.emitter.emit(
                "worker.failed",
                WorkerFailedEvent(
                    download_id=download_id,
                    url=url,
                    error_message=str(download_error),
                    error_type=type(download_error).__name__,
                ),
            )

            # Re-raise to allow caller-specific error handling
            raise download_error

    async def _cleanup_partial_file(self, file_path: Path) -> None:
        """Remove partially downloaded file if it exists.

        This prevents leaving corrupted partial files on disk when downloads fail.
        Logs cleanup failures but doesn't raise exceptions to avoid masking the
        original download error.

        Args:
            file_path: Path to the potentially partial file to remove
        """
        # Use async file operations to avoid blocking event loop
        try:
            if await aiofiles.os.path.exists(file_path):
                await aiofiles.os.remove(file_path)
                self.logger.debug(f"Cleaned up partial file: {file_path}")
        except Exception as cleanup_error:
            # Log but don't raise - we don't want to mask the original error
            self.logger.warning(
                f"Failed to clean up partial file {file_path}: {cleanup_error}"
            )

    async def _validate_download(
        self, url: str, file_path: Path, download_id: str, hash_config: HashConfig
    ) -> None:
        """Validate downloaded file hash matches expected value.

        Emits validation events and raises HashMismatchError on failure.
        Hash mismatches are treated as permanent errors and will not be retried
        by default.

        TODO: Future enhancement - add retry_on_mismatch configuration to
        allow retrying hash validation failures in case of network corruption
        during file transfer (similar to retry policies for download errors).

        Args:
            url: The URL that was downloaded
            file_path: Path to the downloaded file
            download_id: Unique identifier for this download task
            hash_config: Hash configuration with algorithm and expected hash

        Raises:
            HashMismatchError: If calculated hash does not match expected hash
            FileValidationError: If file cannot be accessed or read
        """
        # Emit validation started event
        await self.emitter.emit(
            "worker.validation_started",
            WorkerValidationStartedEvent(
                download_id=download_id, url=url, algorithm=hash_config.algorithm
            ),
        )

        validation_start = time.monotonic()

        try:
            # Perform validation (raises HashMismatchError on failure)
            # Returns the actual calculated hash
            calculated_hash = await self._validator.validate(file_path, hash_config)

            duration_ms = (time.monotonic() - validation_start) * 1000

            # Emit validation completed event
            await self.emitter.emit(
                "worker.validation_completed",
                WorkerValidationCompletedEvent(
                    download_id=download_id,
                    url=url,
                    algorithm=hash_config.algorithm,
                    calculated_hash=calculated_hash,
                    duration_ms=duration_ms,
                ),
            )

            self.logger.debug(
                f"Validation succeeded for {file_path} "
                f"({hash_config.algorithm}, {duration_ms:.2f}ms)"
            )

        except HashMismatchError as exc:
            # Emit validation failed event
            await self.emitter.emit(
                "worker.validation_failed",
                WorkerValidationFailedEvent(
                    download_id=download_id,
                    url=url,
                    algorithm=hash_config.algorithm,
                    expected_hash=exc.expected_hash,
                    actual_hash=exc.actual_hash,
                    error_message=str(exc),
                ),
            )

            self.logger.error(f"Validation failed for {url}: {exc}")

            # Re-raise to trigger cleanup and mark download as failed
            # Note: Hash mismatch is treated as a permanent error by default
            # and will not be retried unless retry_on_mismatch is configured
            raise
