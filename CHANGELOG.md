# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0] - 2025-12-17

### ⚠️ BREAKING CHANGES

- **Event subscription API:** `manager.on()` now returns a `Subscription` handle with `unsubscribe()`. The previous `manager.off()` API has been removed. Event names are now a typed `DownloadEventType` `StrEnum`.
- **HTTP client dependency:** `DownloadManager`, `WorkerPool`, and `DownloadWorker` now depend on a `BaseHttpClient` abstraction (default `AiohttpClient`) instead of raw `aiohttp.ClientSession`. Custom clients must implement `BaseHttpClient`.

### Added

- **Selective cancellation:** `DownloadManager.cancel(download_id) -> CancelResult` with cooperative cancellation for queued downloads and task-level cancellation for in-progress downloads. `DownloadCancelledEvent` now carries `cancelled_from` to distinguish queued vs in-progress cancellations.
- **Cancellation observability:** `DownloadStats` tracks `cancelled` count for manager.stats.
- **File exists strategy policy:** `DestinationResolver` + `FileExistsPolicy` centralise file-exists handling with `default_file_exists_strategy`.
- **Typed events:** `DownloadEventType` enum for event names and `Subscription` handle returned from `manager.on()`.
- **HTTP client abstraction:** `BaseHttpClient` ABC and `AiohttpClient` implementation with SSL factory helpers; supports context-managed and manual lifecycle.
- **Benchmarks:** Added minimal `benchmarks/` suite for future extension, with HTTP fixture server, and pytest-benchmark dependency for throughput profiling.

### Changed

- **Worker wiring:** Workers create and own `DestinationResolver`, simplifying pool wiring; skips are emitted when resolver returns `None`.
- **Exception hierarchy:** New `RheoError` base with `InfrastructureError` → `HttpClientError` → `ClientNotInitialisedError`; `DownloadManagerError` now derives from `RheoError`.
- **CI:** Poetry 2.x install flags updated (`--all-groups`), reordered cache steps, and added version diagnostics.
- **Docs & examples:** Updated to show `DownloadEventType`, subscription handles, and selective cancellation usage.

### Removed

- `manager.off()` (superseded by `Subscription.unsubscribe()`).

## [0.5.0] - 2025-12-09

### ⚠️ BREAKING CHANGES

**Event System Overhaul:**

- Events renamed from `worker.*` to `download.*` namespace (e.g., `worker.started` → `download.started`)
- Tracker no longer emits events - it's now observe-only (receives events, stores state)
- Tracker tracking methods are now private (`_track_*`) - use `manager.on()` for event subscription
- `tracker.on()` removed - subscribe to events via `manager.on()` instead

**Migration:**

```python
# Before (v0.4.0) - subscribe to tracker events
tracker.on("worker.completed", handler)

# After (v0.5.0) - subscribe via manager
manager.on("download.completed", handler)

# Event names changed
# Before: worker.started, worker.progress, worker.completed, worker.failed
# After:  download.started, download.progress, download.completed, download.failed
```

### Added

