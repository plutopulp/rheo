"""Tests for hash validation domain models."""

import pytest
from pydantic import ValidationError

from async_download_manager.domain.hash_validation import (
    HashAlgorithm,
    HashConfig,
    ValidationState,
    ValidationStatus,
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


class TestValidationState:
    """ValidationState behaviour."""

    def test_defaults_to_not_requested(self):
        """ValidationState defaults to NOT_REQUESTED when no data provided."""
        state = ValidationState()
        assert state.status == ValidationStatus.NOT_REQUESTED
        assert state.validated_hash is None
        assert state.error is None

    def test_allows_customisation(self):
        """ValidationState stores provided values."""
        state = ValidationState(
            status=ValidationStatus.FAILED,
            validated_hash="abc",
            error="boom",
        )
        assert state.status == ValidationStatus.FAILED
        assert state.validated_hash == "abc"
        assert state.error == "boom"
