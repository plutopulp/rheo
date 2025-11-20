# Ideas

Here's what we're thinking about for future versions. None of this is promised, just possibilities to explore before commiting them to the [roadmap](ROADMAP.md).

## What's Next

### Multi-Segment Downloads

Splitting large files into parallel chunks could significantly speed up downloads. e.g. downloading a 1GB file as eight 125MB segments simultaneously rather than one long stream. We'd need to handle segment merging, adaptive chunk sizing based on file size, and tracking progress for each segment independently.

### Proxy and Header Support

Adding HTTP/HTTPS proxy configuration and custom headers would let you route downloads through corporate proxies or add authentication tokens. Per-download overrides would be useful for different sources needing different credentials. Although the current system does support injecting custom aiohttp clients.

### CLI Expansion

The CLI currently handles single downloads well enough. We're considering batch downloads from files, resuming interrupted downloads, and retrying failed ones. Maybe some basic config management (`rheo config show/set`). Do wanna keep it simple enough for the time being though.

## What We Won't Do

Things we've explicitly decided against:

- No GUI application (CLI and library only)
- No Full web UI (wrong focus)
- No video streaming or transcoding
- No file hosting service
- No social features or anything like that
- Multi-user systems
- Captcha solving. It's too niche, a moving target and not core library responsibility. The library is for downloading given a URL, not for getting the url in the first place.
- Account management (credential storage) for file hosting services (e.g. RapidShare, Mega etc..)

## Design Decisions

What we've already decided:

- **Event-based architecture** - Events over callbacks for flexibility
- **Dependency injection** - Implementations are swappable, testing is easier
- **Priority queue** - Simple but effective for most use cases
- **Null object pattern** - Cleaner than conditional checks everywhere
- **Library-first** - Not trying to be a full download manager application

Check out the [architecure doc](ARCHITECTURE.md) for more details.

### Event Emission Concerns

The DownloadTracker currently handles multiple jobs: state aggregation, event emission, query interface... This works but mixes concerns and could get out of hand.

Consider splitting into separate trackers (ValidationTracker, SpeedTracker, etc.) and then allow users to compose their own tracker, e.g. builder pattern type of thing. Or make Tracker a pure state store with Worker handling all events. For now, the hybrid approach where Worker emits internal events -> Tracker transforms them into public API, is fine.

If we add complex features like bandwidth limiting or multi-segment coordination, we'll likely split things up using a composition pattern. Not over-engineering early though.
