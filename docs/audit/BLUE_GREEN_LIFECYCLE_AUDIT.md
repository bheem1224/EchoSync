# BLUE_GREEN_LIFECYCLE_AUDIT.md

## 1. The `plugin_id` Mandate
### The Bug
Plugins are still frequently referenced, loaded, and manipulated using their string `namespace` (or derived paths) rather than the strict 32-bit integer `plugin_id`. This causes mismatches between the database state and the runtime state.

### Symptoms & Empirical Proof
In `core/plugin_store.py`:
- `get_plugin_channel`, `_fork_namespace`, `_abort_namespace`, `_cutover_namespace`, and `rollback_plugin` still accept `plugin_id: str` and use it as a string namespace for database lookups in `config_kvs` and `plugin_state_kvs`.
- Pathing relies heavily on `.replace('core.', '').replace('plugin.', '')` to guess physical directory locations rather than querying the `services` table for a confirmed state.

In `core/plugin_loader.py`:
- `PluginRegistry.create_instance` attempts to resolve a `plugin_id` (integer) back to a `namespace` string for lookup using `db.get_service_name(plugin_id)`.
- It uses string-based names for managing disabled plugins (e.g., `_disabled_providers.add(name.lower())`).

### Proposed Architectural Solution
- Completely phase out string-based plugin namespaces (`plugin.author.name`) in the database KVS tables (`config_kvs`, `plugin_state_kvs`) and use the integer `plugin_id`.
- Update `PluginStore` and `PluginLoader` to only accept and route based on `plugin_id` (integer).
- Drop all `replace('plugin.', '')` path-guessing logic in favor of explicitly storing the absolute physical installation path in the database.

## 2. The Channel Opt-In Failure
### The Bug
The Beta vs. Stable channel preference is dropping during updates because the WebUI sends the fallback logic incorrectly, and the backend relies on payload state over DB state.

### Symptoms & Empirical Proof
In `web/routes/plugins.py`:
```python
def update_plugin():
    data = request.json or {}
    plugin_info = data.get('plugin')
    channel = data.get('channel') or (plugin_info.get('channel') if plugin_info else 'stable')
    if channel == 'release': channel = 'stable'
```
If `data.get('channel')` is undefined, it defaults to the `plugin_info`'s channel, or falls back to `stable`. If a plugin is already installed on `beta`, but the frontend payload drops the channel flag during the update request, the backend quietly overwrites the setting to `stable`.
Additionally, `PluginStore.update_plugin` will then download the stable ZIP and execute `config_manager.set(f'plugins.{clean_id}.channel', channel)` overwriting the user's previous beta opt-in in the database.

### Proposed Architectural Solution
- The API endpoint (`/update`) should query the `config_manager` for the currently installed channel of the plugin using its `plugin_id` if the payload does not explicitly mandate a channel override.
- Never fall back to `stable` implicitly during an update if the database explicitly says `beta`.

## 3. The Pathing Hypothesis (Derivation vs. State)
### The Bug
Path derivation is brittle. The current logic uses string manipulation to guess paths:
```python
clean_id = plugin_id.replace('plugin.', '').replace('core.', '')
folder_path = clean_id.replace('.', '/')
dest_dir = self.plugins_dir / folder_path
```
If a plugin's internal structure or extraction mechanism deviates, this guarantees a 404/ModuleNotFoundError.

### Symptoms & Empirical Proof
The `PluginLoader` struggles to dynamically load plugins because `sys.modules` aliasing fails to resolve submodule disk paths correctly without absolute paths. The Principal Architect's hypothesis is correct: dynamic string-replace path guessing is fundamentally unsafe.

### Proposed Architectural Solution
- Modify the `services` table in `config.db` to include a new column: `absolute_install_path` (VARCHAR).
- Upon successful ZIP extraction in `PluginStore.install_plugin`, write the absolute physical path of the extracted `__init__.py` directory to `absolute_install_path`.
- Modify `plugin_loader.py` to read `absolute_install_path` from the DB during instantiation. It can then safely inject this absolute path into `sys.path[0]` inside a strict `try...finally` block, completely eliminating the need to guess the namespace structure.

## 4. The Memory Purge (Uninstall/Rollback)
### The Bug
The hot-unload logic in `PluginStore.uninstall_plugin` is leaking memory. It assumes the plugin was imported with the prefix `plugins.`, but if it was loaded directly, the zombie references survive.

### Symptoms & Empirical Proof
Using an empirical test script (`test_plugin_unload.py`):
When a plugin is loaded directly into `sys.path` (e.g., `import mockauthor.mockplugin`), the module appears in `sys.modules` without the `plugins.` prefix.
However, `PluginStore.uninstall_plugin` attempts to purge:
```python
module_names = [f"plugins.{purge_id.replace('/', '.')}", f"plugins.{clean_id}"]
```
Because the `sys.modules` keys don't have the `plugins.` prefix in certain dynamic loading scenarios, the purge completely misses the loaded modules.

Test Output:
```text
Purge ID: mockauthor/mockplugin
Module Names to purge: ['plugins.mockauthor.mockplugin', 'plugins.mockauthor.mockplugin']
Survived modules: ['mockauthor', 'mockauthor.mockplugin.module_a', 'mockauthor.mockplugin']
```
These zombie references remain active in memory, preventing a clean reinstall/rollback until a full server restart.

### Proposed Architectural Solution
- `PluginLoader` must track the exact `sys.modules` keys that were loaded during the `try...finally` micro-venv injection block.
- Instead of guessing prefix strings (`plugins.`), `uninstall_plugin` should traverse `sys.modules` and pop any module whose `__file__` attribute originates from within the plugin's `absolute_install_path`.
