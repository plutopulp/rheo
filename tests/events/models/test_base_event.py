"""Tests for BaseEvent class."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from rheo.events.models import BaseEvent


class TestBaseEventImmutability:
    """Test that BaseEvent is immutable (frozen)."""

    def test_cannot_modify_occurred_at(self) -> None:
        """BaseEvent fields should be immutable."""
        event = BaseEvent()

        with pytest.raises(ValidationError):
            event.occurred_at = datetime.now(timezone.utc)


class TestBaseEventTimestamp:
    """Test BaseEvent timestamp handling."""

    def test_occurred_at_defaults_to_utc(self) -> None:
        """Default occurred_at should be UTC timezone-aware."""
        event = BaseEvent()

        assert event.occurred_at.tzinfo is not None
        assert event.occurred_at.tzinfo == timezone.utc
