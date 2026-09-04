# EchoSync Core Architecture Overview

## 1. System Topology & Hybrid Architecture

EchoSync is an enterprise-grade music synchronization, acquisition, and management server designed for self-hosted home labs. It operates as a **hybrid monolith** running inside a single containerized environment, combining high-level orchestration in Python with extreme-performance native execution in Rust via PyO3 FFI.

```text
                               +---------------------------------------+
                               |     SvelteKit 2 SPA / Web UI          |
                               +-------------------+-------------------+
                                                   | HTTP / REST / SSE
                                                   v
+--------------------------------------------------------------------------------------------------+
| Python Runtime (FastAPI Engine)                                                                  |
|                                                                                                  |
|  +------------------------+   +-------------------------+   +----------------------------------+ |
|  | Route Controllers      |   | Background Services     |   | Nexus Plugin Framework           | |
|  | - web/routes/*         |   | - LibrarySyncService    |   | - PluginLoader & SDK             | |
|  | - api/routers/*        |   | - MetadataEnhancer      |   | - HookManager & EventBus         | |
|  +-----------+------------+   +------------+------------+   +----------------+-----------------+ |
|              |                             |                             |                       |
|              +-----------------------------+-----------------------------+                       |
|                                            |                                                     |
|                                            v                                                     |
|                               +-------------------------+                                        |
|                               |  I/O Gatekeeper         |                                        |
|                               |  (core/io_gatekeeper)   |                                        |
|                               +------------+------------+                                        |
|                                            | PyO3 FFI                                            |
+--------------------------------------------|-----------------------------------------------------+
                                             v
+--------------------------------------------------------------------------------------------------+
| Rust Core Engine (`echosync_core` Crate)                                                         |
|                                                                                                  |
|  +------------------------+   +-------------------------+   +----------------------------------+ |
|  | Native FS Operations   |   | Metadata Tagging        |   | Ephemeral Cache DB               | |
|  | - safe_move_file       |   | - lofty crate extractor |   | - rusqlite (working.db reader)   | |
|  | - walkdir scanner      |   | - ID3/FLAC/MP4 writer   |   | - zero-copy Dict builder         | |
|  +------------------------+   +-------------------------+   +----------------------------------+ |
+--------------------------------------------------------------------------------------------------+
```

---

## 2. Layer Responsibilities

### Frontend Layer (`webui/`)
- Built with **SvelteKit 2** and **Svelte 5** compiled as a Single Page Application (SPA).
- Communicates with the backend using REST APIs and Server-Sent Events (SSE) for real-time progress streaming.
- Dynamically loads plugin UI components compiled as Web Components (`customElement: true`) via `DynamicPluginLoader.svelte`.

### Application & Routing Layer (`web/routes/`, `api/routers/`)
- **FastAPI / Starlette** controllers handling REST endpoints, auth, webhook ingress, metadata review, and job scheduling.
- Implements strict response contracts: returns raw integer metrics (e.g. seconds for durations) while delegating humanization and formatting to the Svelte frontend.

### Service & Workflow Layer (`services/`)
- Asynchronous background workers executing business workflows:
  - `library_sync_service.py`: Discovers new files and orchestrates library updates.
  - `download_manager.py`: Interacts with download clients (e.g. Slskd) and manages staging.
  - `metadata_enhancer.py`: Executes multi-tier identification (MBID, ISRC, Chromaprint, text match).
  - `suggestion_engine/`: Computes user vibe profiles and recommends tracks.

### Storage & Database Layer (`database/`, `core/database/`)
- Enforces a strict **Three-Database Split**:
  - `config.db`: Read-heavy system configuration, credentials, and API provider keys.
  - `working.db`: High-churn ephemeral task state, ingestion buffers, and review queues.
  - `library.db`: Canonical entity graph (`CanonicalTrack`, `PhysicalMedia`, `VirtualMedia`).
- Managed exclusively by Python via **SQLAlchemy 2.0 ORM** with Repository patterns.

### Native Execution Layer (`src/` / `echosync_core`)
- High-speed Rust PyO3 crate handling heavy file I/O, directory traversal (`walkdir`), audio metadata reading/writing (`lofty`), and Chromaprint fingerprinting.
- Python interacts with Rust strictly through `core/io_gatekeeper.py`.

---

## 3. Core Architectural Principles

1. **Zero-Trust Gatekeeper Security:** All destructive or mutating filesystem operations must be pre-validated by `core/io_gatekeeper.py` before executing in native Rust code.
2. **Lofty Audio Tagging Isolation:** Python code is strictly forbidden from importing `mutagen`, `tinytag`, or `taglib`. Tag reading and writing are strictly delegated to Rust `lofty`.
3. **Database Boundary Separation:** Rust code never connects directly to `library.db` (managed by SQLAlchemy). Rust handles raw dictionary extraction and yields primitive PyDict structures to Python repositories for ORM bulk upsert.
4. **Lightweight Event Communication:** EventBus messages transmit scalar IDs (`sync_id`, `media_id`) rather than heavy serialized track payloads.
