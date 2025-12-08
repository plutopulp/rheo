"""Tests for download domain models."""

import typing as t

import pytest

from rheo.domain.downloads import DownloadInfo, DownloadStatus
from rheo.domain.hash_validation import HashAlgorithm, ValidationResult


@pytest.fixture
def make_download_info() -> t.Callable[..., DownloadInfo]:
    """Factory fixture for creating DownloadInfo instances with sensible defaults.

    Returns a factory function that accepts optional overrides for any field.

    Example:
        info = make_download_info()  # Uses all defaults
        info = make_download_info(download_id="custom123", bytes_downloaded=500)
    """

    def _factory(**overrides: t.Any) -> DownloadInfo:
        defaults = {
            "id": "test_download_id",
            "url": "https://example.com/file.txt",
            "status": DownloadStatus.PENDING,
            "bytes_downloaded": 0,
            "total_bytes": None,
            "destination_path": None,
            "error_message": None,
            "validation": None,
        }
        defaults.update(overrides)
        return DownloadInfo(**defaults)

    return _factory


class TestDownloadInfo:
    """Test DownloadInfo dataclass."""

    def test_downloadinfo_get_progress_with_total_bytes(
        self, make_download_info: t.Callable[..., DownloadInfo]
    ) -> None:
        """Test get_progress() returns correct fraction."""
        info = make_download_info(bytes_downloaded=250, total_bytes=1000)

        assert info.get_progress() == 0.25

    def test_downloadinfo_get_progress_without_total_bytes(
        self, make_download_info: t.Callable[..., DownloadInfo]
    ) -> None:
        """Test get_progress() returns 0.0 when total_bytes is None."""
        info = make_download_info(bytes_downloaded=250, total_bytes=None)

        assert info.get_progress() == 0.0

    def test_downloadinfo_get_progress_with_zero_total_bytes(
        self, make_download_info: t.Callable[..., DownloadInfo]
    ) -> None:
        """Test get_progress() returns 0.0 when total_bytes is 0."""
        info = make_download_info(bytes_downloaded=0, total_bytes=0)

        assert info.get_progress() == 0.0

    def test_downloadinfo_get_progress_caps_at_one(
        self, make_download_info: t.Callable[..., DownloadInfo]
    ) -> None:
        """Test get_progress() never exceeds 1.0."""
        info = make_download_info(bytes_downloaded=1500, total_bytes=1000)

        assert info.get_progress() == 1.0

    @pytest.mark.parametrize(
        "status",
        DownloadStatus.terminal_states(),
    )
    def test_downloadinfo_is_terminal_for_terminal_states(
        self, make_download_info: t.Callable[..., DownloadInfo], status: DownloadStatus
    ) -> None:
        """Test is_terminal() returns True for terminal statuses."""
        info = make_download_info(status=status)

        assert info.is_terminal()

    @pytest.mark.parametrize(
        "status",
        [
            DownloadStatus.QUEUED,
            DownloadStatus.PENDING,
            DownloadStatus.IN_PROGRESS,
        ],
    )
    def test_downloadinfo_is_terminal_for_non_terminal_states(
        self, make_download_info: t.Callable[..., DownloadInfo], status: DownloadStatus
    ) -> None:
        """Test is_terminal() returns False for non-terminal states."""
        info = make_download_info(status=status)

        assert not info.is_terminal()

    def test_validation_field_default_none(
        self, make_download_info: t.Callable[..., DownloadInfo]
    ) -> None:
        """Validation info defaults to None when validation not requested."""
        info = make_download_info()
        assert info.validation is None

    def test_validation_field_stores_result(
        self, make_download_info: t.Callable[..., DownloadInfo]
    ) -> None:
        """Validation result stored when provided."""
        result = ValidationResult(
            algorithm=HashAlgorithm.SHA256,
            expected_hash="a" * 64,
            calculated_hash="a" * 64,
        )
        info = make_download_info(validation=result)
        assert info.validation == result
        assert info.validation.is_valid

    def test_skipped_status_exists(self) -> None:
        """SKIPPED status should exist."""
        assert DownloadStatus.SKIPPED.value == "skipped"

    def test_cancelled_status_exists(self) -> None:
        """CANCELLED status should exist."""
        assert DownloadStatus.CANCELLED.value == "cancelled"
