# Roadmap

What we're actually building, in order of priority.

## Phase 1: MVP (Current Focus)

**Goal**: Make it usable as both a library and CLI tool.

### Core Library Features

- [x] Concurrent downloads with worker pool
- [x] Priority queue system
- [x] Event-based architecture
- [x] Download tracking and state management
- [x] Comprehensive error handling
- [ ] Retry logic with exponential backoff
- [ ] Download resume support (HTTP Range requests)

### CLI Tool

- [ ] Basic download command (`adm download <url>`)
- [ ] Batch downloads (`adm download batch urls.txt`)
- [ ] Progress display (Rich UI)
- [ ] Test command using built-in test files
- [ ] Configuration system

**Acceptance Criteria**:

- Can download files from command line
- Shows progress in terminal
- Handles failures gracefully
- Can be installed via pip

## Phase 2: Production Ready

**Goal**: Make it robust enough for real-world use.

### Reliability

- [ ] Automatic retry with backoff
- [ ] Resume interrupted downloads
- [ ] Bandwidth throttling
- [ ] Connection pooling optimisation
- [ ] Better timeout handling

### Monitoring

- [ ] Queue management commands
- [ ] Download history tracking
- [ ] Statistics and metrics
- [ ] Live monitoring dashboard

### Configuration

- [ ] Config file support (~/.adm/config.toml)
- [ ] Environment variable overrides
- [ ] Per-download configuration
- [ ] Profile system

**Acceptance Criteria**:

- Handles flaky networks
- Can resume large downloads
- Provides useful statistics
- Configuration is persistent

## Phase 3: Advanced Features

**Goal**: Make it extensible and powerful.

### Enhanced Functionality

- [ ] Authentication support (tokens, basic auth)
- [ ] Workspace isolation
- [ ] Plugin system
- [ ] Post-download hooks (unzip, verify, etc.)
- [ ] Duplicate detection

### Integration

- [ ] REST API for programmatic control
- [ ] Webhook notifications
- [ ] Cloud storage integration (S3, etc.)
- [ ] Database backends for history

### Performance

- [ ] Adaptive chunk sizes
- [ ] Parallel chunk downloads (single file)
- [ ] Smart bandwidth allocation
- [ ] Memory usage optimisation

**Acceptance Criteria**:

- Supports common auth methods
- Extensible via plugins
- Can integrate with other tools
- Handles very large files efficiently

## Non-Goals

Things we're explicitly NOT building:

- BitTorrent support
- FTP/SFTP (maybe later)
- GUI application
- Browser extension
- Video streaming/conversion
- File hosting service

## Decision Points

Questions we need to answer:

1. **Storage backend**: SQLite, JSON files, or in-memory only?
2. **Auth storage**: Where/how to store credentials securely?
3. **Plugin API**: What hooks do we expose?
4. **CLI framework**: Typer, Click, or argparse?

## Timeline

Rough estimates (subject to change):

- Phase 1: 2-3 weeks
- Phase 2: 3-4 weeks
- Phase 3: TBD (depends on priorities)

This isn't a promise, just a guide. We'll adjust as we go.
