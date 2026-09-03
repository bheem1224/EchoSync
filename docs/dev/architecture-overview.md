# EchoSync High-Level System Architecture

## 1. Technical Documentation Index

Detailed architectural specifications are organized into the following topic-scoped reference manuals:

* **[Codebase Locator & Symbol Map](codebase-map.md):** Precise mapping of system responsibilities to code paths across Python, Rust, and Svelte layers.
* **[API Reference Specification](api-reference.md):** Complete REST endpoint paths, payload contracts, parameters, and HTTP response codes.
* **[Event Bus Dictionary](event-bus.md):** Asynchronous channel dictionary, event schemas, and lightweight UUID event payload models.
* **[Matching & Suggestion Engines](matching-and-suggestions.md):** Mathematical scoring formulas, fuzzy text matching algorithms, vibe vector profiler, and automated library pruning.
* **[Download Lifecycle & Metadata Pipeline](download-pipeline.md):** Candidate ranking state machine, waterfall metadata resolution, and stream integrity verification.
* **[Database Evolution & 3-DB Split](database-evolution.md):** Physical partitioning model (`config.db`, `working.db`, `library.db`), entity promotion lifecycle, and PostgreSQL migration roadmap.
* **[Native Rust FFI Engine](rust-ffi-engine.md):** `echosync_core` crate architecture, lofty tag parsing/writing, callback batching, and path traversal security.
* **[Architectural Rule Violations Ledger](rule-violations.md):** Live audit matrix of ungated I/O operations, direct DB connections, and remediations.

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
- Isolated database files (`config.db`, `working.db`, `library.db`) enforcing separation of secrets, ephemeral jobs, and canonical media graphs.
- Detailed specification: **[database-evolution.md](database-evolution.md)**.
