# Architecture

High-level overview of how the system works and why it's designed this way.

## What It Does

The async download manager is a library for concurrent HTTP downloads with progress tracking and event notifications. It handles multiple downloads simultaneously, manages retries, tracks state, and lets you hook into the lifecycle via events.

Think of it as a robust download queue with a worker pool, where you can monitor what's happening and respond to events.

## Core Concepts

### 1. Queue-Based Architecture

Downloads don't start immediately. They go into a priority queue:

```text
User adds download → Priority Queue → Workers pick from queue → Download → Track state
```

This means:

- Downloads happen in priority order
- Worker pool prevents overwhelming the system
- Easy to pause/resume/cancel
- Natural backpressure handling

### 2. Event-Driven State

Instead of polling for status, everything is event-based:

```text
Worker emits events → Tracker observes → State updates → Your code responds (optional)
```

Benefits:

- Decoupled components
- Easy to add new observers
- No tight coupling between worker and tracker
- Testable in isolation

### 3. Layered Design

The system is organised into bounded contexts:

```text
Domain        → Core models and business logic
Downloads     → Queue, Manager, Worker
Events        → Event system and data
Tracking      → State tracking and aggregation
Infrastructure→ Logging, HTTP client
CLI           → Command-line interface and configuration
```

Each layer has clear responsibilities and minimal coupling.

## Component Overview

### Domain Layer

**What it does**: Defines the core models and exceptions.

Key pieces:

- `FileConfig`: Download configuration (URL, destination, priority, hash validation, file exists strategy, etc.). Includes path traversal protection on `destination_subdir`
- `FileExistsStrategy`: Enum for handling existing files (SKIP, OVERWRITE, ERROR)
- `DownloadInfo`: Current state of a download (includes final average speed and validation state)
- `DownloadStatus`: Enum for states (queued, pending, in_progress, completed, failed, skipped, cancelled)
- `DownloadStats`: Aggregated statistics
- `HashConfig`: Hash validation configuration (algorithm and expected hash)
- `HashAlgorithm`: Supported hash algorithms (MD5, SHA256, SHA512)
- `ValidationResult`: Hash validation result with `is_valid` property (algorithm, expected/calculated hash, duration)
- `SpeedMetrics`: Real-time speed and ETA snapshot
- `SpeedCalculator`: Calculates instantaneous and moving average speeds with ETA estimation
- Custom exceptions: `ValidationError`, `HashMismatchError`, `FileAccessError`, `FileExistsError`, `ManagerNotInitializedError`, `PendingDownloadsError`, etc.

**Why**: Keeps business logic separate from infrastructure. These models can be used anywhere without importing heavy dependencies.

### Downloads Layer

**What it does**: Manages the download lifecycle.

**DownloadManager**:

- Entry point for the library
- Orchestrates high-level download operations
- Initialises HTTP client
- Wires queue events to tracker (owns this wiring)
- Delegates worker lifecycle to `WorkerPool`
- Context manager for resource cleanup

**WorkerPool**:

- Encapsulates worker lifecycle management
- Creates one isolated worker per task
- Wires worker event emitters to tracker handlers
- Processes queue with timeout-based polling for shutdown responsiveness
- Handles graceful vs immediate shutdown semantics
- Re-queues unstarted downloads during shutdown
- Maintains task lifecycle and cleanup

**DownloadWorker**:

- Does the actual HTTP download
- Checks file exists strategy before downloading (SKIP, OVERWRITE, ERROR)
- Uses async file I/O (`aiofiles`) to prevent blocking the event loop
- Chunks data for progress reporting
- Emits events for lifecycle stages (including real-time speed and validation updates)
- Tracks download speed and ETA using injected `SpeedCalculator`
- Validates downloaded files using injected `BaseFileValidator`
- Handles errors with optional retry logic
- Uses injected `RetryHandler` for automatic retries

**PriorityDownloadQueue**:

- Wraps `asyncio.PriorityQueue`
- Sorts by priority (higher number = higher priority)
- Emits `download.queued` event when items are added
- Thread-safe via asyncio primitives
- Exposes `emitter` property for event wiring

**RetryHandler / ErrorCategoriser**:

