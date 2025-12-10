"""Event subscription handle for unsubscribing from events."""

import typing as t

from .base import BaseEmitter

if t.TYPE_CHECKING:
    from .models.download import EventHandler, EventType


class Subscription:
    """Handle returned by manager.on() for later unsubscription.

    Usage:
        sub = manager.on(DownloadEventType.COMPLETED, handler)
        # ... later ...
        sub.unsubscribe()
    """

    def __init__(
        self,
        emitter: BaseEmitter,
        event_type: "EventType",
        handler: "EventHandler",
    ) -> None:
        self._emitter = emitter
        self._event_type = event_type
        self._handler = handler
        self._active = True

    def unsubscribe(self) -> None:
        """Remove this subscription. Safe to call multiple times."""
        if not self._active:
            return
        self._emitter.off(self._event_type, self._handler)
        self._active = False

    @property
    def is_active(self) -> bool:
        """Whether this subscription is still active."""
        return self._active
