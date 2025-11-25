"""CLI state container."""

import typing as t
from pathlib import Path

import aiohttp

from ..config.settings import Settings
from ..downloads import DownloadManager, DownloadWorker, PriorityDownloadQueue
from ..events import EventEmitter
from ..infrastructure.logging import get_logger
from ..tracking import DownloadTracker
from ..tracking.base import BaseTracker

if t.TYPE_CHECKING:
    import loguru


class ManagerOverrides(t.TypedDict, total=False):
    """Optional overrides for DownloadManager creation."""

    client: aiohttp.ClientSession | None
    worker: DownloadWorker | None
    queue: PriorityDownloadQueue | None
    timeout: float | None
    max_concurrent: int
    logger: "loguru.Logger"


class TrackerOverrides(t.TypedDict, total=False):
    """Optional overrides for DownloadTracker creation."""

    logger: "loguru.Logger"
    emitter: EventEmitter | None


class CLIState:
    """Application state container for CLI commands.

    Holds Settings and provides factories for creating application components
    with proper configuration applied.
    """

    def __init__(
        self,
        settings: Settings,
        manager_factory: t.Callable[..., DownloadManager] | None = None,
        tracker_factory: t.Callable[..., BaseTracker] | None = None,
    ):
        """Initialize CLI state.

        Args:
            settings: Application settings
            manager_factory: Optional factory override for testing
            tracker_factory: Optional factory override for testing
        """
        self.settings = settings
        self._manager_factory = manager_factory or self._default_manager_factory
        self._tracker_factory = tracker_factory or self._default_tracker_factory

    def _default_manager_factory(
        self,
        download_dir: Path | None = None,
        tracker: BaseTracker | None = None,
        **overrides: t.Unpack[ManagerOverrides],
    ) -> DownloadManager:
        """Default factory that creates DownloadManager with settings applied."""
        # Build params with settings defaults, then apply overrides
        params: dict[str, t.Any] = {
            "download_dir": download_dir or self.settings.download_dir,
            "tracker": tracker,
            "max_concurrent": self.settings.max_concurrent,
            "timeout": self.settings.timeout,
        }
        # Overrides take precedence over defaults
        params.update(overrides)
        return DownloadManager(**params)

    def _default_tracker_factory(
        self, **overrides: t.Unpack[TrackerOverrides]
    ) -> BaseTracker:
        """Default factory that creates DownloadTracker with logger."""
        # Build params with defaults, then apply overrides
        params: dict[str, t.Any] = {
            "logger": get_logger(__name__),
        }
        params.update(overrides)
        return DownloadTracker(**params)

    def create_manager(
        self,
        download_dir: Path | None = None,
        tracker: BaseTracker | None = None,
        **overrides: t.Unpack[ManagerOverrides],
    ) -> DownloadManager:
        """Create a DownloadManager using configured factory."""
        return self._manager_factory(
            download_dir=download_dir, tracker=tracker, **overrides
        )

    def create_tracker(self, **overrides: t.Unpack[TrackerOverrides]) -> BaseTracker:
        """Create a DownloadTracker using configured factory."""
        return self._tracker_factory(**overrides)