- Implements exponential backoff retry logic
- Categorises errors as transient (retryable) or permanent
- Uses Python's `match/case` for clean error classification
- Configurable via `RetryPolicy` and `RetryConfig`
- Emits retry events for observability

**BaseRetryHandler / NullRetryHandler**:

- Abstract base for retry implementations
- Null object pattern for no-retry behavior
- Worker always has a handler (no None checks)

**FileValidator / BaseFileValidator / NullFileValidator**:

- Validates downloaded files against expected hashes
- Supports MD5, SHA256, and SHA512 algorithms
- Streams file in chunks for memory efficiency
- Runs in thread pool to avoid blocking event loop
- Uses constant-time comparison to prevent timing attacks
- Abstract base and null object pattern for optional validation

**Why this structure**: Separation of concerns. Manager orchestrates high-level operations, pool manages worker lifecycle, worker executes downloads, queue organises work, retry handler manages failure recovery, validator ensures file integrity.

### Events Layer

**What it does**: Provides event infrastructure.

**EventEmitter**:

- Generic pub/sub system
- Supports sync and async handlers
- Typed events via Pydantic models (immutable, validated)
- Namespaced event names (e.g., `download.progress`)

**Event Models**:

- `BaseEvent`: Common base with `occurred_at` (UTC timestamp)
- `DownloadEvent`: Download-specific base with `download_id`, `url`, and `event_type`
- Download lifecycle events:
  - `DownloadQueuedEvent` - When added to queue (with priority)
  - `DownloadStartedEvent` - When download begins (with total_bytes if known)
  - `DownloadProgressEvent` - Progress updates (includes embedded `SpeedMetrics`)
  - `DownloadCompletedEvent` - Success (includes destination_path, elapsed_seconds, average_speed_bps, optional `ValidationResult`)
  - `DownloadFailedEvent` - Failure (includes `ErrorInfo`, optional `ValidationResult` for hash mismatches)
  - `DownloadSkippedEvent` - Skipped due to file-exists strategy (includes reason, destination_path)
  - `DownloadCancelledEvent` - Cancelled by caller
  - `DownloadRetryingEvent` - Before retry (with retry count, delay, `ErrorInfo`)
  - `DownloadValidatingEvent` - Validation started (algorithm)
- `ErrorInfo`: Structured error model with `exc_type`, `message`, optional `traceback`
- `ValidationResult`: Embedded in completed/failed to carry hash validation outcome (expected/calculated hash, is_valid, duration)
- Self-contained payloads (no external state needed)

**Why events**: Loose coupling. Worker doesn't know tracker exists. Tracker doesn't know worker implementation. Easy to add new observers without modifying existing code.

### Tracking Layer

**What it does**: Aggregates download state and provides statistics.

**DownloadTracker**:

- Pure observer/state store - receives events, stores state, provides queries
- Does NOT emit events (workers and queue emit events directly)
- Maintains `DownloadInfo` for each download
- Tracks transient `SpeedMetrics` for active downloads
- Stores `ValidationResult` from completion/failure events
- Persists average speed and validation results in `DownloadInfo` upon completion/failure
- Thread-safe via `asyncio.Lock`
- Provides query methods (`get_download_info`, `get_all_downloads`, `get_stats`, `get_speed_metrics`)

**BaseTracker / NullTracker**:

- Abstract base for tracker implementations
- Null object pattern for optional tracking
- Avoids conditional checks everywhere

**Why separate tracking**: Not everyone needs tracking. Library users might implement their own. This keeps it optional and replaceable.

### Download ID System

**What it does**: Provides unique identification for each download task.

Each download is uniquely identified by a **download ID**, a 16-character hex string computed from:

```python
download_id = sha256(url + relative_destination_path).hexdigest()[:16]
```

**Key characteristics**:

- **Identity**: Same URL to different destinations = different IDs
- **Deduplication**: Same URL to same destination = same ID (duplicate skipped)
- **Propagated everywhere**: Worker events, tracker keys, queue tracking
- **Stable**: Immutable once `FileConfig` is created

**Why this design**:

