"""Base interface for file validators."""

from abc import ABC, abstractmethod
from pathlib import Path

from ...domain.hash_validation import HashConfig, ValidationResult


class BaseFileValidator(ABC):
    """Abstract base class for file validation implementations."""

    @abstractmethod
    async def validate(self, file_path: Path, config: HashConfig) -> ValidationResult:
        """Validate the downloaded file matches the expected hash.

        Returns:
            ValidationResult with expected/calculated hashes. Check is_valid
            property to determine if validation passed.

        Raises:
            FileAccessError: If file cannot be accessed or read.
        """
