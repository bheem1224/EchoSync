# Plugin Developer SDK Quickstart Guide

## 1. Overview

EchoSync plugin development is powered by the **Nexus Framework**. Plugins extend media provider integrations, metadata enhancers, matching rules, and Web UI interfaces.

## 2. Plugin Structure & Manifest

Every plugin resides in `plugins/<plugin_name>/` and must contain a `manifest.json`:

```json
{
  "plugin_id": "com.example.myplugin",
  "name": "My Custom Plugin",
  "version": "1.0.0",
  "author": "Developer",
  "entry_point": "plugin.py",
  "permissions": ["network_outbound", "storage_read"]
}
```

## 3. SDK Storage Box & Identity Safeguards

Plugins interact with EchoSync using the unified `PluginStorageBox()` facade from `core.nexus_framework.plugin_SDK`. Plugin identity is verified internally using physical file path provenance (`inspect.stack()`), eliminating spoofable identity parameters.
