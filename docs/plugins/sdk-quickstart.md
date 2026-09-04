# Plugin SDK Quickstart & Developer Guide

## 1. Overview & Architecture

EchoSync provides a dynamic, event-driven plugin ecosystem powered by the **Nexus Framework**. Plugins allow developers to extend EchoSync with new metadata providers, media server integrations, download clients, custom matching rules, and custom dashboard UI components.

---

## 2. Directory Layout of a Plugin

Plugins must follow a strict directory structure within the `plugins/` folder:

```text
plugins/
└── EchoSync/
    └── my_custom_plugin/
        ├── manifest.json            # Plugin manifest and permissions
        ├── __init__.py              # Entry point exporting ProviderClass
        ├── provider.py              # Main plugin logic inheriting from PluginBase
        ├── ui_manifest.json         # Optional Web Component UI registration
        └── ui/                      # Optional frontend assets
            └── plugin-component.js  # Compiled Custom Element JS bundle
```

---

## 3. Manifest Specification (`manifest.json`)

```json
{
  "id": "EchoSync.MyCustomPlugin",
  "name": "My Custom Plugin",
  "description": "Integrates custom metadata provider into EchoSync",
  "version": "1.0.0",
  "author": "CommunityDev",
  "type": "metadata",
  "plugin_id": "my_custom_plugin",
  "min_echosync_version": "2.4.0",
  "requirements": [],
  "hooks": ["ON_ENGINE_EVALUATE", "pre_normalize_title"],
  "settings": {
    "api_key": {
      "type": "string",
      "default": "",
      "description": "API Key for authentication"
    }
  }
}
```

---

## 4. Implementing the Plugin Entry Point

```python
from core.plugin_sdk import PluginBase, PluginStorageBox

class MyCustomPlugin(PluginBase):
    def __init__(self):
        super().__init__()
        self.storage = PluginStorageBox()

    def on_plugin_startup(self, hook_manager, config_db):
        """Lifecycle hook fired when the plugin is loaded."""
        self.logger.info("Initializing MyCustomPlugin...")

        # Register custom filters
        hook_manager.add_filter("pre_normalize_title", self.handle_title_normalization)

    def handle_title_normalization(self, title: str, **kwargs) -> str:
        """Custom hook callback modifying track titles before scoring."""
        if "[Remastered]" in title:
            return title.replace("[Remastered]", "").strip()
        return title

# Export entry point
ProviderClass = MyCustomPlugin
```

---

## 5. Sandboxed Storage Access (`PluginStorageBox`)

Plugins must never execute raw SQLite or SQLAlchemy operations against core tables. Storage access is routed through `PluginStorageBox()`, which transparently isolates plugin key-value settings and tables inside `working.db`.
