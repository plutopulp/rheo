"""Tests for FileConfig filename and path resolution methods."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from rheo.domain.file_config import FileConfig
from rheo.domain.hash_validation import HashAlgorithm, HashConfig


class TestFileConfigURLValidation:
    """Test URL validation in FileConfig initialization."""

    def test_valid_http_url(self):
        """Test that valid HTTP URL is accepted."""
        config = FileConfig(url="http://example.com/file.txt")
        assert str(config.url) == "http://example.com/file.txt"

    def test_valid_https_url(self):
        """Test that valid HTTPS URL is accepted."""
        config = FileConfig(url="https://example.com/file.txt")
        assert str(config.url) == "https://example.com/file.txt"

    def test_url_with_port(self):
        """Test that URL with port is accepted."""
        config = FileConfig(url="https://example.com:8080/file.txt")
        assert str(config.url) == "https://example.com:8080/file.txt"

    def test_url_with_query_params(self):
        """Test that URL with query parameters is accepted."""
        config = FileConfig(url="https://example.com/file.txt?param=value")
        assert str(config.url) == "https://example.com/file.txt?param=value"

    def test_empty_url_raises_error(self):
        """Test that empty URL raises ValidationError."""
        with pytest.raises(ValidationError):
            FileConfig(url="")

    def test_whitespace_only_url_raises_error(self):
        """Test that whitespace-only URL raises ValidationError."""
        with pytest.raises(ValidationError):
            FileConfig(url="   ")

    def test_url_without_scheme_raises_error(self):
        """Test that URL without protocol scheme raises ValidationError."""
        with pytest.raises(ValidationError):
            FileConfig(url="example.com/file.txt")

    def test_unsupported_protocol_raises_error(self):
        """Test that unsupported protocol raises ValidationError."""
        with pytest.raises(ValidationError):
            FileConfig(url="ftp://example.com/file.txt")

    def test_file_protocol_raises_error(self):
        """Test that file:// protocol raises ValidationError."""
        with pytest.raises(ValidationError):
            FileConfig(url="file:///path/to/file.txt")

    def test_javascript_protocol_raises_error(self):
        """Test that javascript: protocol raises ValidationError."""
        with pytest.raises(ValidationError):
            FileConfig(url="javascript:alert('xss')")


class TestFileConfigBasicFilenameGeneration:
    """Test basic filename generation from URLs (migrated from test_filename.py)."""

    def test_simple_file_url(self):
        """Test filename generation for basic file URL."""
        config = FileConfig(url="https://example.com/file.txt")
        assert config.get_destination_filename() == "example.com-file.txt"

    def test_nested_path_url(self):
        """Test filename generation for nested path URL (uses last segment)."""
        config = FileConfig(url="https://example.com/folder/subfolder/document.pdf")
        assert config.get_destination_filename() == "example.com-document.pdf"

    def test_domain_only_url(self):
        """Test filename generation for domain-only URL."""
        config = FileConfig(url="https://example.com")
        assert config.get_destination_filename() == "example.com"

    def test_domain_with_trailing_slash(self):
        """Test filename generation for domain with trailing slash."""
        config = FileConfig(url="https://example.com/")
        assert config.get_destination_filename() == "example.com"

    def test_url_with_query_parameters(self):
        """Test that query parameters are stripped from filename."""
        config = FileConfig(url="https://example.com/file.txt?param=value&other=123")
        assert config.get_destination_filename() == "example.com-file.txt"

    def test_url_with_fragment(self):
        """Test that URL fragments are stripped from filename."""
        config = FileConfig(url="https://example.com/file.txt#section")
        assert config.get_destination_filename() == "example.com-file.txt"

    def test_url_with_query_and_fragment(self):
        """Test that both query and fragment are stripped."""
        config = FileConfig(url="https://example.com/file.txt?param=value#section")
        assert config.get_destination_filename() == "example.com-file.txt"

    def test_filename_without_extension(self):
        """Test filename generation for files without extension."""
        config = FileConfig(url="https://example.com/folder/filename")
        assert config.get_destination_filename() == "example.com-filename"

    def test_filename_with_multiple_dots(self):
        """Test that filenames with multiple dots are preserved."""
        config = FileConfig(url="https://example.com/file.name.with.dots.txt")
        assert (
            config.get_destination_filename() == "example.com-file.name.with.dots.txt"
        )

    def test_subdomain_url(self):
        """Test filename generation for subdomain URLs."""
        config = FileConfig(url="https://api.example.com/data.json")
        assert config.get_destination_filename() == "api.example.com-data.json"

    def test_url_with_port(self):
        """Test filename generation for URLs with port numbers."""
        config = FileConfig(url="https://example.com:8080/file.txt")
        assert config.get_destination_filename() == "example.com_8080-file.txt"

    def test_http_protocol(self):
        """Test filename generation for HTTP (non-HTTPS) URLs."""
        config = FileConfig(url="http://example.com/file.txt")
        assert config.get_destination_filename() == "example.com-file.txt"

    def test_path_ending_with_slash(self):
        """Test handling of path ending with slash (directory-like)."""
        config = FileConfig(url="https://example.com/folder/subfolder/")
        assert config.get_destination_filename() == "example.com-subfolder"


