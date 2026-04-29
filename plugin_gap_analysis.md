# EchoSync Plugin Architecture: Surgical Refactor Gap Analysis

## 1. Strict Namespacing
**Current State:**
Plugins are loaded from `providers/` (core) and `plugins/` (community). The `plugin_loader.py` dynamically determines IDs like `plugin.{name}` based on folder structure, but there is no strict enforcement of a deterministic `{source}.{author}.{plugin_name}` namespace format, nor are folder names strictly mapped to this scheme.

**Legacy Debt / Dead Code:**
- `PluginLoader._load_provider_package` constructs IDs manually: `provider_id = f"plugin.{name}" if source_type == 'community' else name`.
- Logic differentiating between 'core' (`providers/`) and 'community' (`plugins/`) namespaces must be removed.

**The Gap:**
- `plugin_loader.py` and `plugin_store.py` must enforce that the folder name perfectly matches the `{source}.{author}.{plugin_name}` format.
- All internal dictionaries and database relationships must strictly use this fully qualified ID.

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

## 7. Key-Value Store (KVS)
**Current State:**
`ProviderStorageBox` in `database/working_database.py` allows providers to create raw SQL tables dynamically using SQLAlchemy metadata. `_PluginConfig` and `_PluginSecrets` exist in `provider_base.py`.

**Legacy Debt / Dead Code:**
- `ProviderStorageBox` and dynamic table creation via `engine.connect()` should be heavily scrutinized or replaced entirely by a simple KVS.
- `_PluginConfig` and `_PluginSecrets` in `provider_base.py`.

**The Gap:**
- Create a unified `plugin_kvs` table in `working.db` (Columns: `plugin_id`, `key`, `value` [JSON/String]).
- Implement `sdk.kvs.set()` and `sdk.kvs.get()` to interact with this table, abstracting the database entirely.

**API Contract Changes:**
- None directly, but plugins will store data differently.

## 8. Native Task Scheduler
**Current State:**
`core/job_queue.py` provides an in-memory task scheduler. Plugins currently don't have a clean, declarative way to register jobs; `plex/routes.py` manually registers one-shot jobs.

**Legacy Debt / Dead Code:**
- Manual job registration calls scattered in plugin code.

**The Gap:**
- Expose an `@sdk.schedule(interval="X")` decorator in the new SDK.
- The SDK must parse the decorator at load time and push a `ScheduledJob` into `JobQueue` tagging it with the `plugin_id`.

**API Contract Changes:**
- None.

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
- Core providers loaded from `providers/` bypass these checks implicitly.

**The Gap:**
- Core and 3rd-party plugins must be loaded identically.
- Any `"verified_source"` string inside a downloaded `manifest.json` must be forcefully stripped.
- The Core must re-apply the `verified_source` flag *only* if the download URL matches a cryptographically signed repo or a hardcoded trusted source list.

**API Contract Changes:**
- None.

## 13. Database Scoping
**Current State:**
Plugins use `ProviderStorageBox` for `working.db`. However, `_PluginModelFacade` in `provider_base.py` exposes raw SQLAlchemy models (`Track`, `Album`, `Artist`) connected to `music_library.db`, granting full write access.

**Legacy Debt / Dead Code:**
- `_PluginModelFacade` granting write-capable SQLAlchemy objects to plugins.

**The Gap:**
- The SDK must provide Read-Only proxy objects or specific accessor methods (e.g., `sdk.library.get_track()`) for `music_library.db`.
- Write operations must go through the EventBus or specific core API requests, never direct DB manipulation.
- Plugins can only write to their specific table or the KVS in `working.db`.

**API Contract Changes:**
- None.

## 14. Secrets Scoping
**Current State:**
`_PluginSecrets` fetches secrets from `config.db` using `f"plugin_{self.plugin_id}"`.

**Legacy Debt / Dead Code:**
- `core/settings.py` handles monolithic, hardcoded legacy secrets (e.g., `spotify.client_secret`, `plex.token`).

**The Gap:**
- The SDK must isolate `sdk.config.get_secret()`.
- Accessing global/core system secrets must require explicit permission (e.g., a prompt) and cannot be read silently.

**API Contract Changes:**
- None directly.

## 15. Deprecation
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
