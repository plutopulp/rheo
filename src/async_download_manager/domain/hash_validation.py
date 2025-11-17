"""Hash validation domain models."""

import enum
import re
from typing import Final

from pydantic import BaseModel, Field, field_validator, model_validator

_HEX_PATTERN: Final = re.compile(r"^[0-9a-f]+$")


class HashAlgorithm(enum.StrEnum):
    """Supported checksum algorithms."""

    MD5 = "md5"
    SHA256 = "sha256"
    SHA512 = "sha512"

    @property
    def hex_length(self) -> int:
        """Expected hexadecimal string length for the algorithm."""
        return {
            HashAlgorithm.MD5: 32,
            HashAlgorithm.SHA256: 64,
            HashAlgorithm.SHA512: 128,
        }[self]


class ValidationStatus(enum.StrEnum):
    """Hash validation lifecycle states."""

    NOT_REQUESTED = "not_requested"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ValidationState(BaseModel):
    """State container for download validation."""

    status: ValidationStatus = Field(
        default=ValidationStatus.NOT_REQUESTED,
        description="Current validation status",
    )
    validated_hash: str | None = Field(
        default=None,
        description="Hash captured during validation if available",
    )
    error: str | None = Field(
        default=None,
        description="Validation error message when validation fails",
    )


class HashConfig(BaseModel):
    """Checksum configuration for post-download validation."""

    algorithm: HashAlgorithm = Field(description="Hash algorithm to use")
    expected_hash: str = Field(
        min_length=1,
        description="Expected checksum in hexadecimal form",
    )

    @field_validator("expected_hash")
    @classmethod
    def _normalize_hash(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("Expected hash cannot be empty")
        if not _HEX_PATTERN.fullmatch(normalized):
            raise ValueError("Expected hash must be hexadecimal")
        return normalized

    @model_validator(mode="after")
    def _validate_length(self) -> "HashConfig":
        expected_length = self.algorithm.hex_length
        if len(self.expected_hash) != expected_length:
            raise ValueError(
                f"{self.algorithm} hash must be {expected_length} characters"
            )
        return self

    @classmethod
    def from_checksum_string(cls, checksum: str) -> "HashConfig":
        """Create config from '<algorithm>:<hash>' strings."""
        if ":" not in checksum:
            raise ValueError("Checksum must be in format '<algorithm>:<hash>'")
        algorithm_part, hash_part = checksum.split(":", 1)
        algorithm_value = algorithm_part.strip().lower()
        try:
            algorithm = HashAlgorithm(algorithm_value)
        except ValueError as exc:
            msg = f"Unsupported hash algorithm '{algorithm_value}'"
            raise ValueError(msg) from exc

        return cls(algorithm=algorithm, expected_hash=hash_part)
