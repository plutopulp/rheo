# Async Download Manager - Architecture Guide

## Overview

The Async Download Manager is a production-ready, high-performance concurrent file downloader built with Python's `asyncio` library. It follows a clean, layered architecture with clear separation of concerns, making it both maintainable and extensible.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │   CLI Tool      │  │   Web API       │  │   Library   │  │
│  │   (Future)      │  │   (Future)      │  │   Usage     │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                 Orchestration Layer                         │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                DownloadManager                          │ │
│  │  • Worker lifecycle management                         │ │
│  │  • Priority queue coordination                         │ │
│  │  • Resource cleanup                                    │ │
│  │  • Context manager protocol                           │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                    Worker Layer                             │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                 DownloadWorker                          │ │
│  │  • HTTP streaming downloads                            │ │
│  │  • Chunked processing                                  │ │
│  │  • Error handling & recovery                          │ │
│  │  • Progress reporting                                  │ │
│  └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                   Tracking Layer                            │
│  ┌───────────────────────┐  ┌─────────────────────────────┐  │
│  │   DownloadTracker     │  │       NullTracker          │  │
│  │ • State management    │  │ • No-op implementation     │  │
│  │ • Progress monitoring │  │ • Performance optimization │  │
│  │ • Rich UI display     │  │ • Testing support          │  │
│  └───────────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                     Data Layer                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │  DownloadInfo   │  │PatchDownloadInfo│  │ FileConfig  │  │
│  │ • Immutable     │  │ • Partial       │  │ • Download  │  │
│  │ • Complete      │  │   updates       │  │   specs     │  │
│  │ • Self-         │  │ • Thread-safe   │  │ • Priority  │  │
│  │   contained     │  │   operations    │  │   info      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────┐
│                 Infrastructure Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   aiohttp   │  │    Rich     │  │    asyncio.Queue    │  │
│  │ • HTTP      │  │ • Terminal  │  │  • Priority         │  │
│  │   client    │  │   UI        │  │    scheduling       │  │
│  │ • Streaming │  │ • Progress  │  │  • Backpressure     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Component Architecture

### 1. Data Layer

The foundation of the system, providing immutable data structures and clear contracts:

#### DownloadInfo

- **Purpose**: Complete state representation of a download
- **Design**: Immutable dataclass with computed properties
- **Key Methods**: `get_progress()`, `is_terminal()`, `get_speed_estimate()`
- **Thread Safety**: Immutable after creation, safe to share

#### PatchDownloadInfo

- **Purpose**: Partial updates for thread-safe state modifications
- **Pattern**: Only non-None fields are applied during updates
- **Benefits**: Atomic updates, prevents accidental overwrites

#### DownloadStatus

- **Purpose**: Well-defined state machine for download lifecycle
- **States**: QUEUED → PENDING → IN_PROGRESS → (COMPLETED | FAILED)
- **Design**: String enum for easy serialization and logging

#### FileConfig

- **Purpose**: Download specification with metadata
- **Features**: Priority system, size estimates, content type hints
- **Usage**: Input format for download requests

### 2. Tracking Layer

Manages state and provides observability:

#### DownloadTracker

- **Responsibilities**:
  - Centralized state management
  - Real-time progress monitoring
  - Rich terminal UI
- **Patterns**: Observer pattern for state updates
- **Performance**: O(1) updates, O(n) bulk queries
- **UI**: Live-updating table with progress bars

#### NullTracker

- **Pattern**: Null Object pattern
- **Purpose**: Optional tracking without conditional logic
- **Benefits**: Eliminates null checks, maintains performance
- **Use Cases**: Testing, performance-critical scenarios

### 3. Worker Layer

Handles the actual download operations:

#### DownloadWorker

- **Core Function**: HTTP streaming downloads with progress tracking
- **Memory Model**: O(chunk_size) memory usage regardless of file size
- **Error Strategy**: Comprehensive error classification and recovery
- **Progress**: Real-time updates via tracker interface

**Key Features**:

- Streaming downloads for memory efficiency
- Configurable chunk sizes (default: 1KB)
- Timeout handling with cleanup
- Atomic operations (complete success or clean failure)
- Progress reporting per chunk

### 4. Orchestration Layer

Coordinates the overall system:

#### DownloadManager

- **Role**: High-level coordinator and resource manager
- **Patterns**: Context manager, dependency injection
- **Concurrency**: Worker pool with configurable limits
- **Queue**: Priority-based scheduling with asyncio.PriorityQueue

**Responsibilities**:

