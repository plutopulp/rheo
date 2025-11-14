"""Abstract base class for event emitters."""

import typing as t
from abc import ABC, abstractmethod


class BaseEmitter(ABC):
    """Abstract base class for event emitters."""

    @abstractmethod
    def on(self, event_type: str, handler: t.Callable) -> None:
        """Subscribe to events."""
        pass

    @abstractmethod
    def off(self, event_type: str, handler: t.Callable) -> None:
        """Unsubscribe from events."""
        pass

    @abstractmethod
    async def emit(self, event_type: str, event_data: t.Any) -> None:
        """Emit an event."""
        pass
