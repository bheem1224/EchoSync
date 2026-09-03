# EchoSync High-Level System Architecture

## 1. System Overview

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

## 2. Core Subsystems

### 2.1 Backend Orchestration & Task Manager
- Managed via `TaskManager` (`core/task_manager/task_manager.py`).
- Manages background thread pools and job scheduling without custom locks inside Rust FFI.

### 2.2 Native Rust FFI Engine (`echosync_core`)
- High-speed directory traversal (`walkdir`).
- Audio tagging and Chromaprint extraction via `lofty`.
- Zero-trust safe file operations (`safe_move_file`, `delete_file`).

### 2.3 Nexus Plugin Framework & AST Sandbox
- Zero-trust execution boundary for community plugins.
- Restricts direct OS/file calls via `PluginSecurityScanner`.
- Serves dynamic UI extensions as Svelte Web Components.

### 2.4 Three-Database Data Architecture
- Isolated database files (`config.db`, `working.db`, `library.db`) enforcing separation of secrets, ephemeral jobs, and canonical media graphs.
