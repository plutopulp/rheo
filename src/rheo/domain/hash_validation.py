"""Hash validation domain models."""

import enum
import re
from typing import Final

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

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


class ValidationResult(BaseModel):
    """Hash validation result (success or failure).

    On success: expected_hash == calculated_hash (is_valid=True)
    On failure: they differ (is_valid=False), giving full mismatch context
    """

    model_config = ConfigDict(frozen=True)

    algorithm: HashAlgorithm = Field(description="Hash algorithm used")
    expected_hash: str = Field(
        min_length=1, description="Expected checksum in hexadecimal form"
    )
    calculated_hash: str = Field(
        min_length=1, description="Calculated checksum in hexadecimal form"
    )
    duration_ms: float = Field(
        default=0.0,
        ge=0,
        description="Validation duration in milliseconds",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_valid(self) -> bool:
        """True if expected and calculated hashes match."""
        return self.expected_hash == self.calculated_hash


class HashConfig(BaseModel):
    """Checksum configuration for post-download validation."""

    algorithm: HashAlgorithm = Field(description="Hash algorithm to use")
    expected_hash: str = Field(
        min_length=1,
        description="Expected checksum in hexadecimal form",
    )

    @field_validator("expected_hash")
    @classmethod
    def _normalise_hash(cls, value: str) -> str:
        normalised = value.strip().lower()
        if not normalised:
            raise ValueError("Expected hash cannot be empty")
        if not _HEX_PATTERN.fullmatch(normalised):
            raise ValueError("Expected hash must be hexadecimal")
        return normalised

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
