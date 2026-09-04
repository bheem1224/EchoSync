# Database Partitioning Model & Evolution Roadmap

## 1. Executive Summary & Architectural Intent

EchoSync implements a strict **Three-Database Split Architecture** to prevent database locks, isolate high-churn ephemeral I/O from long-term canonical media graphs, and protect sensitive authentication credentials.

The three isolated database domains are:
1. `config.db` — System configuration, credentials, and encrypted tokens.
2. `working.db` — Ephemeral task states, download queues, and ingestion staging.
3. `library.db` (`music.db`) — Pristine canonical music entity graph and local media bindings.

---

## 2. Three-Database Scope Split

```
                         ┌───────────────────────────────────┐
                         │       EchoSync Core Engine        │
                         └─┬───────────────┬───────────────┬─┘
                           │               │               │
            ┌──────────────▼──────┐ ┌──────▼─────────────┐ ┌▼───────────────────┐
            │      config.db      │ │     working.db     │ │    library.db     │
            ├─────────────────────┤ ├────────────────────┤ ├───────────────────┤
            │ • System Settings   │ │ • Job Queues       │ │ • Canonical Tracks│
            │ • Encrypted Tokens  │ │ • VirtualCache     │ │ • Artists & Albums│
            │ • Service Configs   │ │ • Review Tasks     │ │ • Physical Media  │
            │ • Quality Profiles  │ │ • Playback History │ │ • Audio Fingerpr. │
            └─────────────────────┘ └────────────────────┘ └───────────────────┘
```

### 2.1 `config.db`
- **Primary Responsibility:** Persistent application settings, service credentials, OAuth tokens, and system quality profiles.
- **Access Pattern:** Read-heavy, write-infrequent. Encrypted at rest via Fernet keys derived from `MASTER_KEY`.
- **Key Tables:**
  - `system_settings`: Key-value pairs for core operational parameters.
  - `services` & `service_configs`: Third-party integration configurations (Plex, Slskd, Spotify, etc.).
  - `account_tokens`: Encrypted OAuth and auth tokens.
  - `quality_profiles` & `quality_profile_steps`: Rule sets for audio acquisition formats (FLAC vs MP3).
  - `plugin_snapshots` & `ui_components`: Installed plugin metadata and registered UI extensions.

### 2.2 `working.db`
- **Primary Responsibility:** High-churn ephemeral task execution, ingestion staging, and user interaction logs.
- **Access Pattern:** High write velocity, frequent row insertions and deletions. Operating strictly under SQLite Write-Ahead Logging (WAL) mode.
- **Key Tables:**
  - `virtual_track_cache`: Temporary storage for unacquired or virtual track metadata discovered during remote provider scans. Mirrors column structure of `Track` for 1:1 migration.
  - `download_queue`: Active, pending, and failed download tasks.
  - `review_tasks`: Ambiguous metadata matches awaiting user confirmation.
  - `playback_history`: Real-time streaming and scrobble logs.
  - `user_ratings` & `suggestion_staging_queue`: Ephemeral input data for the Suggestion Engine.

### 2.3 `library.db` (`music.db`)
- **Primary Responsibility:** Canonical ground-truth music graph and physical file mappings.
- **Access Pattern:** Heavy relational queries, index-optimized reads, batched transactional upserts.
- **Key Tables:**
  - `artists`: Canonical music artists with MBID pointers.
  - `albums`: Albums, releases, release dates, and artwork references.
  - `tracks`: Canonical musical compositions (`CanonicalTrack`).
  - `local_media`: Physical media files on disk bound 1:N to canonical tracks.
  - `audio_fingerprints`: Chromaprint audio fingerprint hashes.
  - `external_identifiers`: External provider references (ISRC, MBID, Spotify ID, Plex Key).

---

## 3. Relational Entity Architecture (1:N Physical Media Mapping)

A foundational invariant of EchoSync is the separation between the **abstract musical composition** (`Track`) and its **concrete physical manifestations** (`LocalMedia`).

```
                    ┌─────────────────────────┐
                    │      Track (ORM)        │
                    │  (Canonical Composition)│
                    └────────────┬────────────┘
                                 │
                   ┌─────────────┴─────────────┐ 1:N Relationship
                   │                           │
        ┌──────────▼───────────┐    ┌──────────▼───────────┐
        │  LocalMedia #1       │    │  LocalMedia #2       │
        │  (24-bit / 96kHz FLAC│    │  (320kbps MP3        │
        │   Main Library)      │    │   Mobile Sync)       │
        └──────────────────────┘    └──────────────────────┘
```

### Entity Definition Matrix

| Entity | Class Name | Table | Description |
| :--- | :--- | :--- | :--- |
| Canonical Composition | `Track` | `tracks` | Represents the abstract song (title, duration, MusicBrainz ID, ISRC, lyrics). |
| Physical Media File | `LocalMedia` | `local_media` | Represents a concrete audio file on the local disk (file path, file size, codec, bit rate, sample rate, file hash). |
| Artist Binding | `TrackArtist` | `track_artists` | Junction table handling primary, featured, and remix artist relationships. |
| External Identifier | `ExternalIdentifier` | `external_identifiers` | Scoped provider keys stored with raw JSON metadata payload in `raw_data`. |

### Cross-Database Entity Promotion Workflow

When a track is searched or imported, it originates in `working.db` as a `VirtualTrackCache` entry. Once acquired physically or confirmed by the user, an atomic dual-session handler promotes it:

1. **Read Phase (`working_session`):** Read `VirtualTrackCache` metadata from `working.db`.
2. **Canonical Insertion Phase (`library_session`):**
   - Query or create canonical `Artist` and `Album` records in `library.db`.
   - Insert canonical `Track` record into `library.db`.
   - Gatekeeper moves physical audio file into target storage root.
   - Insert `LocalMedia` record bound to `track_id` in `library.db`.
3. **Purge Phase (`working_session`):** Delete `VirtualTrackCache` row upon commit.

---

## 4. PostgreSQL Migration Roadmap

While SQLite with WAL mode is the default zero-config storage engine, the repository pattern (`TrackRepository`, `DatabaseGateway`) is engineered to support seamless transition to PostgreSQL for enterprise and multi-node setups.

### Migration Milestones

1. **Repository Abstraction Guardrail:**
   - Eliminate all direct `sqlite3.connect()` calls (documented in `rule-violations.md`).
   - Standardize on SQLAlchemy 2.0 async sessions (`AsyncSession`) and explicit `session_scope()`.
2. **Dialect-Agnostic Type Handlers:**
   - Replace SQLite-specific `JSON` text fallbacks with standard `sqlalchemy.types.JSON`.
   - Replace manual `or_` tuple matching loops with dialect-aware `tuple_in()` generation for PostgreSQL while retaining `or_` chunking for SQLite.
3. **Multi-Database Connection Pooling:**
   - Configure PostgreSQL schema separation (`config`, `working`, `library`) or isolated database endpoints via environment variables (`POSTGRES_CONFIG_URL`, `POSTGRES_WORKING_URL`, `POSTGRES_LIBRARY_URL`).
