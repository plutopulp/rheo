"""Tests for speed tracking domain models."""

import pytest

from async_download_manager.domain.speed import SpeedCalculator


class TestSpeedCalculator:
    """Tests for SpeedCalculator with mocked time."""

    def test_first_chunk_returns_zero_speed(self) -> None:
        """Test that first chunk returns zero speeds (no previous data)."""
        calc = SpeedCalculator(window_seconds=5.0)
        start_time = 100.0

        metrics = calc.record_chunk(
            chunk_bytes=1024,
            bytes_downloaded=1024,
            total_bytes=10240,
            current_time=start_time,
        )

        assert metrics.current_speed_bps == 0.0
        assert metrics.average_speed_bps == 0.0
        assert metrics.elapsed_seconds == 0.0
        # ETA can't be calculated with zero speed
        assert metrics.eta_seconds is None

    def test_second_chunk_calculates_current_speed(self) -> None:
        """Test that second chunk calculates speed correctly."""
        calc = SpeedCalculator(window_seconds=5.0)
        start_time = 100.0

        # First chunk
        calc.record_chunk(
            chunk_bytes=1024,
            bytes_downloaded=1024,
            total_bytes=10240,
            current_time=start_time,
        )

        # Second chunk - 1 second later
        metrics = calc.record_chunk(
            chunk_bytes=1024,
            bytes_downloaded=2048,
            total_bytes=10240,
            current_time=start_time + 1.0,
        )

        # Current speed: 1024 bytes / 1.0 second = 1024 bps
        assert metrics.current_speed_bps == 1024.0
        # Average speed: 2048 bytes / 1.0 second = 2048 bps
        assert metrics.average_speed_bps == 2048.0
        assert metrics.elapsed_seconds == 1.0
        # ETA: (10240 - 2048) / 2048 = 4.0 seconds
        assert metrics.eta_seconds == pytest.approx(4.0)

    def test_moving_average_calculation(self) -> None:
        """Test moving average over time window."""
        calc = SpeedCalculator(window_seconds=2.0)  # 2 second window
        start_time = 100.0

        # Chunk 1 at t=0
        calc.record_chunk(
            chunk_bytes=1000,
            bytes_downloaded=1000,
            total_bytes=None,
            current_time=start_time,
        )

        # Chunk 2 at t=1 (1000 bytes/sec)
        calc.record_chunk(
            chunk_bytes=1000,
            bytes_downloaded=2000,
            total_bytes=None,
            current_time=start_time + 1.0,
        )

        # Chunk 3 at t=2 (1000 bytes/sec)
        calc.record_chunk(
            chunk_bytes=1000,
            bytes_downloaded=3000,
            total_bytes=None,
            current_time=start_time + 2.0,
        )

        # Chunk 4 at t=3.5 (should drop chunk 1, only use chunks 2-4)
        metrics = calc.record_chunk(
            chunk_bytes=1500,
            bytes_downloaded=4500,
            total_bytes=None,
            current_time=start_time + 3.5,
        )

        # Current speed: 1500 bytes / 1.5 seconds = 1000 bps
        assert metrics.current_speed_bps == 1000.0

        # Average speed over last 2 seconds (from t=1.5 to t=3.5):
        # Bytes in window: chunks 2, 3, 4 within window = 2500 bytes
        # Time window: 2.5 seconds (from t=1.0 to t=3.5)
        # Average: 2500 / 2.5 = 1000 bps
        assert metrics.average_speed_bps == pytest.approx(1000.0, rel=0.01)

    def test_eta_with_unknown_total_bytes(self) -> None:
        """Test that ETA is None when total_bytes is unknown."""
        calc = SpeedCalculator(window_seconds=5.0)
        start_time = 100.0

        # First chunk
        calc.record_chunk(
            chunk_bytes=1024,
            bytes_downloaded=1024,
            total_bytes=None,  # Unknown size
            current_time=start_time,
        )

        # Second chunk
        metrics = calc.record_chunk(
            chunk_bytes=1024,
            bytes_downloaded=2048,
            total_bytes=None,  # Still unknown
            current_time=start_time + 1.0,
        )

        assert metrics.current_speed_bps == 1024.0
        assert metrics.average_speed_bps == 2048.0
        assert metrics.eta_seconds is None  # Can't calculate without total

    def test_eta_when_already_complete(self) -> None:
        """Test that ETA is 0 when download is already complete."""
        calc = SpeedCalculator(window_seconds=5.0)
        start_time = 100.0

        # First chunk
        calc.record_chunk(
            chunk_bytes=1024,
            bytes_downloaded=1024,
            total_bytes=2048,
            current_time=start_time,
        )

        # Second chunk - download complete
        metrics = calc.record_chunk(
            chunk_bytes=1024,
            bytes_downloaded=2048,
            total_bytes=2048,  # All bytes downloaded
            current_time=start_time + 1.0,
        )

        assert metrics.eta_seconds == 0.0

    def test_eta_with_zero_average_speed(self) -> None:
        """Test that ETA is None when average speed is zero."""
        calc = SpeedCalculator(window_seconds=5.0)
        start_time = 100.0

        # Only first chunk (average speed is zero)
        metrics = calc.record_chunk(
            chunk_bytes=1024,
            bytes_downloaded=1024,
            total_bytes=10240,
            current_time=start_time,
        )

        assert metrics.average_speed_bps == 0.0
        assert metrics.eta_seconds is None

    def test_multiple_chunks_realistic_scenario(self) -> None:
        """Test realistic download scenario with variable speeds."""
        calc = SpeedCalculator(window_seconds=5.0)
        start_time = 100.0

        # Simulate download with varying chunk sizes and timing
        chunks = [
            (1024, 1024, 0.0),  # t=0
            (2048, 3072, 0.5),  # t=0.5, fast chunk
            (1024, 4096, 1.0),  # t=1.0
            (512, 4608, 1.2),  # t=1.2, slow chunk
            (2048, 6656, 1.8),  # t=1.8, fast again
        ]

        last_metrics = None
        for chunk_bytes, total_downloaded, time_offset in chunks:
            last_metrics = calc.record_chunk(
                chunk_bytes=chunk_bytes,
                bytes_downloaded=total_downloaded,
                total_bytes=10240,
                current_time=start_time + time_offset,
            )

        assert last_metrics is not None
        assert last_metrics.current_speed_bps > 0
        assert last_metrics.average_speed_bps > 0
        assert last_metrics.eta_seconds is not None
        assert last_metrics.elapsed_seconds == pytest.approx(1.8)

    def test_window_cleanup_removes_old_chunks(self) -> None:
        """Test that chunks outside the time window are removed."""
        calc = SpeedCalculator(window_seconds=2.0)
        start_time = 100.0

        # Add chunks that will be outside window
        calc.record_chunk(1000, 1000, None, start_time)
        calc.record_chunk(1000, 2000, None, start_time + 1.0)
        calc.record_chunk(1000, 3000, None, start_time + 2.0)

        # Add chunk at t=5 (only chunks at t=3+ should be in window)
        calc.record_chunk(1000, 4000, None, start_time + 5.0)

        # Verify internal state has cleaned up old chunks
        # Average should only consider recent chunks within 2 second window
        metrics = calc.record_chunk(1000, 5000, None, start_time + 6.0)

        # Only chunks from t=4+ are in window, so average is based on recent data
        assert metrics.average_speed_bps == pytest.approx(1000.0, rel=0.1)

    def test_custom_window_size(self) -> None:
        """Test that custom window size is respected."""
        calc = SpeedCalculator(window_seconds=10.0)  # Large window
        start_time = 100.0

        # Add chunks spread over 8 seconds (all within 10s window)
        for i in range(8):
            calc.record_chunk(
                chunk_bytes=1000,
                bytes_downloaded=(i + 1) * 1000,
                total_bytes=None,
                current_time=start_time + float(i),
            )

        metrics = calc.record_chunk(
            chunk_bytes=1000,
            bytes_downloaded=9000,
            total_bytes=None,
            current_time=start_time + 8.0,
        )

        # All 9 chunks should be in the window
        # Average: 9000 bytes / 8.0 seconds = 1125 bps
        assert metrics.average_speed_bps == pytest.approx(1125.0, rel=0.01)

    def test_chunk_window_size_over_multiple_spans(self) -> None:
        """Test that chunk count stays reasonable over multiple window spans."""
        calc = SpeedCalculator(window_seconds=2.0)  # Small window for testing
        start_time = 100.0

        # Simulate download over 10 seconds (5 window spans)
        # Add chunk every 0.5 seconds = 20 chunks total
        for i in range(20):
            time_offset = i * 0.5
            calc.record_chunk(
                chunk_bytes=1000,
                bytes_downloaded=(i + 1) * 1000,
                total_bytes=None,
                current_time=start_time + time_offset,
            )

            # Check internal state
            chunk_count = len(calc._chunks)

            if time_offset < 2.0:
                # Young download: All chunks retained (+ virtual start)
                # At t=0: 2 chunks (virtual + first)
                # At t=0.5: 3 chunks
                # At t=1.0: 4 chunks
                # At t=1.5: 5 chunks
                expected_max = i + 3  # Virtual start + all chunks so far + 1
                assert chunk_count <= expected_max
            else:
                # Old download: Only chunks within 2s window
                # With chunks every 0.5s, max 5 chunks in 2s window
                # (4 intervals * 0.5s = 2s, plus current = 5 chunks max)
                assert chunk_count <= 6, (
                    f"Too many chunks at t={time_offset}: "
                    f"{chunk_count} (expected <= 6)"
                )

        # Verify old chunks were actually pruned
        final_count = len(calc._chunks)
        assert final_count <= 6, (
            f"Final chunk count too high: {final_count} "
            f"(window should keep ~5 chunks)"
        )
