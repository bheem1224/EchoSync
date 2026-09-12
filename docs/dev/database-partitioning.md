# Three-Database Partitioning Architecture

## 1. Overview & Rationale

To eliminate SQLite lock contention during concurrent high-throughput local library scans, background job processing, and web API requests, EchoSync enforces a strict **3-Database Partitioning Model**. System state is segregated across three independent SQLite databases operating in WAL (Write-Ahead Logging) mode.

---

## 2. Database Partitioning Scope

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │                              EchoSync App                              │
 └───────────┬──────────────────────────┬──────────────────────┬──────────┘
             │                          │                      │
             ▼                          ▼                      ▼
   ┌──────────────────┐       ┌──────────────────┐   ┌──────────────────┐
   │    config.db     │       │    working.db    │   │    library.db    │
   └──────────────────┘       └──────────────────┘   └──────────────────┘
   • System Settings          • Ephemeral Queues     • Canonical Track
   • Encrypted Credentials    • Metadata Staging       Graph
   • OAuth Tokens             • Ingestion Buffers    • Physical Media
   • Plugin Manifests         • Telemetry / SSE      • Virtual Media
                              • Virtual Track Cache  • Artist / Album Graph
```

### 1. `config.db` (Configuration & Credentials)
- **Characteristics:** Read-heavy, extremely low-churn write workload.
- **Contents:** Application settings, encrypted service API keys, OAuth tokens, user preferences, plugin installation state.
- **Security:** Credential fields are encrypted using Fernet symmetric key encryption (derived from `MASTER_KEY`).

### 2. `working.db` (Ephemeral State & Acquisition Bridge)
- **Characteristics:** High-churn, write-heavy, ephemeral storage.
- **Contents:** Task manager queues, ingestion buffers, review queue tasks, active job states, and `virtual_track_cache`.
- **Isolation:** Virtual tracks from external providers remain isolated in `working.db` until physical acquisition occurs.

### 3. `library.db` (Canonical Music Graph)
- **Characteristics:** Search-optimized, structured relational audio graph.
- **Contents:** `CanonicalTrack`, `PhysicalMedia` (local audio files), `VirtualMedia` (remote streaming links), `Artist`, `Album`, and playlist relationships.
- **Invariant:** Direct SQLite connections are strictly forbidden; all interactions must use `DatabaseGateway` scoped ORM sessions.

---

## 3. DatabaseGateway & Scoped Session Context

All database interactions must route through `DatabaseGateway` using the `session_scope()` context manager to guarantee proper commits, rollbacks, and connection cleanup.

### Session Scope Usage Pattern
```python
from database.database_gateway import DatabaseGateway

# Example: Operating within the library database scope
with DatabaseGateway.library_session() as session:
    tracks = session.query(CanonicalTrack).filter_by(artist="Daft Punk").all()
    # Automatic commit on context exit, rollback on exception
```

---

## 4. Acquisition Bridge: Promotion Pattern

When an ephemeral virtual track in `working.db` is physically downloaded and tagged:

1. A dual-session handler opens both `working_session` and `library_session`.
2. Reads track details from `virtual_track_cache` in `working.db`.
3. Constructs the `CanonicalTrack` and `PhysicalMedia` records in `library.db`.
4. Removes or marks the item as promoted in `working.db` within an atomic transaction.
