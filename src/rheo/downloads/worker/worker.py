"""HTTP download worker with error handling and cleanup.

This module provides a DownloadWorker class that handles streaming downloads
with proper error handling, partial file cleanup, and logging.
"""

import asyncio
import time
import typing as t
from dataclasses import dataclass
from pathlib import Path

import aiofiles
import aiofiles.os
import aiohttp
from aiofiles.threadpool.binary import AsyncBufferedIOBase

from ...domain.cancellation import CancelledFrom
from ...domain.exceptions import HashMismatchError
from ...domain.file_config import FileExistsStrategy
from ...domain.hash_validation import HashConfig, ValidationResult
from ...domain.speed import SpeedCalculator
from ...events import (
    BaseEmitter,
    DownloadCancelledEvent,
    DownloadCompletedEvent,
    DownloadFailedEvent,
    DownloadProgressEvent,
    DownloadSkippedEvent,
    DownloadStartedEvent,
    DownloadValidatingEvent,
    ErrorInfo,
    EventEmitter,
)
from ...infrastructure.http import BaseHttpClient
from ...infrastructure.logging import get_logger
from ..destination_resolver import DestinationResolver
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


@dataclass(frozen=True)
class DownloadMetrics:
    """Metrics from a successful download phase (before validation)."""

    bytes_downloaded: int
    elapsed_seconds: float
    average_speed_bps: float


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

    TODO: Performance optimisation
        High-frequency progress events are emitted on every chunk even when no
        listeners are subscribed. Consider adding emitter.has_listeners() check
        before event creation to reduce overhead when events aren't needed.
    """

    def __init__(
        self,
        client: BaseHttpClient,
        logger: "loguru.Logger" = get_logger(__name__),
        emitter: BaseEmitter | None = None,
        retry_handler: BaseRetryHandler | None = None,
        validator: BaseFileValidator | None = None,
        speed_window_seconds: float = 5.0,
        default_file_exists_strategy: FileExistsStrategy = FileExistsStrategy.SKIP,
    ) -> None:
        """Initialise the download worker.

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
            default_file_exists_strategy: Default strategy when per-file override
                                          is not provided. Worker owns the resolver.
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
        # Worker owns resolver; it performs async I/O so lives in downloads layer.
        self._destination_resolver = DestinationResolver(
            default_strategy=default_file_exists_strategy
        )

    @property
    def emitter(self) -> BaseEmitter:
        """Event emitter for broadcasting worker events."""
        return self._emitter

    # Public API

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
        file_exists_strategy: FileExistsStrategy | None = None,
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
            file_exists_strategy: Optional override for handling existing destination
                        files. None uses policy default; SKIP skips, ERROR raises,
                        OVERWRITE replaces.

        Raises:
            aiohttp.ClientError: For network/HTTP related errors
            asyncio.TimeoutError: If download exceeds timeout
            OSError: For filesystem errors (FileNotFoundError, PermissionError, etc.)
            HashMismatchError: If hash validation fails
            FileExistsError: If file exists and strategy is ERROR

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
        # Check file exists strategy before starting download
        resolved_path = await self._destination_resolver.resolve(
            destination_path, file_exists_strategy
        )
        if resolved_path is None:
            self.logger.debug(f"File exists, skipping: {destination_path}")
            await self.emitter.emit(
                "download.skipped",
                DownloadSkippedEvent(
                    download_id=download_id,
                    url=url,
                    reason="file_exists",
                    destination_path=str(destination_path),
                ),
            )
            return

        # Always use retry handler (NullRetryHandler if no retries configured)
        # Note: SpeedCalculator is created inside _download_with_cleanup to ensure
        # each retry attempt gets a fresh calculator with clean state
        await self.retry_handler.execute_with_retry(
            operation=lambda: self._download_with_cleanup(
                url,
                resolved_path,
                download_id,
                chunk_size,
                timeout,
                speed_calculator,
                hash_config,
            ),
            url=url,
            download_id=download_id,
        )

    # Download Orchestration

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
        """Orchestrate download phases with cleanup on failure.

        This is the core download logic that gets wrapped by the retry handler.
        Coordinates: download → validate → emit completion, with proper error handling.

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
        try:
            metrics = await self._perform_download(
                url,
                destination_path,
                download_id,
                chunk_size,
                timeout,
                speed_calculator,
            )

            validation_result = await self._validate_if_configured(
                url, destination_path, download_id, hash_config
            )

            await self._emit_completed(
                download_id, url, destination_path, metrics, validation_result
            )

        except asyncio.CancelledError:
            # CancelledError is a BaseException (not Exception), so needs explicit
            # handling. We clean up but don't emit download.failed - cancellation
            # is not a failure.
            await self._cleanup_partial_file(destination_path)
            self.logger.debug(f"Download cancelled, cleaned up: {destination_path}")
            await self.emitter.emit(
                "download.cancelled",
                DownloadCancelledEvent(
                    download_id=download_id,
                    url=url,
                    cancelled_from=CancelledFrom.IN_PROGRESS,
                ),
            )
            # Must re-raise to propagate cancellation through task hierarchy
            raise

        except HashMismatchError:
            # Hash validation failures already handled (event emitted, file cleaned up)
            # in _handle_validation_failure - just re-raise to propagate to caller
            raise

        except Exception as error:
            await self._handle_download_failure(
                download_id, url, destination_path, error
            )
            raise

    # Download Phase

    async def _perform_download(
        self,
        url: str,
        destination_path: Path,
        download_id: str,
        chunk_size: int,
        timeout: float | None,
        speed_calculator: SpeedCalculator | None,
    ) -> DownloadMetrics:
        """Stream download from URL to file, emitting progress events.

        Handles the core HTTP streaming logic: connect, stream chunks, write to file.
        Emits download.started and download.progress events during the process.

        Args:
            url: HTTP/HTTPS URL to download from
            destination_path: Local filesystem path to save the file
            download_id: Unique identifier for this download task
            chunk_size: Size of data chunks to read/write
            timeout: Maximum time to wait for the entire download
            speed_calculator: Optional speed calculator for tracking metrics

        Returns:
            DownloadMetrics with bytes downloaded, elapsed time, and average speed
        """
        self.logger.debug(f"Starting download: {url} -> {destination_path}")

        # Create fresh calculator for this attempt (ensures clean state on retry)
        calc = speed_calculator or SpeedCalculator(
            window_seconds=self._speed_window_seconds
        )

        bytes_downloaded = 0

        # Ensure parent directories exist before writing.
        # Future: Consider a FileDestination/FileWriter abstraction if non-file
        # destinations (S3, memory streams) are needed.
        await aiofiles.os.makedirs(destination_path.parent, exist_ok=True)

        # Open destination file for binary writing (async to avoid blocking)
        async with aiofiles.open(destination_path, "wb") as file_handle:
            # Create HTTP request with timeout context
            async with self.client.get(url) as response, asyncio.Timeout(timeout):
                # Validate HTTP status - raises ClientResponseError for 4xx/5xx
                response.raise_for_status()

                # Get total bytes if available from Content-Length header
                total_bytes = response.content_length

                # Track start time for elapsed_seconds calculation
                download_start_time = time.monotonic()

                # Emit started event
                await self.emitter.emit(
                    "download.started",
                    DownloadStartedEvent(
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

                    # Emit progress event after each chunk (includes speed metrics)
                    await self.emitter.emit(
                        "download.progress",
                        DownloadProgressEvent(
                            download_id=download_id,
                            url=url,
                            chunk_size=len(chunk),
                            bytes_downloaded=bytes_downloaded,
                            total_bytes=total_bytes,
                            speed=speed_metrics,
                        ),
                    )

        self.logger.debug(f"Download completed successfully: {destination_path}")

        # Calculate final metrics
        elapsed_seconds = time.monotonic() - download_start_time
        average_speed = (
            bytes_downloaded / elapsed_seconds if elapsed_seconds > 0 else 0.0
        )

        return DownloadMetrics(
            bytes_downloaded=bytes_downloaded,
            elapsed_seconds=elapsed_seconds,
            average_speed_bps=average_speed,
        )

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

    # Validation Phase

    async def _validate_if_configured(
        self,
        url: str,
        destination_path: Path,
        download_id: str,
        hash_config: HashConfig | None,
    ) -> ValidationResult | None:
        """Validate download if hash_config is provided.

        Returns ValidationResult on success, raises HashMismatchError on failure.
        If no hash_config provided, returns None (no validation needed).

        Args:
            url: The URL that was downloaded
            destination_path: Path to the downloaded file
            download_id: Unique identifier for this download task
            hash_config: Optional hash configuration for validation

        Returns:
            ValidationResult on success, None if no validation configured

        Raises:
            HashMismatchError: If hash validation fails
        """
        if hash_config is None:
            return None

        result = await self._compute_validation_result(
            url, destination_path, download_id, hash_config
        )

        if not result.is_valid:
            await self._handle_validation_failure(
                download_id, url, destination_path, result
            )
            # _handle_validation_failure raises, so this is unreachable

        return result

    async def _compute_validation_result(
        self, url: str, file_path: Path, download_id: str, hash_config: HashConfig
    ) -> ValidationResult:
        """Compute hash validation result for downloaded file.

        Emits download.validating event and returns ValidationResult. Caller
        should check result.is_valid to determine if validation passed.

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

        Returns:
            ValidationResult with algorithm, expected/calculated hash, duration,
            and is_valid property indicating success/failure

        Raises:
            FileValidationError: If file cannot be accessed or read
        """
        # Emit validation phase event
        await self.emitter.emit(
            "download.validating",
            DownloadValidatingEvent(
                download_id=download_id, url=url, algorithm=hash_config.algorithm
            ),
        )

        validation_start = time.monotonic()
        result = await self._validator.validate(file_path, hash_config)
        duration_ms = (time.monotonic() - validation_start) * 1000

        status = "succeeded" if result.is_valid else "failed"
        self.logger.debug(
            f"Validation {status} for {file_path} "
            f"({hash_config.algorithm}, {duration_ms:.2f}ms)"
        )

        # Return result with timing added
        return ValidationResult(
            algorithm=result.algorithm,
            expected_hash=result.expected_hash,
            calculated_hash=result.calculated_hash,
            duration_ms=duration_ms,
        )

    async def _handle_validation_failure(
        self,
        download_id: str,
        url: str,
        destination_path: Path,
        result: ValidationResult,
    ) -> t.NoReturn:
        """Handle hash validation failure: cleanup, emit event, raise.

        Args:
            download_id: Unique identifier for this download task
            url: The URL that was downloaded
            destination_path: Path to the downloaded file (will be cleaned up)
            result: ValidationResult with mismatch details

        Raises:
            HashMismatchError: Always raised after cleanup and event emission
        """
        await self._cleanup_partial_file(destination_path)

        self.logger.error(
            f"Validation failed for {url}: "
            f"expected {result.expected_hash[:16]}..., "
            f"got {result.calculated_hash[:16]}..."
        )

        await self.emitter.emit(
            "download.failed",
            DownloadFailedEvent(
                download_id=download_id,
                url=url,
                error=ErrorInfo(
                    exc_type="HashMismatchError",
                    message=(
                        f"Hash mismatch: expected {result.expected_hash[:16]}..., "
                        f"got {result.calculated_hash[:16]}..."
                    ),
                ),
                validation=result,
            ),
        )

        raise HashMismatchError(
            expected_hash=result.expected_hash,
            calculated_hash=result.calculated_hash,
            file_path=destination_path,
        )

    # Event Emission

    async def _emit_completed(
        self,
        download_id: str,
        url: str,
        destination_path: Path,
        metrics: DownloadMetrics,
        validation: ValidationResult | None,
    ) -> None:
        """Emit download.completed event with metrics and validation result."""
        await self.emitter.emit(
            "download.completed",
            DownloadCompletedEvent(
                download_id=download_id,
                url=url,
                destination_path=str(destination_path),
                total_bytes=metrics.bytes_downloaded,
                elapsed_seconds=metrics.elapsed_seconds,
                average_speed_bps=metrics.average_speed_bps,
                validation=validation,
            ),
        )

    # Error Handling

    async def _handle_download_failure(
        self,
        download_id: str,
        url: str,
        destination_path: Path,
        error: Exception,
    ) -> None:
        """Handle generic download failure: cleanup, log, emit event.

        Args:
            download_id: Unique identifier for this download task
            url: The URL that was being downloaded
            destination_path: Path to the partial file (will be cleaned up)
            error: The exception that caused the failure
        """
        await self._cleanup_partial_file(destination_path)
        self._log_and_categorize_error(error, url)

        await self.emitter.emit(
            "download.failed",
            DownloadFailedEvent(
                download_id=download_id,
                url=url,
                error=ErrorInfo.from_exception(error),
            ),
        )

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

    # File Utilities

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
