# Core Codebase Locator & Architecture Map

## 1. Technical Reference Index

For detailed subsystem specifications, consult the dedicated technical reference manuals in the developer wiki:
- **[Architecture Overview](architecture-overview.md):** High-level hybrid monolith system architecture, FastAPI/Rust/Svelte topology, and Event Bus schemas.
- **[Database Evolution & 3-DB Split](database-evolution.md):** Physical partitioning (`config.db`, `working.db`, `music_library.db`), entity promotion, and schema evolution.
- **[Metadata Enhancement Subsystem](metadata-enhancement-architecture.md):** The 5-stage cascading decision tree, download manager lifecycle, matching algorithms, and strategy skip hooks.
- **[Native Rust FFI Engine](rust-ffi-engine.md):** Native `echosync_core` PyO3 extension, lofty metadata handling, and safe filesystem operations.
- **[Architectural Rule Violations Ledger](rule-violations.md):** Live audit ledger tracking ungated file mutations, direct DB connections, and rogue HTTP clients.

---

## 2. Directory Responsibility Map

| Directory | Responsibility Scope | Primary File Types | Architectural Notes |
| :--- | :--- | :--- | :--- |
| `core/` | System orchestration, event bus, I/O Gatekeeper, task manager, matching engine, and Nexus Plugin Framework. | Python (`.py`) | Core application layer. Zero direct file mutations permitted outside Gatekeeper. |
| `core/nexus_framework/` | Plugin loader, AST security sandbox, plugin store, and plugin SDK execution engine. | Python (`.py`) | Zero-trust plugin execution boundary. Enforces AST checks and path sandboxing. |
| `services/` | Long-running background business logic, job execution, metadata enhancers, and library watchers. | Python (`.py`) | Service layer operating via DatabaseGateway repositories. |
| `database/` | SQLAlchemy 2.0 ORM models, DatabaseGateway, and database engine abstractions (`config.db`, `working.db`, `music_library.db`). | Python (`.py`) | Strictly managed by SQLAlchemy ORM. Rust is forbidden from directly connecting to `music_library.db`. |
| `web/routes/` & `api/routers/` | FastAPI REST API controllers, SSE endpoints, and request/response schemas. | Python (`.py`) | Returns raw primitive JSON payloads. No UI string formatting in backend controllers. |
| `src/` | Native Rust `echosync_core` extension compiled via PyO3 & Maturin. | Rust (`.rs`) | Fast directory scanning (`scanner.rs`), lofty tag parsing/writing (`extractor.rs`, `writer.rs`), integrity (`integrity.rs`), safe fs ops (`fs_ops.rs`), and working DB operations (`working_db.rs`). |
| `webui/src/` | Decoupled SvelteKit 2 SPA host interface and custom element plugin host loader. | Svelte, TS (`.svelte`, `.ts`) | Host DOM layer rendering custom Web Components via `webui/src/components/DynamicPluginLoader.svelte`. |
| `tools/` | Diagnostic scripts, database inspect tools, and architectural verification linters. | Python (`.py`) | Includes `lint_audio_calls.py` for tagging compliance verification. |

---

## 3. Symbol & Responsibility Lookup Index

### 3.1 Storage, Filesystem & Gatekeeper Operations

| System Responsibility | Primary Class / Symbol | Target File Path |
| :--- | :--- | :--- |
| Zero-Trust I/O Gatekeeper | `Gatekeeper` | `core/io_gatekeeper.py` |
| Native Rust Safe File Operations | `safe_move_file`, `copy_file`, `delete_file` | `src/file_handling/fs_ops.rs` |
| Native Rust Checksum & Integrity | `calculate_checksum` | `src/file_handling/integrity.rs` |
| Storage Root Management | `StorageService` | `services/storage_service.py` |
| Path Traversal Validation | `validate_sandboxed_path` | `core/path_security.py` |
| Fast Directory Scanner | `scan_directory_callback` | `src/file_handling/scanner.rs` |

### 3.2 Audio Tagging & Metadata Extraction

| System Responsibility | Primary Class / Symbol | Target File Path |
| :--- | :--- | :--- |
| Native `lofty` Audio Tag Extractor | `read_audio_tags` | `src/metadata/extractor.rs` |
| Native `lofty` Audio Tag Writer | `write_audio_tags` | `src/metadata/writer.rs` |
| Chromaprint Fingerprint Extractor | `extract_chromaprint` / `FingerprintService` | `core/matching_engine/fingerprinting.py` |
| ISRC Metadata Lookup Service | `ISRCLookupService` | `services/isrc_lookup_service.py` |
| Metadata Enhancement Pipeline | `MetadataEnhancerService` | `services/metadata_enhancer.py` |
| Audio Tagging Compliance Linter | `main` (Tag Scanner) | `tools/lint_audio_calls.py` |

