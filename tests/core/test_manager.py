"""Tests for download manager functionality."""

import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from aiohttp import ClientSession
from aioresponses import aioresponses

from async_download_manager.core.manager import download_file


class TestDownloadFile:
    """Basic tests for download_file function."""

    @pytest_asyncio.fixture
    async def client_session(self):
        """Provide a real ClientSession for testing."""
        session = ClientSession()
        yield session
        await session.close()

    @pytest.fixture
    def temp_download_path(self):
        """Provide a temporary file path for download testing."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            path = Path(tmp.name)
        yield path
        # Cleanup
        if path.exists():
            path.unlink()

    @pytest.fixture
    def sample_urls(self):
        """Sample URLs for testing."""
        return {
            "text_file": "https://example.com/test.txt",
            "binary_file": "https://example.com/image.jpg",
            "large_file": "https://example.com/large_file.zip",
        }

    @pytest.mark.asyncio
    async def test_download_file_basic(
        self, client_session, temp_download_path, sample_urls
    ):
        """Test basic file download functionality."""
        with aioresponses() as mock:
            # Mock the HTTP response with chunked content
            mock.get(sample_urls["text_file"], status=200, body=b"testdatachunks")

            await download_file(
                client=client_session,
                url=sample_urls["text_file"],
                to=temp_download_path,
            )

        # Verify file was created and has expected content
        assert temp_download_path.exists()
        assert temp_download_path.read_bytes() == b"testdatachunks"

    @pytest.mark.asyncio
    async def test_download_file_custom_chunk_size(
        self, client_session, temp_download_path, sample_urls
    ):
        """Test download with custom chunk size."""
        with aioresponses() as mock:
            mock.get(sample_urls["binary_file"], status=200, body=b"binarydata")

            await download_file(
                client=client_session,
                url=sample_urls["binary_file"],
                to=temp_download_path,
                chunk_size=4,
            )

        # Verify file was created with correct content
        assert temp_download_path.exists()
        assert temp_download_path.read_bytes() == b"binarydata"
