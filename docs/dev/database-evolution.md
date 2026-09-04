# Three-Database Partitioning & Database Evolution

## 1. Architectural Principles of the 3-Database Split

EchoSync enforces strict separation of operational state, system settings, and user library data across three dedicated SQLite databases (backed by Write-Ahead Logging for concurrency). This design isolates ephemeral task churn from pristine library metadata and security credentials.

```text
+-----------------------------------------------------------------------------------+
|                                 EchoSync System                                  |
+--------------------------+--------------------------+-----------------------------+
                           |                          |
                           v                          v
             +---------------------------+  +---------------------------+
             |         config.db         |  |        working.db         |
             |                           |  |                           |
             | - Read-heavy settings     |  | - High-churn task states  |
             | - Encrypted tokens/keys   |  | - Ingestion staging queue |
             | - Installed plugin specs  |  | - Virtual track cache     |
             +---------------------------+  +---------------------------+
                                                      |
                                                      | Promotion via
                                                      | Acquisition Bridge
                                                      v
                                            +---------------------------+
                                            |        library.db         |
                                            |                           |
                                            | - Canonical track graph   |
                                            | - Physical media files    |
                                            | - Virtual media mappings  |
                                            +---------------------------+
```

### Database Responsibilities

1. **`config.db` (System Configuration & Credentials)**
   - Holds system settings, user accounts, authentication hashes, provider configuration, and encrypted API credentials (OAuth tokens, Fernet-encrypted keys).
   - Serves as a read-heavy, low-churn database.

2. **`working.db` (Ephemeral Tasks & Virtual Ingestion)**
   - Houses high-frequency task state, background job queues, review items, temporary scan buffers, and the `VirtualTrackCache`.
   - Isolate high write operations (WAL checkpoints, temp allocations) here so that file system lock contention does not block library reads.

3. **`library.db` (Canonical Entity Graph)**
   - Holds the pristine ground-truth music library graph: canonical compositions (`CanonicalTrack`), physical media on disk (`PhysicalMedia`), and remote virtual media links (`VirtualMedia`).
   - Read-heavy, ACID-compliant core domain graph.

---

## 2. Entity Model: 1:N Track-to-Media Relationship

EchoSync decouples abstract musical compositions from specific media instances on disk or remote servers:

```text
                        +----------------------+
                        |    CanonicalTrack    |
                        |                      |
                        | - id (UUID/Integer)  |
                        | - title              |
                        | - artist_name        |
                        | - album_name         |
                        | - mbid / isrc        |
                        +----------+-----------+
                                   |
           +-----------------------+-----------------------+
           | 1                                             | 1
           v N                                             v N
+----------------------+                        +----------------------+
|    PhysicalMedia     |                        |     VirtualMedia     |
|                      |                        |                      |
| - id                 |                        | - id                 |
| - track_id (FK)      |                        | - track_id (FK)      |
| - file_path          |                        | - provider_id        |
| - bit_rate           |                        | - external_id        |
| - format (FLAC/MP3)  |                        | - streaming_url      |
+----------------------+                        +----------------------+
```

- **`CanonicalTrack`**: The immutable musical entity representing a song.
- **`PhysicalMedia`**: A concrete file existing on local storage (e.g., `/data/library/Artist/Album/01-Track.flac`). One `CanonicalTrack` can have multiple physical media files (e.g. FLAC lossless edition vs MP3 mobile edition).
- **`VirtualMedia`**: A remote media reference on third-party services (Plex, Spotify, Tidal).

---

## 3. Acquisition Bridge & Dual-Session Entity Promotion

When a track exists only virtually (or in `VirtualTrackCache` in `working.db`) and is subsequently acquired/downloaded to local storage, it undergoes **Entity Promotion**:

1. A background worker opens a `working_session` on `working.db` and a `library_session` on `library.db`.
2. The virtual entry attributes are read from `working.db`.
3. A `CanonicalTrack` (if not already existing) and a linked `PhysicalMedia` record are constructed and inserted into `library.db` using native SQLAlchemy ORM operations within a single `library_session.begin()` transaction.
4. Upon successful commit in `library.db`, the ephemeral record in `working.db` is purged.

---

## 4. PostgreSQL Migration Roadmap

While zero-config SQLite WAL is the default out-of-the-box engine, EchoSync's SQLAlchemy 2.0 Repository layer is structured to support seamless migration to multi-tenant PostgreSQL for enterprise scale:

- **Schema Abstraction:** Models utilize standard SQLAlchemy types (`String`, `Integer`, `DateTime`, `JSON`).
- **Query Guidelines:** Standard SQL statements avoiding SQLite-specific syntax (e.g., check for multi-column `IN` support, which uses `or_(*[and_(...)])` constructs on SQLite but compiles natively on PostgreSQL).
- **Target Architecture:** In PostgreSQL deployments, `config`, `working`, and `library` schemas reside in separate database schemas (`config.*`, `working.*`, `library.*`) on a single PostgreSQL cluster.
