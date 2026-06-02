# EchoSync Plugin Architecture: Surgical Refactor Gap Analysis

## 1. Strict Namespacing

**Current State:**
Plugins are loaded from `providers/` (core) and `plugins/` (community). The `plugin_loader.py` dynamically determines IDs like `plugin.{name}` based on folder structure, but there is no strict enforcement of a deterministic `{source}.{author}.{plugin_name}` namespace format, nor are folder names strictly mapped to this scheme.

**Legacy Debt / Dead Code:**

- `PluginLoader._load_provider_package` constructs IDs manually: `provider_id = f"plugin.{name}" if source_type == 'community' else name`.
- Logic differentiating between 'core' (`providers/`) and 'community' (`plugins/`) namespaces must be removed.

**The Gap:**

- `plugin_loader.py` and `plugin_store.py` must enforce that the folder name perfectly matches the `{source}.{author}.{plugin_name}` format.
- All internal dictionaries and database relationships must strictly use this fully qualified ID. _(and deprecation of the /providers folder)_

**API Contract Changes:**

- Frontend must expect plugin IDs to be three-part dot-separated strings (e.g., `community.johndoe.spotify`).

## 2. Vendoring (Dependencies)

**Current State:**
`core/plugin_venv.py` creates a full Python virtual environment per plugin (or a shared one for all plugins, but still a standard `venv`). It runs `pip install` inside the venv and prepends `sys.path`.

**Legacy Debt / Dead Code:**

- The entirety of `core/plugin_venv.py` is marked for deletion. It uses `venv.create(venv_path, with_pip=True)`, which is slow and wastes disk space.

**The Gap:**

- Implement a lightweight vendoring system. Dependencies should be installed globally into `/data/plugins/site-packages` when possible.
- For conflicts, use `pip install --target=/data/plugins/{plugin_id}/vendor <package>`.
- Modify `plugin_loader.py` to dynamically prepend `/data/plugins/{plugin_id}/vendor` to `sys.path` immediately before importing a specific plugin, and restore it afterward, or use an `importlib` hook to intercept imports for that plugin.

**API Contract Changes:**

- None.

## 3. Manifest Diet

**Current State:**
`plugin_store.py` and `plugin_loader.py` parse `manifest.json` for metadata. Some configurations and settings are likely defined here or in a companion `ui_manifest.json` (as seen in `get_all_plugins`).

**Legacy Debt / Dead Code:**

- Parsing logic in `plugin_loader.py` / `settings.py` that extracts hooks, settings, or UI components directly from `manifest.json`.
- `ui_manifest.json` loading logic.

**The Gap:**

- `manifest.json` should strictly schema-validate to only contain store metadata (`name`, `version`, `author`, `description`).
- Plugins must programmatically define and register their default settings and UI components upon initialization via the new SDK.

**API Contract Changes:**

- The `/api/plugins` payload will no longer contain deeply nested settings/hooks objects read statically from JSON.

## 4. Hot-Reloading

**Current State:**
The system uses an atomic swap for updates and sets `system_state.restart_pending = True` (in `plugin_store.py`), requiring a full app restart. Loading errors cause plugins to be disabled indefinitely.

**Legacy Debt / Dead Code:**

- The `restart_required: True` flag in `PLUGIN_UPDATE_COMPLETE` events.

**The Gap:**

- Implement a `reload_plugin(plugin_id)` function in `plugin_loader.py`.
- Unmount Flask blueprints/API routes dynamically.
- Unwire subscriptions from `EventBus` (requires tracking which handlers belong to which plugin).
- Call `del sys.modules[mod_name]` for all modules under the plugin's namespace.
- Re-run `importlib.import_module`.

**API Contract Changes:**

- A new endpoint `POST /api/plugins/{plugin_id}/reload` might be exposed, and update events will no longer indicate `restart_required: True`.

## 5. AST Enforcer

**Current State:**
`PluginSecurityScanner` in `core/plugin_loader.py` uses AST to block `builtins`, `os`, `shutil`, `importlib`, etc. It checks imports and method calls (like `.unlink()`).

**Legacy Debt / Dead Code:**

- None. The current implementation is a good starting point.

**The Gap:**

- The scanner must be expanded to strictly block `threading`, `multiprocessing`, `requests`, and `httpx`.
- Add rules blocking `urllib`, `urllib3`, and any socket-level modules to enforce the use of `RequestManager` (which will become part of the SDK).