class TestFileConfigCustomFilename:
    """Test custom filename handling."""

    def test_custom_filename_is_used(self):
        """Test that custom filename is used when provided."""
        config = FileConfig(
            url="https://example.com/file.txt", filename="custom_name.txt"
        )
        assert config.get_destination_filename() == "custom_name.txt"

    def test_none_filename_generates_from_url(self):
        """Test that None filename falls back to URL generation."""
        config = FileConfig(url="https://example.com/file.txt", filename=None)
        assert config.get_destination_filename() == "example.com-file.txt"

    def test_custom_filename_is_sanitized(self):
        """Test that custom filename is sanitized for invalid characters."""
        config = FileConfig(
            url="https://example.com/file.txt", filename="my<file>name:test.txt"
        )
        # Should sanitize invalid characters
        result = config.get_destination_filename()
        assert "<" not in result
        assert ">" not in result
        assert ":" not in result


class TestFileConfigSanitization:
    """Test filename sanitization for filesystem safety."""

    def test_sanitize_invalid_characters(self):
        """Test that invalid filesystem characters are replaced."""
        # Test with URL containing characters that end up in filename
        config = FileConfig(url="https://example.com/file<name>.txt")
        result = config.get_destination_filename()
        assert "<" not in result
        assert ">" not in result

    def test_sanitize_colons_in_port(self):
        """Test that colons in port numbers are handled."""
        config = FileConfig(url="https://example.com:8080/file.txt")
        result = config.get_destination_filename()
        # Colon should be replaced with underscore
        assert "example.com_8080-file.txt" == result

    def test_sanitize_multiple_spaces(self):
        """Test that multiple consecutive spaces are collapsed."""
        config = FileConfig(
            url="https://example.com/file.txt", filename="my    file.txt   "
        )
        assert config.get_destination_filename() == "my file.txt"

    def test_reserved_windows_filename_con(self):
        """Test that reserved Windows filename CON is handled."""
        config = FileConfig(url="https://example.com/file.txt", filename="CON")
        result = config.get_destination_filename()
        # Should append underscore to avoid Windows reserved name
        assert result == "CON_"

    def test_very_long_filename_truncation(self):
        """Test that very long filenames are truncated intelligently."""
        long_name = "a" * 300 + ".txt"
        config = FileConfig(url="https://example.com/file.txt", filename=long_name)
        result = config.get_destination_filename()
        # Should be truncated to 255 chars or less
        assert len(result) <= 255
        # Should preserve extension
        assert result.endswith(".txt")

    def test_unicode_characters_preserved(self):
        """Test that valid Unicode characters are preserved."""
        config = FileConfig(url="https://example.com/file.txt", filename="文件名.txt")
        assert config.get_destination_filename() == "文件名.txt"


