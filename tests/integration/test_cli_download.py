"""Integration tests for CLI download command."""

import hashlib

import pytest
from aioresponses import aioresponses


class TestCLIDownloadIntegration:
    """Integration tests for the download command end-to-end.

    Note: Event display output (e.g. "Downloaded:") is temporarily disabled
    while event subscription interface is being redesigned. Tests verify
    functionality (exit code, file contents) without checking for output text.
    """

    def test_download_file_with_mocked_response(
        self, cli_runner, default_app, tmp_path
    ):
        """Integration test downloading a file using mocked HTTP response.

        This tests the full CLI → Manager → Worker → FileSystem flow
        without requiring network access.
        """
        test_url = "https://example.com/testfile.bin"
        test_content = b"x" * 1024  # 1KB of test data

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)

            result = cli_runner.invoke(
                default_app, ["download", test_url, "-o", str(tmp_path)]
            )

        assert result.exit_code == 0, f"Command failed with: {result.stdout}"

        # Verify file was created with correct content
        downloaded_files = list(tmp_path.iterdir())
        assert len(downloaded_files) == 1
        assert downloaded_files[0].read_bytes() == test_content

    def test_download_with_custom_filename(self, cli_runner, default_app, tmp_path):
        """Test CLI download with custom filename."""
        test_url = "https://example.com/original.bin"
        test_content = b"custom file content"

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)

            result = cli_runner.invoke(
                default_app,
                [
                    "download",
                    test_url,
                    "-o",
                    str(tmp_path),
                    "--filename",
                    "custom.bin",
                ],
            )

        assert result.exit_code == 0

        # Verify custom filename was used
        custom_file = tmp_path / "custom.bin"
        assert custom_file.exists()
        assert custom_file.read_bytes() == test_content

    def test_download_with_hash_validation(self, cli_runner, default_app, tmp_path):
        """Test CLI download with hash validation."""
        test_url = "https://example.com/verified.bin"
        test_content = b"verified content"

        # Calculate actual SHA256 hash
        expected_hash = hashlib.sha256(test_content).hexdigest()

        with aioresponses() as mock:
            mock.get(test_url, status=200, body=test_content)

            result = cli_runner.invoke(
                default_app,
                [
                    "download",
                    test_url,
                    "-o",
                    str(tmp_path),
                    "--hash",
                    f"sha256:{expected_hash}",
                ],
            )

        assert result.exit_code == 0, f"Command failed with: {result.stdout}"

        # Verify file exists with correct content
        downloaded_files = list(tmp_path.iterdir())
        assert len(downloaded_files) == 1
        assert downloaded_files[0].read_bytes() == test_content

    @pytest.mark.network
    def test_download_real_https_url_with_ssl(self, cli_runner, default_app, tmp_path):
        """Real network test to verify SSL configuration works correctly.

        This test makes an actual HTTPS request to verify SSL certificates
        are properly configured via certifi. Marked with @pytest.mark.network
        so it's skipped by default but can be run explicitly with:
            pytest -m network

        This test validates the fix for SSLCertVerificationError that occurred
        on macOS with Python 3.14 when system certificates weren't found.
        """
        # Use a reliable, small file from a trusted source with valid SSL
        test_url = (
            "https://raw.githubusercontent.com/github/gitignore/main/Python.gitignore"
        )

        result = cli_runner.invoke(
            default_app, ["download", test_url, "-o", str(tmp_path)]
        )

        assert result.exit_code == 0, f"Command failed with: {result.stdout}"

        # Verify file was created
        downloaded_files = list(tmp_path.iterdir())
        assert len(downloaded_files) == 1
        assert downloaded_files[0].stat().st_size > 0
