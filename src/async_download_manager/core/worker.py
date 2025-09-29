"""HTTP download worker with error handling and cleanup.

This module provides a DownloadWorker class that handles streaming downloads
with proper error handling, partial file cleanup, and logging.
"""

import asyncio
from io import BufferedWriter
from pathlib import Path
from typing import TYPE_CHECKING, Union

import aiohttp

from .logger import get_logger

if TYPE_CHECKING:
    import loguru

# Type alias for all exceptions that can occur during downloads
DownloadException = Union[
    aiohttp.ClientError,  # Network/HTTP errors
    asyncio.TimeoutError,  # Timeout errors
    OSError,  # File system errors (includes FileNotFoundError, PermissionError)
    Exception,  # Generic fallback
]


class DownloadWorker:
    """Handles HTTP streaming downloads with comprehensive error handling.

    This class provides file downloading with the following features:
    - Streaming downloads for memory efficiency
    - Automatic partial file cleanup on errors
    - Comprehensive error handling and logging
    - Configurable chunk sizes and timeouts
    - HTTP status code validation

    Implementation Decisions:
    - Uses dependency injection for client and logger to enable easy testing
        and configuration
    - Cleans up partial files on any error to avoid corrupted downloads
    - Re-raises exceptions after logging to allow caller-specific error handling
    - Uses aiohttp's raise_for_status() for consistent HTTP error handling
    """

    def __init__(
        self,
        client: aiohttp.ClientSession,
        logger: "loguru.Logger" = get_logger(__name__),
    ) -> None:
        """Initialize the download worker.

        Args:
            client: Configured aiohttp ClientSession for making HTTP requests
            logger: Logger instance for recording download events and errors
        """
        self.client = client
        self.logger = logger

    def _write_chunk_to_file(self, chunk: bytes, file_handle: BufferedWriter) -> None:
        """Write a data chunk to the output file.

        This method is separate to enable easy testing and potential future
        enhancements like progress tracking or data validation.

        Args:
            chunk: Binary data chunk to write
            file_handle: Open file handle to write to
        """
        file_handle.write(chunk)

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
        chunk_size: int = 1024,
        timeout: float | None = None,
    ) -> None:
        """Download a file from URL to local path with error handling.

        This method streams the download in chunks for memory efficiency and provides
        error handling with automatic cleanup of partial files.

        Implementation decisions:
        - Uses streaming to handle large files without loading into memory
        - Validates HTTP status codes using raise_for_status()
        - Cleans up partial files on any error to prevent corruption
        - Re-raises exceptions after logging to allow caller-specific handling
        - Uses asyncio.Timeout for consistent timeout behavior

        Args:
            url: HTTP/HTTPS URL to download from
            destination_path: Local filesystem path to save the file
            chunk_size: Size of data chunks to read/write (default: 1024 bytes)
            timeout: Maximum time to wait for the entire download (None = no timeout)

        Raises:
            aiohttp.ClientError: For network/HTTP related errors
            asyncio.TimeoutError: If download exceeds timeout
            OSError: For filesystem errors (FileNotFoundError, PermissionError, etc.)

        Example:
            ```python
            async with aiohttp.ClientSession() as session:
                worker = DownloadWorker(session, logger)
                await worker.download("https://example.com/file.zip", Path("./file.zip"))
            ```
        """
        self.logger.debug(f"Starting download: {url} -> {destination_path}")

        try:
            # Open destination file for binary writing
            with open(destination_path, "wb") as file_handle:
                # Create HTTP request with timeout context
                async with self.client.get(url) as response, asyncio.Timeout(timeout):
                    # Validate HTTP status - raises ClientResponseError for 4xx/5xx
                    response.raise_for_status()

                    # Stream download in chunks for memory efficiency
                    async for chunk in response.content.iter_chunked(chunk_size):
                        self._write_chunk_to_file(chunk, file_handle)

            self.logger.debug(f"Download completed successfully: {destination_path}")

        except Exception as download_error:
            # Clean up partial file to prevent corruption
            await self._cleanup_partial_file(destination_path)

            # Log the error with appropriate categorization
            self._log_and_categorize_error(download_error, url)

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
        if file_path.exists():
            try:
                file_path.unlink()
                self.logger.debug(f"Cleaned up partial file: {file_path}")
            except Exception as cleanup_error:
                # Log but don't raise - we don't want to mask the original error
                self.logger.warning(
                    f"Failed to clean up partial file {file_path}: {cleanup_error}"
                )