- Prevents duplicate downloads (same URL+destination queued twice)
- Enables same URL to different destinations (different IDs)
- Allows re-downloading same file after completion (ID removed from queue tracking)
- Fail-fast validation (queue raises `KeyError` if `task_done()` called with invalid ID)

**Where it's used**:

- `FileConfig.id` - generates and caches the ID
- `DownloadInfo.id` - tracks download identity
- Worker/Tracker events - `download_id` field on all events
- Tracker methods - first parameter for all `track_*` methods
- Queue deduplication - `_queued_ids` set prevents duplicates
- WorkerPool - passes ID from `FileConfig` to worker

**Example**:

```python
# These are treated as different downloads (different IDs):
config1 = FileConfig(url="https://example.com/file.zip", destination_subdir="dir1")
config2 = FileConfig(url="https://example.com/file.zip", destination_subdir="dir2")

# These are treated as duplicates (same ID):
config3 = FileConfig(url="https://example.com/file.zip", destination_subdir="dir1")
config4 = FileConfig(url="https://example.com/file.zip", destination_subdir="dir1")
# Adding both config3 and config4 will only queue one download
```

### Infrastructure Layer

**What it does**: Cross-cutting concerns like logging.

**Logging**:

- Uses `loguru` for structured logging
- Configurable via settings
- Injected as dependency (testable)
- Each component gets its own logger

**Why**: Centralised, consistent logging. Easy to test without output noise.

### CLI Layer

**What it does**: Provides command-line interface for end users.

**Key components**:

- **`CLIState`**: Application state container with factory methods for creating configured components
- **`create_cli_app()`**: Typer app factory with dependency injection support for testing
- **`download` command**: Single file download with progress tracking and hash validation
- **Configuration system**: Layered config (CLI flags > env vars > .env file > defaults)
- **Event-driven display**: Subscribes to tracker events for real-time progress updates
- **Settings**: `pydantic-settings` based configuration with environment variable support

**Design patterns**:

- **Factory pattern**: `CLIState` factories create pre-configured manager and tracker instances
- **Dependency injection**: Factories accept overrides for testing (using `TypedDict` and `Unpack`)
- **Event-driven**: Display functions respond to tracker events (no polling)
- **Layered configuration**: Multiple config sources with clear precedence
- **Early validation**: Input validation at CLI boundary (URL, hash format)

**Why**: Clean separation between CLI concerns and library logic. The CLI is just another consumer of the library, with its own configuration and display logic. Event-driven architecture eliminates polling and ensures real-time updates.

## Data Flow

### Adding a Download

```text
1. User creates FileConfig(url="...", priority=1)
2. User calls manager.add([config])
3. Manager adds to PriorityDownloadQueue
4. Queue emits download.queued event
5. Tracker observes event, creates DownloadInfo with QUEUED status
6. Queue sorts by priority
```

### Processing Downloads

```text
1. Manager.open() wires queue events to tracker
2. Manager delegates to WorkerPool.start(client)
3. Pool creates N isolated worker tasks, each with its own EventEmitter
4. Pool wires each worker's emitter to tracker handlers
5. Each worker calls queue.get_next() with timeout (blocks until available)
6. Worker downloads file in chunks
7. Worker emits events: download.started → download.progress (with speed) → ... → (validation if configured) → download.completed
8. Tracker observes events, updates state (including real-time speed metrics and validation state)
9. Worker marks queue task as done
10. Worker loops back to step 5
```

**Speed Tracking Flow**:

```text
1. Worker creates SpeedCalculator for each download
2. After each chunk downloaded:
   a. Worker calls speed_calculator.record_chunk(bytes, total, timestamp)
   b. Calculator updates instantaneous speed and moving average
   c. Calculator estimates ETA based on average speed
   d. Worker emits download.progress with embedded SpeedMetrics
3. Tracker receives progress event, stores transient SpeedMetrics
4. On completion/failure:
   a. Tracker captures final average_speed_bps
   b. Tracker persists speed to DownloadInfo
   c. Tracker clears transient SpeedMetrics (frees memory)
```

### Handling Events

```text
1. Worker calls emitter.emit("download.progress", DownloadProgressEvent(...))
2. Emitter finds all registered handlers for that event
3. Emitter calls each handler (sync or async)
4. If handler fails, logs error but continues
```

