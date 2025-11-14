"""Speed tracking domain models and calculation logic."""

import typing as t
from collections import deque

from pydantic import BaseModel, Field


class ChunkRecord(t.NamedTuple):
    """Record of a downloaded chunk for speed calculation."""

    timestamp: float  # Monotonic time when chunk was received
    bytes_downloaded: int  # Cumulative bytes downloaded at this point


class SpeedMetrics(BaseModel):
    """Download speed metrics snapshot.

    Contains instantaneous speed, moving average speed, ETA, and elapsed time
    for a download at a specific point in time.
    """

    current_speed_bps: float = Field(
        ge=0.0,
        description="Current instantaneous speed in bytes per second",
    )
    average_speed_bps: float = Field(
        ge=0.0,
        description="Moving average speed in bytes per second",
    )
    eta_seconds: float | None = Field(
        default=None,
        ge=0.0,
        description="Estimated time to completion in seconds (None if unknown)",
    )
    elapsed_seconds: float = Field(
        ge=0.0,
        description="Time elapsed since download started",
    )


class SpeedCalculator:
    """Calculates download speed metrics with moving average.

    Tracks download chunks over time and calculates:
    - Instantaneous speed: bytes/second since last chunk
    - Moving average speed: bytes/second over a time window
    - ETA: estimated time to completion based on average speed

    The moving average uses a sliding time window (default 5 seconds) to
    smooth out speed fluctuations and provide more accurate ETA estimates.

    Important: Uses time.monotonic() for all timestamps to ensure accuracy
    even when system clocks are adjusted (NTP sync, DST, manual changes).

    Example:
        ```python
        import time

        calc = SpeedCalculator(window_seconds=5.0)

        # Record each chunk as it arrives
        metrics = calc.record_chunk(
            chunk_bytes=1024,
            bytes_downloaded=1024,
            total_bytes=10240,
            current_time=time.monotonic(),
        )

        print(f"Speed: {metrics.average_speed_bps} bps")
        print(f"ETA: {metrics.eta_seconds} seconds")
        ```
    """

    def __init__(self, window_seconds: float = 5.0) -> None:
        """Initialize speed calculator.

        Args:
            window_seconds: Time window for moving average calculation.
                          Older chunks outside this window are discarded.
        """
        self._window_seconds = window_seconds
        self._chunks: deque[ChunkRecord] = deque()
        self._start_time: float | None = None
        self._last_time: float | None = None
        self._last_bytes: int = 0

    def record_chunk(
        self,
        chunk_bytes: int,
        bytes_downloaded: int,
        total_bytes: int | None,
        current_time: float,
    ) -> SpeedMetrics:
        """Record a downloaded chunk and calculate speed metrics.

        Args:
            chunk_bytes: Bytes in this specific chunk
            bytes_downloaded: Total bytes downloaded so far (cumulative)
            total_bytes: Total file size if known, None otherwise
            current_time: Current monotonic timestamp (from time.monotonic()).
                         Must use monotonic time to avoid issues with system
                         clock adjustments.

        Returns:
            SpeedMetrics with current speed, average speed, ETA, and elapsed time
        """
        if self._start_time is None:
            return self._initialize_first_chunk(current_time, bytes_downloaded)

        current_speed = self._calculate_current_speed(chunk_bytes, current_time)
        self._update_chunk_window(current_time, bytes_downloaded)
        average_speed = self._calculate_moving_average(bytes_downloaded, current_time)
        eta = self._calculate_eta(bytes_downloaded, total_bytes, average_speed)
        elapsed_seconds = current_time - self._start_time

        self._last_time = current_time
        self._last_bytes = bytes_downloaded

        return SpeedMetrics(
            current_speed_bps=current_speed,
            average_speed_bps=average_speed,
            eta_seconds=eta,
            elapsed_seconds=elapsed_seconds,
        )

    def _initialize_first_chunk(
        self,
        current_time: float,
        bytes_downloaded: int,
    ) -> SpeedMetrics:
        """Initialize state on first chunk.

        Args:
            current_time: Current timestamp
            bytes_downloaded: Bytes downloaded in first chunk

        Returns:
            SpeedMetrics with zero speeds (no previous data to compare)
        """
        self._start_time = current_time
        self._last_time = current_time
        self._last_bytes = bytes_downloaded

        # Add virtual start point at (start_time, 0) to track from true beginning
        # This ensures average calculation includes all bytes from start
        self._chunks.append(ChunkRecord(current_time, 0))
        self._chunks.append(ChunkRecord(current_time, bytes_downloaded))

        return SpeedMetrics(
            current_speed_bps=0.0,
            average_speed_bps=0.0,
            eta_seconds=None,
            elapsed_seconds=0.0,
        )

    def _calculate_current_speed(
        self,
        chunk_bytes: int,
        current_time: float,
    ) -> float:
        """Calculate instantaneous speed since last chunk.

        Args:
            chunk_bytes: Bytes in current chunk
            current_time: Current timestamp

        Returns:
            Speed in bytes per second
        """
        assert self._last_time is not None, "last_time must be set after first chunk"

        time_delta = current_time - self._last_time
        return chunk_bytes / time_delta if time_delta > 0 else 0.0

    def _update_chunk_window(
        self,
        current_time: float,
        bytes_downloaded: int,
    ) -> None:
        """Add current chunk and remove old chunks outside window.

        Args:
            current_time: Current timestamp
            bytes_downloaded: Cumulative bytes downloaded
        """
        self._chunks.append(ChunkRecord(current_time, bytes_downloaded))

        cutoff_time = current_time - self._window_seconds
        while self._chunks and self._chunks[0].timestamp < cutoff_time:
            self._chunks.popleft()

    def _calculate_moving_average(
        self,
        bytes_downloaded: int,
        current_time: float,
    ) -> float:
        """Calculate moving average speed over the time window.

        Always calculates from the first to last chunk in the window.
        The window naturally adapts:
        - Young downloads: All chunks retained, calculates from start
        - Old downloads: Old chunks pruned, calculates recent speed

        Args:
            bytes_downloaded: Cumulative bytes downloaded
            current_time: Current timestamp

        Returns:
            Average speed in bytes per second
        """
        if len(self._chunks) < 2:
            # Edge case: All historical chunks pruned
            # Not enough data points - need at least two for speed calculation
            return 0.0

        # Calculate speed from oldest to newest chunk in window
        window_start = self._chunks[0]
        window_duration = current_time - window_start.timestamp
        window_bytes = bytes_downloaded - window_start.bytes_downloaded

        return window_bytes / window_duration if window_duration > 0 else 0.0

    def _calculate_eta(
        self,
        bytes_downloaded: int,
        total_bytes: int | None,
        average_speed: float,
    ) -> float | None:
        """Calculate estimated time to completion.

        Args:
            bytes_downloaded: Bytes downloaded so far
            total_bytes: Total file size if known
            average_speed: Average download speed in bytes/second

        Returns:
            Estimated seconds remaining, or None if can't calculate
        """
        # Can't calculate ETA without knowing total size
        if total_bytes is None:
            return None

        # Already complete
        if bytes_downloaded >= total_bytes:
            return 0.0

        # Can't calculate with zero speed
        if average_speed <= 0:
            return None

        remaining_bytes = total_bytes - bytes_downloaded
        return remaining_bytes / average_speed
