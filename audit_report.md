# Legacy Provider Data Trace & Nexus Architecture Audit Report

This report documents the architectural violations within the EchoSync codebase preventing the final transition to the Nexus Framework (a 100% agnostic plugin system).

## 1. Monolithic Config Dependencies (The God Object)

The `ConfigManager` (and `settings.py`) acts as a "God Object," hardcoding logic for specific services instead of utilizing an agnostic plugin schema.

* **File:** `core/settings.py`
  * **Violations:** Defines hardcoded configuration variables (`spotify_accounts`, `active_tidal_account_id`, `slskd_url`, `plex`, `jellyfin`, `navidrome`, `soulseek`, `listenbrainz`).
  * **Violations:** Defines hardcoded retrieval methods such as:
    * `get_spotify_config`, `get_spotify_accounts`, `add_spotify_account`, `update_spotify_account`, `set_active_spotify_account`, `get_active_spotify_account`, `get_spotify_active_credentials`
    * `get_tidal_accounts`, `add_tidal_account`, `update_tidal_account`, `set_active_tidal_account`, `get_active_tidal_account`
    * `get_plex_config`, `get_jellyfin_config`, `get_navidrome_config`, `get_soulseek_config`
  * **Trace:** These God Object methods are invoked throughout the codebase:
    * `core/account_manager.py:17` -> `config_manager.get_spotify_accounts()`
    * `core/backend_services.py:62` -> `config_manager.get_spotify_config()`
    * `services/health_check.py:60` -> `config_manager.get_spotify_config()`
    * `services/sync_service.py:664` -> `config_manager.get_spotify_accounts()`
    * `plugins/EchoSync/navidrome/client.py:292` -> `config_manager.get_navidrome_config()`
    * `plugins/EchoSync/spotify/routes.py:143` -> `config_manager.get_spotify_config()`
    * `plugins/EchoSync/jellyfin/client.py:368` -> `config_manager.get_jellyfin_config()`

## 2. Terminology & Legacy Database Drift

The ghost of the legacy monolithic "Provider" system is still heavily present in the codebase, both in terminology and database usage.

* **File:** `core/plugin_loader.py:876`
  * **Violation:** Legacy alias `ProviderRegistry = PluginRegistry` is actively mapping the old registry system to the new one.
* **File:** `core/plugin_store.py:623-687`
  * **Violation:** Legacy database table `config_kvs` is still being queried and updated alongside the new state management tables.
* **File:** `core/plugin_SDK.py:303-322`
  * **Violation:** The Plugin SDK uses the legacy `config_kvs` database table for storage (`SELECT value FROM config_kvs`).
* **File:** `database/migrations/config/versions/8f6df972e61a...py` & `database/config_database.py`
  * **Violation:** The `account_metadata` table is explicitly protected and actively used to store active user secrets/tokens instead of using the new unified secret facade.
* **File:** `services/download_manager.py:799-880`
  * **Violation:** Extremely heavy reliance on the `provider` terminology (e.g., `winning_provider_name`, `download_provider = provider`).
* **File:** `services/user_history_service.py:434-455`
  * **Violation:** Normalizing `provider` terminology (`interaction.provider`).

## 3. Core Agnosticism Violations

The core EchoSync engine explicitly imports plugin logic or checks for specific plugin namespaces, violating the strict Zero-Trust Plugin Sandbox and Core Agnosticism requirements.

* **File:** `core/account_manager.py` (Lines 16, 38, 68, 114)
  * **Violation:** Core engine explicitly checks `if service_name == 'spotify':` and `elif service_name == 'tidal':`.
* **File:** `core/settings.py` (Lines 893, 900, 976)
  * **Violation:** Core engine explicitly checks `if server not in ['plex', 'jellyfin', 'navidrome']:` and `if active_server == 'plex':`.
* **File:** `web/routes/playlists.py` (Lines 85, 89, 1399, 2012)
  * **Violation:** API layer checks `if provider_name == 'spotify':`, `if target == "plex":`.
* **File:** `web/routes/plugins_api.py` (Lines 293, 296)
  * **Violation:** Core route explicitly checks `if plugin_id == 'spotify':`.
* **File:** `web/routes/system.py` (Lines 343, 354, 359, 431)
  * **Violation:** Core route logic hardcodes colors and validations: `'color': '#1DB954' if plugin['id'] == 'spotify'`.
* **File:** `services/sync_service.py` (Lines 154, 159)
  * **Violation:** Core service checks `if active_server == "jellyfin":`.

## 4. Event Bus / SDK Verification

The core engine is bypassing the Nexus Framework SDK (`plugin_SDK.py`) and Event Bus, relying on legacy monolithic dictionary methods and explicit object instantiation.

* **File:** `plugins/EchoSync/*/client.py` & `routes.py` (e.g., Spotify, Navidrome, Jellyfin, Plex, Slskd, Acoustid)
  * **Violation:** All official plugins are bypassing the `PluginSDK` configuration facade (`self.sdk.config.get`) and are instead importing the monolithic `config_manager` directly to call `config_manager.get_jellyfin_config()` and `config_manager.get_spotify_config()`.
* **File:** `services/sync_service.py` (Lines 93, 106, 126, 132)
  * **Violation:** The `SyncService` is not utilizing the Event Bus or Plugin SDK discovery to find valid plugins. It hardcodes instance creation: `PluginRegistry.create_instance('spotify')`, `PluginRegistry.create_instance('plex')`, `PluginRegistry.create_instance('jellyfin')`.
* **File:** `services/download_manager.py` (Line 146, 342)
  * **Violation:** Direct tight-coupled client generation: `PluginRegistry.create_instance(active_client)`.
* **File:** `services/media_manager.py` (Line 94, 256)
  * **Violation:** Uses `PluginRegistry.create_instance(active_server)` instead of an abstracted event pipeline.

**Conclusion:**
Deleting the legacy `config_manager` God Object methods and strictly enforcing `PluginSDK` boundaries right now will result in catastrophic failure of the `SyncService`, `BackendServices`, `DownloadManager`, and `MediaManager`, along with breaking every official plugin's ability to fetch configuration data. A staged refactor is required to map these plugins to the new `_ConfigFacade` and `_SecretsFacade` before the monolithic functions can be purged.
