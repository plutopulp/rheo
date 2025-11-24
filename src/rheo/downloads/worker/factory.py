"""Worker factory types for dependency injection."""

import typing as t

import aiohttp

from ...events import BaseEmitter
from .base import BaseWorker

if t.TYPE_CHECKING:
    import loguru

# Factory signature: creates worker given client, logger, emitter
WorkerFactory = t.Callable[
    [aiohttp.ClientSession, "loguru.Logger", BaseEmitter],
    BaseWorker,
]
