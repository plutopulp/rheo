# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
  - Comprehensive test suite with 15+ tests covering initialization, lifecycle, shutdown, and error handling

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

- **Package reorganization (#41):**

  - Restructured `downloads/` package into focused subdirectories:
    - `downloads/worker/` - Download worker implementations
    - `downloads/validation/` - Hash validation logic
    - `downloads/retry/` - Retry handling and error categorization
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
  - Reorganized manager tests by functionality (queue, pool, lifecycle, properties)
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
