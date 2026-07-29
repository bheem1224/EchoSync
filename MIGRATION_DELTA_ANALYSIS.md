# EchoSync: Rust PyO3 Ingestion Pipeline Migration Analysis

## 1. Database Schema Audit & Multi-Database Concurrency

### Current Architecture Assessment
The current implementation splits databases correctly using native SQLAlchemy `sessionmaker` scopes, with `working_database.py` and `music_database.py` (representing `library.db`).
Additionally, `database/engine.py` implements a bespoke multi-threaded DB queueing class (`_DBWriter`) for concurrent write ingestion using SQLite WAL mode.

**Issue/Delta:** The legacy `_DBWriter` in `engine.py` is actively routing queries via manual `queue.Queue` threads, abstracting away SQLAlchemy's built-in session handlers in some places. Moving to the high-throughput Rust engine means this Python-level queueing bottleneck must be bypassed. Rust will emit bulk kwargs, and we must inject those via standard SQLAlchemy 2.0 Core `insert().on_conflict_do_update()` statements.

### 3-Database Strict Routing
- `config.db`: Handled by `database/models.py` (Service, ServiceConfig).
- `working.db`: Handled by `database/working_database.py` (Job Queues, Transient state, and our target `virtual_track_cache`).
- `library.db`: Handled by `database/music_database.py` (Tracks, Artists, LocalMedia).

**Migration Action:** Do NOT touch `database/models.py` or `music_database.py`. The models are perfectly suited to accept raw dictionary kwargs from Rust.

## 2. The `virtual_track_cache` Schema Implementation

Currently, `music_database.py` accounts for virtual media via string parsing (`~LocalMedia.file_path.startswith('virtual://')`), which pollutes the canonical graph. We will introduce a new model into `working.db` (via `working_database.py`) to isolate this.

**Delta Schema (working_database.py):**
```python
class VirtualTrackCache(WorkingBase):
    __tablename__ = "virtual_track_cache"
    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(nullable=False, index=True) # CRC32 of provider
    external_uri: Mapped[str] = mapped_column(String, nullable=False, index=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utc_now)
```
*When a virtual track is successfully acquired as physical media, it is dropped from this table and inserted into `library.db` as `Track` + `LocalMedia`.*

## 3. Rust PyO3 Boundary & Python Mapping (Zero-Overhead)

To avoid Pydantic serialization overhead, the Rust `echosync_core` extension will return standard dictionaries that map *exactly* to the SQLAlchemy models.

### Rust Minimal Interface Map
```python
from typing import TypedDict, List

class RawTrackMetadata(TypedDict):
    title: str
    artist_name: str
    album_title: str
    duration: float
    track_number: int
    disc_number: int
    bitrate: int
    file_path: str
    file_format: str
    file_size_bytes: int

class TrackTagPayload(TypedDict):
    file_path: str
    tags: dict[str, str]

# Rust Interface Definition
def scan_directory(path: str) -> List[RawTrackMetadata]: ...
def extract_tags_batch(paths: List[str]) -> List[TrackTagPayload]: ...
```

### Python Bulk Ingestion Core Loop
Replacing `database_update_worker.py` logic:
```python
import echosync_core
from database.music_database import music_session_registry, Track, LocalMedia
from sqlalchemy.dialects.sqlite import insert

def ingest_directory(directory_path: str):
    # 1. Rust engine multi-threaded walk (takes ~1-2s for 50k files)
    scanned_payloads = echosync_core.scan_directory(directory_path)

    # 2. Extract into DB kwarg dictionaries
    with music_session_registry() as session:
        for chunk in chunked(scanned_payloads, 1000):
            # 3. Direct Core Bulk Insert / Upsert bypassing the ORM overhead
            # We map the dicts directly into the insert statement
            stmt = insert(Track).values(chunk)
            # ... resolve conflicts, then link LocalMedia
            session.execute(stmt)
        session.commit()
```

## 4. Minimal Code Change Roadmap (Non-Destructive)

1. **Rust Scaffold:** Add PyO3/Maturin build pipeline to `pyproject.toml` and write the Rust `scan_directory` function.
2. **Virtual Isolation:** Add `VirtualTrackCache` to `working_database.py` and remove `virtual://` file path checks from `music_database.py`.
3. **Deprecate Queue Threading:** Phase out the `_DBWriter` in `engine.py` as Rust will provide batched payloads that can utilize native bulk `execute` natively, negating Python-side queue locks.
4. **Swap Worker:** Replace the sequential ingestion loops in `core/database_update_worker.py` with `echosync_core.scan_directory()`, passing the raw PyDict results directly into `sqlalchemy.insert()`. Existing API routes querying `library.db` will remain entirely unbroken.