class TestFileConfigPathResolution:
    """Test get_destination_path() method."""

    def test_path_without_subdirectory(self):
        """Test path resolution without subdirectory."""
        config = FileConfig(url="https://example.com/file.txt")
        base_dir = Path("/downloads")
        result = config.get_destination_path(base_dir)
        assert result == Path("/downloads/example.com-file.txt")

    def test_path_with_subdirectory(self):
        """Test path resolution with subdirectory."""
        config = FileConfig(
            url="https://example.com/file.txt", destination_subdir="docs"
        )
        base_dir = Path("/downloads")
        result = config.get_destination_path(base_dir)
        assert result == Path("/downloads/docs/example.com-file.txt")

    def test_path_with_nested_subdirectories(self):
        """Test path resolution with nested subdirectories."""
        config = FileConfig(
            url="https://example.com/file.txt", destination_subdir="docs/reports/2024"
        )
        base_dir = Path("/downloads")
        result = config.get_destination_path(base_dir)
        assert result == Path("/downloads/docs/reports/2024/example.com-file.txt")

    def test_path_with_custom_filename_and_subdir(self):
        """Test path resolution with both custom filename and subdirectory."""
        config = FileConfig(
            url="https://example.com/file.txt",
            filename="report.pdf",
            destination_subdir="reports",
        )
        base_dir = Path("/downloads")
        result = config.get_destination_path(base_dir)
        assert result == Path("/downloads/reports/report.pdf")

    def test_path_with_trailing_slashes_normalized(self):
        """Test that paths with trailing slashes are normalized."""
        config = FileConfig(
            url="https://example.com/file.txt", destination_subdir="docs/"
        )
        base_dir = Path("/downloads/")
        result = config.get_destination_path(base_dir)
        # Should normalize to standard path without double slashes
        assert result == Path("/downloads/docs/example.com-file.txt")

    def test_path_with_relative_base_dir(self):
        """Test path resolution with relative base directory."""
        config = FileConfig(url="https://example.com/file.txt")
        base_dir = Path("downloads")
        result = config.get_destination_path(base_dir)
        assert result == Path("downloads/example.com-file.txt")

    def test_path_with_deeply_nested_subdirectories(self):
        """Test path resolution with deeply nested subdirectories.

        Note: Directory creation is now handled by infrastructure (DownloadWorker),
        not the domain model. This test verifies pure path computation.
        """
        config = FileConfig(
            url="https://example.com/file.txt", destination_subdir="new/nested/dir"
        )
        base_dir = Path("/downloads")
        result = config.get_destination_path(base_dir)
        # Should return correct path - directory creation is caller's responsibility
        assert result == Path("/downloads/new/nested/dir/example.com-file.txt")
        assert result.parent == Path("/downloads/new/nested/dir")


class TestFileConfigEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_url_path(self):
        """Test handling of URL with empty path."""
        config = FileConfig(url="https://example.com")
        assert config.get_destination_filename() == "example.com"

    def test_dots_in_filename_preserved(self):
        """Test that dots in filename are preserved (not confused with extensions)."""
        config = FileConfig(url="https://example.com/my.file.name.tar.gz")
        assert config.get_destination_filename() == "example.com-my.file.name.tar.gz"

    def test_special_characters_in_url_path(self):
        """Test handling of special characters in URL path."""
        config = FileConfig(url="https://example.com/file%20name.txt")
        result = config.get_destination_filename()
        # Should handle URL encoding appropriately
        assert "file" in result

    @pytest.mark.parametrize(
        "url,expected_filename",
        [
            ("https://example.com/file", "example.com-file"),
            ("https://test.org/data.json", "test.org-data.json"),
            ("https://api.service.com/v1/endpoint", "api.service.com-endpoint"),
        ],
    )
    def test_parametrized_filename_cases(self, url, expected_filename):
        """Test multiple URL cases using parametrization."""
        config = FileConfig(url=url)
        assert config.get_destination_filename() == expected_filename


class TestFileConfigHashIntegration:
    """Ensure FileConfig stores optional hash configuration."""

    def test_accepts_hash_config(self):
        """FileConfig can store and expose HashConfig."""
        hash_config = HashConfig(
            algorithm=HashAlgorithm.MD5,
            expected_hash="a" * HashAlgorithm.MD5.hex_length,
        )
        config = FileConfig(url="https://example.com/file.txt", hash_config=hash_config)
        assert config.hash_config is hash_config


