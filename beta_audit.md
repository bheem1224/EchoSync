# EchoSync Bug Hunt: The Beta Loop Audit Report

**Prepared by:** Principal Python Architect
**Scope:** v2.4.2 Plugin Ecosystem - Beta Plugin Loading Loop

## Executive Summary
I have conducted a deep-dive trace of the application boot sequence, module resolution logic, and UI manifest reporting endpoints. I can confirm that the infinite beta download loop is entirely caused by two major logic flaws in `core/plugin_loader.py`.

The configuration state is perfectly healthy, but the loader fails to correctly map to the `/beta/` subfolders during both Python dynamic importing and API manifest reporting. This results in the backend loading the Stable code while thinking it's on Beta, and reporting the Stable version to the SvelteKit frontend, which then continually prompts the user to upgrade to Beta.

---

### 1. The Race Condition Check
**Finding:** CLEAN. No race condition exists.

**Analysis:**
I traced the boot sequence from `run_api.py` -> `core/settings.py` -> `web/api_app.py`.
* The `config_manager` is instantiated globally in `core/settings.py`.
* During its `__init__`, it synchronously calls `_load_config()`, which parses `config/config.json`.
* `web/api_app.py` is executed, initializing the databases, and *then* instantiating `PluginLoader(app_root)`.
* The `beta_opt_in` flag (`ui.beta_plugin_ui`) and individual plugin channels (`plugins.{plugin_id}.channel`) are fully loaded and accessible in memory before `PluginLoader` ever scans a directory.

---

### 2. The Module Resolution Trace
**Finding:** CRITICAL FLAW in `core/plugin_loader.py`.

**Analysis:**
The issue occurs during the transition between directory scanning and module importing.

1. In `_scan_directory()` (lines 231-240), the logic correctly identifies when a plugin is on the beta channel and successfully redirects the `current_item` pointer to the `/beta/` subfolder:
   ```python
   channel = config_manager.get_plugin_channel(provider_name)
   if channel == 'beta' and (item / 'beta').exists():
       current_item = item / 'beta'
   ```
2. The `PluginSecurityScanner` correctly scans the beta source code using this updated `current_item`.
3. **THE BUG:** However, on line ~302, when calling the import helper, it uses the original parameters instead of the beta path:
   ```python
   self._load_provider_package(provider_name, directory.name, source_type)
   ```
4. In `_load_provider_package()` (line 355), the module path is built blindly using the parent directory:
   ```python
   module_path = f"{parent_dir_name}.{name}" # Results in "plugins.my_plugin"
   module = importlib.import_module(module_path)
   ```
5. Python's standard `sys.path` resolution takes over. Because the string is exactly `"plugins.my_plugin"`, Python looks for `/plugins/my_plugin/__init__.py` and imports the **Stable** version, completely ignoring the beta subfolder that was just securely scanned.

*Result: The beta code is completely bypassed during execution.*

---

### 3. The Manifest Reporting Check
**Finding:** CRITICAL FLAW in `get_all_plugins()` within `core/plugin_loader.py`.

**Analysis:**
The `GET /api/system/plugins` endpoint relies on the `get_all_plugins()` function to report the active version to the UI.

1. `get_all_plugins()` iterates over `plugins_dir` (starting line ~454).
2. **THE BUG:** It hardcodes the manifest path to the root of the plugin folder:
   ```python
   json_file = item / "manifest.json"
   ```
3. It entirely lacks the channel-checking logic found in `_scan_directory()`. It never checks `config_manager.get_plugin_channel(item.name)` to determine if it should be reading from `item / "beta" / "manifest.json"`.
4. As a result, the backend parses the `version` from the Stable manifest and serves it to the frontend.

*Result: The SvelteKit frontend receives the Stable version number. Since it knows the user wants Beta, and the store lists a higher Beta version, the UI correctly (from its perspective) assumes the system is outdated and prompts the user to download the Beta artifact again, creating the infinite loop.*

## Conclusion
To fix this bug in your clean production branch, you must update `core/plugin_loader.py`:
1. Refactor `_load_provider_package` or `_scan_directory` to dynamically alter the `importlib.import_module` path string to specifically target `.beta` when the beta channel is active (e.g., `importlib.import_module("plugins.my_plugin.beta")`).
2. Update `get_all_plugins()` to implement the same channel-checking logic used in `_scan_directory()`, ensuring it reads the `manifest.json` from the `/beta/` subfolder when applicable so the UI receives the correct version number.
