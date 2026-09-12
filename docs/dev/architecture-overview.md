# System Architecture Overview

## 1. High-Level System Design

EchoSync is an audiophile-grade universal music synchronization, metadata enhancement, and library orchestration engine. The system employs a hybrid monolith architecture combining Python (FastAPI / ASGI Orchestration) with a high-performance native Rust core (`echosync_core` PyO3 extension module).

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │                         Web / API Gateway                              │
 │                 FastAPI ASGI App (web/api_app.py)                       │
 └──────────────────────────────────┬─────────────────────────────────────┘
                                    │
                                    ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      Service Orchestration Layer                       │
 │  ┌────────────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
 │  │ Metadata Resolution    │  │ Task / Job Queue │  │ Plugin Engine  │ │
 │  │ Engine                 │  │ Manager          │  │ (Nexus)        │ │
 │  └────────────────────────┘  └──────────────────┘  └────────────────┘ │
 └───────────┬──────────────────────────┬──────────────────────┬──────────┘
             │                          │                      │
             ▼                          ▼                      ▼
 ┌────────────────────────┐ ┌──────────────────────┐ ┌────────────────────┐
 │  3-Database Architecture│ │ IO Gatekeeper        │ │ Native Rust Core   │
 │  - config.db           │ │ (core/io_gatekeeper) │ │ (echosync_core FFI)│
 │  - working.db          │ │ Zero-trust sandbox   │ │ Multi-threaded scan│
 │  - library.db          │ │ Safe move/unlink/copy│ │ Lofty tag parser   │
 └────────────────────────┘ └──────────────────────┘ └────────────────────┘
```

---

## 2. Core Subsystem Boundaries

1. **FastAPI Controllers (`web/routes/`, `api/routers/`):** Expose RESTful API endpoints, handle OAuth workflows, and stream SSE event feeds.
2. **IO Gatekeeper (`core/io_gatekeeper.py`):** Single point of entry for all physical filesystem mutations (moves, renames, deletions). Guarantees path sandboxing and zero loss.
3. **RequestManager (`core/request_manager.py`):** Global outbound HTTP client enforcing domain rate limits, retry policies, and circuit breaking.
4. **DatabaseGateway (`database/database_gateway.py`):** Scoped database connection management wrapping SQLAlchemy 2.0 ORM sessions.
5. **Nexus Plugin Framework (`core/nexus_framework/`):** Zero-trust isolated plugin execution environment supporting Python dynamic modules and WASM runtimes.
6. **Native Rust DSP Engine (`echosync_core`):** Compiled via Maturin; handles multi-threaded directory traversing, Lofty audio tag reading/writing, Symphonia audio decoding, and Chromaprint acoustic fingerprint generation.
