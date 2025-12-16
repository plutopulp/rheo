"""Cancellation-related domain models."""

from enum import StrEnum


class CancelResult(StrEnum):
    """Result of a cancel operation.

    Provides explicit semantics for what happened when cancel() was called,
    rather than an ambiguous boolean.
    """

    CANCELLED = "cancelled"
    NOT_FOUND = "not_found"
    ALREADY_TERMINAL = "already_terminal"


class CancelledFrom(StrEnum):
    """State the download was in when cancelled.

    Used in DownloadCancelledEvent to distinguish between cancelling a queued
    download vs an in-progress download.
    """

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
