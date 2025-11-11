"""Tests for DownloadWorker class."""

import asyncio
from pathlib import Path

import aiohttp
import pytest
from aioresponses import aioresponses

from async_download_manager.core.worker import DownloadWorker


@pytest.fixture
def test_worker(aio_client, test_logger):
    return DownloadWorker(aio_client, test_logger)


class TestDownloadWorkerInitialization:
    """Test DownloadWorker initialization and basic setup."""

    def test_init_with_explicit_logger(self, aio_client, test_logger):
        """Test worker initialization with explicit logger."""
        worker = DownloadWorker(aio_client, test_logger)
        assert worker.client is aio_client
        assert worker.logger is test_logger

    def test_init_with_default_logger(self, aio_client):
        """Test worker initialization with default logger."""
        worker = DownloadWorker(aio_client)
        assert worker.client is aio_client
        assert worker.logger is not None


class TestDownloadWorkerSuccessfulDownloads:
    """Test successful download scenarios."""

    @pytest.mark.asyncio
    async def test_basic_download_success(self, test_worker, tmp_path, test_logger):
        """Test basic successful file download."""
        test_url = "https://example.com/test.txt"
        test_content = b"Hello, World!"
        temp_file = tmp_path / "test.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)

            await test_worker.download(test_url, temp_file)

        # Verify file was created with correct content
        assert temp_file.exists()
        assert temp_file.read_bytes() == test_content

        # Verify logging - check that both start and completion messages were logged
        test_logger.debug.assert_any_call(
            f"Starting download: {test_url} -> {temp_file}"
        )
        test_logger.debug.assert_any_call(
            f"Download completed successfully: {temp_file}"
        )

    @pytest.mark.asyncio
    async def test_download_with_custom_chunk_size(self, test_worker, tmp_path):
        """Test download with custom chunk size."""
        test_url = "https://example.com/binary.dat"
        test_content = b"x" * 1000  # 1KB of data
        temp_file = tmp_path / "binary.dat"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)

            await test_worker.download(test_url, temp_file, chunk_size=256)

        assert temp_file.exists()
        assert temp_file.read_bytes() == test_content

    @pytest.mark.asyncio
    async def test_download_large_file(self, test_worker, tmp_path):
        """Test download of larger file to ensure chunking works."""
        test_url = "https://example.com/large.bin"
        test_content = b"A" * 10000  # 10KB file
        temp_file = tmp_path / "large.bin"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)

            await test_worker.download(test_url, temp_file, chunk_size=1024)

        assert temp_file.exists()
        assert temp_file.read_bytes() == test_content

    @pytest.mark.asyncio
    async def test_download_empty_file(self, test_worker, tmp_path):
        """Test download of empty file."""
        test_url = "https://example.com/empty.txt"
        temp_file = tmp_path / "empty.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=b"")

            await test_worker.download(test_url, temp_file)

        assert temp_file.exists()
        assert temp_file.read_bytes() == b""


class TestDownloadWorkerHTTPErrors:
    """Test HTTP error handling."""

    @pytest.mark.asyncio
    async def test_download_404_error(self, test_worker, tmp_path, test_logger):
        """Test handling of 404 Not Found error."""
        test_url = "https://example.com/notfound.txt"
        temp_file = tmp_path / "notfound.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=404, body="Not Found")

            with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                await test_worker.download(test_url, temp_file)

        # Verify error handling
        assert exc_info.value.status == 404
        assert not temp_file.exists()  # Partial file should be cleaned up
        test_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_download_500_error(self, test_worker, tmp_path, test_logger):
        """Test handling of 500 Internal Server Error."""
        test_url = "https://example.com/server-error.txt"
        temp_file = tmp_path / "server-error.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=500, body="Internal Server Error")

            with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                await test_worker.download(test_url, temp_file)

        assert exc_info.value.status == 500
        assert not temp_file.exists()
        test_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_download_403_forbidden(self, test_worker, tmp_path, test_logger):
        """Test handling of 403 Forbidden error."""
        test_url = "https://example.com/forbidden.txt"
        temp_file = tmp_path / "forbidden.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=403, body="Forbidden")

            with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                await test_worker.download(test_url, temp_file)

        assert exc_info.value.status == 403
        assert not temp_file.exists()


