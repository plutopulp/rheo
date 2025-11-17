"""Null Object implementation for file validators."""

from pathlib import Path

from ..domain.hash_validation import HashConfig
from .base_validator import BaseFileValidator


class NullFileValidator(BaseFileValidator):
    """No-op validator used when hash validation is disabled."""

    async def validate(self, file_path: Path, config: HashConfig) -> None:
        return None
