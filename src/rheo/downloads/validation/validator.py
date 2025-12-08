"""Concrete file validator implementation."""

import asyncio
import hashlib
import typing as t
from pathlib import Path

import aiofiles
import aiofiles.os

from ...domain.exceptions import FileAccessError
from ...domain.hash_validation import HashConfig, ValidationResult
from ...infrastructure.logging import get_logger
from .base import BaseFileValidator

if t.TYPE_CHECKING:
    from loguru import Logger


class FileValidator(BaseFileValidator):
    """Validates downloaded files using hashing algorithms."""

    def __init__(
        self,
        *,
        chunk_size: int = 8192,
        logger: t.Optional["Logger"] = None,
    ) -> None:
        self._chunk_size = chunk_size
        self._logger = logger or get_logger(__name__)

    async def validate(self, file_path: Path, config: HashConfig) -> ValidationResult:
        """Validate file using configured hash.

        Returns:
            ValidationResult with expected/calculated hashes. Check is_valid
            property to determine if validation passed.

        Raises:
            FileAccessError: If file cannot be accessed or read.
        """
        if not await aiofiles.os.path.exists(file_path):
            raise FileAccessError(f"File not found for validation: {file_path}")
        if not await aiofiles.os.path.isfile(file_path):
            raise FileAccessError(f"Path is not a file: {file_path}")

        try:
            calculated_hash = await self._calculate_hash(file_path, config)
        except OSError as exc:
            raise FileAccessError(
                f"Unable to read file for validation: {file_path}"
            ) from exc

        return ValidationResult(
            algorithm=config.algorithm,
            expected_hash=config.expected_hash,
            calculated_hash=calculated_hash,
        )

    async def _calculate_hash(self, file_path: Path, config: HashConfig) -> str:
        return await asyncio.to_thread(
            self._calculate_hash_sync,
            file_path,
            config,
        )

    def _calculate_hash_sync(self, file_path: Path, config: HashConfig) -> str:
        hasher = hashlib.new(str(config.algorithm))
        with file_path.open("rb") as handle:
            while chunk := handle.read(self._chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()


__all__ = [
    "FileValidator",
]
