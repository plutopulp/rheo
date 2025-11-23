"""Error categorisation for retry decisions using pattern matching."""

import asyncio

import aiohttp

from ...domain.retry import ErrorCategory, RetryPolicy


class ErrorCategoriser:
    """Categorises exceptions into transient/permanent categories."""

    def __init__(self, policy: RetryPolicy):
        """
        Initialise categoriser with retry policy.

        Args:
            policy: Policy defining transient/permanent status codes
        """
        self.policy = policy

    def categorise(self, exception: Exception) -> ErrorCategory:
        """
        Categorise exception as transient, permanent, or unknown.

        Uses match/case for clean pattern matching.

        Args:
            exception: The exception to categorise

        Returns:
            ErrorCategory indicating if error should be retried
        """
        match exception:
            # SSL errors - PERMANENT (certificate issues)
            # Must come before ClientOSError as ClientSSLError inherits from it
            case aiohttp.ClientSSLError():
                return ErrorCategory.PERMANENT

            # Network/connection errors - TRANSIENT (combined)
            case (
                aiohttp.ClientConnectorError()
                | aiohttp.ClientOSError()
                | aiohttp.ClientPayloadError()
                | asyncio.TimeoutError()
            ):
                return ErrorCategory.TRANSIENT

            # HTTP response errors - check status code via policy
            case aiohttp.ClientResponseError(status=status):
                if self.policy.should_retry_status(status):
                    return ErrorCategory.TRANSIENT
                return ErrorCategory.PERMANENT

            # Filesystem errors - PERMANENT (combined)
            case FileNotFoundError() | PermissionError() | OSError():
                return ErrorCategory.PERMANENT

            # Unknown errors - use policy
            case _:
                return (
                    ErrorCategory.TRANSIENT
                    if self.policy.retry_unknown_errors
                    else ErrorCategory.UNKNOWN
                )

    def is_transient(self, exception: Exception) -> bool:
        """
        Convenience method: check if error is transient.

        Args:
            exception: The exception to check

        Returns:
            True if error is transient and should be retried
        """
        return self.categorise(exception) == ErrorCategory.TRANSIENT
