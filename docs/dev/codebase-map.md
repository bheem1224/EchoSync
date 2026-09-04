# EchoSync Core Codebase Locator

## 1. Directory Responsibility Map

| Directory Path | Responsibility & Architectural Scope |
| :--- | :--- |
| `api/routers/` | FastAPI REST controllers for public API v1/v2 endpoints, API key authentication, and schema definitions. |
| `web/routes/` | Web application route controllers for system operations, webhooks, auth, and metadata review workflows. |
| `core/` | Core application orchestration, state management, security boundaries, event dispatching, and matching logic. |
| `core/nexus_framework/` | Plugin execution framework: loader, AST sandbox scanner, SDK facade, and store management. |
| `core/matching_engine/` | Tier 1/2 metadata matching engine, scoring modifier filters, and CJK text normalization. |
| `core/suggestion_engine/` | Content-based vibe profiling, ListenBrainz discovery, track lifecycle deletion & upgrade decisions. |
| `core/database/` | SQLAlchemy 2.0 ORM models, Repository pattern implementations, and migration scripts. |
| `services/` | Asynchronous background services executing library sync, download staging, and metadata enhancement. |
| `database/` | Database engine gateways, connection pool management, and 3-database scope split configurations. |
| `src/` | Native Rust `echosync_core` PyO3 crate: `walkdir` filesystem scanner, `lofty` tag extractor, and `rusqlite` cache writer. |
| `tools/` | Diagnostic utilities, codebase linting (`lint_audio_calls.py`), and system inspection tools. |
| `webui/src/` | SvelteKit 2 + Svelte 5 frontend SPA host shell, dynamic plugin loaders, and YAML dashboard renderers. |

---

## 2. Symbol Lookup Index

| Architectural Symbol / Class | Primary File Location | Responsibilities |
| :--- | :--- | :--- |
| `IOGatekeeper` | `core/io_gatekeeper.py` | Centralized pre-flight permission validator for all native Rust file mutations. |
| `EventBus` | `core/event_bus.py` | Lightweight event bus dispatching scalar payloads (`sync_id`, `media_id`). |
| `JobQueue` | `core/job_queue.py` | Priority job queue worker pool with session rollback safeguards. |
| `PluginLoader` | `core/nexus_framework/plugin_loader.py` | Plugin discovery, AST security scanning, module imports, and lifecycle hooks. |
| `PluginStorageBox` | `core/nexus_framework/plugin_SDK.py` | Unified facade routing plugin storage requests to sandboxed `working.db` tables. |
| `WeightedMatchingEngine` | `core/matching_engine/matching_engine.py` | Multi-tier metadata confidence scoring and candidate evaluation. |
| `VibeProfiler` | `core/suggestion_engine/vibe_profiler.py` | User listening signature calculation using audio feature vectors. |
| `TrackRepository` | `core/database/repositories/track_repo.py` | Repository pattern implementation for `CanonicalTrack` ORM entities. |
| `LibrarySyncService` | `services/library_sync_service.py` | Background filesystem scanner orchestrating library ingestion. |
| `DownloadManager` | `services/download_manager.py` | Download acquisition staging and client protocol wrapper (Slskd, etc.). |
| `MetadataEnhancerService` | `services/metadata_enhancer.py` | 5-step retroactive library metadata identification pipeline. |
| `scan_directory` (Rust) | `src/file_handling/scanner.rs` | Native multi-threaded recursive directory scanner yielding PyDict chunks. |
| `read_tags` / `write_tags` (Rust) | `src/metadata/extractor.rs` | Native audio tagging interface using the Rust `lofty` crate. |
| `DynamicPluginLoader.svelte` | `webui/src/components/DynamicPluginLoader.svelte` | Svelte host component dynamically mounting plugin Web Components. |
