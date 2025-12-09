"""Event emission helper for publish-subscribe pattern."""

import asyncio
import typing as t

from ..infrastructure.logging import get_logger
from .base import BaseEmitter

if t.TYPE_CHECKING:
    import loguru

# Any used for event data flexibility - events can carry any payload type
EventHandler = t.Callable[[t.Any], t.Union[None, t.Awaitable[None]]]


class EventEmitter(BaseEmitter):
    """Helper class for event emission and subscription.

    Supports both sync and async handlers, handles exceptions gracefully,
    and provides subscribe/unsubscribe functionality.

    Usage:
        emitter = EventEmitter()

        def handler(event):
            print(f"Received: {event}")

        emitter.on("my.event", handler)
        await emitter.emit("my.event", {"data": "value"})
    """

    def __init__(self, logger: "loguru.Logger" = get_logger(__name__)):
        """Initialize event emitter.

        Args:
            logger: Logger instance for recording event errors.
                   Defaults to module-specific logger if not provided.
        """
        self._handlers: dict[str, list[EventHandler]] = {}
        self._logger = logger

    def on(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe to events.

        Args:
            event_type: Type of event to listen for
            handler: Callback function (can be sync or async)

        Example:
            def my_handler(event):
                print(f"Event received: {event}")

            emitter.on("user.created", my_handler)
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def off(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe from events.

        Args:
            event_type: Type of event to stop listening for
            handler: The handler function to remove
        """
        try:
            self._handlers[event_type].remove(handler)
        except (KeyError, ValueError):
            self._logger.warning(f"Handler {handler} not found for event {event_type}")

    async def emit(self, event_type: str, event_data: t.Any) -> None:
        """Emit event to all subscribers.

        Handles both sync and async handlers. Exceptions in handlers are
        logged but don't prevent other handlers from executing.
        Wildcard "*" handlers receive all events.

        Args:
            event_type: Type of event being emitted
            event_data: Event data to pass to handlers

        Example:
            await emitter.emit("user.created", {"user_id": 123})
        """
        # Get handlers for this specific event type and wildcard handlers
        handlers = self._handlers.get(event_type, []).copy()
        handlers.extend(self._handlers.get("*", []))

        # Execute sync handlers, collect async tasks
        tasks = self._execute_sync_handlers(handlers, event_type, event_data)

        # Await async handlers
        if tasks:
            await self._execute_async_handlers(tasks, event_type)

    def _execute_sync_handlers(
        self, handlers: list[EventHandler], event_type: str, event_data: t.Any
    ) -> list[t.Coroutine]:
        """Execute synchronous handlers, return async tasks.

        Args:
            handlers: List of handlers to execute
            event_type: Event type being emitted
            event_data: Event data to pass to handlers

        Returns:
            List of coroutines from async handlers
        """
        tasks = []
        for handler in handlers:
            try:
                result = handler(event_data)
                if asyncio.iscoroutine(result):
                    tasks.append(result)
            except Exception:
                self._logger.exception(f"Error in event handler for {event_type}")
        return tasks

    async def _execute_async_handlers(
        self, tasks: list[t.Coroutine], event_type: str
    ) -> None:
        """Execute async handlers with exception logging.

        Args:
            tasks: List of coroutines to execute
            event_type: Event type being emitted
        """
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                self._logger.opt(
                    exception=(type(result), result, result.__traceback__)
                ).error(f"Error in async handler for {event_type}")
