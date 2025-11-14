"""Tests for download domain models."""

import pytest

from async_download_manager.domain.downloads import DownloadInfo, DownloadStatus
from async_download_manager.domain.file_config import FileConfig


@pytest.fixture
def sample_file_config():
    """Provide a sample FileConfig for testing."""
    return FileConfig(
        url="https://example.com/test.txt",
        priority=1,
        size_bytes=1024,
        size_human="1 KB",
    )


class TestDownloadInfo:
    """Test DownloadInfo dataclass."""

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
