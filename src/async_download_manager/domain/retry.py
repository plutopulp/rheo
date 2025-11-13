"""Domain models for retry configuration and policies."""

import random
from dataclasses import dataclass, field
from enum import Enum


class ErrorCategory(Enum):
    """Classification of download errors for retry decisions."""

    TRANSIENT = "transient"  # Temporary, should retry
    PERMANENT = "permanent"  # Won't fix itself, don't retry
    UNKNOWN = "unknown"  # Conservative: don't retry


@dataclass
class RetryPolicy:
    """Policy for determining if errors should be retried.

    This is a configuration object that defines which errors are transient.
    Users can customise status codes and error types.
    """

    # HTTP status codes that indicate transient errors
    transient_status_codes: frozenset[int] = field(
        default_factory=lambda: frozenset(
            {
                408,  # Request Timeout
                429,  # Too Many Requests
                500,  # Internal Server Error
                502,  # Bad Gateway
                503,  # Service Unavailable
                504,  # Gateway Timeout
            }
        )
    )

    # HTTP status codes that indicate permanent errors
    permanent_status_codes: frozenset[int] = field(
        default_factory=lambda: frozenset(
            {
                400,  # Bad Request
                401,  # Unauthorised
                403,  # Forbidden
                404,  # Not Found
                405,  # Method Not Allowed
                410,  # Gone
            }
        )
    )

    # Whether to retry on unknown errors (conservative default: False)
    retry_unknown_errors: bool = False

    def should_retry_status(self, status_code: int) -> bool:
        """
        Check if HTTP status code should trigger retry.

        Permanent codes take precedence over transient codes.

        Args:
            status_code: HTTP status code to check

        Returns:
            True if should retry, False otherwise
        """
        if status_code in self.permanent_status_codes:
            return False
        if status_code in self.transient_status_codes:
            return True
        # Unknown status code - use conservative policy
        return self.retry_unknown_errors


@dataclass
class RetryConfig:
    """Configuration for retry behaviour with exponential backoff."""

    max_retries: int = 3
    base_delay: float = 1.0  # Initial delay in seconds
    max_delay: float = 60.0  # Cap maximum delay
    exponential_base: float = 2.0  # Delay multiplier
    jitter: bool = True  # Add randomness to avoid thundering herd
    policy: RetryPolicy = field(default_factory=RetryPolicy)

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for given retry attempt using exponential backoff.

        Formula: min(base_delay * (exponential_base ^ attempt), max_delay)

        Args:
            attempt: Current retry attempt (0-indexed)

        Returns:
            Delay in seconds with optional jitter

        Examples:
            >>> config = RetryConfig(base_delay=1.0, exponential_base=2.0)
            >>> config.calculate_delay(0)  # First retry
            1.0
            >>> config.calculate_delay(1)  # Second retry
            2.0
            >>> config.calculate_delay(2)  # Third retry
            4.0
        """
        delay = self.base_delay * (self.exponential_base**attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add random jitter: ±25% of delay
            jitter_amount = delay * 0.25
            delay = delay + random.uniform(-jitter_amount, jitter_amount)
            delay = max(0.1, delay)  # Ensure delay stays positive

        return delay
