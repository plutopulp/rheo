"""Tests for download command."""

from async_download_manager.domain.downloads import DownloadInfo, DownloadStatus
from async_download_manager.domain.hash_validation import HashAlgorithm


class TestDownloadCommandBasics:
    """Test basic download command functionality."""

    def test_download_creates_correct_file_config(
        self, cli_runner, app_with_mock_manager, mock_download_manager
    ):
        """Test that download command creates FileConfig correctly."""
        result = cli_runner.invoke(
            app_with_mock_manager, ["download", "http://example.com/file.zip"]
        )

        assert result.exit_code == 0
        mock_download_manager.add_to_queue.assert_called_once()

        # Inspect the FileConfig that was created
        call_args = mock_download_manager.add_to_queue.call_args[0][0]
        assert len(call_args) == 1
        assert str(call_args[0].url) == "http://example.com/file.zip"
        assert call_args[0].filename is None
        assert call_args[0].hash_config is None

    def test_download_with_custom_filename(
        self, cli_runner, app_with_mock_manager, mock_download_manager
    ):
        """Test download with custom filename."""
        result = cli_runner.invoke(
            app_with_mock_manager,
            ["download", "http://example.com/file.zip", "--filename", "custom.zip"],
        )

        assert result.exit_code == 0
        call_args = mock_download_manager.add_to_queue.call_args[0][0]
        assert call_args[0].filename == "custom.zip"


class TestDownloadCommandPaths:
    """Test output path and filename handling."""

    def test_download_with_custom_output_dir(
        self, cli_runner, app_with_mock_manager, mock_download_manager, tmp_path
    ):
        """Test -o flag for custom output directory."""
        result = cli_runner.invoke(
            app_with_mock_manager,
            ["download", "http://example.com/file.zip", "-o", str(tmp_path)],
        )

        assert result.exit_code == 0
        # Verify manager was created with correct download_dir
        # (implementation detail - can check via mock_download_manager creation)


class TestDownloadCommandHashValidation:
    """Test hash validation integration."""

    def test_download_with_hash_creates_hash_config(
        self, cli_runner, app_with_mock_manager, mock_download_manager
    ):
        """Test --hash flag creates proper HashConfig."""
        # Use valid hash length for SHA256 (64 hex chars)
        valid_hash = "a" * 64
        result = cli_runner.invoke(
            app_with_mock_manager,
            [
                "download",
                "http://example.com/file.zip",
                "--hash",
                f"sha256:{valid_hash}",
            ],
        )

        assert result.exit_code == 0
        call_args = mock_download_manager.add_to_queue.call_args[0][0]
        hash_config = call_args[0].hash_config

        assert hash_config is not None
        assert hash_config.algorithm == HashAlgorithm.SHA256
        assert hash_config.expected_hash == valid_hash

    def test_download_with_invalid_hash_format(self, cli_runner, app_with_mock_manager):
        """Test invalid hash format shows error."""
        result = cli_runner.invoke(
            app_with_mock_manager,
            ["download", "http://example.com/file.zip", "--hash", "invalid"],
        )

        assert result.exit_code == 1
        assert "Invalid hash" in result.stdout
        assert "Checksum must be in format" in result.stdout


class TestDownloadCommandErrors:
    """Test error handling and user feedback."""

    def test_download_failed_status_exits_with_error(
        self, cli_runner, app_with_mock_manager, mock_tracker
    ):
        """Test that failed download shows error and exits with code 1."""

        # Mock tracker to return failed download info
        mock_tracker.get_download_info.return_value = DownloadInfo(
            url="http://example.com/file.zip",
            status=DownloadStatus.FAILED,
        )

        result = cli_runner.invoke(
            app_with_mock_manager, ["download", "http://example.com/file.zip"]
        )

        assert result.exit_code == 1
        # Verify tracker was queried for download info
        mock_tracker.get_download_info.assert_called_with("http://example.com/file.zip")
