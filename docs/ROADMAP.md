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
- [x] **Retry logic with exponential backoff**
- [x] **Configurable retry policies (transient vs permanent errors)**
- [x] **Speed and ETA tracking**
- [x] **Hash validation (MD5, SHA256, SHA512)**
- [ ] Download resume support (HTTP Range requests)
- [ ] Multi-segment downloads (parallel chunks per file)
- [ ] Custom HTTP headers and cookies support
- [ ] Basic proxy support (HTTP/HTTPS)
- [ ] Skip existing files option

### CLI Tool

- [x] **Basic download command (`rheo download <url>`)**
- [x] **Hash verification option**
- [x] **Configuration system (env vars, .env file, CLI flags)**
- [ ] Batch downloads (`rheo download batch urls.txt`)
- [ ] Progress display with speed/ETA (Rich UI)
- [ ] Proxy configuration
- [ ] Test command using built-in test files

**Acceptance Criteria**:

- Can download files from command line ✅
- Shows progress in terminal ✅ (basic, Rich UI pending)
- Handles failures gracefully ✅
- Can be installed via pip
- Verifies file integrity with hashes ✅
- Downloads faster with multi-segment support (pending)

## Phase 2: Production Ready

**Goal**: Make it robust enough for real-world use.

### Reliability

- [x] **Automatic retry with exponential backoff** ✅
- [ ] Resume interrupted downloads
- [ ] Mirror URL support with failover
- [ ] Configurable segment sizes
- [ ] Bandwidth throttling
- [ ] Connection pooling optimisation
- [ ] Download state persistence (.part files)
- [ ] Better timeout handling

### Automation

- [ ] Clipboard monitoring (auto-detect URLs)
- [ ] Download scheduling (specific time, recurring)
- [ ] Auto-resume incomplete downloads on startup
- [ ] Expired URL detection and refresh

### Enhanced CLI

- [ ] Package system (grouped downloads)
- [ ] SOCKS proxy support (SOCKS4, SOCKS5)
- [ ] Advanced filtering and search

### Monitoring

- [ ] Queue management commands
- [ ] Download history tracking
- [ ] Statistics and metrics
- [ ] Live monitoring dashboard

### Configuration

- [ ] Config file support (~/.rheo/config.toml)
- [ ] Environment variable overrides
- [ ] Per-download configuration
- [ ] Profile system

**Acceptance Criteria**:

- Handles flaky networks
- Can resume large downloads
- Provides useful statistics
- Configuration is persistent
- Auto-resumes interrupted downloads
- Works with expired/refreshable URLs

## Phase 3: Advanced Features

**Goal**: Make it extensible and powerful.

### Enhanced Functionality

- [ ] Authentication support (tokens, basic auth)
- [ ] Post-download hooks (unzip, verify, etc.)
- [ ] Duplicate detection
- [ ] Persistence layer (SQLite for history)
- [ ] Advanced statistics and analytics

### Integration

- [ ] Webhook notifications
- [ ] Cloud storage integration (S3, etc.)

### Performance

- [ ] Adaptive chunk sizes
- [ ] Smart bandwidth allocation
- [ ] Memory usage optimisation

**Acceptance Criteria**:

- Supports common auth methods
- Can integrate with other tools
- Handles very large files efficiently
- Persists history across sessions
- Integrates with external services

## Non-Goals

Things we're explicitly NOT building:

- BitTorrent support
- FTP/SFTP (maybe later)
- GUI application
- Browser extension
- Video streaming/conversion
- File hosting service
- Multi-user systems
- Web-based GUI
- Account management for premium hosters
- Captcha solving
- Container/link decryption
- Click 'N' Load server

## Decision Points

Questions we need to answer:

1. **Storage backend**: Use SQLite in Phase 3, JSON for state files in Phase 2
2. **CLI framework**: ✅ Typer (with Rich for future enhanced UI)
3. **Segment size algorithm**: Static vs adaptive vs user-configurable?
4. **Mirror selection strategy**: Random, sequential, or fastest-first?

## Timeline

Rough estimates (subject to change):

- Phase 1: 3-4 weeks (more features now)
- Phase 2: 4-6 weeks (automation features added)
- Phase 3: TBD (simplified scope)

This isn't a promise, just a guide. We'll adjust as we go.