**API Contract Changes:**

- None.

## 6. Event Bus Expansion

**Current State:**
`core/event_bus.py` handles lightweight events and legacy queued events. It supports wildcards but is primarily used for internal app state (`SYSTEM`, `DOWNLOAD_INTENT`).

**Legacy Debt / Dead Code:**

- The `channel` and `event_type` legacy argument parsing in `publish()`.

**The Gap:**

- The EventBus must explicitly support custom `{plugin_id}.*` event namespaces.
- Ensure the reload mechanism (Point 4) can wipe handlers bound to a specific plugin ID.

**API Contract Changes:**

- WebSocket streams or polling endpoints will need to accommodate dynamically registered event types.

## 7. Key-Value Store (KVS) & Non-Sensitive Settings

**Current State:**
Plugins have no standardized way to save user settings or generic state. `config.db` currently uses rigid relational tables (like `service_config`) for simple API keys, requiring Alembic migrations for every new plugin.

**Legacy Debt / Dead Code:**

- The `service_config` table in `config.db` is inflexible and deprecated.

**The Gap:**

- Convert/replace `service_config` into a single `config_kvs` table in `config.db`: `(namespace, key, value [JSON], is_secret)`.
- Core uses the `core` namespace; plugins use their strict `{plugin_id}` namespace.
- This KVS is strictly for **unencrypted, non-sensitive** settings (e.g., "scan_interval", "theme_color").
- Implement `sdk.config.set()` / `sdk.config.get()` to transparently read/write from this table based on the caller's ID.

**API Contract Changes:**

- New endpoints for the frontend to build generic settings UI: `GET /api/plugins/{plugin_id}/config` and `POST /api/plugins/{plugin_id}/config`.

## 8. Native Task Scheduler

**Current State:**
`core/job_queue.py` provides an in-memory task scheduler. Plugins currently don't have a clean, declarative way to register jobs; `plex/routes.py` manually registers one-shot jobs.

**Legacy Debt / Dead Code:**

- Manual job registration calls scattered in plugin code.

**The Gap:**

- Expose an `@sdk.schedule(interval="X")` decorator in the new SDK.
- The SDK must parse the decorator at load time and push a `ScheduledJob` into `JobQueue` tagging it with the `plugin_id`.
- **Managed Threads:** For plugins requiring long-running background loops not suitable for simple cron-like scheduling, the SDK must expose a `sdk.threads.spawn(name, target, *args)` wrapper. This wrapper must register the thread ID with the `PluginLoader` so it can be gracefully terminated or joined during a plugin reload/disable event.

## 9. Scoped Logging

**Current State:**
`provider_base.py` assigns a logger: `get_logger(f"plugin.{self._name}")`.

**Legacy Debt / Dead Code:**

- The logger setup in `ProviderBase`.

**The Gap:**

- Move logging instantiation into the SDK wrapper. Ensure the log formatter automatically prepends `[plugin_id]` (e.g., `[community.johndoe.plex]`) instead of just `plugin.plex`.

**API Contract Changes:**

- None.

## 10. Dual-Channel (Beta/Stable)

**Current State:**
`plugin_store.py` manages `beta` and `stable` artifacts by unpacking them into different subdirectories (e.g., `plugins/plex/beta/`). Atomic swaps overwrite stable directories when leaving beta.

**Legacy Debt / Dead Code:**

- The atomic swap `shutil.rmtree` logic that destroys the stable artifact when installing beta.

**The Gap:**

- `plugin_store.py` should download beta artifacts into a parallel `/beta` directory, but keep the `/stable` directory untouched.
- `plugin_loader.py` must decide at load-time which directory to import based on the user's config, allowing instant rollback.

**API Contract Changes:**

- UI must be able to toggle the channel and trigger a hot-reload (Point 4) rather than a full reinstall/download cycle.

## 11. API Route Jails

**Current State:**
`PluginLoader` extracts `RouteBlueprint` variables from plugin modules and appends them to `loaded_blueprints`. The blueprints dictate their own prefixes.

**Legacy Debt / Dead Code:**

- Plugins defining their own `url_prefix` inside their Blueprint definitions.

**The Gap:**

