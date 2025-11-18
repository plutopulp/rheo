"""Tests for error categoriser using pattern matching."""

import asyncio

import aiohttp
import pytest

from rheo.domain.retry import ErrorCategory, RetryPolicy
from rheo.downloads.error_categoriser import ErrorCategoriser


@pytest.fixture
def default_categoriser():
    """Provide an error categoriser with default policy."""
    return ErrorCategoriser(RetryPolicy())


@pytest.fixture
def custom_categoriser():
    """Provide an error categoriser with custom policy."""
    custom_policy = RetryPolicy(
        transient_status_codes=frozenset({404, 418}),
        permanent_status_codes=frozenset({500}),
        retry_unknown_errors=True,
    )
    return ErrorCategoriser(custom_policy)


class TestErrorCategoriserNetworkErrors:
    """Test categorisation of network/connection errors."""

    @pytest.mark.parametrize(
        "error",
        [
            asyncio.TimeoutError(),
            aiohttp.ClientConnectorError(None, OSError("Connection refused")),
            aiohttp.ClientOSError(),
            aiohttp.ClientPayloadError(),
        ],
    )
    def test_network_errors_are_transient(self, default_categoriser, error):
        """Network errors should be transient."""
        assert default_categoriser.categorise(error) == ErrorCategory.TRANSIENT


class TestErrorCategoriserHTTPErrors:
    """Test categorisation of HTTP response errors."""

    @pytest.mark.parametrize("status_code", [500, 503, 429])
    def test_status_codes_are_transient_by_policy(
        self, default_categoriser, status_code
    ):
        """Status codes should be transient with default policy."""
        error = aiohttp.ClientResponseError(None, None, status=status_code)
        assert default_categoriser.categorise(error) == ErrorCategory.TRANSIENT

    @pytest.mark.parametrize("status_code", [404, 403])
    def test_status_codes_are_permanent_by_policy(
        self, default_categoriser, status_code
    ):
        """Status codes should be permanent with default policy."""
        error = aiohttp.ClientResponseError(None, None, status=status_code)
        assert default_categoriser.categorise(error) == ErrorCategory.PERMANENT

    def test_custom_policy_changes_categorisation(self, custom_categoriser):
        """Custom policy can make 404 transient and 500 permanent."""
        # 404 is transient in custom policy
        error_404 = aiohttp.ClientResponseError(None, None, status=404)
        assert custom_categoriser.categorise(error_404) == ErrorCategory.TRANSIENT

        # 500 is permanent in custom policy
        error_500 = aiohttp.ClientResponseError(None, None, status=500)
        assert custom_categoriser.categorise(error_500) == ErrorCategory.PERMANENT


class TestErrorCategoriserSSLErrors:
    """Test categorisation of SSL/TLS errors."""

    def test_ssl_error_is_permanent(self, default_categoriser):
        """SSL errors should be permanent."""
        # ClientSSLError requires an OSError parameter
        os_error = OSError("SSL certificate verification failed")
        error = aiohttp.ClientSSLError(None, os_error)
        assert default_categoriser.categorise(error) == ErrorCategory.PERMANENT


class TestErrorCategoriserFilesystemErrors:
    """Test categorisation of filesystem errors."""

    @pytest.mark.parametrize(
        "error", [FileNotFoundError(), PermissionError(), OSError()]
    )
    def test_filesystem_errors_are_permanent(self, default_categoriser, error):
        """Filesystem errors should be permanent."""
        assert default_categoriser.categorise(error) == ErrorCategory.PERMANENT


class TestErrorCategoriserUnknownErrors:
    """Test categorisation of unknown errors."""

    def test_unknown_error_is_unknown_by_default(self, default_categoriser):
        """Unknown exception types should be UNKNOWN."""
        error = ValueError("Some random error")
        assert default_categoriser.categorise(error) == ErrorCategory.UNKNOWN

    def test_unknown_error_respects_policy(self):
        """Unknown errors respect policy retry_unknown_errors setting."""
        # Conservative policy
        policy_conservative = RetryPolicy(retry_unknown_errors=False)
        categoriser_conservative = ErrorCategoriser(policy_conservative)
        error = ValueError("Random error")
        assert categoriser_conservative.categorise(error) == ErrorCategory.UNKNOWN

        # Aggressive policy
        policy_aggressive = RetryPolicy(retry_unknown_errors=True)
        categoriser_aggressive = ErrorCategoriser(policy_aggressive)
        assert categoriser_aggressive.categorise(error) == ErrorCategory.TRANSIENT


class TestErrorCategoriserConvenienceMethod:
    """Test is_transient convenience method."""

    @pytest.mark.parametrize(
        "error, expected_result",
        [
            (asyncio.TimeoutError(), True),
            (aiohttp.ClientResponseError(None, None, status=500), True),
            (aiohttp.ClientResponseError(None, None, status=404), False),
            (PermissionError(), False),
            (OSError(), False),
            (FileNotFoundError(), False),
        ],
    )
    def test_is_transient_method(self, default_categoriser, error, expected_result):
        """is_transient should return boolean."""
        assert default_categoriser.is_transient(error) is expected_result
