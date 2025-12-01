"""Tests for DownloadWorker class."""

import asyncio
import typing as t
from pathlib import Path

import aiofiles
import aiohttp
import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses
from pytest_mock import MockerFixture

from rheo.domain.exceptions import FileExistsError
from rheo.domain.file_config import FileExistsStrategy
from rheo.downloads import DownloadWorker

if t.TYPE_CHECKING:
    from loguru import Logger


@pytest.fixture
def test_worker(aio_client: ClientSession, mock_logger: "Logger") -> DownloadWorker:
    return DownloadWorker(aio_client, mock_logger)


class TestDownloadWorkerInitialization:
    """Test DownloadWorker initialization and basic setup."""

    def test_init_with_explicit_logger(
        self, aio_client: ClientSession, mock_logger: "Logger"
    ) -> None:
        """Test worker initialization with explicit logger."""
        worker = DownloadWorker(aio_client, mock_logger)
        assert worker.client is aio_client
        assert worker.logger is mock_logger

    def test_init_with_default_logger(self, aio_client: ClientSession) -> None:
        """Test worker initialization with default logger."""
        worker = DownloadWorker(aio_client)
        assert worker.client is aio_client
        assert worker.logger is not None


class TestDownloadWorkerSuccessfulDownloads:
    """Test successful download scenarios."""

    @pytest.mark.asyncio
    async def test_basic_download_success(
        self, test_worker: DownloadWorker, tmp_path: Path, mock_logger: "Logger"
    ) -> None:
        """Test basic successful file download."""
        test_url = "https://example.com/test.txt"
        test_content = b"Hello, World!"
        temp_file = tmp_path / "test.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)

            await test_worker.download(test_url, temp_file, download_id="test-id")

        # Verify file was created with correct content
        assert temp_file.exists()
        assert temp_file.read_bytes() == test_content

        # Verify logging - check that both start and completion messages were logged
        mock_logger.debug.assert_any_call(
            f"Starting download: {test_url} -> {temp_file}"
        )
        mock_logger.debug.assert_any_call(
            f"Download completed successfully: {temp_file}"
        )

    @pytest.mark.asyncio
    async def test_download_with_custom_chunk_size(
        self, test_worker: DownloadWorker, tmp_path: Path, mock_logger: "Logger"
    ) -> None:
        """Test download with custom chunk size."""
        test_url = "https://example.com/binary.dat"
        test_content = b"x" * 1000  # 1KB of data
        temp_file = tmp_path / "binary.dat"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)

            await test_worker.download(
                test_url, temp_file, download_id="test-id", chunk_size=256
            )

        assert temp_file.exists()
        assert temp_file.read_bytes() == test_content

    @pytest.mark.asyncio
    async def test_download_large_file(
        self, test_worker: DownloadWorker, tmp_path: Path, mock_logger: "Logger"
    ) -> None:
        """Test download of larger file to ensure chunking works."""
        test_url = "https://example.com/large.bin"
        test_content = b"A" * 10000  # 10KB file
        temp_file = tmp_path / "large.bin"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)

            await test_worker.download(
                test_url, temp_file, download_id="test-id", chunk_size=1024
            )

        assert temp_file.exists()
        assert temp_file.read_bytes() == test_content

    @pytest.mark.asyncio
    async def test_download_empty_file(
        self, test_worker: DownloadWorker, tmp_path: Path, mock_logger: "Logger"
    ) -> None:
        """Test download of empty file."""
        test_url = "https://example.com/empty.txt"
        temp_file = tmp_path / "empty.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=b"")

            await test_worker.download(test_url, temp_file, download_id="test-id")

        assert temp_file.exists()
        assert temp_file.read_bytes() == b""

    @pytest.mark.asyncio
    async def test_download_creates_parent_directories(
        self, test_worker: DownloadWorker, tmp_path: Path, mock_logger: "Logger"
    ) -> None:
        """Worker should create parent directories before writing file.

        This ensures downloads to subdirectories work even when the
        directories don't exist yet. Directory creation was moved from
        FileConfig (domain) to Worker (infrastructure) for layer purity.
        """
        test_url = "https://example.com/file.txt"
        test_content = b"Hello from nested dir!"
        # Destination in non-existent nested subdirectory
        dest_file = tmp_path / "new" / "nested" / "dir" / "file.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)

            await test_worker.download(test_url, dest_file, download_id="test-id")

        assert dest_file.exists()
        assert dest_file.read_bytes() == test_content