### 3.3 Database, ORM & Repositories

| System Responsibility | Primary Class / Symbol | Target File Path |
| :--- | :--- | :--- |
| Canonical Track Model | `Track` | `database/music_database.py` |
| Physical Media Model | `LocalMedia` | `database/music_database.py` |
| Ephemeral Virtual Track Cache | `VirtualTrackCache` | `database/working_database.py` |
| Native Rust Working DB Handler | `WorkingDbHandler` | `src/database/working_db.rs` |
| Config & Credentials Database | `ConfigDatabase` | `database/config_database.py` |
| Track Repository Operations | `TrackRepository` | `core/database/repositories/track_repo.py` |
| Database Engine & Writer | `MusicDatabase`, `_DBWriter` | `database/engine.py` |

### 3.4 Plugin Engine & Nexus Framework

| System Responsibility | Primary Class / Symbol | Target File Path |
| :--- | :--- | :--- |
| Nexus Plugin Loader & Resolver | `PluginLoader`, `get_plugin` / `get_provider` | `core/nexus_framework/plugin_loader.py` |
| Zero-Trust AST Security Scanner | `PluginSecurityScanner` | `core/nexus_framework/plugin_loader.py` |
| Plugin Unified Facade SDK | `PluginStorageBox` | `core/nexus_framework/plugin_SDK.py` |
| WASM Execution Wrapper | `WasmPluginWrapper` | `core/nexus_framework/plugin_SDK.py` |
| Plugin Hook Lifecycle Manager | `HookManager` | `core/hook_manager.py` |
| Svelte Web Component Dynamic Loader | `DynamicPluginLoader.svelte` | `webui/src/components/DynamicPluginLoader.svelte` |

### 3.5 Event Dispatcher, Jobs & Matching Engine

| System Responsibility | Primary Class / Symbol | Target File Path |
| :--- | :--- | :--- |
| Event Bus Dispatcher | `EventBus` | `core/event_bus.py` |
| Weighted Metadata Matching | `WeightedMatchingEngine` | `core/matching_engine/matching_engine.py` |
| Background Task Manager | `TaskManager` | `core/task_manager/task_manager.py` |
| System Background Jobs | `SystemJobs` | `core/task_manager/system_jobs.py` |
| Suggestion & Recommendation Engine | `SuggestionEngine` | `core/suggestion_engine/suggestion_engine.py` |

---

## 4. FastAPI REST Endpoint Directory

### 4.1 Zero-Trust Sub-Application Namespacing
All dynamically registered plugin REST endpoints are mounted under `/api/v1/plugins/{plugin_id}/` to ensure strict route collision isolation.

### 4.2 Core REST Controllers Reference

| Method | Endpoint Path | Controller File | Purpose |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/tracks` | `web/routes/tracks.py` | Query canonical tracks with filtering, pagination, and sorting. |
| `GET` | `/api/v1/tracks/{sync_id}` | `web/routes/tracks.py` | Fetch detailed track entity including associated physical media paths. |
| `PATCH` | `/api/v1/tracks/{sync_id}` | `web/routes/tracks.py` | Update logical metadata (title, track number, rating, MBID). |
| `DELETE`| `/api/v1/tracks/{sync_id}` | `web/routes/tracks.py` | Soft or hard delete track and associated local media files. |
| `GET` | `/api/v1/review/queue` | `web/routes/metadata_review.py` | List pending metadata review tasks staged in `working.db`. |
| `POST` | `/api/v1/review/{task_id}/lookup/acoustid` | `web/routes/metadata_review.py` | Trigger AcoustID fingerprint lookup for staged review item. |
| `POST` | `/api/v1/review/{task_id}/approve` | `web/routes/metadata_review.py` | Approve review task and promote virtual track to `music_library.db`. |
| `GET` | `/api/v1/system/status` | `web/routes/system.py` | Retrieve system health, memory usage, and component statuses. |
| `POST` | `/api/v1/system/enhance/trigger` | `web/routes/system.py` | Trigger retroactive metadata enhancement job. |
| `POST` | `/api/v1/webhooks/{provider}` | `web/routes/webhooks.py` | Inbound media server webhooks (Plex, Jellyfin, Navidrome scrobbles). |
| `GET` | `/api/v1/ui/registry` | `web/routes/ui_registry.py` | Registry of compiled Svelte Web Component UI extensions. |
