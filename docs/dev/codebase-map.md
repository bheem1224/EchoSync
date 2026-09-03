# Core Codebase Locator & Architecture Map

## 1. Directory Responsibility Map

| Directory | Responsibility Scope | Primary File Types | Architectural Notes |
| :--- | :--- | :--- | :--- |
| `core/` | System orchestration, event bus, I/O Gatekeeper, task manager, matching engine, and Nexus Plugin Framework. | Python (`.py`) | Core application layer. Zero direct file mutations permitted outside Gatekeeper. |
| `core/nexus_framework/` | Plugin loader, AST security sandbox, plugin store, and plugin SDK execution engine. | Python (`.py`) | Zero-trust plugin execution boundary. Enforces AST checks and path sandboxing. |
| `services/` | Long-running background business logic, job execution, metadata enhancers, and library watchers. | Python (`.py`) | Service layer operating via DatabaseGateway repositories. |
| `database/` | SQLAlchemy 2.0 ORM models, DatabaseGateway, and database engine abstractions (`config.db`, `working.db`, `library.db`). | Python (`.py`) | Strictly managed by SQLAlchemy ORM. Rust is forbidden from directly connecting to `library.db`. |
| `web/routes/` & `api/routers/` | FastAPI REST API controllers, SSE endpoints, and request/response schemas. | Python (`.py`) | Returns raw primitive JSON payloads. No UI string formatting in backend controllers. |
| `src/` | Native Rust `echosync_core` extension compiled via PyO3 & Maturin. | Rust (`.rs`) | Fast filesystem traversal (`walkdir`), audio tagging/chromaprint (`lofty`), and safe file moves. |
| `webui/src/` | Decoupled SvelteKit 2 SPA host interface and custom element plugin host loader. | Svelte, TS (`.svelte`, `.ts`) | Host DOM layer rendering custom Web Components via `DynamicPluginLoader.svelte`. |
| `tools/` | Diagnostic scripts, database inspect tools, and architectural verification linters. | Python (`.py`) | Includes `lint_audio_calls.py` for tagging compliance verification. |

---

## 2. Symbol & Responsibility Lookup Index

### 2.1 Storage, Filesystem & Gatekeeper Operations

| System Responsibility | Primary Class / Symbol | Target File Path |
| :--- | :--- | :--- |
| Zero-Trust I/O Gatekeeper | `Gatekeeper` | `core/io_gatekeeper.py` |
| Native Rust Safe File Operations | `safe_move_file`, `copy_file`, `delete_file` | `src/file_handling/fs_ops.rs` |
| Storage Root Management | `StorageService` | `services/storage_service.py` |
| Path Traversal Validation | `validate_sandboxed_path` | `core/path_security.py` |
| Fast Directory Scanner | `scan_directory_callback` | `src/file_handling/scanner.rs` |

### 2.2 Audio Tagging & Metadata Extraction

| System Responsibility | Primary Class / Symbol | Target File Path |
| :--- | :--- | :--- |
| Native `lofty` Audio Tag Reader/Writer | `read_audio_tags`, `write_audio_tags` | `src/metadata/extractor.rs` |
| Chromaprint Fingerprint Extractor | `extract_chromaprint` | `src/metadata/fingerprint.rs` |
| ISRC Metadata Lookup Service | `ISRCLookupService` | `services/isrc_lookup_service.py` |
| Metadata Enhancement Pipeline | `MetadataEnhancerService` | `services/metadata_enhancer.py` |
| Audio Tagging Compliance Linter | `main` (Tag Scanner) | `tools/lint_audio_calls.py` |

### 2.3 Database, ORM & Repositories

| System Responsibility | Primary Class / Symbol | Target File Path |
| :--- | :--- | :--- |
| Canonical Track Model | `Track` | `database/music_database.py` |
| Physical Media Model | `LocalMedia` | `database/music_database.py` |
| Ephemeral Virtual Track Cache | `VirtualTrackCache` | `database/working_database.py` |
| Config & Credentials Database | `ConfigDatabase` | `database/config_database.py` |
| Track Repository Operations | `TrackRepository` | `core/database/repositories/track_repo.py` |
| Database Engine & Writer | `MusicDatabase`, `_DBWriter` | `database/engine.py` |

### 2.4 Plugin Engine & Nexus Framework

| System Responsibility | Primary Class / Symbol | Target File Path |
| :--- | :--- | :--- |
| Nexus Plugin Loader & Resolver | `PluginLoader`, `get_plugin` / `get_provider` | `core/nexus_framework/plugin_loader.py` |
| Zero-Trust AST Security Scanner | `PluginSecurityScanner` | `core/nexus_framework/plugin_loader.py` |
| Plugin Unified Facade SDK | `PluginStorageBox` | `core/nexus_framework/plugin_SDK.py` |
| WASM Execution Wrapper | `WasmPluginWrapper` | `core/nexus_framework/plugin_SDK.py` |
| Plugin Hook Lifecycle Manager | `HookManager` | `core/hook_manager.py` |
| Svelte Web Component Dynamic Loader | `DynamicPluginLoader.svelte` | `webui/src/lib/components/DynamicPluginLoader.svelte` |

### 2.5 Event Dispatcher, Jobs & Matching Engine

| System Responsibility | Primary Class / Symbol | Target File Path |
| :--- | :--- | :--- |
| Event Bus Dispatcher | `EventBus` | `core/event_bus.py` |
| Weighted Metadata Matching | `WeightedMatchingEngine` | `core/matching_engine/matching_engine.py` |
| Background Task Manager | `TaskManager` | `core/task_manager/task_manager.py` |
| System Background Jobs | `SystemJobs` | `core/task_manager/system_jobs.py` |
| Suggestion & Recommendation Engine | `SuggestionEngine` | `core/suggestion_engine/suggestion_engine.py` |

### 2.6 FastAPI Route Controllers

| API Subsystem | Primary Controller File | Functionality Scope |
| :--- | :--- | :--- |
| Library & Tracks API | `web/routes/tracks.py` & `library.py` | Track querying, physical media details, CRUD. |
| Metadata Review & Promotion | `web/routes/metadata_review.py` | Ingestion staging confirmation and virtual promotion. |
| System Operations & Status | `web/routes/system.py` | Health metrics, system restarts, log streaming. |
| Webhooks Integration Router | `web/routes/webhooks.py` | Inbound webhooks from Plex, Jellyfin, and external tools. |
| Dynamic UI Components Registry | `web/routes/ui_registry.py` | Serving plugin Svelte web component bundles. |