class TestFileConfigPathTraversalSecurity:
    """Test that destination_subdir prevents path traversal attacks."""

    def test_destination_subdir_rejects_parent_references(self):
        """Test that parent directory references (..) are rejected.

        Security: Prevents path traversal attacks that could write files
        outside the intended download directory.
        """
        # Simple parent reference
        with pytest.raises(ValidationError) as exc_info:
            FileConfig(url="https://example.com/file.txt", destination_subdir="..")
        assert "cannot contain '..'" in str(exc_info.value).lower()

        # Parent reference in path
        with pytest.raises(ValidationError) as exc_info:
            FileConfig(url="https://example.com/file.txt", destination_subdir="../etc")
        assert "cannot contain '..'" in str(exc_info.value).lower()

        # Nested parent references (path traversal attempt)
        with pytest.raises(ValidationError) as exc_info:
            FileConfig(
                url="https://example.com/malware.py",
                destination_subdir="docs/../../etc",
            )
        assert "cannot contain '..'" in str(exc_info.value).lower()

    def test_destination_subdir_rejects_absolute_paths(self):
        """Test that absolute paths are rejected.

        Security: Prevents writing to arbitrary filesystem locations.
        """
        # Unix absolute path
        with pytest.raises(ValidationError) as exc_info:
            FileConfig(url="https://example.com/file.txt", destination_subdir="/etc")
        assert "must be relative" in str(exc_info.value).lower()

        # Unix absolute path with subdirs
        with pytest.raises(ValidationError) as exc_info:
            FileConfig(
                url="https://example.com/file.txt", destination_subdir="/home/user/docs"
            )
        assert "must be relative" in str(exc_info.value).lower()

    def test_destination_subdir_accepts_valid_relative_paths(self):
        """Test that valid relative paths are accepted."""
        # Simple subdirectory
        config = FileConfig(
            url="https://example.com/file.txt", destination_subdir="docs"
        )
        assert config.destination_subdir == "docs"

        # Nested subdirectories
        config = FileConfig(
            url="https://example.com/file.txt", destination_subdir="videos/lectures"
        )
        assert config.destination_subdir == "videos/lectures"

        # Deep nesting (valid as long as no ..)
        config = FileConfig(
            url="https://example.com/file.txt", destination_subdir="a/b/c/d/e"
        )
        assert config.destination_subdir == "a/b/c/d/e"

    def test_destination_subdir_rejects_empty_string(self):
        """Test that empty string is rejected (ambiguous intent)."""
        with pytest.raises(ValidationError) as exc_info:
            FileConfig(url="https://example.com/file.txt", destination_subdir="")
        assert "cannot be empty" in str(exc_info.value).lower()

    def test_destination_subdir_rejects_current_directory_only(self):
        """Test that current directory '.' is rejected (no effect)."""
        with pytest.raises(ValidationError) as exc_info:
            FileConfig(url="https://example.com/file.txt", destination_subdir=".")
        assert "cannot be empty" in str(exc_info.value).lower()

    def test_destination_subdir_none_is_valid(self):
        """Test that None (default) is valid - means no subdirectory."""
        config = FileConfig(url="https://example.com/file.txt", destination_subdir=None)
        assert config.destination_subdir is None

        # Also test omitting the field entirely
        config = FileConfig(url="https://example.com/file.txt")
        assert config.destination_subdir is None


class TestFileConfigId:
    """Test ID generation from URL and destination path."""

    def test_id_stable_for_same_config(self):
        """Test that same config produces same ID consistently."""
        config1 = FileConfig(url="https://example.com/file.txt")
        config2 = FileConfig(url="https://example.com/file.txt")

        assert config1.id == config2.id

    def test_id_different_for_different_urls(self):
        """Test that different URLs produce different IDs."""
        config1 = FileConfig(url="https://example.com/file1.txt")
        config2 = FileConfig(url="https://example.com/file2.txt")

        assert config1.id != config2.id

    def test_id_different_for_different_destinations(self):
        """Test that same URL but different filenames produce different IDs."""
        config1 = FileConfig(url="https://example.com/file.txt", filename="custom1.txt")
        config2 = FileConfig(url="https://example.com/file.txt", filename="custom2.txt")

        assert config1.id != config2.id

    def test_id_different_for_different_subdirs(self):
        """Test that same filename but different subdirs produce different IDs."""
        config1 = FileConfig(
            url="https://example.com/file.txt", destination_subdir="folder1"
        )
        config2 = FileConfig(
            url="https://example.com/file.txt", destination_subdir="folder2"
        )

        assert config1.id != config2.id

    def test_id_is_correct_length_hex(self):
        """Test that ID format is correct length hex string."""
        config = FileConfig(url="https://example.com/file.txt")
        download_id = config.id

        # Should be exactly DOWNLOAD_ID_LENGTH characters
        assert len(download_id) == FileConfig.DOWNLOAD_ID_LENGTH

        # Should be valid hexadecimal
        assert int(download_id, 16) >= 0

    def test_frozen_config_prevents_mutation(self):
        """Test that frozen=True prevents field mutation."""
        config = FileConfig(url="https://example.com/file.txt")

        # Should not be able to modify URL
        with pytest.raises(ValidationError):
            config.url = "https://example.com/different.txt"

        # Should not be able to modify filename
        with pytest.raises(ValidationError):
            config.filename = "modified.txt"