### Querying State

```text
1. User calls tracker.get_download(url)
2. Tracker acquires lock
3. Tracker returns copy of DownloadInfo
4. User reads state (status, bytes_downloaded, etc.)
```

### Retry Flow

```text
1. Worker calls retry_handler.execute_with_retry(download_operation, url)
2. Retry handler executes operation
3. If operation fails:
   a. Error categoriser classifies error (transient/permanent/unknown)
   b. If permanent → raise immediately
   c. If transient and retries remaining:
      - Calculate backoff delay (exponential with jitter)
      - Emit download.retrying event (with ErrorInfo)
      - Sleep for delay
      - Retry operation
   d. If max retries exhausted → raise last exception
4. If operation succeeds → return result
```

### Validation Flow

```text
1. Worker completes file download successfully
2. If FileConfig has hash_config:
   a. Worker emits worker.validation_started event
   b. Worker calls validator.validate(file_path, hash_config)
   c. Validator calculates hash in thread pool (via asyncio.to_thread):
      - Opens file in binary mode
      - Reads file in 8KB chunks
      - Updates hasher with each chunk
      - Returns hexadecimal hash
   d. Validator compares hashes using hmac.compare_digest (constant-time)
   e. If hashes match:
      - Worker emits worker.validation_completed event
      - Worker emits download.completed event
   f. If hashes don't match:
      - Worker emits worker.validation_failed event
      - Worker deletes corrupted file
      - Worker raises HashMismatchError (not retried by default)
3. Tracker observes validation events, updates DownloadInfo.validation
```

Note: Validation events still use `worker.*` namespace and will be renamed to `download.*` in a future release.

### Shutdown Flow

The system uses an event-based shutdown mechanism for clean termination:

```text
1. User calls manager.close(wait_for_current=True/False)
2. Manager delegates to pool.shutdown(wait_for_current)
3. Pool sets internal _shutdown_event
4. Worker process_queue loops check event status:
   a. If shutdown event set → exit loop gracefully
   b. Queue get_next uses 1-second timeout to periodically check event
   c. If item retrieved after shutdown → requeue item and exit
5. If wait_for_current=True:
   - Pool waits for all workers to complete current downloads
   - Workers finish naturally and log "Worker shutting down gracefully"
6. If wait_for_current=False:
   - Pool immediately cancels all worker tasks
   - Workers raise CancelledError and stop immediately
7. Pool clears task list and returns
```

**Key features**:

- Workers periodically check shutdown event (1-second intervals)
- No downloads are lost - items are requeued if shutdown during retrieval
- Graceful shutdown allows current downloads to complete
- Immediate cancellation available for urgent stops
- Context manager (`async with`) triggers immediate shutdown on exit
- Raises `PendingDownloadsError` if exiting with unhandled pending downloads (to prevent silent data loss)
- Pool encapsulates all shutdown complexity, keeping manager interface simple

## Design Patterns

### Dependency Injection

Everything takes its dependencies as constructor args:

```python
DownloadManager(
    download_dir=Path(...),
    max_concurrent=3,
    queue=custom_queue,           # Optional
    tracker=custom_tracker,       # Optional
    logger=custom_logger,         # Optional
    worker_factory=custom_worker, # Optional
    worker_pool_factory=custom_pool,  # Optional
)
```

**Why**: Decoupling, flexibility and makes testing easy. Mock what you need, pass real implementations otherwise. Pool extraction allows testing manager orchestration independently of worker lifecycle.

### Null Object Pattern

Instead of `if tracker is not None`, we use `NullTracker`. Same for retry handlers:

```python
tracker = tracker or NullTracker()
tracker.on_download_started(...)  # Always safe to call

retry_handler = retry_handler or NullRetryHandler()
await retry_handler.execute_with_retry(...)  # Always safe to call
```

**Why**: Cleaner code. No conditionals scattered everywhere. Polymorphism over branching.

### Context Manager

Manager implements `__aenter__` and `__aexit__`:

```python
async with DownloadManager(...) as manager:
    await manager.add(files)
    await manager.wait_until_complete()
# Workers stopped, HTTP client closed automatically
```

**Why**: Resource cleanup is automatic. Can't forget to clean up.

