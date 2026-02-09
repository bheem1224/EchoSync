# SoulSync Application Overview

**SoulSync** is an intelligent music collection manager and automated discovery platform. It bridges streaming services (Spotify, Tidal, YouTube) with local music libraries (Plex, Jellyfin, Navidrome) by automatically downloading, organizing, and enriching music with metadata.

---

## Table of Contents

1. [Core Features](#core-features)
2. [Architecture Overview](#architecture-overview)
3. [Providers](#providers)
4. [Key Systems](#key-systems)
5. [Workflow](#workflow)
6. [Configuration](#configuration)
7. [Database Schema](#database-schema)

---

## Core Features

### 1. **Playlist Synchronization**
- **Spotify → Library**: Automatically sync Spotify playlists to your media server
- **Tidal Support**: Same as Spotify for Tidal
- **YouTube Fallback**: Same as Spotify for YouTube Music
- **Scheduled Sync**: Set playlists to auto-sync on configurable intervals
- **Conflict Resolution**: "Keep Both" strategy prevents data loss when versions differ

### 2. **Intelligent Matching Engine**
- **EXACT_SYNC Profile**: Strict text matching (title, artist, album) with ±3s duration tolerance
- **DOWNLOAD_SEARCH Profile**: Flexible matching for messy P2P filenames
- **Fingerprint-Based Matching**: Chromaprint/AcoustID identifies identical audio across formats
- **Fallback Chain**: Fingerprint → Text search → Manual review queue
- **Confidence Scoring**: Each match includes a confidence percentage (0-100%)

### 3. **Metadata Enhancement**
- **Chromaprint Fingerprinting**: Generate audio fingerprints for accurate track identification
- **AcoustID Lookup**: Convert fingerprints to MusicBrainz IDs (MBIDs)
- **MusicBrainz Integration**: Fetch authoritative metadata (title, artist, album art)
- **Automatic Tagging**: ID3v2.4 (MP3) and Vorbis Comments (FLAC) with full metadata
- **LRC Lyrics**: Automatically fetch synchronized lyrics from LRClib

### 4. **Download Management**
- **Soulseek P2P**: Makes use of detailed user defined quality profiles to download the exact track in the exact quality the user wants
- **Quality Detection**: Identify bitrate, sample rate, and bit depth
- **Bandwidth Control**: Rate limiting prevents network saturation
- **Resume Support**: Failed downloads can be retried automatically

### 5. **Discovery & Automation**
- **Artist Watchlist**: Monitor artists for new releases
- **Wishlist System**: Queue tracks with automatic retry (30-min intervals)
- **Similar Artist Recommendations**: Find related artists via MusicBrainz
- **Beatport Charts**: Electronic music discovery integration (not yet implemented)
- **Scheduled Tasks**: Background jobs handle all automation without manual intervention

### 6. **Library Management**
- **Database Tracking**: SQLite database stores sync history, download status, and metadata
- **Deduplication**: Automatic detection of duplicate files (same audio, different tags)
- **Health Checks**: Monitor all provider connections and availability
- **Review Queue**: Manual review interface for low-confidence matches
- **Batch Operations**: Process multiple files/playlists simultaneously

---

## Architecture Overview

### Design Philosophy

**SoulSync follows a centralized, provider-agnostic architecture:**

```
┌─────────────────────────────────────────────────┐
│              Web UI / API Layer                 │
│         (Flask REST API + Svelte Frontend)      │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│            Core (Smart) - Central Control       │
│  ├─ Job Queue (Scheduler)                       │
│  ├─ Matching Engine (Scoring & Comparison)      │
│  ├─ Request Manager (Rate Limiting & Retries)   │
│  ├─ Settings & Configuration                    │
│  ├─ Database Access Layer                       │
│  └─ Health Check Registry                       │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│    Providers (Dumb) - Data Fetchers Only        │
│  ├─ Source: Spotify, Tidal, YouTube            │
│  ├─ Metadata: MusicBrainz, AcoustID, LRClib    │
│  ├─ Library: Plex, Jellyfin, Navidrome         │
│  ├─ Download: Slskd (Soulseek)                 │
│  └─ Utility: ListenBrainz, LyricFind           │
└─────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────┐
│      Database (SQLite)                          │
│  ├─ Tracks & Albums                            │
│  ├─ Sync History & Status                       │
│  ├─ Downloads & Queue                          │
│  ├─ Metadata Cache                             │
│  └─ Configuration (encrypted)                  │
└─────────────────────────────────────────────────┘
```

### Key Architectural Principles

1. **Central Control**: Core module controls ALL scheduling, database access, and orchestration
2. **Dumb Providers**: Providers are read-only data fetchers. They don't schedule jobs or write to DB
3. **Universal Data Format**: All providers use `SoulSyncTrack` object for interoperability
4. **Rate Limiting**: Centralized HTTP client enforces per-provider rate limits
5. **Provider-Agnostic Core**: Core knows nothing about specific providers; works with SoulSyncTrack only
6. **Graceful Degradation**: Fallback chains ensure service continues if one provider fails

---

## Providers

### Source Providers

#### **Spotify**
- **Purpose**: Fetch user playlists, liked tracks, and recommendations
- **Authentication**: OAuth 2.0
- **Features**: 
  - Full playlist sync with track ordering
  - Release Radar and Discover Weekly
  - Device playback control
  - Artist/album browsing
- **Rate Limit**: 429 handling with exponential backoff
- **Health Check**: Validates token freshness every 5 minutes

#### **Tidal**
- **Purpose**: Alternative premium streaming with higher audio quality
- **Authentication**: OAuth 2.0 (device flow)
- **Features**:
  - Playlist sync
  - High-fidelity audio detection
  - Artist watchlist
- **Rate Limit**: 100 req/10s automatic throttling
- **Health Check**: Connection validation

#### **YouTube Music** Not yet implemented
- **Purpose**: Fallback source and search engine
- **Authentication**: Browser session cookie
- **Features**:
  - Playlist sync
  - Video search and download metadata
  - Upload library support
- **Rate Limit**: Adaptive (respects 429 responses)
- **Health Check**: Session validity check

### Library Providers

#### **Plex**
- **Purpose**: Centralized media library and streaming
- **Authentication**: API token
- **Features**:
  - Library scanning and import
  - Track matching and deduplication
  - Playlist management
  - Album artwork sync
- **Rate Limit**: 4 req/sec (configurable)
- **Health Check**: Server availability and library size

#### **Jellyfin**
- **Purpose**: Open-source media server alternative
- **Authentication**: API token
- **Features**:
  - Library management
  - Metadata sync
  - Collection organization
- **Rate Limit**: Adaptive (no hard limit)
- **Health Check**: Authentication and connectivity

#### **Navidrome**
- **Purpose**: Lightweight music streaming server
- **Authentication**: OAuth 2.0 or basic auth
- **Features**:
  - Music library management
  - Playlist sync
  - Play statistics
- **Rate Limit**: None (direct API)
- **Health Check**: Server status

### Download Provider

#### **Slskd (Soulseek)**
- **Purpose**: P2P file sharing network for rare/quality audio
- **Authentication**: Soulseek username/password (via Slskd API)
- **Features**:
  - FLAC-priority search
  - Bandwidth throttling
  - User reputation tracking
  - Search result filtering
- **Rate Limit**: 1 concurrent search (Soulseek limitation)
- **Health Check**: Network connectivity and user status

### Metadata Providers

#### **MusicBrainz**
- **Purpose**: Authoritative music metadata database
- **Authentication**: None (rate-limited public API)
- **Features**:
  - Track/album/artist lookup
  - ISRC search
  - Release group relationships
  - Tag database
- **Rate Limit**: 1 req/sec (enforced by RequestManager)
- **Health Check**: API availability

#### **AcoustID**
- **Purpose**: Convert Chromaprint fingerprints to MusicBrainz IDs
- **Authentication**: Application API key
- **Features**:
  - Fingerprint-to-MBID lookup
  - Confidence scoring
  - Recording metadata
- **Rate Limit**: 1 req/sec (AcoustID requirement)
- **Health Check**: API availability

#### **LRClib** Not yet implemented
- **Purpose**: Synchronized lyrics database
- **Authentication**: None (public API)
- **Features**:
  - Lyric search by artist/title
  - LRC format timestamps
  - Community-submitted lyrics
- **Rate Limit**: None (adaptive)
- **Health Check**: API availability

#### **ListenBrainz** Not yet implemented
- **Purpose**: Play history tracking and statistics
- **Authentication**: User token (optional)
- **Features**:
  - Submit play events
  - Fetch user top tracks
  - Personalized statistics
- **Rate Limit**: 50 req/min (per ListenBrainz)
- **Health Check**: API availability

---

## Key Systems

### 1. **Job Queue & Scheduler**

Located in `core/job_queue.py`

**Purpose**: Background task execution with scheduling and retry logic

**Features**:
- Periodic job execution (configurable intervals)
- One-off job support
- Automatic retries with exponential backoff
- Worker thread pool (configurable concurrency)
- Duplicate job prevention (same job can't run twice simultaneously)
- Enable/disable per job (no restart required)

**Jobs Registered**:
- `auto_import_scan` (5 min interval): Scan downloads folder, identify new files, tag and move to library
- `download_manager_status` (5 min interval): Check download queue, process failed downloads
- `health_check_*` (5 min intervals): Monitor provider health and availability
- `database_update` (hourly): Clean up stale entries, update metadata
- Sync jobs: Per-provider playlist sync on user-defined schedule

**Startup Behavior**: Jobs wait for their configured interval before first run (e.g., 5-minute job waits 5 minutes before first execution)

### 2. **Matching Engine**

Located in `core/matching_engine/`

**Purpose**: Intelligent track comparison using multiple scoring strategies

**Profiles**:
- **EXACT_SYNC** (85% threshold): Strict matching for Spotify→Library
  - Text: Title (35%) + Artist (35%) + Album (10%)
  - Duration: ±3 seconds (20%)
  - Fingerprint: Not used (metadata-only)
  
- **DOWNLOAD_SEARCH** (70% threshold): Flexible matching for P2P filenames
  - Text: Title (40%) + Artist (30%) + Album (10%)
  - Duration: ±5 seconds (20%) - BS detector
  - Quality bonus: FLAC+FLAC = +5%

- **LIBRARY_IMPORT** (80% threshold): Fingerprint-primary matching
  - Fingerprint: 30%
  - Duration: ±3 seconds (30%)
  - Text: Fallback if fingerprint fails

**Scoring Features**:
- Fuzzy string matching (Levenshtein distance)
- Version/Remix detection and penalization
- ISRC (International Standard Recording Code) instant match (100%)
- Album type detection (compilation vs single artist)
- Multiple identifier support (MBID, ISRC, Spotify ID)

### 3. **Request Manager**

Located in `core/request_manager.py`

**Purpose**: Centralized HTTP client with automatic rate limiting and retries

**Features**:
- Per-provider rate limit configuration
- Automatic retry on network errors and 5xx responses
- Exponential backoff with jitter
- Session management and connection pooling
- Timeout configuration per provider

**Rate Limiting**:
- Prevents "429 Too Many Requests" errors
- Adaptive: responds to 429 by increasing backoff
- Per-provider: MusicBrainz 1 req/sec, AcoustID 1 req/sec, Spotify adaptive

### 4. **Metadata Enhancement**

Located in `services/metadata_enhancer.py`

**Purpose**: Identify and enrich audio file metadata

**Process**:
1. **Fingerprint Generation**: Chromaprint hash from audio file
2. **AcoustID Lookup**: Convert fingerprint → MusicBrainz ID
3. **Metadata Fetch**: Get authoritative metadata from MusicBrainz
4. **Fallback Search**: If AcoustID fails, search by filename
5. **Tagging**: Write metadata to file (ID3v2.4, Vorbis Comments)
6. **Review Queue**: If confidence < threshold, queue for manual review

**Confidence Scoring**:
- AcoustID exact match: 95%
- Filename search with EXACT_SYNC: Varies (typically 70-95%)
- Manual review: 0% (awaiting user decision)

### 5. **Auto-Importer**

Located in `services/auto_importer.py`

**Purpose**: Scan downloads folder and automatically organize into library

**Process**:
1. **Scan**: Watch downloads folder for new audio files
2. **Identify**: Call MetadataEnhancer to get metadata and confidence
3. **Decide**: 
   - If confidence ≥ threshold and auto-import enabled: Tag and move
   - Otherwise: Queue for manual review
4. **Move**: Organize using configurable folder template (e.g., `$albumartist/$album/$track - $title`)
5. **Cleanup**: Remove empty directories

**Concurrency Control**:
- File-level locking prevents duplicate processing
- Recent completion tracking (10-sec window) prevents race conditions
- Scan-level lock prevents concurrent scans

### 6. **Database Layer**

Located in `database/`

**Tables**:
- `tracks`: Audio files with metadata
- `albums`: Album information
- `artists`: Artist information
- `downloads`: Download queue and status
- `sync_history`: Playlist sync records
- `review_tasks`: Manual review queue
- `config`: Service credentials (encrypted)

**Features**:
- SQLite with automatic backups
- Encrypted credential storage
- Full-text search on track names
- Deduplication tracking (fingerprint-based)
- Bulk operation support

---

## Workflow

### Typical Playlist Sync Workflow

```
User initiates "Sync Spotify Playlist"
    ↓
Spotify Provider fetches playlist (limit 50 tracks/page, paginate)
    ↓
For each track in playlist:
  ├─ Check if already in Plex library (exact match)
  ├─ If not found:
  │   ├─ Search Plex with Matching Engine (EXACT_SYNC profile)
  │   ├─ If found with confidence ≥ 85%:
  │   │   └─ Mark as matched, create playlist entry
  │   └─ If not found:
  │       └─ Add to download queue
  └─ Continue
    ↓
For each download queued:
  ├─ Search Slskd for best match following quality profile
  ├─ If desired quality is available: Download
  ├─ Else: Fallback to next in line in the quality profile
  ├─ Rate limit: 1 concurrent download
  └─ Store in downloads folder
    ↓
Download Manager monitors completion:
  ├─ When file complete: Trigger auto-import
  └─ Resume failed downloads (exponential backoff)
    ↓
Auto-Importer processes downloads:
  ├─ Generate Chromaprint fingerprint
  ├─ AcoustID lookup (1 req/sec rate limit)
  ├─ Fetch metadata from MusicBrainz
  ├─ Tag file with metadata
  ├─ Move to library folder structure
  └─ Add to Plex library
    ↓
Playlist finalized with all matched tracks
```

### Manual Review Queue Workflow

```
File identified with low confidence (< 85%)
    ↓
Created ReviewTask in database with detected metadata
    ↓
User opens "Review Queue" in Web UI
    ↓
User approves/rejects each match:
  ├─ Approve: Tag file, move to library, delete ReviewTask
  ├─ Reject: Keep in review, await manual metadata input
  └─ Ignore: Delete ReviewTask, don't process again
    ↓
Approved files auto-tagged and imported
```

---

## Configuration

### config.json Structure

```json
{
  "library": {
    "root_directory": "/music",
    "folder_template": "$albumartist/$album/$track - $title"
  },
  "metadata_enhancement": {
    "enabled": true,
    "auto_import": true,
    "confidence_threshold": 85,
    "register_auto_import_on_startup": false
  },
  "download_manager": {
    "downloads_directory": "/downloads",
    "auto_import_on_download_complete": false,
    "register_job_on_startup": false
  },
  "providers": {
    "spotify": {
      "enabled": true
    },
    "plex": {
      "enabled": true,
      "url": "http://localhost:32400"
    }
  },
  "acoustid": {
    "api_key": "your_application_key_here"
  }
}
```

### Service Credentials (Encrypted)

Stored in `config.db` with encryption:
- Spotify: client_id, client_secret, refresh_token
- Plex: token
- AcoustID: api_key (application key, not user key)
- Slskd: username, password
- MusicBrainz: User-Agent header

---

## Database Schema

### Core Tables

**tracks**
- `id`: Primary key
- `file_path`: Full path to audio file
- `title`, `artist`, `album`: Metadata
- `duration`: In milliseconds
- `fingerprint`: Chromaprint hash
- `mbid`: MusicBrainz recording ID
- `isrc`: International Standard Recording Code
- `added_at`: Timestamp

**downloads**
- `id`: Primary key
- `track_id`: Foreign key to tracks
- `status`: queued|downloading|complete|failed|verified
- `source`: Spotify|Tidal|YouTube
- `quality`: FLAC|MP3_320|MP3_256|etc
- `started_at`, `completed_at`: Timestamps
- `retry_count`: Exponential backoff tracking

**review_tasks**
- `id`: Primary key
- `file_path`: Path to file awaiting review
- `detected_metadata`: JSON with identified metadata
- `confidence_score`: 0-100%
- `status`: pending|approved|ignored
- `created_at`, `updated_at`: Timestamps

**sync_history**
- `id`: Primary key
- `playlist_id`: External playlist ID
- `provider`: Spotify|Tidal|YouTube
- `last_sync`: Timestamp
- `track_count`: Tracks in playlist
- `matched_count`: Successfully matched
- `downloaded_count`: Downloaded via Slskd

---

## Advanced Features

### Deduplication Strategy

SoulSync uses **fingerprint-based deduplication** to identify identical audio:

1. **Fingerprint Generation**: Chromaprint hash of audio content
2. **Comparison**: Two files with same fingerprint = same audio
3. **Action Options**:
   - Keep both: Higher quality version preferred
   - Keep highest quality: Delete lower bitrate/format
   - Keep original: Newest import deleted
   - Manual review: User decides

### Error Handling & Resilience

**Graceful Degradation**:
- Provider connection fails → Use cached metadata
- Fingerprinting fails → Fallback to filename search
- AcoustID unavailable → Search by text
- Download fails → Retry with exponential backoff (max 3 attempts)
- Metadata incomplete → Queue for manual review

**Health Checks**:
- Every provider has 5-minute health check
- Failed checks trigger notifications and alert logs
- Disabled providers skip associated jobs
- Automatic recovery when provider comes back online

### Performance Optimizations

1. **Caching**: 
   - Track metadata cached (1-hour TTL)
   - MBID lookups cached
   - Fingerprint cache in database

2. **Batch Operations**:
   - Process multiple files concurrently (worker pool)
   - Bulk database inserts
   - Batch API requests where supported

3. **Rate Limiting**:
   - Per-provider limits prevent API bans
   - Automatic backoff on 429 responses
   - Jitter in retry intervals prevents thundering herd

---

## Future Roadmap

- [ ] Multi-user support with per-user libraries
- [ ] Direct streaming from Soulseek (without download)
- [ ] Lyric synchronization with video display
- [ ] Machine learning-based match confidence
- [ ] Recommendation engine with collaborative filtering
- [ ] Backup/restore functionality
- [ ] Mobile companion app

---

## Support & Resources

- **GitHub**: https://github.com/Nezreka/SoulSync
- **Documentation**: See `/docs` folder
- **Issues**: Report bugs on GitHub Issues
- **Configuration**: See `config.example.json`
- **Database**: SQLite3 at `config.db` or configured path
