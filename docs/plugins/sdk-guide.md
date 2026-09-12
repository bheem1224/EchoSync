# EchoSync Plugin SDK Developer Guide

## 1. Overview

The Nexus Plugin Framework (`core/nexus_framework/`) allows developers to extend EchoSync with custom metadata providers, media server integrations, download clients, and UI web components. Plugins execute within zero-trust sandboxed sub-applications mounted under `/api/v1/plugins/{plugin_id}/`.

---

## 2. Plugin Structure & Manifest (`plugin.json`)

Every plugin must be contained within a dedicated directory under `plugins/` and specify a manifest:

```json
{
  "plugin_id": "com.example.myplugin",
  "name": "My Plugin",
  "version": "1.0.0",
  "description": "Custom metadata provider plugin",
  "author": "Developer",
  "entrypoint": "main.py",
  "capabilities": ["metadata_provider", "download_client"],
  "permissions": ["network_outbound", "storage_box"]
}
```

---

## 3. StorageBox SDK Usage

Plugins must never perform raw file operations or direct SQL queries against core databases. Storage management routes strictly through `PluginStorageBox`:

```python
from core.nexus_framework.plugin_SDK import PluginStorageBox

storage = PluginStorageBox()
# Store encrypted key-value settings
storage.set_setting("api_key", "secret_value")
# Read setting
api_key = storage.get_setting("api_key")
```

---

## 4. WASM Plugin Runtime

EchoSync supports WebAssembly (WASM) sandboxed execution via `WasmPluginWrapper`. WASM plugins execute in completely isolated memory spaces with explicit capability boundaries.