class TestDownloadWorkerHTTPErrors:
    """Test HTTP error handling."""

    @pytest.mark.asyncio
    async def test_download_404_error(
        self, test_worker: DownloadWorker, tmp_path: Path, mock_logger: "Logger"
    ) -> None:
        """Test handling of 404 Not Found error."""
        test_url = "https://example.com/notfound.txt"
        temp_file = tmp_path / "notfound.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=404, body="Not Found")

            with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                await test_worker.download(test_url, temp_file, download_id="test-id")

        # Verify error handling
        assert exc_info.value.status == 404
        assert not temp_file.exists()  # Partial file should be cleaned up
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_download_500_error(
        self, test_worker: DownloadWorker, tmp_path: Path, mock_logger: "Logger"
    ) -> None:
        """Test handling of 500 Internal Server Error."""
        test_url = "https://example.com/server-error.txt"
        temp_file = tmp_path / "server-error.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=500, body="Internal Server Error")

            with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                await test_worker.download(test_url, temp_file, download_id="test-id")

        assert exc_info.value.status == 500
        assert not temp_file.exists()
        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_download_403_forbidden(
        self, test_worker: DownloadWorker, tmp_path: Path, mock_logger: "Logger"
    ) -> None:
        """Test handling of 403 Forbidden error."""
        test_url = "https://example.com/forbidden.txt"
        temp_file = tmp_path / "forbidden.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=403, body="Forbidden")

            with pytest.raises(aiohttp.ClientResponseError) as exc_info:
                await test_worker.download(test_url, temp_file, download_id="test-id")

        assert exc_info.value.status == 403
        assert not temp_file.exists()


class TestDownloadWorkerNetworkErrors:
    """Test network-related error handling."""

    @pytest.mark.asyncio
    async def test_connection_error(
        self, test_worker: DownloadWorker, tmp_path: Path, mock_logger: "Logger"
    ) -> None:
        """Test handling of connection errors."""
        test_url = "https://example.com/test.txt"
        temp_file = tmp_path / "test.txt"

        with aioresponses() as mock:
            # Use a simple exception that aioresponses can handle
            mock.get(test_url, exception=ConnectionError("Connection failed"))

            with pytest.raises(ConnectionError):
                await test_worker.download(test_url, temp_file, download_id="test-id")

        assert not temp_file.exists()
        mock_logger.error.assert_called()
        # Check the error message contains expected text
        error_call = mock_logger.error.call_args[0][0]
        assert "File system error downloading from" in error_call

    @pytest.mark.asyncio
    async def test_ssl_error(
        self, test_worker: DownloadWorker, tmp_path: Path, mock_logger: "Logger"
    ) -> None:
        """Test handling of SSL errors."""
        test_url = "https://example.com/test.txt"
        temp_file = tmp_path / "test.txt"

        with aioresponses() as mock:
            # Use a simple SSL error for testing
            mock.get(test_url, exception=Exception("SSL verification failed"))

            with pytest.raises(Exception):
                await test_worker.download(test_url, temp_file, download_id="test-id")

        assert not temp_file.exists()
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert "Unexpected error downloading from" in error_call

    @pytest.mark.asyncio
    async def test_payload_error(
        self, test_worker: DownloadWorker, tmp_path: Path, mock_logger: "Logger"
    ) -> None:
        """Test handling of payload errors."""
        test_url = "https://example.com/test.txt"
        temp_file = tmp_path / "test.txt"

        with aioresponses() as mock:
            mock.get(test_url, exception=aiohttp.ClientPayloadError("Invalid payload"))

            with pytest.raises(aiohttp.ClientPayloadError):
                await test_worker.download(test_url, temp_file, download_id="test-id")

        assert not temp_file.exists()
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert "Invalid response payload from" in error_call


class TestDownloadWorkerTimeouts:
    """Test timeout handling."""

    @pytest.mark.asyncio
    async def test_timeout_error(
        self, test_worker: DownloadWorker, tmp_path: Path, mock_logger: "Logger"
    ) -> None:
        """Test handling of timeout errors."""
        test_url = "https://example.com/slow.txt"
        temp_file = tmp_path / "slow.txt"

        with aioresponses() as mock:
            # Just use a timeout exception directly instead of trying to
            # simulate slow response
            mock.get(test_url, exception=asyncio.TimeoutError())

            with pytest.raises(asyncio.TimeoutError):
                await test_worker.download(
                    test_url, temp_file, download_id="test-id", timeout=0.01
                )  # Very short timeout

        assert not temp_file.exists()
        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert "Timeout downloading from" in error_call


