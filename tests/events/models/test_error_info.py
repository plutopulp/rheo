"""Tests for ErrorInfo model."""

import pytest
from pydantic import ValidationError

from rheo.events.models import ErrorInfo


class TestErrorInfo:
    """Test ErrorInfo model."""

    def test_immutable(self) -> None:
        """ErrorInfo should be frozen."""
        info = ErrorInfo(exc_type="ValueError", message="test")
        with pytest.raises(ValidationError):
            info.message = "changed"

    def test_traceback_optional(self) -> None:
        """Traceback defaults to None."""
        info = ErrorInfo(exc_type="ValueError", message="test")
        assert info.traceback is None


class TestErrorInfoFromException:
    """Test ErrorInfo.from_exception classmethod."""

    def test_captures_exception_type(self) -> None:
        """Should capture full module.ClassName."""
        try:
            raise ValueError("test error")
        except ValueError as e:
            info = ErrorInfo.from_exception(e)

        assert info.exc_type == "builtins.ValueError"
        assert info.message == "test error"

    def test_traceback_excluded_by_default(self) -> None:
        """Traceback should not be included by default."""
        try:
            raise ValueError("test")
        except ValueError as e:
            info = ErrorInfo.from_exception(e)

        assert info.traceback is None

    def test_traceback_included_when_requested(self) -> None:
        """Traceback should be included when flag is True."""
        try:
            raise ValueError("test")
        except ValueError as e:
            info = ErrorInfo.from_exception(e, include_traceback=True)

        assert info.traceback is not None
        assert "ValueError" in info.traceback