class TestDownloadWorkerNetworkErrors:
    """Test network-related error handling."""

    @pytest.mark.asyncio
    async def test_connection_error(self, test_worker, tmp_path, test_logger):
        """Test handling of connection errors."""
        test_url = "https://example.com/test.txt"
        temp_file = tmp_path / "test.txt"

        with aioresponses() as mock:
            # Use a simple exception that aioresponses can handle
            mock.get(test_url, exception=ConnectionError("Connection failed"))

            with pytest.raises(ConnectionError):
                await test_worker.download(test_url, temp_file)

        assert not temp_file.exists()
        test_logger.error.assert_called()
        # Check the error message contains expected text
        error_call = test_logger.error.call_args[0][0]
        assert "File system error downloading from" in error_call

    @pytest.mark.asyncio
    async def test_ssl_error(self, test_worker, tmp_path, test_logger):
        """Test handling of SSL errors."""
        test_url = "https://example.com/test.txt"
        temp_file = tmp_path / "test.txt"

        with aioresponses() as mock:
            # Use a simple SSL error for testing
            mock.get(test_url, exception=Exception("SSL verification failed"))

            with pytest.raises(Exception):
                await test_worker.download(test_url, temp_file)

        assert not temp_file.exists()
        test_logger.error.assert_called()
        error_call = test_logger.error.call_args[0][0]
        assert "Unexpected error downloading from" in error_call

    @pytest.mark.asyncio
    async def test_payload_error(self, test_worker, tmp_path, test_logger):
        """Test handling of payload errors."""
        test_url = "https://example.com/test.txt"
        temp_file = tmp_path / "test.txt"

        with aioresponses() as mock:
            mock.get(test_url, exception=aiohttp.ClientPayloadError("Invalid payload"))

            with pytest.raises(aiohttp.ClientPayloadError):
                await test_worker.download(test_url, temp_file)

        assert not temp_file.exists()
        test_logger.error.assert_called()
        error_call = test_logger.error.call_args[0][0]
        assert "Invalid response payload from" in error_call


class TestDownloadWorkerTimeouts:
    """Test timeout handling."""

    @pytest.mark.asyncio
    async def test_timeout_error(self, test_worker, tmp_path, test_logger):
        """Test handling of timeout errors."""
        test_url = "https://example.com/slow.txt"
        temp_file = tmp_path / "slow.txt"

        with aioresponses() as mock:
            # Just use a timeout exception directly instead of trying to
            # simulate slow response
            mock.get(test_url, exception=asyncio.TimeoutError())

            with pytest.raises(asyncio.TimeoutError):
                await test_worker.download(
                    test_url, temp_file, timeout=0.01
                )  # Very short timeout

        assert not temp_file.exists()
        test_logger.error.assert_called()
        error_call = test_logger.error.call_args[0][0]
        assert "Timeout downloading from" in error_call


class TestDownloadWorkerFileSystemErrors:
    """Test file system related error handling."""

    @pytest.mark.asyncio
    async def test_permission_error(self, test_worker, tmp_path, test_logger):
        """Test handling of permission errors when writing files."""
        test_url = "https://example.com/test.txt"

        # Create a read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir(mode=0o555)  # Read and execute only
        readonly_file = readonly_dir / "test.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=b"test content")

            with pytest.raises(PermissionError):
                await test_worker.download(test_url, readonly_file)

        test_logger.error.assert_called()
        error_call = test_logger.error.call_args[0][0]
        assert "Permission denied writing file from" in error_call

    @pytest.mark.asyncio
    async def test_file_not_found_directory(self, test_worker, test_logger):
        """Test handling when parent directory doesn't exist."""
        test_url = "https://example.com/test.txt"
        nonexistent_path = Path("/nonexistent/directory/file.txt")

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=b"test content")

            with pytest.raises(FileNotFoundError):
                await test_worker.download(test_url, nonexistent_path)

        test_logger.error.assert_called()
        error_call = test_logger.error.call_args[0][0]
        assert "Could not create file for downloading from" in error_call


