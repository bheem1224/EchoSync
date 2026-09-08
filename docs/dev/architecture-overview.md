# EchoSync High-Level System Architecture & Technical Overview

## 1. Technical Documentation Index

Detailed architectural specifications and component guides are organized into the following topic-scoped reference manuals:

* **[Codebase Locator & Symbol Map](codebase-map.md):** Precise mapping of system responsibilities to code paths across Python, Rust, and Svelte layers.
* **[Architectural Rule Violations Ledger](rule-violations.md):** Live audit matrix of ungated I/O operations, direct DB connections, and remediations.
* **[Database Evolution & 3-DB Split](database-evolution.md):** Physical partitioning model (`config.db`, `working.db`, `library.db`), entity promotion lifecycle, and PostgreSQL migration roadmap.
* **[Native Rust FFI Engine](rust-ffi-engine.md):** `echosync_core` crate architecture, lofty tag parsing/writing, callback batching, and path traversal security.
* **[Plugin SDK Quickstart](../plugins/sdk-quickstart.md):** Developer guide for building EchoSync plugins.
* **[Plugin Hook Matrix](../plugins/hook-matrix.md):** Hook filter/action lifecycle catalog and custom element frontend integration.

---

## 2. System Overview

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

## 3. Core Subsystems & Operational Pipelines

### 3.1 Backend Orchestration & Task Manager
- Managed via `TaskManager` (`core/task_manager/task_manager.py`).
- Manages background thread pools and job scheduling without custom thread locks inside Rust FFI.

### 3.2 Native Rust FFI Engine (`echosync_core`)
- High-speed directory traversal (`walkdir` in `src/file_handling/scanner.rs`).
- Audio tagging reading/writing strictly via `lofty` in `src/metadata/extractor.rs` and `writer.rs`.
- Zero-trust safe file operations (`safe_move_file`, `copy_file`, `delete_file` in `src/file_handling/fs_ops.rs`).
- Detailed specification: **[rust-ffi-engine.md](rust-ffi-engine.md)**.

### 3.3 Nexus Plugin Framework & Sandbox Security
- Zero-trust execution boundary for community plugins (`core/nexus_framework/`).
- Enforces AST checks (`PluginSecurityScanner`) and path traversal sandboxing.
- Serves dynamic UI extensions as Svelte Web Components (`customElement: true`).

### 3.4 Three-Database Data Architecture
- Isolated database files (`config.db`, `working.db`, `library.db`) enforcing strict separation between credentials, ephemeral task states, and the canonical music entity graph.
- Detailed specification: **[database-evolution.md](database-evolution.md)**.

### 3.5 Event Bus & Lightweight Identity Dispatch
- Event dispatcher located in `core/event_bus.py`.
- Modern API (`EventBus.publish(payload)`) transmits lightweight entity identifiers (`sync_id`, `media_id`), avoiding monolithic serialized track payloads.
- State serialization is performed before queueing to prevent race conditions.

### 3.6 Matching & Suggestion Pipelines
- Tier 1 weighted metadata scoring (`WeightedMatchingEngine`) combined with Tier 2 exact title + strict duration fallback.
- Chromaprint fingerprinting via `FingerprintService` (`core/matching_engine/fingerprinting.py`).
- Automated suggestion engine and vibe profiling (`core/suggestion_engine/`).

### 3.7 Ingestion & Download Lifecycle
- Auto-importer monitoring (`core/auto_importer.py`) and retroactive metadata enrichment (`services/metadata_enhancer.py`).
- Candidate evaluation state machine and fallback waterfalls in `services/download_manager.py`.
