# Core Codebase Locator & Architecture Map

## 1. Technical Reference Index

For detailed subsystem specifications, consult the dedicated technical reference manuals:
- **[API Reference Specification](api-reference.md):** Complete REST endpoint paths, query parameters, payload schemas, and response contracts.
- **[Event Bus Dictionary & Lifecycle](event-bus.md):** Channel registry, event payload schemas, and lightweight UUID migration targets.
- **[Matching & Suggestion Engines](matching-and-suggestions.md):** Weighted metadata scoring formulas, token sorting, vibe profiling, and recommendation pipelines.
- **[Download Lifecycle & Metadata Pipeline](download-pipeline.md):** State transition machine, candidate heuristics, fallback waterfalls, and stream verification.

---

## 2. Directory Responsibility Map

| Directory | Responsibility Scope | Primary File Types | Architectural Notes |
| :--- | :--- | :--- | :--- |
| `core/` | System orchestration, event bus, I/O Gatekeeper, task manager, matching engine, and Nexus Plugin Framework. | Python (`.py`) | Core application layer. Zero direct file mutations permitted outside Gatekeeper. |
| `core/nexus_framework/` | Plugin loader, AST security sandbox, plugin store, and plugin SDK execution engine. | Python (`.py`) | Zero-trust plugin execution boundary. Enforces AST checks and path sandboxing. |
| `services/` | Long-running background business logic, job execution, metadata enhancers, and library watchers. | Python (`.py`) | Service layer operating via DatabaseGateway repositories. |
| `database/` | SQLAlchemy 2.0 ORM models, DatabaseGateway, and database engine abstractions (`config.db`, `working.db`, `library.db`). | Python (`.py`) | Strictly managed by SQLAlchemy ORM. Rust is forbidden from directly connecting to `library.db`. |
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

### 3.6 FastAPI Route Controllers

| API Subsystem | Primary Controller File | Functionality Scope |
| :--- | :--- | :--- |
| Library & Tracks API | `web/routes/tracks.py` & `library.py` | Track querying, physical media details, CRUD. |
| Metadata Review & Promotion | `web/routes/metadata_review.py` | Ingestion staging confirmation and virtual promotion. |
| System Operations & Status | `web/routes/system.py` | Health metrics, system restarts, log streaming. |
| Webhooks Integration Router | `web/routes/webhooks.py` | Inbound webhooks from Plex, Jellyfin, and external tools. |
| Dynamic UI Components Registry | `web/routes/ui_registry.py` | Serving plugin Svelte web component bundles. |
