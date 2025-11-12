"""Abstract base class for event emitters."""

from abc import ABC, abstractmethod
from typing import Any, Callable


class BaseEmitter(ABC):
    """Abstract base class for event emitters."""

    @abstractmethod
    def on(self, event_type: str, handler: Callable) -> None:
        """Subscribe to events."""
        pass

    @abstractmethod
    def off(self, event_type: str, handler: Callable) -> None:
        """Unsubscribe from events."""
        pass

    @abstractmethod
    async def emit(self, event_type: str, event_data: Any) -> None:
        """Emit an event."""
        pass
