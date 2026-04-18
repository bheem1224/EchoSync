# EchoSync v2.4.1 Plugin Architecture Audit Report

This report documents the findings from the security and architectural audit of the new "Total Freedom Plugin Architecture" introduced in EchoSync v2.4.1.

## 1. Implementation Verification

### CRITICAL: Missing Plugin Uninstallation Logic
**Finding:** The endpoint or mechanism to uninstall a plugin (`web/routes/plugins.py`, `core/plugin_store.py`) is completely missing. Without it, dropping the scoped plugin database tables (`DROP TABLE plugin_{id}_...`) is impossible, leading to orphaned tables and storage bloat when users try to remove a plugin.
**Remediation:** Implement an `uninstall` endpoint in `web/routes/plugins.py` that delegates to `plugin_store.py`. Crucially, it must query the SQLite master table for `plugin_{id}_%` and drop them before deleting the directory.

```python
# core/plugin_store.py
def uninstall_plugin(self, plugin_id: str) -> bool:
    dest_dir = self.plugins_dir / plugin_id
    if not dest_dir.exists():
        return False

    # Drop associated tables
    try:
        from database.working_database import get_working_database
        from database.music_database import get_database

        safe_id = re.sub(r'[^a-zA-Z0-9_]', '_', plugin_id).lower()
        prefix = f"plugin_{safe_id}_%"

        for db_engine in [get_working_database().engine, get_database().engine]:
            with db_engine.connect() as conn:
                tables = conn.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '{prefix}'").fetchall()
                for (table_name,) in tables:
                    conn.execute(f"DROP TABLE IF EXISTS {table_name}")
    except Exception as e:
        logger.error(f"Failed to drop tables for {plugin_id}: {e}")

    # Delete directory
    import shutil
    shutil.rmtree(dest_dir, ignore_errors=True)
    return True
```

### HIGH: Missing `ON_API_STARTUP` Hook Injection
**Finding:** The `ON_API_STARTUP` hook documented in `HOOKS_REFERENCE.md` is completely absent from the actual source code (`web/api_app.py` and `core/plugin_loader.py`). Plugins relying on this hook to register custom Blueprints or run initialization logic will fail to execute.
**Remediation:** Inject the hook execution in `web/api_app.py` immediately before the backend services thread is started or inside the Blueprint registration loop.

```python
# web/api_app.py (Inside create_app)
from core.hook_manager import hook_manager

# Register Dynamic Blueprints from Providers/Plugins
for bp in loader.get_all_blueprints():
    try:
        app.register_blueprint(bp)
    except Exception as e:
        print(f"[ERROR] Failed to register blueprint {bp.name}: {e}")

# INJECT HOOK HERE
try:
    hook_manager.apply_filters('ON_API_STARTUP', app)
except Exception as e:
    print(f"[ERROR] Failed to execute ON_API_STARTUP hook: {e}")
```

### HIGH: Blocking `pip install` on Startup
**Finding:** In `core/plugin_venv.py`, the `subprocess.run` call for `pip install` is entirely blocking and synchronous during the initial plugin load cycle. For a large number of plugins or slow connections, this will severely delay the application boot process or cause WSGI timeouts.
**Remediation:** If `requirements` exist, the batch installation should either be triggered asynchronously or pushed to the `job_queue` so the core UI can boot up while plugins are initializing in the background. Note: Because plugins are loaded dynamically and require these dependencies immediately, a loading state mechanism should be introduced if async.

---

## 2. Crash Isolation (Sandboxing)

**Status:** Robust.
- The `try/except` boundaries around `hook_manager.apply_filters` correctly swallow exceptions to prevent the main execution loop from halting. It even handles async rejections smoothly (closing coroutines to silence `ResourceWarning`).
- Dynamic imports in `_load_provider_package` are well-isolated. A catastrophic `SyntaxError` or missing dependency inside a community plugin will safely fallback to disabling the plugin via `config_manager`.

---

## 3. Zero-Trust Security & Exploit Check

### CRITICAL: Path Traversal (Zip Slip) in `PluginStore`
**Finding:** The custom zip extraction logic in `core/plugin_store.py` dynamically resolves the destination by slicing `target_prefix` off the zip's internal `zi.filename`, but it never validates if `rel_path` contains directory traversal sequences like `../../`. A malicious plugin zip can overwrite host configuration files (e.g., `../../config.db`).
**Remediation:** Use Python's `os.path.abspath` or `pathlib.Path.resolve` to verify the final written path strictly resides inside `dest_dir`.

```python
# core/plugin_store.py
rel_path = zi.filename[len(target_prefix):]
if rel_path:
    # REMEDIATION: Sanitize path
    if '..' in rel_path or rel_path.startswith('/'):
        logger.error(f"Malicious path detected in zip: {rel_path}")
        return False

    target_file = (dest_dir / rel_path).resolve()

    # Double check it hasn't escaped the dest_dir sandbox
    if not str(target_file).startswith(str(dest_dir.resolve())):
        logger.error(f"Zip Slip prevented for: {target_file}")
        return False

    target_file.parent.mkdir(parents=True, exist_ok=True)
    with target_file.open('wb') as f:
        f.write(z.read(zi))
```

### HIGH: Database Table Spoofing (`plugin_orm.py`)
**Finding:** The `get_plugin_base` factory dynamically sets the table prefix. However, if a malicious plugin author explicitly overrides `__tablename__` inside their model definition *and* accesses the core engine directly (since `database` imports aren't blocked in `PluginSecurityScanner`), they can overwrite core tables like `tracks`.
**Remediation:** Enforce strict SQLAlchemy engine sandboxing or block `database` module imports in `core/plugin_loader.py` AST scanner.

```python
# core/plugin_loader.py (PluginSecurityScanner)
def visit_Import(self, node: ast.Import) -> None:
    for alias in node.names:
        # ADD 'database' to forbidden imports
        if alias.name.split('.')[0] in ("os", "subprocess", "sqlite3", "sys", "importlib", "database"):
            self.violations.append((node.lineno, f"forbidden import '{alias.name}'"))
```

### MEDIUM: Secrets Gateway Cross-Access
**Finding:** `_PluginSecrets` uses `self.plugin_id` to namespace secrets. Because `ProviderBase.name` is a mutable class attribute, a plugin can dynamically change `self.name = "spotify"` and then call `self.secrets.get("refresh_token")` to steal OAuth tokens belonging to other plugins.
**Remediation:** The `name` attribute in `ProviderBase` should be enforced as a read-only property or validated via the registry so it cannot be mutated post-instantiation.

```python
# core/provider_base.py
class ProviderBase(ABC):
    def __init__(self):
        # Freeze the name to prevent reassignment
        self._name = self.name
        self.secrets = _PluginSecrets(self._name)
```
