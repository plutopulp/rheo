"""Null object implementation of event emitter."""

import typing as t

from .base import BaseEmitter


class NullEmitter(BaseEmitter):
    """Null object implementation of emitter that does nothing."""

    def on(self, event_type: str, handler: t.Callable) -> None:
        pass

    def off(self, event_type: str, handler: t.Callable) -> None:
        pass

    async def emit(self, event_type: str, event_data: t.Any) -> None:
        pass
