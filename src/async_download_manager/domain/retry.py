"""Domain models for retry configuration and policies."""

import random
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ErrorCategory(Enum):
    """Classification of download errors for retry decisions."""

    TRANSIENT = "transient"  # Temporary, should retry
    PERMANENT = "permanent"  # Won't fix itself, don't retry
    UNKNOWN = "unknown"  # Conservative: don't retry


class RetryPolicy(BaseModel):
    """Policy for determining if errors should be retried.

    This is a configuration object that defines which errors are transient.
    Users can customise status codes and error types.
    """

    model_config = ConfigDict(frozen=True)

    # HTTP status codes that indicate transient errors
    transient_status_codes: frozenset[int] = Field(
        default=frozenset(
            {
                408,  # Request Timeout
                429,  # Too Many Requests
                500,  # Internal Server Error
                502,  # Bad Gateway
                503,  # Service Unavailable
                504,  # Gateway Timeout
            }
        ),
        description="HTTP status codes considered transient (will retry)",
    )

    # HTTP status codes that indicate permanent errors
    permanent_status_codes: frozenset[int] = Field(
        default=frozenset(
            {
                400,  # Bad Request
                401,  # Unauthorised
                403,  # Forbidden
                404,  # Not Found
                405,  # Method Not Allowed
                410,  # Gone
            }
        ),
        description="HTTP status codes considered permanent (won't retry)",
    )

    # Whether to retry on unknown errors (conservative default: False)
    retry_unknown_errors: bool = Field(
        default=False,
        description="Whether to retry errors not in transient/permanent lists",
    )

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


class RetryConfig(BaseModel):
    """Configuration for retry behaviour with exponential backoff."""

    model_config = ConfigDict(frozen=True)

    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retry attempts for transient errors",
    )
    base_delay: float = Field(
        default=1.0,
        gt=0,
        description="Initial delay in seconds before first retry",
    )
    max_delay: float = Field(
        default=60.0,
        gt=0,
        description="Maximum delay cap in seconds",
    )
    exponential_base: float = Field(
        default=2.0,
        gt=1.0,
        description="Delay multiplier for exponential backoff",
    )
    jitter: bool = Field(
        default=True,
        description="Add randomness to delays to avoid thundering herd",
    )
    policy: RetryPolicy = Field(
        default_factory=RetryPolicy,
        description="Policy defining which errors are retryable",
    )

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
