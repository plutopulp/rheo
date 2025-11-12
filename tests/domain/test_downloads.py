"""Tests for download domain models."""

import pytest

from async_download_manager.domain.downloads import (
    DownloadInfo,
    DownloadStatus,
    FileConfig,
)


@pytest.fixture
def sample_file_config():
    """Provide a sample FileConfig for testing."""
    return FileConfig(
        url="https://example.com/test.txt",
        priority=1,
        size_bytes=1024,
        size_human="1 KB",
    )


class TestFileConfig:
    """Test FileConfig dataclass."""

    def test_fileconfig_minimal_creation(self):
        """Test creating FileConfig with just URL."""
        config = FileConfig(url="https://example.com/file.txt")

        assert config.url == "https://example.com/file.txt"
        assert config.priority == 1  # Default
        assert config.type is None
        assert config.description is None
        assert config.size_human is None
        assert config.size_bytes is None
        assert config.filename is None
        assert config.destination_subdir is None
        assert config.timeout is None
        assert config.max_retries == 0

    def test_fileconfig_with_all_fields(self):
        """Test creating FileConfig with all fields populated."""
        config = FileConfig(
            url="https://example.com/file.txt",
            priority=5,
            type="document",
            description="Test file",
            size_human="1 MB",
            size_bytes=1048576,
            filename="custom_name.txt",
            destination_subdir="downloads/docs",
            timeout=30.0,
            max_retries=3,
        )

        assert config.url == "https://example.com/file.txt"
        assert config.priority == 5
        assert config.type == "document"
        assert config.description == "Test file"
        assert config.size_human == "1 MB"
        assert config.size_bytes == 1048576
        assert config.filename == "custom_name.txt"
        assert config.destination_subdir == "downloads/docs"
        assert config.timeout == 30.0
        assert config.max_retries == 3


class TestDownloadInfo:
    """Test DownloadInfo dataclass."""

    def test_downloadinfo_minimal_creation(self):
        """Test creating DownloadInfo with just URL."""
        info = DownloadInfo(url="https://example.com/file.txt")

        assert info.url == "https://example.com/file.txt"
        assert info.status == DownloadStatus.PENDING
        assert info.bytes_downloaded == 0
        assert info.total_bytes is None
        assert info.error is None

    def test_downloadinfo_get_progress_with_total_bytes(self):
        """Test get_progress() returns correct fraction."""
        info = DownloadInfo(
            url="https://example.com/file.txt",
            bytes_downloaded=250,
            total_bytes=1000,
        )

        assert info.get_progress() == 0.25

    def test_downloadinfo_get_progress_without_total_bytes(self):
        """Test get_progress() returns 0.0 when total_bytes is None."""
        info = DownloadInfo(
            url="https://example.com/file.txt",
            bytes_downloaded=250,
            total_bytes=None,
        )

        assert info.get_progress() == 0.0

    def test_downloadinfo_get_progress_with_zero_total_bytes(self):
        """Test get_progress() returns 0.0 when total_bytes is 0."""
        info = DownloadInfo(
            url="https://example.com/file.txt",
            bytes_downloaded=0,
            total_bytes=0,
        )

        assert info.get_progress() == 0.0

    def test_downloadinfo_get_progress_caps_at_one(self):
        """Test get_progress() never exceeds 1.0."""
        info = DownloadInfo(
            url="https://example.com/file.txt",
            bytes_downloaded=1500,
            total_bytes=1000,
        )

        assert info.get_progress() == 1.0

    def test_downloadinfo_is_terminal_for_completed(self):
        """Test is_terminal() returns True for COMPLETED status."""
        info = DownloadInfo(
            url="https://example.com/file.txt",
            status=DownloadStatus.COMPLETED,
        )

        assert info.is_terminal()

    def test_downloadinfo_is_terminal_for_failed(self):
        """Test is_terminal() returns True for FAILED status."""
        info = DownloadInfo(
            url="https://example.com/file.txt",
            status=DownloadStatus.FAILED,
        )

        assert info.is_terminal()

    @pytest.mark.parametrize(
        "status",
        [
            DownloadStatus.QUEUED,
            DownloadStatus.PENDING,
            DownloadStatus.IN_PROGRESS,
        ],
    )
    def test_downloadinfo_is_terminal_for_non_terminal_states(self, status):
        """Test is_terminal() returns False for non-terminal states."""
        info = DownloadInfo(
            url="https://example.com/file.txt",
            status=status,
        )

        assert not info.is_terminal()
