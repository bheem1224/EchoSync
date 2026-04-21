# EchoSync Core Architecture & Plugins Reference

This document maps out the core Python modules and explains the fundamental division of responsibilities within EchoSync.

## 1. The `core` package

The `core` directory is the engine room of EchoSync. It contains pure business logic, database models, event routing, and utility classes that are framework-agnostic.

* **Rule of Thumb:** Code in `core` does **not** make direct network requests to external APIs (like Spotify or MusicBrainz). External communication is strictly routed through the `ProviderRegistry` and handled by plugins.

### Core File Map (Highlights)

| File / Folder | Purpose |
|---------------|---------|
| `core/caching/` | Centralized caching framework (e.g., `@provider_cache`). |
| `core/file_handling/` | Safe file I/O operations (e.g., `LocalFileHandler`) replacing legacy path mappers. |
| `core/matching_engine/` | Logic for fuzzy string matching, scoring profiles, and metadata comparison. |
| `core/plugin_loader.py` | AST Scanner and dynamic loading of community plugins. |
| `core/hook_manager.py` | The central event bus and injection point registry for plugins. |
| `core/plugin_loader.py` | Dynamic loading of community plugins and enforcement of the Zero-Trust AST Sandbox (`PluginSecurityScanner`). |
| `core/plugin_store.py` | The Plugin Marketplace manager. Handles downloading, installing, zip extraction, and uninstalling community plugins. |
| `core/plugin_orm.py` | Provides the `ProviderStorageBox` SDK, managing sandboxed database access for plugins. |
| `core/request_manager.py` | HTTP client wrapper handling automatic retries, exponential backoff, and rate limiting. |
| `core/job_queue.py` | Background task scheduling and concurrency locking. |
| `core/event_bus.py` | Lightweight message passing (Claim Check Pattern) between system components. |
| `core/migrations.py` | Alembic integration for automated database schema management. |

---

## 2. Total Freedom Plugin Architecture (Formerly "Providers")

The legacy concept of hardcoded "Providers" has been deprecated. EchoSync now utilizes the **Total Freedom Plugin Architecture**.

Instead of writing rigid adapter classes, developers now write **Plugins** that interact with the core application via a comprehensive **Hook System**. This allows plugins to not just provide data, but to alter, intercept, or completely hijack almost any application state or lifecycle event.

Plugins are dynamically loaded via `core/plugin_loader.py`.

### The Hook System

The architecture relies on three types of hooks dispatched through the central `core.hook_manager.HookManager`:

1. **Event Hooks (Read-Only)**
   - **Purpose:** To notify plugins that an action has occurred so they can react (e.g., logging, triggering an external webhook).
   - **Behavior:** The plugin receives a dictionary payload but cannot modify the core application's state.

2. **Mutator Hooks (Modify in Transit)**
   - **Purpose:** To allow plugins to alter data before the core engine processes it.
   - **Behavior:** The plugin receives a payload, modifies it, and returns the modified payload.

3. **Skip Hooks (Hijack/Bypass)**
   - **Purpose:** To allow a plugin to completely take over a core function.
   - **Behavior:** The core engine checks the hook's return value. If the plugin returns `{"skip": True, "result": ...}`, the core engine immediately aborts its default logic and uses the plugin's result instead.
   - **Example:** `AUTHENTICATE_USER` allows an OIDC plugin to validate a user. If successful, the core SQLite password check is entirely bypassed.

> **Developer Note:** For full details on building plugins, AST Sandbox constraints, and Database Engine swapping, see the [Plugin SDK Guide](PLUGIN_SDK_GUIDE.md).

---

## 3. Services

Services are the background workers that orchestrate complex workflows by gluing together `core` logic and Plugin capabilities. They are registered with the `core/job_queue.py`.

| Service module | Purpose |
|----------------|---------|
| `auto_importer.py` | Monitors download directories, routes files to the Metadata Enhancer, and organizes verified tracks into the media library. |
| `download_manager.py` | Manages the queue. Listens for `DOWNLOAD_INTENT` events and uses a waterfall strategy across downloader plugins based on Quality Profiles. |
| `library_hygiene.py` | Deduplicates library tracks by identifying shared AcoustID fingerprint hashes. |
| `media_manager.py` | Orchestrates track upgrades (replacing low-quality files) and removals based on user ratings. |
| `metadata_enhancer.py` | A 5-step pipeline that extracts local tags, generates fingerprints, and queries metadata plugins to enrich track data. |
| `sync_service.py` | The orchestration engine that reads source playlists, triggers the Matching Engine, and queues missing tracks for download. |

---

*Last updated: Today*
