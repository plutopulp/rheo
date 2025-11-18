"""Async Download Manager - Production-ready concurrent file downloader."""

from .domain import (
    DownloadInfo,
    DownloadStats,
    DownloadStatus,
    FileConfig,
)
from .downloads import (
    DownloadManager,
    DownloadWorker,
    PriorityDownloadQueue,
)
from .events import (
    EventEmitter,
)
from .tracking import (
    DownloadTracker,
    NullTracker,
)

__all__ = [
    # Domain Models
    "FileConfig",
    "DownloadInfo",
    "DownloadStatus",
    "DownloadStats",
    # Download Operations
    "DownloadManager",
    "DownloadWorker",
    "PriorityDownloadQueue",
    # Tracking
    "DownloadTracker",
    "NullTracker",
    # Events
    "EventEmitter",
]

__version__ = "0.1.0"