- In the new SDK (or in `plugin_loader.py`), intercept the Blueprint registration. Force the `url_prefix` to exactly `/api/plugins/{plugin_id}/`.
- Ensure wildcard captures or internal routing cannot break out of this jail.

**API Contract Changes:**

- All plugin API endpoints will strictly move to `/api/plugins/{source}.{author}.{plugin_name}/...`. The frontend must update all API calls directed at plugins.

## 12. Anti-Spoofing

**Current State:**
`plugin_store.py` checks `if plugin_info.get("_source_repo") == self.default_repo:` and injects `verified_source = "official"` and bypasses the AST scanner.

**Legacy Debt / Dead Code:**

- Core providers loaded from `providers/` bypass these checks implicitly. _(/providers folder should be deleted and not part of the image at all)_

**The Gap:**

- Core and 3rd-party plugins must be loaded identically.
- Any `"verified_source"` string inside a downloaded `manifest.json` must be forcefully stripped.
- The Core must re-apply the `verified_source` flag _only_ if the download URL matches a cryptographically signed repo or a hardcoded trusted source list.

**API Contract Changes:**

- None.

## 13. Database Scoping

**Current State:**
Plugins use `PluginStorageBox` for `working.db`. However, `_PluginModelFacade` in `provider_base.py` exposes raw SQLAlchemy models (`Track`, `Album`, `Artist`) connected to `music_library.db`, granting full write access.

**Legacy Debt / Dead Code:**

- `_PluginModelFacade` granting write-capable SQLAlchemy objects to plugins.

**The Gap:**

- The SDK must provide Read-Only proxy objects or specific accessor methods (e.g., `sdk.library.get_track()`) for `music_library.db`.
- Write operations to the main library must go through the EventBus or specific core API requests, never direct DB manipulation.
- **Relational Plugin Storage:** Plugins are granted the ability to create and manage their own relational tables within the central `working.db` file. The SDK must enforce a strict naming convention (e.g., `{plugin_id}__tablename`) and use a database jail to prevent plugins from accessing or modifying tables belonging to other plugins or the core system.
- **KVS Access:** In addition to relational tables, the standard KVS table remains available for simple settings, keyed by namespace.
- **Privileged Mode:** Direct database connections or breakout from these jails is strictly forbidden unless the plugin is running in **Privileged Mode**, which requires explicit, high-level user consent via the UI.

## 14. Secrets Scoping & The Hybrid Config Vault

**Current State:**
`config.db` relies on a highly fragmented relational structure (`spotify_accounts`, `plex_server`, etc.). Secrets are managed globally.

**Legacy Debt / Dead Code:**

- `account_metadata` table is dead weight and must be dropped.
- Hardcoded legacy secrets in `core/settings.py`.

**The Gap:**

- Implement a **Hybrid Config Vault**. We keep `accounts`, `account_mappings`, and `pkce_sessions` as strictly relational tables for OAuth flows and Fernet encryption.
- **The "Service Account" Pattern:** For service-level secrets (like a Spotify Client ID), the SDK stores them in the `accounts` table under `account_id = 0` tied to the `service_id`. Actual user OAuth accounts start at `account_id >= 1`.
- **Strict Access Control:** `sdk.accounts.get_token()` will block read requests unless the plugin possesses **Privileged Mode** (Root Access) granted by the user.

**API Contract Changes:**

- Token lookup logic is unified internally, simplifying the backend, though the frontend OAuth routes remain largely unchanged.

## 15. Deprecation & The Great "Provider" Migration

**Current State:**
The concept of "Providers" is deeply embedded. `core/provider.py` acts as a monolithic hub containing the `ProviderRegistry`, Enums (`ProviderCapabilities`), and specialized interfaces (`MediaServerProvider`, `DownloaderProvider`, etc.). It is imported by over 40 core files.

**Legacy Debt / Dead Code:**
- `ProviderRegistry` is completely obsolete (state is now handled by `config.db` and `plugin_loader`).
- The term "Provider" is deprecated in favor of "Plugin".
- Hardcoded references in `core/settings.py` (e.g., `"active_media_server"`, `"spotify": {...}`) must be removed.
- All built-in plugins in the source code repository (`providers/` directory) are dead weight.

