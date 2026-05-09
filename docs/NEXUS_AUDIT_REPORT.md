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

## Task 1: The Namespace Eradication Audit

As part of the shift to using a 32-bit integer `plugin_id`, all string-based identifiers, namespaces, and routing parameters must be systematically replaced.

**API Routes using String Identifiers:**
- `web/routes/metadata.py` - `@bp.get("/isrc/<string:isrc>")` (Note: ISRC is a string standard, this may not be a plugin ID, but worth noting if it relates).
- `web/routes/plugins.py` - Contains routes using `<plugin_id>` that currently expect strings (like `plugin.name` or `core.spotify`):
  - `@bp.route('/<plugin_id>/ui/<path:filename>', methods=['GET'])`
  - `@bp.route('/<plugin_id>/static/<path:filename>', methods=['GET'])`
  - `@bp.route('/<plugin_id>/toggle', methods=['POST'])`
  - `clean_id = plugin_id.replace('core.', '').replace('plugin.', '').replace('.', '/')` (This cleaning logic proves it expects string names).
  - *Recommendation:* Update routes to `<int:plugin_id>`, query `config.db` to map to the local file path, and completely remove `clean_id` string replacing.

**Memory/Logic usage of `provider.name` / `provider_name` / `plugin_name`:**
- `core/plugin_loader.py` - `PluginRegistry._providers` is keyed by lowercase strings. The `get_plugin`, `create_instance`, `disable_provider`, and `enable_provider` methods all take `name: str`.
- `services/download_manager.py` - Extensively uses `winning_provider_name = provider.name` to track the best download source. All logs and cache lookups use this string.
- `services/state_listener.py` - Resolves account ID via string `provider_name` (`User.provider == provider_name`).
- `web/services/library_service.py` - Iterates over `provider_names = PluginRegistry.list_providers()` and creates instances via string names.
- `web/services/search_service.py` - Federates search via string `provider_name`. Dedup logic maps tracks back to `dedup_map[match_key]["sources"].append(provider_name)`.
- `web/routes/playlists.py` - Hardcoded provider name checks like `if provider_name == 'spotify':` to load accounts.

**Conclusion:**
The codebase is fundamentally wired to track plugins via string names (e.g. `'spotify'`, `'plex'`, `'local_server'`). Eradicating this requires changing the `PluginRegistry` to index by a database-issued `int` ID. Then, the database schema (e.g. `User.provider`) and caching logic must be migrated to foreign keys on `plugin_id`.

## Task 2: Logger Resolution Audit

When the system transitions fully to using `plugin_id` (a 32-bit integer), the current log outputs will degrade into unreadable integer traces (e.g., `[plugin 4912]`).

**Current Logging Architecture:**
- `core/tiered_logger.py` uses a `SourceTagAdapter` class to intercept and format log messages.
- The `_derive_tag(self, name: str)` method splits the logger name (e.g., `plugins.4912`) and injects it into the log prefix via `return f"[plugin {parts[1]}]"`.
- `core/plugin_SDK.py` exposes a `logger` property for plugins: `get_logger(f"plugin.{self._name}")`. Once `_name` becomes an integer `plugin_id`, the adapter will simply print `[plugin <id>]`.

**Architectural Solution (Runtime Translation):**
To keep logs human-readable without polluting the core execution pipeline with heavy string lookups, we should inject a translation layer specifically into `SourceTagAdapter`:
1. Maintain an asynchronous/lightweight RAM cache (or rely on `config.db` directly if it uses SQLite's WAL mode for fast reads) mapping `plugin_id (int) -> plugin_name (str)`.
2. Inside `SourceTagAdapter._derive_tag`, intercept the integer ID.
3. Attempt to resolve the integer ID against the RAM cache right before string formatting.
4. If resolution succeeds: `[plugin {resolved_name}]`. If it fails: `[plugin ID:{plugin_id}]`.
5. This ensures the engine operates purely on `int` values for speed, and only spends clock cycles converting to strings at the edge when formatting terminal/file strings for humans.

## Task 3: Core Bias & Provider Ghosts Audit

The core logic should not be biased toward any specific provider. The Nexus Framework dictates that the Core handles generic objects (like `EchosyncTrack` and `EchosyncPlaylist`), while plugins handle their proprietary formatting.

**Core Bias Violations Found:**
1. `services/sync_service.py` is deeply biased toward Spotify:
   - Contains a hardcoded class `class SpotifyPlaylist:` (Line 29). This class should be a generic `EchosyncPlaylist` object.
   - Contains methods heavily tailored to Spotify API concepts, like `_get_spotify_playlist`, `_get_all_spotify_playlists`, and explicitly references `spotify_track: EchosyncTrack`.
   - Iterates specifically through `self.spotify_clients` using hardcoded string lookups for the `'spotify'` plugin.
   - Evaluates download intents by searching specifically for `spotify_id = identifiers.get("spotify")` and calling `wishlist_service.add_spotify_track_to_wishlist()`.
2. `services/health_check.py` looks explicitly for `spotify` via `config_db.get_or_create_service_id('spotify')` and fetches `spotify_creds`.

**Architectural Violation:**
The synchronization and media layer logic is fundamentally coupled to the concept that Spotify is the source of truth, rather than treating Spotify as just another "Playlist Provider" plugin.

**Conclusion:**
To respect the Nexus framework, `services/sync_service.py` must be completely stripped of the word "Spotify". It should accept a generic `EchosyncPlaylist` from any plugin that supports `Capability.READ_PLAYLIST`, process the `EchosyncTrack` objects within it, and output generic `DOWNLOAD_INTENT` actions without checking if the track originated from Spotify.

## Task 4: Unnecessary Abstractions & Helper Bloat Audit

The Nexus Framework dictates that core logic should use raw, standard functions, minimizing middleware wrappers (with the exception of `core/plugin_sdk.py`).

**Helper Bloat & Abstraction Leaks Found:**
1. `time_utils.py`
   - **Issue:** The file contains wrappers like `utc_now()` which merely returns `datetime.now(UTC)`, and `ensure_utc()` / `parse_utc_datetime()`. While useful in a massive monolith, this acts as middleware over standard library `datetime` objects.
   - **Recommendation:** Fold custom SQLAlchemy types (`UTCDateTime`) directly into `core/models.py`. Standardize timestamps directly in the core using native Python `datetime` objects rather than routing them through a generic `time_utils` script.
2. `core/network_utils.py`
   - **Issue:** Contains `get_lan_ip()` which wraps standard socket logic and `get_main_app_port()` which simply queries the `config_manager`.
   - **Recommendation:** Collapse `get_main_app_port()` into `settings.py` where the config manager actually resides. Inline `get_lan_ip()` into the network bootloader, as a standalone utility file for a 5-line standard socket ping is unnecessary bloat.
3. `core/plugin_orm.py`
   - **Issue:** Provides `get_plugin_base` and `copy_table_data` middleware to dynamically generate SQL table names (`plugin_musicbrainz_cache`) and perform basic SQL inserts for plugins switching channels.
   - **Recommendation:** This is a severe abstraction leak. Plugin ORM management should be consolidated directly into `core/plugin_sdk.py` or the `core/migrations.py` database module.

**Conclusion:**
Dismantle standalone utility files that exist simply to wrap standard library functions. Move database migrations to `migrations.py`, config lookups to `settings.py`, and eliminate generic `<subject>_utils.py` files to enforce linear execution without bouncing through middleware abstractions.