- Worker lifecycle management
- HTTP session management
- Queue coordination
- Resource cleanup
- Configuration management

## Design Patterns Used

### 1. **Context Manager Pattern**

```python
async with DownloadManager() as dm:
    # Automatic resource management
    # HTTP sessions, workers cleaned up automatically
```

### 2. **Dependency Injection**

```python
# All dependencies are injectable for testing
manager = DownloadManager(
    client=custom_session,
    tracker=custom_tracker,
    worker=custom_worker
)
```

### 3. **Observer Pattern**

```python
# Worker reports progress to tracker
worker.tracker.patch_download(url, PatchDownloadInfo(bytes_downloaded=1024))
```

### 4. **Null Object Pattern**

```python
# No conditional logic needed
self.tracker = tracker or NullTracker()
self.tracker.patch_download(...)  # Always works
```

### 5. **State Machine**

```python
# Clear state transitions
QUEUED → PENDING → IN_PROGRESS → (COMPLETED | FAILED)
```

### 6. **Strategy Pattern**

```python
# Different tracking strategies
tracker = DownloadTracker()  # Full tracking with UI
tracker = NullTracker()      # No-op tracking
```

## Data Flow

### Download Request Flow

```
1. FileConfig created with URL and metadata
2. DownloadManager.add_to_queue() adds to priority queue
3. DownloadTracker.register_download() creates initial state
4. Worker picks up task from queue
5. DownloadWorker.download() performs HTTP streaming
6. Progress updates sent to tracker via patch operations
7. Final state (COMPLETED/FAILED) recorded
8. Cleanup performed (partial files removed on failure)
```

### State Update Flow

```
1. Worker processes chunk of data
2. Creates PatchDownloadInfo with new bytes_downloaded
3. Calls tracker.patch_download() with patch
4. Tracker applies patch to DownloadInfo in-place
5. Monitor coroutine displays updated progress
6. Process repeats until download complete
```

### Error Handling Flow

```
1. Exception occurs in download operation
2. Worker._handle_exception() classifies error type
3. Partial file cleanup performed
4. Error state recorded via patch_download()
5. Monitor displays error in UI
6. Worker continues with next queued item
```

## Concurrency Model

### Thread Safety

- **Single-threaded**: All operations on asyncio event loop
- **No locks needed**: Event loop provides natural serialization
- **Immutable data**: Prevents race conditions
- **Atomic updates**: Patch operations are atomic

### Performance Characteristics

- **Memory**: O(workers × chunk_size) - constant regardless of file sizes
- **CPU**: Minimal overhead, I/O bound operations
- **Network**: Efficient streaming, configurable chunk sizes
- **Concurrency**: Configurable worker pool (default: 3)

### Scalability

- **Horizontal**: Add more workers for higher throughput
- **Vertical**: Increase chunk size for larger files
- **Memory**: Streaming prevents memory exhaustion
- **Network**: Connection pooling via aiohttp

## Configuration System

### Priority System

```python
priority: int = 1  # Higher numbers = higher priority
# 1-2: Background/low priority
# 3: Normal priority
# 4-5: High/urgent priority
```

### Size Estimation

```python
size_bytes: int | None = None     # Enables progress bars
size_human: str | None = None     # Human-readable display
```

### Worker Configuration

```python
max_workers: int = 3              # Concurrent download limit
timeout: float | None = None      # Per-download timeout
chunk_size: int = 1024           # Streaming chunk size
```

## Error Handling Strategy

### Error Classification

1. **Connection Errors**: Network issues, DNS failures
2. **Timeout Errors**: Request/response timeouts
3. **HTTP Errors**: 4xx/5xx status codes
4. **File Errors**: Disk space, permissions
5. **Generic Errors**: Unexpected exceptions

### Recovery Mechanisms

- **Automatic cleanup**: Remove partial files on failure
- **State consistency**: Always maintain valid state
- **Error propagation**: Clear error messages in UI
- **Graceful degradation**: Continue with other downloads

### Monitoring and Observability

- **Real-time UI**: Live progress display
- **Structured logging**: Detailed operation logs
- **State tracking**: Complete download history
- **Error reporting**: Clear error messages and classifications

## Extension Points

The architecture provides several extension points for customization:

1. **Custom Trackers**: Implement tracker interface for different UIs
2. **Custom Workers**: Override download logic for different protocols
3. **Custom Queues**: Different scheduling algorithms
4. **Plugin System**: Hook into lifecycle events
5. **Storage Backends**: Different file storage mechanisms

This architecture balances simplicity with extensibility, providing a solid foundation for both basic usage and advanced customization scenarios.
