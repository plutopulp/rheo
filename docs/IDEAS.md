# Ideas

A bank of ideas that aren't in the [roadmap](ROADMAP.md) yet. These may or may not become part of the roadmap. Once something moves to the roadmap, it gets removed from here.

## Future Possibilities

### CLI Expansion

Beyond v0.2.0's batch downloads and resume support, we're considering:

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
- Skip existing files option (check if file exists before downloading)
- Cloud storage integration (upload to S3, GCS, etc. after download)
- Adaptive chunk sizes depending on speed
- Memory usage optimisation for very large files

These are all technically feasible but need careful thought about scope and complexity.

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

Check out the [architecture doc](ARCHITECTURE.md) for more details.

### Event Emission Concerns

The DownloadTracker currently handles multiple jobs: state aggregation, event emission, query interface... This works but mixes concerns and could get out of hand.

Consider splitting into separate trackers (ValidationTracker, SpeedTracker, etc.) and then allow users to compose their own tracker, e.g. builder pattern type of thing. Or make Tracker a pure state store with Worker handling all events. For now, the hybrid approach where Worker emits internal events -> Tracker transforms them into public API, is fine.

If we add complex features like bandwidth limiting or multi-segment coordination, we'll likely split things up using a composition pattern. Not over-engineering early though.
