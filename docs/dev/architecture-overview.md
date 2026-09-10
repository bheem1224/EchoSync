# EchoSync High-Level System Architecture

## 1. Technical Documentation Index

Detailed architectural specifications are organized into the following topic-scoped reference manuals:

* **[Codebase Locator & Symbol Map](codebase-map.md):** Precise mapping of system responsibilities to code paths across Python, Rust, and Svelte layers.
* **[Architectural Rule Violations Ledger](rule-violations.md):** Audit matrix of ungated I/O operations, direct DB connections, rogue HTTP clients, and remediations.
* **[Database Partitioning Model & Evolution](database-evolution.md):** Physical partitioning model (`config.db`, `working.db`, `library.db`), entity promotion lifecycle, and PostgreSQL migration roadmap.
* **[Metadata Enhancement, Matching Engine & Download Pipeline](metadata-enhancement-architecture.md):** Comprehensive audit of metadata enhancement ingress, cascading 5-stage decision tree, weighted text matching, candidate ranking, download state machine, and rate limiting.
* **[Native Rust FFI Engine](rust-ffi-engine.md):** `echosync_core` crate architecture, lofty tag parsing/writing, callback batching, and path traversal security.

---

## 2. System Overview & Monolith Topology

EchoSync is an asynchronous hybrid monolith built on **Python 3.12 (FastAPI / SQLAlchemy 2.0)** and **Rust (`echosync_core` via PyO3)**, paired with a decoupled **SvelteKit 2 SPA host interface**.

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
│             [config.db]      [working.db]      [library.db]             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Subsystems

### 3.1 Backend Orchestration & Task Manager
- Managed via `TaskManager` (`core/task_manager/task_manager.py`).
- Executes background thread pools and job scheduling. Concurrency locks belong strictly to Python's `TaskManager`; Rust FFI functions run synchronously inside thread pool allocations granted by `TaskManager`.

### 3.2 Native Rust FFI Engine (`echosync_core`)
- High-speed directory traversal (`walkdir` in `src/file_handling/scanner.rs`).
- Audio tagging reading/writing via `lofty` in `src/metadata/extractor.rs` and `writer.rs`.
- Zero-trust safe file operations (`safe_move_file`, `delete_file` in `src/file_handling/fs_ops.rs`).
- Detailed specification: **[rust-ffi-engine.md](rust-ffi-engine.md)**.

### 3.3 Nexus Plugin Framework & AST Sandbox
- Zero-trust execution boundary for community plugins (`core/nexus_framework/`).
- Restricts direct OS/file calls via `PluginSecurityScanner`.
- Serves dynamic UI extensions as Svelte Web Components (`DynamicPluginLoader.svelte`).
- Plugin specifications: **[docs/plugins/sdk-quickstart.md](../plugins/sdk-quickstart.md)** and **[docs/plugins/sandbox-security.md](../plugins/sandbox-security.md)**.

### 3.4 Three-Database Data Architecture
- Isolated database files (`config.db`, `working.db`, `library.db`) enforcing separation of secrets, ephemeral jobs, and canonical media graphs.
- Detailed specification: **[database-evolution.md](database-evolution.md)**.

### 3.5 Asynchronous Event Bus (`core/event_bus.py`)
- Distributes internal system events (`TRACK_IMPORTED`, `DOWNLOAD_INTENT`, `job_progress`) across background services and SSE endpoints.
- Event payloads carry lightweight identifiers (`sync_id`, `media_id`, `job_name`), avoiding serialized track dictionaries. State is frozen before enqueueing to prevent race conditions.