class TestDownloadWorkerFileCleanup:
    """Test file cleanup behavior on errors."""

    @pytest.mark.asyncio
    async def test_partial_file_cleanup_on_http_error(
        self, test_worker, tmp_path, test_logger
    ):
        """Test that partial files are cleaned up on HTTP errors."""
        test_url = "https://example.com/test.txt"
        temp_file = tmp_path / "test.txt"

        # Pre-create the file to simulate partial download
        temp_file.write_bytes(b"partial content")
        assert temp_file.exists()

        with aioresponses() as mock:
            mock.get(test_url, status=404)

            with pytest.raises(aiohttp.ClientResponseError):
                await test_worker.download(test_url, temp_file)

        # File should be cleaned up
        assert not temp_file.exists()
        test_logger.debug.assert_any_call(f"Cleaned up partial file: {temp_file}")


class TestDownloadWorkerChunkWriting:
    """Test the chunk writing functionality."""

    def test_write_chunk_to_file(self, test_worker, tmp_path):
        """Test that _write_chunk_to_file writes data correctly."""
        test_data = b"test chunk data"
        temp_file = tmp_path / "chunk.txt"

        with open(temp_file, "wb") as f:
            test_worker._write_chunk_to_file(test_data, f)

        assert temp_file.read_bytes() == test_data

    def test_write_multiple_chunks(self, test_worker, tmp_path):
        """Test writing multiple chunks sequentially."""
        chunks = [b"chunk1", b"chunk2", b"chunk3"]
        temp_file = tmp_path / "chunks.txt"

        with open(temp_file, "wb") as f:
            for chunk in chunks:
                test_worker._write_chunk_to_file(chunk, f)

        assert temp_file.read_bytes() == b"chunk1chunk2chunk3"


class TestDownloadWorkerExceptionHandling:
    """Test the exception handling and logging functionality."""

    def test_handle_client_connector_error(self, test_worker, mocker, test_logger):
        """Test handling of ClientConnectorError."""
        test_url = "https://example.com/test.txt"

        # Create a mock exception that behaves like ClientConnectorError
        exception = mocker.Mock(spec=aiohttp.ClientConnectorError)
        exception.__class__ = aiohttp.ClientConnectorError
        exception.__str__ = mocker.Mock(return_value="Connection refused")

        test_worker._log_and_categorize_error(exception, test_url)

        test_logger.error.assert_called_once()
        error_message = test_logger.error.call_args[0][0]
        assert "Failed to connect to" in error_message
        assert test_url in error_message

    def test_handle_client_response_error(self, test_worker, mocker, test_logger):
        """Test handling of ClientResponseError."""
        test_url = "https://example.com/test.txt"

        # Create a mock ClientResponseError with proper request_info
        mock_request_info = mocker.Mock()
        mock_request_info.real_url = test_url
        exception = aiohttp.ClientResponseError(
            request_info=mock_request_info, history=(), status=404, message="Not Found"
        )

        test_worker._log_and_categorize_error(exception, test_url)

        test_logger.error.assert_called_once()
        error_message = test_logger.error.call_args[0][0]
        assert "HTTP 404 error from" in error_message
        assert test_url in error_message

    def test_handle_timeout_error(self, aio_client, test_logger):
        """Test handling of TimeoutError."""
        test_worker = DownloadWorker(aio_client, test_logger)
        test_url = "https://example.com/test.txt"
        exception = asyncio.TimeoutError()

        test_worker._log_and_categorize_error(exception, test_url)

        test_logger.error.assert_called_once()
        error_message = test_logger.error.call_args[0][0]
        assert "Timeout downloading from" in error_message
        assert test_url in error_message

    def test_handle_generic_exception(self, aio_client, test_logger):
        """Test handling of generic exceptions."""
        test_worker = DownloadWorker(aio_client, test_logger)
        test_url = "https://example.com/test.txt"
        exception = ValueError("Some unexpected error")

        test_worker._log_and_categorize_error(exception, test_url)

        test_logger.error.assert_called_once()
        test_logger.debug.assert_called_once()

        error_message = test_logger.error.call_args[0][0]
        assert "Unexpected error downloading from" in error_message
        assert test_url in error_message

        debug_message = test_logger.debug.call_args[0][0]
        assert "Uncaught exception of type" in debug_message