class TestDownloadWorkerFileSystemErrors:
    """Test file system related error handling."""

    @pytest.mark.asyncio
    async def test_permission_error(
        self, test_worker: DownloadWorker, tmp_path: Path, mock_logger: "Logger"
    ) -> None:
        """Test handling of permission errors when writing files."""
        test_url = "https://example.com/test.txt"

        # Create a read-only directory
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir(mode=0o555)  # Read and execute only
        readonly_file = readonly_dir / "test.txt"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=b"test content")

            with pytest.raises(PermissionError):
                await test_worker.download(
                    test_url, readonly_file, download_id="test-id"
                )

        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert "Permission denied writing file from" in error_call

    @pytest.mark.asyncio
    async def test_makedirs_failure_on_protected_path(
        self, test_worker: DownloadWorker, mock_logger: "Logger"
    ) -> None:
        """Test handling when makedirs fails on a protected system path.

        Worker creates parent directories automatically, but this should
        fail gracefully when attempting to create directories at locations
        where the user lacks permission (e.g., root-level paths).
        """
        test_url = "https://example.com/test.txt"
        # Attempting to create directories at root level should fail
        protected_path = Path("/nonexistent/directory/file.txt")

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=b"test content")

            with pytest.raises(OSError):  # PermissionError or similar
                await test_worker.download(
                    test_url, protected_path, download_id="test-id"
                )

        mock_logger.error.assert_called()
        error_call = mock_logger.error.call_args[0][0]
        assert test_url in error_call


class TestDownloadWorkerFileCleanup:
    """Test file cleanup behavior on errors."""

    @pytest.mark.asyncio
    async def test_partial_file_cleanup_on_http_error(
        self, test_worker: DownloadWorker, tmp_path: Path, mock_logger: "Logger"
    ) -> None:
        """Test that partial files are cleaned up on HTTP errors."""
        test_url = "https://example.com/test.txt"
        temp_file = tmp_path / "test.txt"

        # Pre-create the file to simulate partial download
        temp_file.write_bytes(b"partial content")
        assert temp_file.exists()

        with aioresponses() as mock:
            mock.get(test_url, status=404)

            with pytest.raises(aiohttp.ClientResponseError):
                await test_worker.download(test_url, temp_file, download_id="test-id")

        # File should be cleaned up
        assert not temp_file.exists()
        mock_logger.debug.assert_any_call(f"Cleaned up partial file: {temp_file}")


class TestDownloadWorkerChunkWriting:
    """Test the chunk writing functionality."""

    @pytest.mark.asyncio
    async def test_write_chunk_to_file(
        self, test_worker: DownloadWorker, tmp_path: Path
    ) -> None:
        """Test that _write_chunk_to_file writes data correctly with async I/O."""

        test_data = b"test chunk data"
        temp_file = tmp_path / "chunk.txt"

        async with aiofiles.open(temp_file, "wb") as f:
            await test_worker._write_chunk_to_file(test_data, f)

        assert temp_file.read_bytes() == test_data

    @pytest.mark.asyncio
    async def test_write_multiple_chunks(
        self, test_worker: DownloadWorker, tmp_path: Path
    ) -> None:
        """Test writing multiple chunks sequentially with async I/O."""

        chunks = [b"chunk1", b"chunk2", b"chunk3"]
        temp_file = tmp_path / "chunks.txt"

        async with aiofiles.open(temp_file, "wb") as f:
            for chunk in chunks:
                await test_worker._write_chunk_to_file(chunk, f)

        assert temp_file.read_bytes() == b"chunk1chunk2chunk3"