### Observer Pattern

Workers emit events, trackers observe via pool wiring:

```python
# Worker doesn't know about tracker
await worker.emitter.emit("download.completed", DownloadCompletedEvent(...))

# Pool wires worker emitter to tracker handlers
worker.emitter.on("download.completed", lambda e: tracker.track_completed(...))
```

**Why**: Decoupling. Easy to add new observers.

### Composition Over Inheritance

Components own an `EventEmitter` rather than inheriting:

```python
class DownloadWorker:
    def __init__(self, emitter: BaseEmitter):
        self._emitter = emitter
```

**Why**: Flexibility. Can swap emitter implementations. No inheritance hierarchy.

## Extension Points

If you want to customise behaviour:

1. **Custom Queue**: Implement queue interface, pass to manager
2. **Custom Tracker**: Extend `BaseTracker`, pass to manager
3. **Custom Worker**: Implement `BaseWorker`, pass factory to manager
4. **Custom Pool**: Implement `BaseWorkerPool`, pass factory to manager
5. **Event Handlers**: Register your own handlers with tracker

Example - custom worker pool:

```python
class CustomPool(BaseWorkerPool):
    """Custom pool with different worker creation strategy."""

    async def start(self, client: ClientSession) -> None:
        # Your custom worker creation logic
        pass

    # ... implement other methods

manager = DownloadManager(
    worker_pool_factory=CustomPool,
    # ... other params
)
```

## Why These Choices?

### Why asyncio?

HTTP downloads are I/O bound. Async lets us handle many concurrent connections without threading overhead. We use `aiofiles` for file I/O to ensure disk writes don't block the event loop—critical for maintaining concurrency on slow disks or network mounts.

### Why events instead of callbacks?

Events are more flexible:

- Multiple observers per event
- Add/remove observers dynamically
- No tight coupling
- Easier to test

### Why dependency injection?

Decoupling and flexibility.. also makes testing trivial:

- Mock HTTP client
- Mock logger
- Mock tracker
- No monkeypatching needed

### Why separate domain models?

Keeps business logic clean:

- No framework dependencies
- Easy to reason about
- Portable to other contexts
- Serialisable for storage/API

### Why priority queue?

Simple and effective:

- Download urgent files first
- Fair scheduling
- Built into asyncio
- Easy to understand

## Performance Characteristics

**Concurrency**: Linear scaling up to network/CPU limits. Three workers = roughly 3x throughput.

**Memory**: O(n) where n = number of tracked downloads. Completed downloads stay in memory (for now).

**Event overhead**: Minimal. Events are just function calls with Pydantic model creation.

**Thread safety**: Uses asyncio primitives (`Lock`, `Queue`). Safe for concurrent access within event loop.

## What's Not Here

Things we explicitly didn't build (yet):

- ✅ ~~No retry logic~~ - **Implemented with exponential backoff**
- ✅ ~~No speed/ETA tracking~~ - **Implemented with moving average and real-time updates**
- ✅ ~~No hash validation~~ - **Implemented with MD5, SHA256, SHA512 support**
- No resume support (planned for Phase 1)
- No multi-segment parallel downloads (planned for Phase 1)
- No persistent storage (planned for Phase 2)
- No authentication (planned for Phase 2)
- No distributed coordination (maybe Phase 3)

## Testing Strategy

Each layer is tested in isolation:

- Domain: Pure data models, no I/O
- Downloads: Mock HTTP client via `aioresponses`
- Events: Test emitter and handlers separately
- Tracking: Test state transitions with events
- Integration: Test full flow with real async tasks

Fixtures in `conftest.py` provide common test dependencies.

**Blocking Call Detection**: Tests use `blockbuster` to catch any synchronous I/O operations in async code, ensuring the event loop never blocks on disk or network operations.

## Further Reading

- `docs/ROADMAP.md`: What we're building next
- `docs/IDEAS.md`: Future possibilities
- `README.md`: Quick start guide
- Source code: It's structured to be readable

## Questions?

If something's unclear, check the code. It's organised to be self-documenting:

- File names match responsibilities
- Classes are focused
- Methods are small
- Tests show usage examples

When in doubt, look at the tests.
