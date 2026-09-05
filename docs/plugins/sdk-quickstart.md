# Plugin Developer SDK Quickstart Guide

## 1. Overview

EchoSync plugin development is powered by the **Nexus Framework**. Plugins allow community developers to extend media provider integrations, metadata enhancers, matching rules, and Web UI interfaces.

---

## 2. Plugin Directory Anatomy

Every plugin resides in `/data/plugins/{author}.{plugin_name}/`:

```text
community.spotify/
├── manifest.json         # Plugin manifest and permissions
├── main.py               # Entry point class implementing Provider interface
├── storage_box.py        # Isolated storage helper
└── public/
    └── bundle.js         # Compiled Web Component UI bundle
```

---

## 3. Plugin Manifest Schema (`manifest.json`)

```json
{
  "plugin_id": "community.spotify.provider",
  "name": "Spotify Integration",
  "version": "1.0.0",
  "author": "EchoSync Community",
  "description": "Fetches metadata and playlist recommendations from Spotify.",
  "entry_point": "main:SpotifyPlugin",
  "capabilities": ["FETCH_METADATA", "PROVIDE_PLAYLISTS"],
  "supports_isrc_lookup": true,
  "metadata_richness": 85,
  "privileged": false,
  "components": {
    "music_service": "echosync-spotify-card"
  }
}
```

---

## 4. Writing a Plugin Entry Point

Plugins interact with EchoSync using `PluginStorageBox` from `core.nexus_framework.plugin_SDK`:

```python
from core.nexus_framework.plugin_SDK import PluginStorageBox


class SpotifyPlugin:
    def __init__(self):
        # Initialize storage facade with zero arguments
        self.sdk = PluginStorageBox()

    def on_plugin_startup(self, hook_manager, config_db):
        """Register hook handlers upon plugin load."""
        hook_manager.register_filter("pre_search_query", self.enhance_search_query)

    def enhance_search_query(self, query: str, target: dict) -> str:
        # Custom query enrichment logic
        return f"{query} spotify_enhanced"
```

---

## 5. Storage & Config Access

Plugins must store internal data and settings using `PluginStorageBox` API:

- `self.sdk.get_setting("api_key")`: Fetch plugin setting.
- `self.sdk.set_setting("api_key", value)`: Persist setting.
- `self.sdk.get_storage_path()`: Returns isolated plugin data folder.