**The Gap:**
- **Phase A (Separation of Concerns):** 
    - Move `ProviderRegistry` and all runtime plugin management logic into `core/plugin_loader.py`. It will be renamed to `PluginRegistry`. This ensures the registry is a "loader function" and prevents circular dependencies.
    - Extract Enums, Capabilities, and base Interfaces (e.g., `MediaServerPlugin`, `DownloaderPlugin`) into `core/plugin_sdk.py`.
- **Phase B (SDK Isolation):** The SDK becomes a standalone package with ZERO imports from the core engine. All plugins import from the SDK; the Loader imports both the SDK and the Core.
- **Phase C (Import Refactoring):** Surgically update all ~40 downstream files to pull interfaces from the SDK and registration/lookup from the Loader's `PluginRegistry`.
- **Phase D (Execution):** **DELETE ENTIRELY:** `core/provider_base.py` and `core/provider.py`.

**API Contract Changes:**
- Endpoint nomenclature must change from `/providers` to `/plugins`.
- App configuration payloads will no longer contain hardcoded `spotify_accounts` or `plex` configuration keys; these become dynamic plugin configuration payloads.
- **Note:** `active_media_server` remains in `config.json` as it is a global user preference, not a plugin-internal setting.

## 15.5 Deprecation

**Current State:**
The concept of "Providers" is deeply embedded. `core/provider_base.py`, `ProviderRegistry`, and monolithic integrations (Spotify, Plex, Tidal, Jellyfin) are hardcoded into settings and routes.

**Legacy Debt / Dead Code:**

- **DELETE ENTIRELY:** `core/provider_base.py`.
- **DELETE ENTIRELY:** `core/provider.py` (`ProviderRegistry`).
- Remove all built-in plugins from the source code repository (`providers/` directory).
- Remove hardcoded references in `core/settings.py` (e.g., `"active_media_server": "plex"`, `"spotify": {...}`).

**The Gap:**

- Replace `provider_base.py` with `core/plugin_sdk.py` containing the new decorators, KVS, and Route Jails.
- Transition purely to the term "Plugin" system-wide.
- Core engine must treat the `plugins/` directory purely as external dynamically loaded code.

**API Contract Changes:**

- Endpoint nomenclature must change from `/providers` to `/plugins`.
- App configuration payloads will no longer contain hardcoded `spotify_accounts` or `plex` configuration keys; these become dynamic plugin configuration payloads.

## 16. Authoritative Plugin State (Deprecating config.json arrays)

**Current State:**
EchoSync relies on an in-memory `PluginLoader` list and an insecure array in `config.json` (`disabled_providers`) to track what is active or crashed.

**Legacy Debt / Dead Code:**

- The `disabled_providers` array parsing logic in `config_manager`.
- The `POST /api/system/plugins/config` endpoint that accepts full arrays of disabled plugins.

**The Gap:**

- The `services` table in `config.db` becomes the absolute source of truth for plugin state.
- It must track `plugin_id`, `version_no`, `is_enabled` (boolean), `service_type`, `created_at`, and `updated_at`.
- When a plugin crashes, the AST Sandbox toggles `is_enabled = False` in the database.
- Dynamic unloading/reloading queries this table instead of `config.json`.

**API Contract Changes:**

- Add `POST /api/system/plugins/{plugin_id}/toggle` to accept `{"enabled": true/false}` and update the `services` table directly.
- **Database Migration:** A specific migration script must be authored to transform existing `config.db` structures and `config.json` data into the new `services` table schema.

## 17. Frontend & UI Migration (Frontend Scope)

**Current State:**
The frontend relies on `/api/providers` and hardcoded UI components for "Official" services.

**The Gap:**

- **Static Asset Serving:** Implement a backend route `/api/plugins/{plugin_id}/static/<path:filename>` that maps to the `static/` directory of the plugin. The frontend must use this to fetch icons, custom CSS, or logo assets.
- **Nomenclature Update:** All "Music Services" or "Providers" UI labels must be renamed to "Plugins".
- **Dynamic Config UI:** The Settings page must move from hardcoded forms (Spotify Client ID, etc.) to a dynamic form generator that renders input fields based on the schema returned by `GET /api/plugins/{plugin_id}/config`.
- **Endpoint Sync:** Update all API calls from `/api/providers/...` to `/api/plugins/...`.
- **Source Attribution:** Update the UI to handle the new `{source}.{author}.{plugin_name}` ID format, potentially showing pills for "Verified" or "Official" sources based on the new `plugin_store` verification logic.
