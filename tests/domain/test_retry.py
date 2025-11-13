"""Tests for retry domain models."""

import pytest

from async_download_manager.domain.retry import (
    RetryConfig,
    RetryPolicy,
)


@pytest.fixture
def default_transient_status_codes():
    """Transient status codes for testing."""
    return frozenset({408, 429, 500, 502, 503, 504})


@pytest.fixture
def default_permanent_status_codes():
    """Permanent status codes for testing."""
    return frozenset({400, 401, 403, 404, 405, 410})


@pytest.fixture
def default_retry_policy(
    default_transient_status_codes, default_permanent_status_codes
):
    """Provide a sample RetryPolicy for testing."""
    return RetryPolicy(
        transient_status_codes=default_transient_status_codes,
        permanent_status_codes=default_permanent_status_codes,
        retry_unknown_errors=False,
    )


class TestRetryPolicy:
    """Test retry policy for status code categorisation."""

    def test_should_retry_transient_status_codes(
        self, default_retry_policy, default_transient_status_codes
    ):
        """Transient status codes should retry."""
        for status_code in default_transient_status_codes:
            assert default_retry_policy.should_retry_status(status_code) is True

    def test_should_not_retry_permanent_status_codes(
        self, default_retry_policy, default_permanent_status_codes
    ):
        """Permanent status codes should not retry."""
        for status_code in default_permanent_status_codes:
            assert default_retry_policy.should_retry_status(status_code) is False

    def test_unknown_status_respects_policy(self, default_retry_policy):
        """Unknown status codes respect retry_unknown_errors setting."""
        # Conservative: don't retry unknown
        assert default_retry_policy.should_retry_status(999) is False

    def test_custom_transient_codes(self):
        """Can customise transient status codes."""
        custom_transient_status_codes = frozenset({418, 420})
        custom_retry_policy = RetryPolicy(
            transient_status_codes=custom_transient_status_codes
        )
        assert custom_retry_policy.should_retry_status(418) is True
        assert (
            custom_retry_policy.should_retry_status(500) is False
        )  # Not in custom set

    def test_custom_permanent_codes(self):
        """Can customise permanent status codes."""
        policy = RetryPolicy(
            transient_status_codes=frozenset({404}),
            permanent_status_codes=frozenset({451}),
        )
        assert policy.should_retry_status(451) is False
        assert policy.should_retry_status(404) is True  # In transient set

    def test_permanent_takes_precedence(self):
        """Permanent codes take precedence over transient."""
        # If code is in both sets, permanent wins
        policy = RetryPolicy(
            transient_status_codes=frozenset({500}),
            permanent_status_codes=frozenset({500}),
        )
        assert policy.should_retry_status(500) is False


class TestRetryConfig:
    """Test retry configuration and backoff calculation."""

    def test_calculate_delay_exponential(self):
        """Delay grows exponentially without jitter."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            jitter=False,
        )
        assert config.calculate_delay(0) == 1.0  # 1.0 * 2^0
        assert config.calculate_delay(1) == 2.0  # 1.0 * 2^1
        assert config.calculate_delay(2) == 4.0  # 1.0 * 2^2
        assert config.calculate_delay(3) == 8.0  # 1.0 * 2^3

    def test_calculate_delay_respects_max(self):
        """Delay is capped at max_delay."""
        config = RetryConfig(
            base_delay=1.0,
            max_delay=5.0,
            exponential_base=2.0,
            jitter=False,
        )
        assert config.calculate_delay(10) == 5.0  # Would be 1024, capped at 5
        assert config.calculate_delay(100) == 5.0

    def test_calculate_delay_with_jitter(self):
        """Jitter adds randomness but keeps delay positive."""
        config = RetryConfig(base_delay=10.0, jitter=True)
        delays = [config.calculate_delay(0) for _ in range(100)]

        # All delays should be positive
        assert all(d > 0 for d in delays)

        # Should have variation (not all identical)
        assert len(set(delays)) > 1

        # Should be roughly around base_delay (within ±25%)
        assert all(7.5 <= d <= 12.5 for d in delays)

    def test_calculate_delay_jitter_minimum(self):
        """Jitter never produces delays below 0.1s."""
        config = RetryConfig(base_delay=0.1, jitter=True)
        delays = [config.calculate_delay(0) for _ in range(100)]
        assert all(d >= 0.1 for d in delays)

    def test_custom_exponential_base(self):
        """Can customise exponential base."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=3.0,
            jitter=False,
        )
        assert config.calculate_delay(0) == 1.0  # 1.0 * 3^0
        assert config.calculate_delay(1) == 3.0  # 1.0 * 3^1
        assert config.calculate_delay(2) == 9.0  # 1.0 * 3^2

    def test_custom_policy(self):
        """Can provide custom retry policy."""
        custom_policy = RetryPolicy(
            transient_status_codes=frozenset({418}),
        )
        config = RetryConfig(policy=custom_policy)
        assert config.policy is custom_policy
