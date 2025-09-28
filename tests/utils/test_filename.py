"""Tests for filename utility functions."""

import pytest

from async_download_manager.utils.filename import generate_filename


class TestGenerateFilename:
    """Test cases for generate_filename function."""

    @pytest.fixture
    def basic_urls(self):
        """Fixture providing basic URL test cases."""
        return {
            "simple_file": "https://example.com/file.txt",
            "nested_path": "https://example.com/folder/subfolder/document.pdf",
            "domain_only": "https://example.com",
            "domain_with_slash": "https://example.com/",
        }

    @pytest.fixture
    def edge_case_urls(self):
        """Fixture providing edge case URL test cases."""
        return {
            "with_query": "https://example.com/file.txt?param=value&other=123",
            "with_fragment": "https://example.com/file.txt#section",
            "with_both": "https://example.com/file.txt?param=value#section",
            "no_extension": "https://example.com/folder/filename",
            "multiple_dots": "https://example.com/file.name.with.dots.txt",
            "subdomain": "https://api.example.com/data.json",
            "port": "https://example.com:8080/file.txt",
        }

    def test_basic_file_url(self, basic_urls):
        """Test filename generation for basic file URL."""
        result = generate_filename(basic_urls["simple_file"])
        assert result == "example.com-file.txt"

    def test_nested_path_url(self, basic_urls):
        """Test filename generation for nested path URL."""
        result = generate_filename(basic_urls["nested_path"])
        assert result == "example.com-document.pdf"

    def test_domain_only_url(self, basic_urls):
        """Test filename generation for domain-only URL."""
        result = generate_filename(basic_urls["domain_only"])
        assert result == "example.com"

    def test_domain_with_trailing_slash(self, basic_urls):
        """Test filename generation for domain with trailing slash."""
        result = generate_filename(basic_urls["domain_with_slash"])
        assert result == "example.com"

    def test_url_with_query_parameters(self, edge_case_urls):
        """Test that query parameters are stripped from filename."""
        result = generate_filename(edge_case_urls["with_query"])
        assert result == "example.com-file.txt"

    def test_url_with_fragment(self, edge_case_urls):
        """Test filename generation with URL fragment."""
        result = generate_filename(edge_case_urls["with_fragment"])
        assert result == "example.com-file.txt"

    def test_url_with_query_and_fragment(self, edge_case_urls):
        """Test filename generation with both query and fragment."""
        result = generate_filename(edge_case_urls["with_both"])
        assert result == "example.com-file.txt"

    def test_filename_without_extension(self, edge_case_urls):
        """Test filename generation for files without extension."""
        result = generate_filename(edge_case_urls["no_extension"])
        assert result == "example.com-filename"

    def test_filename_with_multiple_dots(self, edge_case_urls):
        """Test filename generation for files with multiple dots."""
        result = generate_filename(edge_case_urls["multiple_dots"])
        assert result == "example.com-file.name.with.dots.txt"

    def test_subdomain_url(self, edge_case_urls):
        """Test filename generation for subdomain URLs."""
        result = generate_filename(edge_case_urls["subdomain"])
        assert result == "api.example.com-data.json"

    def test_url_with_port(self, edge_case_urls):
        """Test filename generation for URLs with port numbers."""
        result = generate_filename(edge_case_urls["port"])
        assert result == "example.com:8080-file.txt"


class TestGenerateFilenameEdgeCases:
    """Test edge cases and potential error conditions."""

    def test_http_protocol(self):
        """Test filename generation for HTTP (non-HTTPS) URLs."""
        result = generate_filename("http://example.com/file.txt")
        assert result == "example.com-file.txt"

    def test_ftp_protocol(self):
        """Test filename generation for FTP URLs."""
        result = generate_filename("ftp://files.example.com/document.pdf")
        assert result == "files.example.com-document.pdf"

    def test_multiple_slashes_in_path(self):
        """Test handling of multiple slashes in URL path."""
        result = generate_filename("https://example.com//folder//file.txt")
        assert result == "example.com-file.txt"

    def test_path_ending_with_slash(self):
        """Test handling of path ending with slash (directory-like)."""
        result = generate_filename("https://example.com/folder/subfolder/")
        assert result == "example.com-subfolder"

    def test_empty_filename_in_path(self):
        """Test handling of empty filename in nested path."""
        result = generate_filename("https://example.com/folder/")
        assert result == "example.com-folder"

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://example.com/file", "example.com-file"),
            ("https://test.org/data.json", "test.org-data.json"),
            ("https://api.service.com/v1/endpoint", "api.service.com-endpoint"),
        ],
    )
    def test_parametrized_basic_cases(self, url, expected):
        """Test multiple basic cases using parametrization."""
        assert generate_filename(url) == expected
