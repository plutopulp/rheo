"""Base event class for all events in the system."""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class BaseEvent(BaseModel):
    """Base class for all events.

    Provides common configuration and the occurred_at timestamp.
    Events are immutable (frozen) to prevent accidental or unwanted modification.
    """

    model_config = ConfigDict(frozen=True)

    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this event occurred (UTC)",
    )
