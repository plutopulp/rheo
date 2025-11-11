"""Null object implementation of event emitter."""

from typing import Any, Callable

from .base import BaseEmitter


class NullEmitter(BaseEmitter):
    """Null object implementation of emitter that does nothing."""

    def on(self, event_type: str, handler: Callable) -> None:
        pass

    def off(self, event_type: str, handler: Callable) -> None:
        pass

    async def emit(self, event_type: str, event_data: Any) -> None:
        pass
