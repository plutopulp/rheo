# Ideas

A bank of ideas that aren't in the [roadmap](ROADMAP.md) yet. These may or may not become part of the roadmap. Once something moves to the roadmap, it gets removed from here.

## Future Possibilities

### CLI Expansion

Beyond the planned batch downloads and resume support, we're considering:

- Config management commands (`rheo config show/set`)
- Download history and statistics commands
- Package system (grouped downloads with metadata)
- Queue management (pause/resume/cancel specific downloads whilst running)

### Proxy and Header Support

Adding support for HTTP client configuration. Whilst you can currently inject custom aiohttp clients, having an API for this may be more convenient:

- Custom HTTP headers per download
- Cookie support
- HTTP/HTTPS proxy configuration
- Proxy authentication
- Per-download configuration overrides

### Automation Features

Ideas that might be useful but aren't priorities:

- Download scheduling (start at specific time or recurring downloads, i.e. cron-jobs)
- Cloud storage integration (upload to S3, GCS, etc. after download)
- Adaptive chunk sizes depending on speed
- Memory usage optimisation for very large files

These are all technically feasible but need careful thought about scope and complexity.

### Manager Lifecycle Events

Potential manager-level events for orchestration:

- `manager.idle` - All downloads complete, queue empty (useful for pipelines, UI updates)
- `manager.ready` - Manager started and accepting downloads
- `manager.shutting_down` / `manager.closed` - For cleanup coordination

The `manager.idle` event has the highest value for pipeline orchestration and UI state management.

## What We Won't Do

Things we've explicitly decided against:

- GUI application (CLI and library only)
- Web-based UI (wrong focus for a library-first tool)
- Video streaming or transcoding
- File hosting service
- Social features or anything like that
- Multi-user systems
- Captcha solving (too niche, moving target, not core library responsibility)
- Account management for file hosting services (e.g. RapidShare, Mega etc..)
- Container/link decryption (library is for downloading given a URL, not extracting URLs)

## Design Decisions

What we've already decided:

- **Event-based architecture** - Events over callbacks for flexibility
- **Dependency injection** - Implementations are swappable, testing is easier
- **Priority queue** - Simple but effective for most use cases
- **Null object pattern** - Cleaner than conditional checks everywhere
- **Library-first** - Not trying to be a full download manager application
- **Manager as event facade** - Single point for event subscription via `manager.on()`/`off()`
- **Tracker as observer** - Pure state store, receives events, provides queries (doesn't emit)
- **Shared emitter** - Single emitter owned by manager, passed to queue/pool/workers

Check out the [architecture doc](ARCHITECTURE.md) for more details.