- **Manager as event facade** (#74):

  - `manager.on(event, handler)` - Subscribe to download events
  - `manager.off(event, handler)` - Unsubscribe from events
  - `manager.on("*", handler)` - Wildcard subscription for all events
  - `manager.get_download_info(id)` - Query download state by ID
  - `manager.stats` property - Get aggregate download statistics

- **New download lifecycle events**:

  - `download.queued` - Emitted when download is added to queue (#69)
  - `download.skipped` - Emitted when download is skipped (file exists) (#71)
  - `download.cancelled` - Emitted when download is cancelled (#71)
  - `download.validating` - Emitted when hash validation starts (#70)
  - `download.retrying` - Emitted before retry attempt (#67)

- **New download statuses**: `SKIPPED`, `CANCELLED` with `is_terminal` helper (#71)

- **ValidationResult embedded in events** (#70):

  - `download.completed` and `download.failed` include `validation` field
  - Self-contained validation context with `is_valid`, `expected_hash`, `calculated_hash`

- **ErrorInfo model** (#67): Structured error information with `exc_type`, `message`, `traceback`

- **destination_path tracking** (#71): Stored on `DownloadInfo` for completed/skipped downloads

- **New examples** (#75):

  - `04_progress_display.py` - Real-time progress bar with speed/ETA
  - `05_event_logging.py` - Lifecycle event debugging with wildcard subscription
  - `06_batch_summary.py` - Batch download with summary report

- **CLI progress display restored**: Real-time progress bar with speed/ETA during downloads

### Changed

- **Event classes migrated to Pydantic** (#66):

  - All events inherit from `BaseEvent` with UTC `occurred_at` timestamp
  - Field validation with `ge=0`/`ge=1` constraints
  - Immutable (frozen) event instances

- **Tracker refactored to observe-only role** (#67):

  - No longer emits events - workers and queue emit directly
  - Pure state store with query methods
  - Tracking methods now private (`_track_queued`, `_track_started`, etc.)

- **Centralised event wiring** (#73):

  - Manager creates and owns all event wiring
  - WorkerPool is tracker-agnostic, receives `EventWiring` from Manager
  - New `EventSource` enum (QUEUE/WORKER) for type-safe wiring

- **Shared emitter architecture** (#74):

  - Single `EventEmitter` owned by Manager
  - Passed through to queue, pool, and all workers
  - Enables unified event subscription point

- **SpeedMetrics embedded in progress events** (#67): No separate speed event

- **ValidationResult replaces ValidationState** (#70): Simpler, self-contained model

### Removed

- `tracker.on()` / `tracker.off()` - Use `manager.on()` / `manager.off()` instead
- `tracker.track_*()` public methods - Now private (`_track_*`)
- `worker.*` event namespace - Replaced by `download.*`
- Separate `tracker_events.py` - Events consolidated in `events/models/`
- `ValidationState` model - Replaced by `ValidationResult`

## [0.4.0] - 2025-12-01

### ⚠️ BREAKING CHANGES

**File Exists Handling:**

- Default behavior changed: existing files are now **SKIP**ped instead of silently overwritten
- To restore previous behavior, set `file_exists_strategy=FileExistsStrategy.OVERWRITE`

**Context Manager Safety:**

- `PendingDownloadsError` now raised when exiting `async with` block with unhandled downloads
- Must call `wait_until_complete()` or `close()` before exiting to avoid this error

**Migration:**

```python
# Before (v0.3.0) - files silently overwritten, pending downloads silently cancelled
async with DownloadManager(download_dir=Path("./downloads")) as manager:
    await manager.add(files)
    # Exiting without wait_until_complete() would silently cancel

# After (v0.4.0) - explicit handling required
async with DownloadManager(download_dir=Path("./downloads")) as manager:
    await manager.add(files)
    await manager.wait_until_complete()  # Required to avoid PendingDownloadsError

# Or to restore overwrite behavior:
async with DownloadManager(
    download_dir=Path("./downloads"),
    file_exists_strategy=FileExistsStrategy.OVERWRITE,
) as manager:
    ...
```

### Added

- **FileExistsStrategy enum** (#63):

  - `SKIP` (default): Skip download if file exists
  - `OVERWRITE`: Replace existing file
  - `ERROR`: Raise `FileExistsError` if file exists
  - Configurable at manager level or per-file in `FileConfig`

- **PendingDownloadsError** (#62):

  - Raised when exiting context manager with unprocessed downloads
  - Prevents silent data loss from cancelled downloads
  - `queue.pending_count` property exposes pending download count

- **FileExistsError exception**: Raised when file exists and strategy is ERROR

### Fixed

- **Partial file cleanup on cancellation** (#60):
  - `CancelledError` now properly triggers cleanup of partial files
  - Previously, cancellation left corrupted partial files on disk

### Changed

- **Domain purity** (#61):

  - Removed I/O from `FileConfig.get_destination_path()`
  - Directory creation moved to `DownloadWorker` (uses async `aiofiles.os.makedirs`)
  - Examples updated to use `destination_subdir` for organisation

- **Worker checks file existence** before download using async I/O

## [0.3.0] - 2025-12-01

### ⚠️ BREAKING CHANGES

**API Simplification:**

- `cancel_all()` removed from DownloadManager - use `close(wait_for_current=True/False)` instead
- `stop()` and `request_shutdown()` removed from WorkerPool public interface

**Migration:**

```python
# Before (v0.2.0)
await manager.cancel_all(wait_for_current=True)

# After (v0.3.0)
await manager.close(wait_for_current=True)
```

### Changed

- **Simplified shutdown API:**

  - WorkerPool now exposes single `shutdown(wait_for_current)` method
  - Manager's `close(wait_for_current)` handles both graceful and immediate shutdown
  - Context manager methods (`__aenter__`/`__aexit__`) delegate to `open()`/`close()`
  - Clearer control flow with inlined cancellation logic

- **Download ID system:**
  - Each download has a unique 16-char hex ID from URL + destination
  - Tracker keyed by download_id instead of URL
  - Queue deduplication prevents duplicate downloads (same URL+destination)
  - All events include download_id for correlation

### Fixed

- Example 03 (hash validation): Use `file_config.id` instead of URL for tracker lookup
- Example 04 (progress tracking): Extract filename from `event.url` (no `filename` attribute)

## [0.2.0] - 2025-11-25

### ⚠️ BREAKING CHANGES

This release includes a major refactor of the DownloadManager API to provide a cleaner, more intuitive interface, plus significant internal improvements.

**API Changes:**

- `add_to_queue()` → `add()`
- `queue.join()` → `wait_until_complete()`
- `start_workers()` → `open()` or use context manager
- `stop_workers()` → `close()` or use context manager
- `shutdown()` → `cancel_all()`
- `request_shutdown()` removed (use `cancel_all()`)
- `max_workers` parameter → `max_concurrent` (in DownloadManager, Settings, and CLI)
- `worker=` parameter → `worker_factory=` (for dependency injection)

**Migration Example:**

```python
# Before (v0.1.0)
async with DownloadManager(max_workers=5, worker=my_worker) as manager:
    await manager.add_to_queue(files)
    await manager.queue.join()
    await manager.shutdown(wait_for_current=True)

# After (v0.2.0)
async with DownloadManager(max_concurrent=5, worker_factory=my_factory) as manager:
    await manager.add(files)
    await manager.wait_until_complete()
    await manager.cancel_all(wait_for_current=True)
```

### Added

- **New DownloadManager API methods:**

  - `add(files)` - Add files to download queue
  - `wait_until_complete(timeout=None)` - Wait for all downloads to finish
  - `cancel_all(wait_for_current=False)` - Cancel pending downloads
  - `open()` / `close()` - Manual lifecycle management
  - `is_active` property - Check if manager is running

- **WorkerPool extraction (#43):**

  - New `WorkerPool` class for managing worker lifecycle and queue processing
  - `BaseWorkerPool` ABC defining pool interface
  - `WorkerPoolFactory` Protocol for type safety
  - Comprehensive test suite with 15+ tests covering initialisation, lifecycle, shutdown, and error handling

- **Worker isolation improvements (#42):**

  - `BaseWorker` ABC for worker interface
  - `WorkerFactory` Protocol for dependency injection
  - Per-task worker instances with isolated event emitters to prevent race conditions
  - Worker factory pattern tests

- **Examples improvements:**
  - Unique filenames in all examples to prevent overwrites
  - Naming scheme: `{example_number}-{category}-{size}-{descriptor}.dat`
  - Real-time progress display with `flush=True`

### Changed

- **Package reorganisation (#41):**

  - Restructured `downloads/` package into focused subdirectories:
    - `downloads/worker/` - Download worker implementations
    - `downloads/validation/` - Hash validation logic
    - `downloads/retry/` - Retry handling and error categorisation
  - Improved separation of concerns and extensibility

- **DownloadManager improvements:**

  - Refactored to delegate worker management to `WorkerPool`
  - Simplified manager test suite
  - Workers remain active after `wait_until_complete()`, enabling multiple add/wait cycles

- **Documentation:**

  - Updated all documentation to reflect new API
  - Comprehensive usage examples in DownloadManager docstring
  - Updated README.md, docs/README.md, and docs/ARCHITECTURE.md
  - All 5 example files updated with new API

- **Testing:**
  - Reorganised manager tests by functionality (queue, pool, lifecycle, properties)
  - Created new `test_lifecycle.py` for integration scenarios
  - Removed obsolete `test_worker_isolation.py` (functionality moved to WorkerPool tests)

### Removed

- `add_to_queue()` method - replaced by `add()`
- `start_workers()` method - use `open()` or context manager
- `stop_workers()` method - use `close()` or context manager
- `shutdown()` method - replaced by `cancel_all()`
- `request_shutdown()` method - use `cancel_all()`
- `worker=` parameter - replaced by `worker_factory=`
- Backwards compatibility for `max_workers` parameter

### Internal

- Worker instances created per-task instead of shared across all tasks
- Each worker gets isolated EventEmitter to prevent race conditions
- WorkerPool handles worker lifecycle, queue processing, and graceful shutdown
- Improved test coverage with comprehensive worker pool test suite

## [0.1.0] - 2025-11-21

Initial release. See [README.md](README.md) for full feature list.
