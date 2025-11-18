"""Tests for file hash validator."""

from pathlib import Path

import pytest

from rheo.domain.exceptions import (
    FileValidationError,
    HashMismatchError,
)
from rheo.domain.hash_validation import HashAlgorithm, HashConfig
from rheo.downloads.null_validator import NullFileValidator
from rheo.downloads.validation import FileValidator


def _write_file(path: Path, content: bytes) -> None:
    path.write_bytes(content)


class TestFileValidatorSuccessCases:
    """Happy-path validation behaviour."""

    @pytest.mark.asyncio
    async def test_file_validator_success(self, calculate_hash, tmp_path: Path) -> None:
        """Validator passes when hash matches and returns calculated hash."""
        file_path = tmp_path / "file.bin"
        content = b"hello world"
        _write_file(file_path, content)

        expected_hash = calculate_hash(content, HashAlgorithm.SHA256)
        config = HashConfig(
            algorithm=HashAlgorithm.SHA256,
            expected_hash=expected_hash,
        )
        validator = FileValidator()

        result = await validator.validate(file_path, config)
        assert result == expected_hash


class TestFileValidatorFailureCases:
    """Error handling scenarios for FileValidator."""

    @pytest.mark.asyncio
    async def test_file_validator_hash_mismatch(
        self, calculate_hash, tmp_path: Path
    ) -> None:
        """Validator raises on mismatch with actual hash available."""
        file_path = tmp_path / "file.bin"
        _write_file(file_path, b"hello world")

        config = HashConfig(
            algorithm=HashAlgorithm.MD5,
            expected_hash="b" * HashAlgorithm.MD5.hex_length,
        )
        validator = FileValidator()

        with pytest.raises(HashMismatchError) as exc:
            await validator.validate(file_path, config)

        assert exc.value.expected_hash == config.expected_hash
        assert exc.value.actual_hash is not None
        assert exc.value.file_path == file_path

    @pytest.mark.asyncio
    async def test_file_validator_missing_file(self, tmp_path: Path) -> None:
        """Missing file raises FileValidationError."""
        file_path = tmp_path / "missing.bin"
        validator = FileValidator()
        config = HashConfig(
            algorithm=HashAlgorithm.SHA256,
            expected_hash="a" * HashAlgorithm.SHA256.hex_length,
        )

        with pytest.raises(FileValidationError):
            await validator.validate(file_path, config)

    @pytest.mark.asyncio
    async def test_file_validator_directory_path(self, tmp_path: Path) -> None:
        """Directory path raises FileValidationError."""
        directory = tmp_path / "dir"
        directory.mkdir()
        validator = FileValidator()
        config = HashConfig(
            algorithm=HashAlgorithm.SHA512,
            expected_hash="c" * HashAlgorithm.SHA512.hex_length,
        )

        with pytest.raises(FileValidationError):
            await validator.validate(directory, config)


class TestNullFileValidator:
    """Behaviour of the null validator."""

    @pytest.mark.asyncio
    async def test_null_file_validator_noop(self, tmp_path: Path) -> None:
        """NullFileValidator ignores validation entirely and returns expected hash."""
        file_path = tmp_path / "file.bin"
        _write_file(file_path, b"noop")

        validator = NullFileValidator()
        expected = "a" * HashAlgorithm.MD5.hex_length
        config = HashConfig(
            algorithm=HashAlgorithm.MD5,
            expected_hash=expected,
        )

        result = await validator.validate(file_path, config)
        assert result == expected
