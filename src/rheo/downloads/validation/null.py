"""Null Object implementation for file validators."""

from pathlib import Path

from ...domain.hash_validation import HashConfig, ValidationResult
from .base import BaseFileValidator


class NullFileValidator(BaseFileValidator):
    """No-op validator used when hash validation is disabled."""

    async def validate(self, file_path: Path, config: HashConfig) -> ValidationResult:
        """No-op validation that always succeeds.

        Returns:
            ValidationResult with matching hashes (always valid).
        """
        return ValidationResult(
            algorithm=config.algorithm,
            expected_hash=config.expected_hash,
            calculated_hash=config.expected_hash,  # Always matches
        )
