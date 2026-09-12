# EchoSync Codebase Map & Directory Layout

## 1. Primary Directory Layout

```text
EchoSync/
├── api/                     # High-level system FastAPI routers & schemas
│   ├── routers/             # System tasks and system jobs controllers
│   └── schemas/             # Pydantic request/response schemas
├── core/                    # System orchestration engine & security boundaries
│   ├── io_gatekeeper.py     # Single point of entry for filesystem mutations
│   ├── request_manager.py   # Global rate-limited outbound HTTP manager
│   ├── rate_limiter.py      # Async domain rate-limiting implementation
│   ├── event_bus.py         # In-memory pub/sub event dispatcher
│   ├── matching_engine/     # Metadata matching & text normalization engine
│   ├── nexus_framework/     # Plugin SDK, loader, security scanner, and WASM runtime
│   └── task_manager/        # Background queue execution & job scheduling
├── database/                # SQLAlchemy ORM models, DatabaseGateway, and 3-DB splits
│   ├── database_gateway.py  # Scoped session managers for config/working/library DBs
│   ├── music_database.py    # CanonicalTrack, PhysicalMedia, VirtualMedia models
│   ├── config_database.py   # Encrypted application settings repository
│   └── working_database.py  # Ephemeral queues and virtual track staging cache
├── docs/                    # Diátaxis-compliant wiki documentation
│   ├── user/                # Practical user workflows and integration guides
│   ├── dev/                 # Deep architecture specs & invariant rule-violations ledger
│   ├── reference/           # OpenAPI route contracts, parameters, and error schemas
│   ├── plugins/             # Plugin SDK developer guides and hook specifications
│   └── agents/              # Agent directives, invariants, and verification protocols
├── plugins/                 # EchoSync first-party and third-party plugins
│   └── EchoSync/            # Core plugins (plex, spotify, slskd, navidrome, jellyfin, tidal)
├── services/                # High-level background business logic services
│   ├── download_manager.py  # Download queue processor & acquisition bridge
│   ├── metadata_enhancer.py # 6-Stage metadata resolution coordinator
│   ├── media_manager.py     # Library hygiene & duplicate resolution service
│   └── library_sync.py      # Media server sync orchestrator
├── src/                     # Native Rust core extension module (echosync_core)
│   ├── lib.rs               # PyO3 FFI module exports
│   ├── file_handling/       # Multi-threaded walkdir scanner & fs operations
│   ├── metadata/            # Lofty audio tag parser, Symphonia decoder, Chromaprint
│   └── database/            # Direct rusqlite ingestion writer for working.db
├── tools/                   # Diagnostic scripts and AST linter tools
│   └── lint_audio_calls.py  # Linter enforcing native Rust tag call prohibitions
└── web/                     # Primary FastAPI sub-application routes & UI service
    ├── routes/              # Core API router implementations
    └── services/            # Frontend support services & UI registries
```