class TestDownloadWorkerExceptionHandling:
    """Test the exception handling and logging functionality."""

    def test_handle_client_connector_error(
        self,
        test_worker: DownloadWorker,
        mocker: MockerFixture,
        mock_logger: "Logger",
    ) -> None:
        """Test handling of ClientConnectorError."""
        test_url = "https://example.com/test.txt"

        # Create a mock exception that behaves like ClientConnectorError
        exception = mocker.Mock(spec=aiohttp.ClientConnectorError)
        exception.__class__ = aiohttp.ClientConnectorError
        exception.__str__ = mocker.Mock(return_value="Connection refused")

        test_worker._log_and_categorize_error(exception, test_url)

        mock_logger.error.assert_called_once()
        error_message = mock_logger.error.call_args[0][0]
        assert "Failed to connect to" in error_message
        assert test_url in error_message

    def test_handle_client_response_error(
        self,
        test_worker: DownloadWorker,
        mocker: MockerFixture,
        mock_logger: "Logger",
    ) -> None:
        """Test handling of ClientResponseError."""
        test_url = "https://example.com/test.txt"

        # Create a mock ClientResponseError with proper request_info
        mock_request_info = mocker.Mock()
        mock_request_info.real_url = test_url
        exception = aiohttp.ClientResponseError(
            request_info=mock_request_info, history=(), status=404, message="Not Found"
        )

        test_worker._log_and_categorize_error(exception, test_url)

        mock_logger.error.assert_called_once()
        error_message = mock_logger.error.call_args[0][0]
        assert "HTTP 404 error from" in error_message
        assert test_url in error_message

    def test_handle_timeout_error(
        self, aio_client: ClientSession, mock_logger: "Logger"
    ) -> None:
        """Test handling of TimeoutError."""
        test_worker = DownloadWorker(aio_client, mock_logger)
        test_url = "https://example.com/test.txt"
        exception = asyncio.TimeoutError()

        test_worker._log_and_categorize_error(exception, test_url)

        mock_logger.error.assert_called_once()
        error_message = mock_logger.error.call_args[0][0]
        assert "Timeout downloading from" in error_message
        assert test_url in error_message

    def test_handle_generic_exception(
        self, aio_client: ClientSession, mock_logger: "Logger"
    ) -> None:
        """Test handling of generic exceptions."""
        test_worker = DownloadWorker(aio_client, mock_logger)
        test_url = "https://example.com/test.txt"
        exception = ValueError("Some unexpected error")

        test_worker._log_and_categorize_error(exception, test_url)

        mock_logger.error.assert_called_once()
        mock_logger.debug.assert_called_once()

        error_message = mock_logger.error.call_args[0][0]
        assert "Unexpected error downloading from" in error_message
        assert test_url in error_message

        debug_message = mock_logger.debug.call_args[0][0]
        assert "Uncaught exception of type" in debug_message


class TestWorkerFileExistsStrategy:
    """Test file exists strategy handling in worker."""

    @pytest.mark.asyncio
    async def test_skip_strategy_skips_download(
        self,
        test_worker: DownloadWorker,
        tmp_path: Path,
        mock_logger: "Logger",
        mocker: MockerFixture,
    ) -> None:
        """SKIP strategy should skip download if file exists."""
        existing_file = tmp_path / "existing.txt"
        existing_file.write_text("original content")

        download_spy = mocker.spy(test_worker, "_download_with_cleanup")

        await test_worker.download(
            "https://example.com/file.txt",
            existing_file,
            download_id="test-id",
            file_exists_strategy=FileExistsStrategy.SKIP,
        )

        download_spy.assert_not_called()
        assert existing_file.read_text() == "original content"
        mock_logger.debug.assert_called_with(f"File exists, skipping: {existing_file}")

    @pytest.mark.asyncio
    async def test_error_strategy_raises_on_existing_file(
        self, test_worker: DownloadWorker, tmp_path: Path
    ) -> None:
        """ERROR strategy should raise FileExistsError."""
        existing_file = tmp_path / "existing.txt"
        existing_file.write_text("original content")

        with pytest.raises(FileExistsError) as exc_info:
            await test_worker.download(
                "https://example.com/file.txt",
                existing_file,
                download_id="test-id",
                file_exists_strategy=FileExistsStrategy.ERROR,
            )

        assert exc_info.value.path == existing_file

    @pytest.mark.asyncio
    async def test_overwrite_strategy_overwrites_existing_file(
        self, test_worker: DownloadWorker, tmp_path: Path
    ) -> None:
        """OVERWRITE strategy should replace existing file."""
        existing_file = tmp_path / "existing.txt"
        existing_file.write_text("original content")

        with aioresponses() as mock:
            mock.get("https://example.com/file.txt", body=b"new content")

            await test_worker.download(
                "https://example.com/file.txt",
                existing_file,
                download_id="test-id",
                file_exists_strategy=FileExistsStrategy.OVERWRITE,
            )

        assert existing_file.read_bytes() == b"new content"

    @pytest.mark.asyncio
    async def test_skip_proceeds_if_file_does_not_exist(
        self, test_worker: DownloadWorker, tmp_path: Path
    ) -> None:
        """SKIP strategy should download if file doesn't exist."""
        new_file = tmp_path / "new.txt"

        with aioresponses() as mock:
            mock.get("https://example.com/file.txt", body=b"content")

            await test_worker.download(
                "https://example.com/file.txt",
                new_file,
                download_id="test-id",
                file_exists_strategy=FileExistsStrategy.SKIP,
            )

        assert new_file.read_bytes() == b"content"
