"""Base interface for file validators."""

from abc import ABC, abstractmethod
from pathlib import Path

from ..domain.hash_validation import HashConfig


class BaseFileValidator(ABC):
    """Abstract base class for file validation implementations."""

    @abstractmethod
    async def validate(self, file_path: Path, config: HashConfig) -> None:
        """Validate the downloaded file matches the expected hash."""
