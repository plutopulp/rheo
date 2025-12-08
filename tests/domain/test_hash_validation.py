"""Tests for hash validation domain models."""

import pytest
from pydantic import ValidationError

from rheo.domain.hash_validation import (
    HashAlgorithm,
    HashConfig,
    ValidationResult,
)


class TestHashAlgorithm:
    """Hash algorithm metadata helpers."""

    def test_hex_length_map(self):
        """Each algorithm exposes expected hex length."""
        assert HashAlgorithm.MD5.hex_length == 32
        assert HashAlgorithm.SHA256.hex_length == 64
        assert HashAlgorithm.SHA512.hex_length == 128


class TestHashConfigValidation:
    """Validation behaviour for HashConfig."""

    def test_valid_sha256(self):
        """Valid SHA256 checksum passes validation."""
        config = HashConfig(
            algorithm=HashAlgorithm.SHA256,
            expected_hash="a" * HashAlgorithm.SHA256.hex_length,
        )
        assert config.expected_hash == "a" * 64

    def test_rejects_non_hex_characters(self):
        """Reject checksums with characters outside hexadecimal range."""
        with pytest.raises(ValidationError):
            HashConfig(
                algorithm=HashAlgorithm.MD5,
                expected_hash="g" * HashAlgorithm.MD5.hex_length,
            )

    def test_rejects_wrong_length(self):
        """Reject checksums that do not match algorithm length."""
        with pytest.raises(ValidationError):
            HashConfig(
                algorithm=HashAlgorithm.SHA512,
                expected_hash="a" * (HashAlgorithm.SHA512.hex_length - 1),
            )

    def test_strips_whitespace_and_lowercases(self):
        """Whitespace trimmed and uppercase converted."""
        raw = ("A" * HashAlgorithm.MD5.hex_length).upper()
        config = HashConfig(
            algorithm=HashAlgorithm.MD5,
            expected_hash=f"  {raw}  ",
        )
        assert config.expected_hash == raw.lower()


class TestHashConfigHelpers:
    """Helper factories for checksum parsing."""

    def test_from_checksum_string_parses_algorithm(self):
        """Parses '<algo>:<value>' format."""
        checksum = "sha256:" + "b" * HashAlgorithm.SHA256.hex_length
        config = HashConfig.from_checksum_string(checksum)
        assert config.algorithm == HashAlgorithm.SHA256
        assert config.expected_hash == "b" * HashAlgorithm.SHA256.hex_length

    def test_from_checksum_string_invalid_format(self):
        """Raises simple ValueError for malformed strings (no colon)."""
        with pytest.raises(ValueError):
            HashConfig.from_checksum_string("notvalid")

    def test_from_checksum_string_invalid_algorithm(self):
        """Raises ValueError for unsupported hash algorithm."""
        with pytest.raises(ValueError, match="Unsupported hash algorithm"):
            HashConfig.from_checksum_string("invalid:abc123")


class TestValidationResult:
    """ValidationResult behaviour."""

    def test_is_valid_when_hashes_match(self):
        """is_valid returns True when expected equals calculated."""
        result = ValidationResult(
            algorithm=HashAlgorithm.SHA256,
            expected_hash="a" * 64,
            calculated_hash="a" * 64,
            duration_ms=10.5,
        )
        assert result.is_valid is True

    def test_is_valid_when_hashes_differ(self):
        """is_valid returns False when expected differs from calculated."""
        result = ValidationResult(
            algorithm=HashAlgorithm.SHA256,
            expected_hash="a" * 64,
            calculated_hash="b" * 64,
            duration_ms=10.5,
        )
        assert result.is_valid is False

    def test_frozen_model(self):
        """ValidationResult is immutable."""
        result = ValidationResult(
            algorithm=HashAlgorithm.SHA256,
            expected_hash="a" * 64,
            calculated_hash="a" * 64,
        )
        with pytest.raises(Exception):
            result.expected_hash = "b" * 64
