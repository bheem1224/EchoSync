# Nexus Framework Deep Audit Report

## Task 1: Plugin Registration & Instantiation Tracking

**The Issue:** `ValueError: Provider 'plex' not registered` when calling `PluginRegistry.create_instance()`.

**Root Cause:**
There is a mismatch between the namespace used when registering a plugin and the namespace used when trying to instantiate it in the background jobs.
- When `PlexClient` is registered, it defines its name as `EchoSync.plex` (`name = "EchoSync.plex"` in `plugins/EchoSync/plex/client.py`).
- `PluginRegistry.register` stores the provider under this full name, converting it to lowercase: `echosync.plex`.
- However, in `core/system_jobs.py` (specifically `run_database_update` and `register_media_server_scan_job`), the code fetches active servers via `PluginRegistry.get_active_services_by_type('media_server')` and then improperly strips the prefix by doing `.split('.')[-1]`:
  ```python
  active_server = active_servers[0].split('.')[-1] if active_servers else 'plex'
  provider = PluginRegistry.create_instance(active_server)
  ```
- Because of `.split('.')[-1]`, it requests `plex` instead of `echosync.plex`. Since the registry keyed it as `echosync.plex`, it raises `ValueError: Provider 'plex' not registered`.

**Conclusion:**
Background jobs must use the full plugin ID (e.g., `echosync.plex`) when calling `PluginRegistry.create_instance()` instead of stripping it back to the legacy short string (`plex`).


## Task 2: Svelte Web Component Theming Analysis

**The Issue:** Svelte Plugin Web Components (like `SpotifyCard.svelte` and `PlexCard.svelte`) are failing to inherit the global CSS Teal theme from the main app, despite attempts to use CSS variables like `var(--color-primary)` or `shadow="none"`.

**Root Cause:**
1. The Vite configuration in `vite.config.js` for the plugins sets `compilerOptions: { customElement: true }` for Svelte.
2. In Svelte 4+, compiling a component with `customElement: true` automatically encapsulates it inside a Shadow DOM.
3. The Shadow DOM completely isolates the internal CSS of the web component from the document's global CSS. By default, even CSS variables defined on `:root` or `body` in the main application will not pierce the shadow boundary unless they are explicitly targeted to the custom element tag, or if the variables are inheritable and the host element accepts them, but global selectors like class names are strictly isolated.
4. Setting `<svelte:options customElement="some-tag" />` enforces this Shadow DOM behavior. You cannot bypass it simply by setting `shadow="none"` as an attribute, because Svelte Custom Elements do not support a "light DOM" compilation target directly via that attribute.

**Architectural Reason:**
Svelte's custom element compilation enforces strict Web Component standards, which mandates Shadow DOM encapsulation to prevent style leakage. This isolates the component, stripping it of access to standard global style cascades from the `/webui/` main app.

**Conclusion:**
To resolve this, the architectural approach to Svelte Web Components must be adjusted. Either the global CSS variables need to be explicitly passed down via CSS custom properties that piece the shadow boundary, or the components must inject the main theme's CSS file explicitly into their Shadow DOM styles.


## Task 3: The "Provider" Purge & Dependency Trace

As part of the legacy purge, several functions and variables still utilize the old `provider` terminology and logic rather than the new `plugin` framework logic. Here is the dependency trace for the remaining legacy code:

### 1. `get_provider` & `get_providers_with_capability` & `get_providers_by_type` (in `core/plugin_loader.py`)
- **File/Line:** `core/plugin_loader.py` (lines 595, 712, 745, 989, 1000)
- **Function:** `get_plugin`, `PluginRegistry.get_providers_with_capability`, `PluginRegistry.get_providers_by_type`, `get_provider` (alias)
- **Dependency Trace:**
  - Required by `core/plugin_SDK.py` (line 76)
  - Required by `core/system_jobs.py` (line 606) for `acoustid`
  - Required by `core/models.py` (line 164)
  - Required heavily by `services/metadata_enhancer.py` (lines 140, 142, 166, 167, 258, 490, 491, 648) to resolve `Capability.FETCH_METADATA` and `Capability.RESOLVE_FINGERPRINT` via `mb_client` and `musicbrainz`.
  - Required by `services/isrc_lookup_service.py` (line 74)
  - Required by `services/auto_importer.py` (line 346)
  - Required by `services/download_manager.py` (line 129)
  - Required by `plugins/EchoSync/spotify/cache_manager.py` (line 20, 24)
- **Plugin Framework Alternative:** Refactor to `get_plugin`, `PluginRegistry.get_plugins_with_capability`, and `PluginRegistry.get_plugins_by_type`. `metadata_enhancer.py` needs to rely exclusively on capabilities rather than hardcoded string lookups like `"musicbrainz"`.

### 2. `active_server` (Hardcoded Media Server logic)
- **File/Line:** `core/media_scan_manager.py` (lines 57-71), `core/watchlist_scanner.py` (lines 569-571), `core/system_jobs.py` (lines 112-250)
- **Function:** `run_media_server_scan`, `run_database_update`, `check_track_exists`
- **Dependency Trace:**
  - Required by `services/sync_service.py` (lines 152-453) which still hardcodes `jellyfin` and `navidrome` checks based on `active_server`.
  - Required heavily by `services/media_manager.py` (lines 79-327) which manually maps `active_server` string names to track sync removal and path mappings.
- **Plugin Framework Alternative:** Replace `active_server` variables with `active_plugins = PluginRegistry.get_active_services_by_type('media_server')`. `services/sync_service.py` should iterate over capabilities instead of switching on hardcoded string values like `"jellyfin"`.

### 3. `create_instance`
- **File/Line:** `core/plugin_loader.py` (lines 605, 739, 800, 816, 824, 862)
- **Function:** `PluginRegistry.create_instance`, `create_instance_by_type`
- **Dependency Trace:**
  - Required by `core/plugin_SDK.py` (line 80)
  - Required by `core/system_jobs.py` (line 126, 221)
  - Required by `core/backend_services.py` (lines 58, 68, 78, 88)
  - Required extensively by `services/sync_service.py` (lines 93, 106, 113, 126, 132, 138, 684, 759, 858, 978) which hardcodes instances for `'spotify'`, `'plex'`, `'jellyfin'`, and `'navidrome'`.
  - Required by `services/download_manager.py` (lines 146, 342)
  - Required by `services/user_history_service.py` (line 83)
  - Required by `services/media_manager.py` (lines 98, 313)
  - Required by `plugins/EchoSync/spotify/routes.py` (line 66) and `plugins/EchoSync/spotify/client.py` (line 765)
- **Plugin Framework Alternative:** Rename `create_instance` to `instantiate_plugin`. Refactor `sync_service.py` to stop explicitly instantiating plugins by static string names (`'spotify'`) and instead rely on dependency injection or interface capabilities dynamically provided by the `PluginRegistry`.
