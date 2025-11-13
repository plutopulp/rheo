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
```

Each layer has clear responsibilities and minimal coupling.

## Component Overview

### Domain Layer

**What it does**: Defines the core models and exceptions.

Key pieces:

- `FileConfig`: Download configuration (URL, destination, priority, etc.)
- `DownloadInfo`: Current state of a download
- `DownloadStatus`: Enum for states (pending, downloading, completed, failed)
- `DownloadStats`: Aggregated statistics
- Custom exceptions: `ValidationError`, `ManagerNotInitializedError`, etc.

**Why**: Keeps business logic separate from infrastructure. These models can be used anywhere without importing heavy dependencies.

### Downloads Layer

**What it does**: Manages the download lifecycle.

**DownloadManager**:

- Entry point for the library
- Manages worker pool
- Initialises HTTP client
- Wires events from workers to tracker
- Context manager for resource cleanup

**DownloadWorker**:

- Does the actual HTTP download
- Chunks data for progress reporting
- Emits events for lifecycle stages
- Handles errors with optional retry logic
- Uses injected `RetryHandler` for automatic retries

**PriorityDownloadQueue**:

- Wraps `asyncio.PriorityQueue`
- Sorts by priority (lower number = higher priority)
- Thread-safe via asyncio primitives

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

**Why this structure**: Separation of concerns. Manager orchestrates, worker executes, queue organises, retry handler manages failure recovery.

### Events Layer

**What it does**: Provides event infrastructure.

**EventEmitter**:

- Generic pub/sub system
- Supports sync and async handlers
- Typed events via dataclasses
- Namespaced event names (e.g., `worker.started`)

**Event Models**:

- `WorkerEvent`: Base class with `url` and `timestamp`
- Specific events: `WorkerStartedEvent`, `WorkerProgressEvent`, `WorkerCompletedEvent`, `WorkerFailedEvent`, `WorkerRetryEvent`
- Self-contained payloads (no external state needed)

**Why events**: Loose coupling. Worker doesn't know tracker exists. Tracker doesn't know worker implementation. Easy to add new observers without modifying existing code.

### Tracking Layer

**What it does**: Aggregates download state and provides statistics.

**DownloadTracker**:

- Observes worker events
- Maintains `DownloadInfo` for each URL
- Thread-safe via `asyncio.Lock`
- Provides query methods (`get_download`, `get_all_downloads`, `get_stats`)

**BaseTracker / NullTracker**:

- Abstract base for tracker implementations
- Null object pattern for optional tracking
- Avoids conditional checks everywhere

**Why separate tracking**: Not everyone needs tracking. Library users might implement their own. This keeps it optional and replaceable.

### Infrastructure Layer

**What it does**: Cross-cutting concerns like logging.

**Logging**:

- Uses `loguru` for structured logging
- Configurable via settings
- Injected as dependency (testable)
- Each component gets its own logger

**Why**: Centralised, consistent logging. Easy to test without output noise.

## Data Flow

### Adding a Download

```text
1. User creates FileConfig(url="...", priority=1)
2. User calls manager.add_to_queue([config])
3. Manager adds to PriorityDownloadQueue
4. Queue sorts by priority
```

### Processing Downloads

```text
1. Manager starts N worker tasks
2. Each worker calls queue.get_next() (blocks until available)
3. Worker downloads file in chunks
4. Worker emits events: started → chunk → chunk → ... → completed
5. Tracker observes events, updates state
6. Worker marks queue task as done
7. Worker loops back to step 2
```

### Handling Events

```text
1. Worker calls emitter.emit("worker.chunk_downloaded", ChunkDownloaded(...))
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
      - Emit WorkerRetryEvent
      - Sleep for delay
      - Retry operation
   d. If max retries exhausted → raise last exception
4. If operation succeeds → return result
```

## Design Patterns

### Dependency Injection

Everything takes its dependencies as constructor args:

```python
DownloadManager(
    download_dir=Path(...),
    max_workers=3,
    queue=custom_queue,      # Optional
    tracker=custom_tracker,  # Optional
    logger=custom_logger,    # Optional
)
```

**Why**: Decoupling, flexibility and makes testing easy. Mock what you need, pass real implementations otherwise.

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
    await manager.add_to_queue(files)
    await manager.queue.join()
# Workers stopped, HTTP client closed automatically
```

**Why**: Resource cleanup is automatic. Can't forget to clean up.

### Observer Pattern

Workers emit events, trackers observe:

```python
# Worker doesn't know about tracker
worker.emitter.emit("worker.completed", ...)

# Tracker registered to observe
tracker.on_download_completed(event)
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
3. **Event Handlers**: Register your own handlers with manager
4. **Custom Worker**: Create your own worker class

Example - custom event handler:

```python
async def log_progress(event: ChunkDownloaded):
    print(f"Downloaded {event.bytes_downloaded} bytes")

manager = DownloadManager(...)
manager.worker.emitter.on("worker.chunk_downloaded", log_progress)
```

## Why These Choices?

### Why asyncio?

HTTP downloads are I/O bound. Async lets us handle many concurrent connections without threading overhead.

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

**Event overhead**: Minimal. Events are just function calls with dataclass creation.

**Thread safety**: Uses asyncio primitives (`Lock`, `Queue`). Safe for concurrent access within event loop.

## What's Not Here

Things we explicitly didn't build (yet):

- ✅ ~~No retry logic~~ - **Implemented with exponential backoff**
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
