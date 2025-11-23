"""Base interface for file validators."""

from abc import ABC, abstractmethod
from pathlib import Path

from ...domain.hash_validation import HashConfig


class BaseFileValidator(ABC):
    """Abstract base class for file validation implementations."""

    @abstractmethod
    async def validate(self, file_path: Path, config: HashConfig) -> str:
        """Validate the downloaded file matches the expected hash.

        Returns:
            The calculated hash value (hex string).

        Raises:
            HashMismatchError: If calculated hash doesn't match expected hash.
            FileAccessError: If file cannot be accessed or read.
        """
