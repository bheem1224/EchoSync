# EchoSync High-Level System Architecture

## 1. Technical Documentation Index

Detailed architectural specifications are organized into the following topic-scoped reference manuals in the developer wiki hierarchy:

* **[Codebase Locator & Symbol Map](codebase-map.md):** Directory responsibility map, comprehensive REST API endpoint paths, and symbol lookup index across Python, Rust, and Svelte layers.
* **[Database Evolution & Partitioning](database-evolution.md):** Physical partitioning model (`config.db`, `working.db`, `music_library.db`), entity promotion lifecycle (`VirtualTrackCache` -> `Track` + `LocalMedia`), 1:N relations, and PostgreSQL migration roadmap.
* **[Metadata Enhancement Subsystem](metadata-enhancement-architecture.md):** Comprehensive audit of all metadata enhancement callers, 5-stage cascading decision tree, download manager lifecycle, matching scoring formulas, AcoustID/Picard divergence, and strategy skip hooks.
* **[Native Rust FFI Engine](rust-ffi-engine.md):** `echosync_core` crate architecture, PyO3 bindings, lofty tag parsing/writing, callback batching, and path traversal security.
* **[Architectural Invariant Violation Ledger](rule-violations.md):** Live audit matrix of ungated I/O operations, direct DB connections, rogue HTTP clients, and remediation strategies.

---

## 2. System Overview

EchoSync is an asynchronous hybrid monolith built on **Python 3.12 (FastAPI / SQLAlchemy 2.0)** and **Rust (`echosync_core` PyO3 extension compiled via Maturin)**, paired with a decoupled **SvelteKit 2 SPA host interface**.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           SvelteKit 2 SPA UI                            │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ REST API / SSE
┌────────────────────────────────────▼────────────────────────────────────┐
│                         FastAPI Web Controllers                         │
│                    (web/routes/ & api/routers/)                         │
└──────────┬─────────────────────────┬──────────────────────────┬─────────┘
           │                         │                          │
┌──────────▼──────────────┐ ┌────────▼───────────────┐ ┌────────▼─────────┐
│    Orchestration &      │ │ Zero-Trust I/O         │ │  Nexus Plugin   │
│   Background Services   │ │ Gatekeeper             │ │   Framework     │
│ (services/ & core/)     │ │ (core/io_gatekeeper)   │ │ (core/nexus_fw) │
└──────────┬──────────────┘ └────────┬───────────────┘ └────────┬────────┘
           │                         │ PyO3 FFI                 │
           │                ┌────────▼───────────────┐          │
           │                │    echosync_core       │          │
           │                │     (Native Rust)      │          │
           │                └────────────────────────┘          │
┌──────────▼────────────────────────────────────────────────────▼─────────┐
│                      SQLAlchemy 2.0 ORM Engines                         │
│             [config.db]      [working.db]   [music_library.db]          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Subsystems

### 3.1 Backend Orchestration & Task Manager
- Managed via `TaskManager` (`core/task_manager/task_manager.py`).
- Manages background thread pools and job scheduling without custom locks inside Rust FFI.

### 3.2 Native Rust FFI Engine (`echosync_core`)
- High-speed directory traversal (`walkdir` in `src/file_handling/scanner.rs`).
- Audio tagging reading/writing via `lofty` in `src/metadata/extractor.rs` and `writer.rs`.
- Zero-trust safe file operations (`safe_move_file`, `delete_file` in `src/file_handling/fs_ops.rs`).
- Detailed specification: **[rust-ffi-engine.md](rust-ffi-engine.md)**.

### 3.3 Nexus Plugin Framework & AST Sandbox
- Zero-trust execution boundary for community plugins (`core/nexus_framework/`).
- Restricts direct OS/file calls via `PluginSecurityScanner`.
- Serves dynamic UI extensions as Svelte Web Components.
- Plugin specifications: **[docs/plugins/sdk-quickstart.md](../plugins/sdk-quickstart.md)** and **[docs/plugins/sandbox-security.md](../plugins/sandbox-security.md)**.

### 3.4 Three-Database Data Architecture
- Isolated database files (`config.db`, `working.db`, `music_library.db`) enforcing separation of secrets, ephemeral jobs, and canonical media graphs.
- Detailed specification: **[database-evolution.md](database-evolution.md)**.

---

## 4. Asynchronous Event Bus Architecture

The core event bus (`core/event_bus.py`) coordinates decoupled system actions using lightweight entity identifiers (`sync_id`, `media_id`, `job_name`) rather than monolithic serialized track dictionaries.

### 4.1 Dispatching Paradigm

1. **Lightweight Modern Dispatch:** `EventBus.publish(payload_dict)`
   - Dispatched immediately in caller thread to subscribers registered via `event_bus.subscribe("EVENT_NAME", handler)`.
   - Event state is frozen during dispatch to prevent race conditions.

2. **Legacy Streaming Channel Dispatch:** `EventBus.publish(channel, event_type, data)`
   - Buffers events in per-channel queues for polling via `event_bus.get_events(channel, since_id)` (e.g., UI playlist sync status).

### 4.2 Standard System Event Payloads

#### `DOWNLOAD_INTENT`
Published by `services/sync_service.py` when missing tracks are discovered during sync. Consumed by `DownloadManager._on_download_intent()`.

```json
{
  "event": "DOWNLOAD_INTENT",
  "sync_id": "spotify:track:4iV5W9uYEdYUVa79Axb7v0",
  "duration_ms": 214000,
  "isrc": "USRC17607839",
  "timestamp": "2026-05-27T19:00:00Z",
  "source": "playlist_sync"
}
```

#### `TRACK_IMPORTED`
Published by `services/library_watcher.py` when a file is ingested into local storage. Cancels matching pending downloads in `DownloadManager`.

```json
{
  "event": "TRACK_IMPORTED",
  "track": {
    "title": "Midnight City",
    "artist_name": "M83",
    "album_title": "Hurry Up, We're Dreaming",
    "duration_ms": 243000,
    "isrc": "FR6V81100021",
    "file_path": "/music/M83/Hurry Up, We're Dreaming/01 Midnight City.flac",
    "source": "local_server"
  }
}
```

#### `TRACK_RATED` / `TRACK_PLAYED`
Published by webhook parsers (`core/webhook_parsers.py`) when media servers record plays/ratings. Consumed by `services/state_listener.py` and suggestion profilers.

```json
{
  "event": "TRACK_RATED",
  "sync_id": "sync_991823",
  "data": {
    "rating": 5.0,
    "user_id": "admin",
    "provider": "plex",
    "provider_item_id": "109823"
  }
}
```

#### Lifecycle & Feedback Intents
- `HARD_DELETE_INTENT`: Dispatched by `core/suggestion_engine/deletion.py` upon automated track removal.
- `QUALITY_UPGRADE_INTENT`: Dispatched when low-bitrate media is staged for replacement.
- `PREFERENCE_MODEL_FEEDBACK`: Transmits consensus score feedback into the user vibe model.
