import threading
"""Dynamic plugin loader for Echosync providers and plugins."""

import ast
import importlib
import os
import sys
import json
from pathlib import Path
from typing import Type, TypeVar, Protocol, List, Optional, Dict, Any

from flask import Blueprint

from core.enums import Capability

from core.nexus_framework.plugin_SDK import PluginBase, DownloaderProvider, MediaServerProvider, SyncServiceProvider
from core.tiered_logger import get_logger
from core.settings import config_manager

logger = get_logger("plugin_loader")
import zlib
import types


def generate_plugin_id(name: str) -> int:
    """Generate a consistent 32-bit integer ID from a plugin name."""
    return zlib.crc32(name.encode('utf-8')) & 0xFFFFFFFF


def get_relative_entry_path(url_or_path: str) -> str:
    """
    Extracts the relative path within the plugin's install directory from
    absolute paths, relative paths, or URL paths (e.g. `/api/system/plugins/spotify/static/bundle.js` -> `static/bundle.js`).
    """
    if not url_or_path:
        return ""
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        return url_or_path
    
    # Normalize slashes
    normalized = url_or_path.replace("\\", "/").lstrip("/")
    parts = normalized.split("/")
    
    # 1. Check for /api/system/plugins/<plugin_id>/<relative_path>
    if len(parts) >= 4 and parts[0] == "api" and parts[1] == "system" and parts[2] == "plugins":
        return "/".join(parts[4:])
    # 2. Check for /api/plugins/<plugin_id>/<relative_path>
    elif len(parts) >= 3 and parts[0] == "api" and parts[1] == "plugins":
        return "/".join(parts[3:])
    # 3. Check for /plugins/<plugin_id>/<relative_path>
    elif len(parts) >= 2 and parts[0] == "plugins":
        return "/".join(parts[2:])
        
    return normalized


def _sync_ui_components_to_db(plugin_id: int, install_path: str, is_core: bool = False) -> None:
    """Read ui_manifest.json once and UPSERT component definitions into ui_components.

    Called during plugin boot and installation.  Handles orphan cleanup for
    components that are no longer declared in the manifest.
    """
    from database.config_database import get_config_database
    from database import execute_write

    manifest_path = Path(install_path) / "ui_manifest.json"
    resolved_manifest = manifest_path if manifest_path.exists() else None
    if not resolved_manifest:
        # Check standard and beta fallbacks just in case
        manifest_path = Path(install_path) / "beta" / "ui_manifest.json"
        resolved_manifest = manifest_path if manifest_path.exists() else None
        if not resolved_manifest:
            return
    manifest_path = resolved_manifest

    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("UI Registry operation failed due to an unexpected error.")
        logger.debug(f"Raw exception data: {exc}", exc_info=True)
        return

    raw_components = manifest_data.get("components", {})
    raw_assets = manifest_data.get("assets", {})

    # Derive canonical bundle URL
    plugins_dir = Path(config_manager.get_plugins_dir())
    try:
        relative_path = Path(install_path).resolve().relative_to(plugins_dir.resolve())
        parts = list(relative_path.parts)
        if parts and parts[-1] == "beta":
            parts.pop()
        folder_name = ".".join(parts)
    except Exception:
        folder_name = Path(install_path).name
    default_bundle = f"/api/system/plugins/{folder_name}/static/bundle.js"
    bundle_url = (
        raw_assets.get("js")
        or raw_assets.get("bundle.js")
        or raw_assets.get("main")
        or default_bundle
    )

    # Collect (tag_name, component_type, entry_path) tuples
    entries: list[tuple[str, str, str]] = []
    for category, value in raw_components.items():
        if isinstance(value, str):
            rel_path = get_relative_entry_path(bundle_url)
            entries.append((value, category, rel_path))
        elif isinstance(value, dict):
            tag = value.get("element_tag", "")
            entry = value.get("bundle_url") or bundle_url
            if tag:
                rel_path = get_relative_entry_path(entry)
                entries.append((tag, category, rel_path))

    # Also materialise views as component_type="view"
    for view in manifest_data.get("views", []):
        if isinstance(view, dict) and view.get("id"):
            tag = f"es-view-{view['id']}"
            yaml_path = view.get("yaml_path", "")
            rel_path = get_relative_entry_path(yaml_path)
            entries.append((tag, "view", rel_path))

    if not entries:
        return

    db = get_config_database()
    tag_names_in_manifest = {e[0] for e in entries}

    def _upsert(cursor):
        for tag_name, comp_type, entry_path in entries:
            cursor.execute(
                """
                INSERT INTO ui_components (plugin_id, tag_name, component_type, entry_path, is_core, updated_at)
                VALUES (?, ?, ?, ?, ?, strftime('%s','now'))
                ON CONFLICT(tag_name) DO UPDATE SET
                    plugin_id      = excluded.plugin_id,
                    component_type = excluded.component_type,
                    entry_path     = excluded.entry_path,
                    is_core        = excluded.is_core,
                    updated_at     = strftime('%s','now')
                """,
                (plugin_id, tag_name, comp_type, entry_path, 1 if is_core else 0),
            )

        # Orphan cleanup: remove rows for this plugin that are no longer in manifest
        cursor.execute(
            "SELECT tag_name FROM ui_components WHERE plugin_id = ?", (plugin_id,)
        )
        existing = {row[0] for row in cursor.fetchall()}
        orphans = existing - tag_names_in_manifest
        for orphan_tag in orphans:
            cursor.execute(
                "DELETE FROM ui_components WHERE plugin_id = ? AND tag_name = ?",
                (plugin_id, orphan_tag),
            )

    try:
        execute_write(str(db.database_path), _upsert)
        logger.info(f"[UIRegistry] Synced {len(entries)} UI components for plugin {plugin_id}")
    except Exception as exc:
        logger.error("UI Registry operation failed due to an unexpected error.")
        logger.debug(f"Raw exception data: {exc}", exc_info=True)

# ---------------------------------------------------------------------------
# Zero-Trust Plugin Security Scanner
# ---------------------------------------------------------------------------
# Forbidden bare-name calls (Python builtins used for direct file I/O)
_FORBIDDEN_BARE_CALLS: frozenset = frozenset({"open", "__import__", "eval", "exec", "getattr", "setattr", "globals", "locals", "compile", "delattr", "memoryview", "input"})

# Forbidden module.method() patterns
_FORBIDDEN_MODULE_CALLS: dict = {
    "os": frozenset({"system", "popen", "fdopen", "kill", "execve", "spawn", "remove", "unlink", "rename", "rmdir", "mkdir", "chmod", "chown", "symlink", "link", "environ"}),
    "shutil": frozenset({"move", "copy", "rmtree"}),
    "importlib": frozenset({"import_module", "reload"}),
    "builtins": frozenset({"eval", "exec", "getattr", "setattr", "delattr", "open", "compile", "__import__", "globals", "locals", "memoryview", "input"}),
    "subprocess": frozenset({"*"}),
    "urllib": frozenset({"*"}),
    "pty": frozenset({"*"}),
    "posix": frozenset({"*"}),
    "tarfile": frozenset({"*"}),
    "zipfile": frozenset({"*"}),
    "codecs": frozenset({"*"}),
    "io": frozenset({"*"}),
    "dbm": frozenset({"*"}),
    "sys": frozenset({"modules", "exit"}),
}

# Forbidden method names on *any* receiver.
# pathlib.Path is the primary target; AST-only scanning cannot resolve types,
# so we match conservatively — plugins must not call these directly regardless
# of receiver type.  All legitimate I/O must go through LocalFileHandler.
_FORBIDDEN_METHOD_CALLS: frozenset = frozenset({"unlink", "write_text", "open"})


class PluginSecurityScanner(ast.NodeVisitor):
    """
    AST-based pre-load security scanner for community plugins.

    Walks the parse tree of each .py source file *before* importlib touches it
    and flags any raw file-I/O calls that bypass the LocalFileHandler gateway.

    Forbidden patterns detected
    ---------------------------
    - ``open(...)``                              bare builtin
    - ``os.remove/unlink/rename(...)``           direct OS-level ops
    - ``shutil.move/copy/rmtree(...)``           shutil destructive ops
    - ``<any>.unlink()``                         pathlib.Path.unlink
    - ``<any>.write_text()``                     pathlib.Path.write_text
    - ``<any>.open()``                           pathlib.Path.open (and builtin
                                                 open accessed as an attribute)
    """

    def __init__(self, privileged: bool = False) -> None:
        self.privileged = privileged
        # Each entry is (line_number, human_readable_description)
        self.violations: list = []
    def visit_Attribute(self, node: ast.Attribute) -> None:
        forbidden_attrs = {"__class__", "__base__", "__subclasses__", "__mro__", "__dict__", "__globals__", "__traceback__"}
        if node.attr in forbidden_attrs:
            self.violations.append((node.lineno, f"access to forbidden attribute '{node.attr}'"))
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id == "__builtins__":
            self.violations.append((node.lineno, "access to __builtins__ is forbidden"))
        self.generic_visit(node)


    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            base_module = alias.name.split('.')[0]
            if base_module in ("os", "subprocess", "sys", "importlib", "database", "inspect", "ctypes", "gc", "builtins"):
                if base_module == "database" and self.privileged:
                    continue # Allow core database if privileged
                if base_module in ("subprocess", "ctypes") and self.privileged:
                    continue
                self.violations.append((node.lineno, f"forbidden import '{alias.name}'"))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module in ("os", "subprocess", "sys", "importlib", "database", "inspect", "ctypes", "gc", "builtins"):
                if base_module == "database" and self.privileged:
                    pass # Allow core database if privileged
                elif base_module in ("subprocess", "ctypes") and self.privileged:
                    pass
                else:
                    self.violations.append((node.lineno, f"forbidden from-import '{node.module}'"))
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            if "config.db" in node.value:
                self.violations.append((node.lineno, "forbidden string literal containing 'config.db'"))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func

        if isinstance(func, ast.Name):
            # Pattern 1: bare open(...)
            if func.id in _FORBIDDEN_BARE_CALLS:
                self.violations.append(
                    (node.lineno, f"bare call to {func.id}()")
                )

        elif isinstance(func, ast.Attribute):
            attr = func.attr
            receiver = func.value

            # Pattern 2: module.method() — e.g. os.remove(), shutil.move()
            if isinstance(receiver, ast.Name):
                module = receiver.id
                forbidden_attrs = _FORBIDDEN_MODULE_CALLS.get(module)
                if forbidden_attrs and ("*" in forbidden_attrs or attr in forbidden_attrs):
                    self.violations.append(
                        (node.lineno, f"{module}.{attr}()")
                    )

            # Pattern 3: .unlink() / .write_text() / .open() on any receiver
            # (pathlib.Path is the primary target; conservative match is
            # intentional — plugins must not perform raw I/O at all)
            if attr in _FORBIDDEN_METHOD_CALLS:
                self.violations.append(
                    (node.lineno, f".{attr}() method call")
                )

        # Recurse into all child expressions
        self.generic_visit(node)




class PluginLoader:
    """
    Scans and loads providers from 'providers/' (core) and 'plugins/' (community).
    Registers them with the PluginRegistry and collects Flask blueprints.
    """

    _load_lock = threading.Lock()

    def __init__(self, app_root: Path):
        self.app_root = Path(app_root)
        self.plugins_dir = Path(config_manager.get_plugins_dir())
        self.loaded_blueprints: List[Blueprint] = []
        from core.hook_manager import hook_manager
        from database.config_database import get_config_database
        self.hook_manager = hook_manager
        self.config_db = get_config_database()


    def reload_plugin(self, plugin_id: int):
        """Perform a true Zero-Downtime hot reload of a plugin."""
        logger.info(f"🔄 HOT-SWAP INITIATED: {plugin_id}")
        
        # 1. Resolve Namespace and Channel from DB
        from database.config_database import get_config_database
        from pathlib import Path
        db = get_config_database()
        
        conn = db._open_connection()
        try:
            c = conn.cursor()
            c.execute("SELECT absolute_install_path, name, beta_opt_in FROM services WHERE plugin_id=?", (plugin_id,))
            row = c.fetchone()
            if row and row[0]:
                plugin_dir = Path(row[0])
                base_ns = row[1]
                is_beta = bool(row[2])
            else:
                raise ValueError(f"Plugin ID {plugin_id} not found in database for reload or missing absolute_install_path")
        finally:
            conn.close()

        clean_ns = base_ns.split('@')[0]
        channel = 'beta' if is_beta else 'stable'

        if not plugin_dir.exists():
            raise ValueError(f"Plugin directory {plugin_dir} does not exist.")

        logger.info(f"Reloading {plugin_id} ({channel}) from {plugin_dir}")


        # 2. Kill Workers
        try:
            from core.job_queue import job_queue
            job_queue.kill_jobs_by_plugin(plugin_id)
        except Exception as e:
            logger.warning("Failed to kill workers for the target plugin.")
            logger.debug(f"Raw exception data: {e}", exc_info=True)
            logger.debug(f"Raw exception data: {e}", exc_info=True)

        # 3. Purge Memory (Strict DB-Driven Unload)
        try:
            conn = db._open_connection()
            try:
                c = conn.cursor()
                c.execute("SELECT loaded_modules FROM services WHERE plugin_id=?", (plugin_id,))
                row = c.fetchone()
                if row and row[0]:
                    import json
                    loaded_modules = json.loads(row[0])
                    logger.debug(f"Purging {len(loaded_modules)} tracked modules for {plugin_id} from sys.modules")
                    for mod_ns in loaded_modules:
                        if mod_ns in sys.modules:
                            del sys.modules[mod_ns]
                else:
                    logger.warning(f"No loaded_modules array found for plugin_id {plugin_id}, skipping strict purge.")
            finally:
                conn.close()
        except Exception as e:
            logger.error(f"Failed to fetch or parse loaded_modules during reload: {e}")

        # 4. Reload Package
        try:
            disabled = config_manager.get_disabled_plugins()
            is_disabled = clean_ns in disabled or str(plugin_id) in disabled
            
            success = self._load_plugin_package(
                plugin_id,
                is_beta=(channel == 'beta'), 
                is_disabled=is_disabled
            )
            if success is False:
                raise Exception(f"Live-swap failed to load module for {plugin_id}")
            logger.info(f"✅ Successfully live-swapped: {plugin_id}")
        except Exception as e:
            logger.error("An error occurred during framework execution.")
            logger.debug(f"Raw exception data: {e}", exc_info=True)
            logger.debug(f"Raw exception data: {e}", exc_info=True)
            raise

    def reconcile_services(self):
        """
        Authoritative startup reconciliation to enforce schema integrity,
        prune orphaned records, and garbage collect physical files.
        """
        logger.info("Starting authoritative services registry reconciliation...")
        import sqlite3
        import binascii
        import shutil
        from database.config_database import get_config_database
        db = get_config_database()
        
        plugins_dir = Path(config_manager.get_plugins_dir())
        core_services = {'system'}
        app_root = self.app_root
        core_path = str((app_root / "core").resolve())

        def has_valid_entry_point(path: Path) -> bool:
            return (
                (path / "manifest.json").exists() or 
                (path / "__init__.py").exists() or 
                (path / "main.wasm").exists()
            )

        active_db_paths = set()

        conn = db._open_connection()
        try:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Fetch all records
            c.execute("""
                SELECT id, name, plugin_id, service_type, absolute_install_path, is_active, version, 
                       beta_opt_in, verified_source, privileged_mode, permissions 
                FROM services
            """)
            existing_rows = c.fetchall()
            
            seen_plugin_ids = set()
            seen_names = set()
            
            for row in existing_rows:
                db_id = row['id']
                name = row['name']
                p_id = row['plugin_id']
                install_path = row['absolute_install_path']
                
                is_duplicate = False
                if p_id in seen_plugin_ids or (name.lower() in seen_names and name.lower() == 'system'):
                    is_duplicate = True
                
                if p_id is not None:
                    seen_plugin_ids.add(p_id)
                seen_names.add(name.lower())
                
                # Core Service handling
                if name.lower() in core_services:
                    if is_duplicate:
                        c.execute("DELETE FROM services WHERE id=?", (db_id,))
                        continue
                    
                    target_plugin_id = binascii.crc32(name.lower().encode('utf-8')) & 0xFFFFFFFF
                    c.execute("""
                        UPDATE services 
                        SET plugin_id=?, absolute_install_path=?, version=?, service_type=?, is_active=?, 
                            description=?, beta_opt_in=?, verified_source=?, privileged_mode=?, permissions=?, 
                            updated_at=strftime('%s','now')
                        WHERE id=?
                    """, (target_plugin_id, core_path, '2.5.2', 'system', 1, 
                          f"{name.capitalize()} service", 0, 1, 1, '[]', db_id))
                    continue

                is_invalid = False
                reason = ""
                
                if is_duplicate:
                    is_invalid = True
                    reason = "Duplicate record"
                elif not install_path:
                    is_invalid = True
                    reason = "Empty absolute_install_path in database"
                else:
                    resolved_install = Path(install_path)
                    if not resolved_install.exists():
                        is_invalid = True
                        reason = f"Install path '{install_path}' does not exist on disk"
                    elif not has_valid_entry_point(resolved_install):
                        is_invalid = True
                        reason = f"Install path '{install_path}' does not contain entry points"
                    else:
                        active_db_paths.add(str(resolved_install.resolve()))

                if is_invalid:
                    logger.warning(f"🚨 Authoritative Pruning: Deleting invalid database record: {name} (ID: {db_id}, Reason: {reason})")
                    c.execute("DELETE FROM services WHERE id=?", (db_id,))
                    c.execute("DELETE FROM service_config WHERE service_id=?", (db_id,))
                    if p_id is not None:
                        c.execute("DELETE FROM ui_components WHERE plugin_id=?", (p_id,))
                    continue
                else:
                    disabled_plugins = config_manager.get_disabled_plugins() or []
                    is_disabled = (name in disabled_plugins) or (str(p_id) in disabled_plugins)
                    target_active = 0 if is_disabled else 1
                    c.execute("UPDATE services SET is_active = ? WHERE id = ?", (target_active, db_id))

            # Ensure all core services are present
            for name in core_services:
                target_plugin_id = binascii.crc32(name.lower().encode('utf-8')) & 0xFFFFFFFF
                c.execute("SELECT id FROM services WHERE plugin_id=?", (target_plugin_id,))
                if not c.fetchone():
                    logger.info(f"Bootstrapping missing core service: {name}")
                    c.execute("""
                        INSERT INTO services(name, plugin_id, service_type, description, absolute_install_path, version, is_active, 
                                             beta_opt_in, verified_source, privileged_mode, permissions, created_at, updated_at)
                        VALUES(?, ?, 'system', ?, ?, '2.5.2', 1, 0, 1, 1, '[]', strftime('%s','now'), strftime('%s','now'))
                    """, (name, target_plugin_id, f"{name.capitalize()} service", core_path))
            conn.commit()
        finally:
            conn.close()

        # Startup Garbage Collection Sweep
        if plugins_dir.exists():
            for author_item in list(plugins_dir.iterdir()):
                if not author_item.is_dir() or author_item.name.startswith('_') or author_item.name.lower() == 'system':
                    continue

                is_empty = True
                has_active_children = False

                for plugin_item in list(author_item.iterdir()):
                    is_empty = False
                    if str(plugin_item.resolve()) in active_db_paths:
                        has_active_children = True
                    elif plugin_item.is_dir():
                        
                        # check children like beta
                        for sub_item in plugin_item.iterdir():
                            if str(sub_item.resolve()) in active_db_paths:
                                has_active_children = True
                                break

                if is_empty or not has_active_children:
                    logger.info(f"Garbage collecting unused/orphaned plugin directory: {author_item}")
                    shutil.rmtree(author_item, ignore_errors=True)

    def load_all(self):
        """Scan and load all plugins based on database definitions."""
        logger.info("Starting plugin discovery from database...")
        
        safe_mode = os.environ.get('ECHOSYNC_SAFE_MODE') == '1' or config_manager.get('safe_mode') == True
        if safe_mode:
            logger.critical("SAFE MODE is active. Skipping community plugin discovery.")
            return

        # Perform authoritative services reconciliation first to prune duplicates/orphans and sync physical plugins
        try:
            self.reconcile_services()
        except Exception as err:
            logger.error("Startup reconciliation halted: Services registry validation failed.")
            logger.debug(f"Raw exception data: {err}", exc_info=True)

        import sqlite3
        from database.config_database import get_config_database
        db = get_config_database()
        
        active_services = []
        try:
            conn = db._open_connection()
            try:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT name, plugin_id, absolute_install_path, loaded_modules, beta_opt_in FROM services WHERE is_active = 1")
                active_services = c.fetchall()
            finally:
                conn.close()
        except Exception as e:
            logger.error("Failed to query active services from the database.")
            logger.debug(f"Raw exception data: {e}", exc_info=True)
            logger.debug(f"Raw exception data: {e}", exc_info=True)
            return

        for row in active_services:
            p_id = row['plugin_id']
            name = row['name']
            install_path = row['absolute_install_path']
            beta_opt_in = row['beta_opt_in']
            
            # Skip core/built-in services (only 'system' is core now, others are community)
            if name.lower() in {'system'}:
                continue

            # Determine plugin channel directly from database record
            channel = 'beta' if beta_opt_in == 1 else 'stable'

            if install_path and os.path.exists(install_path):
                plugin_dir = Path(install_path)
            else:
                logger.error(f"Plugin directory not specified or does not exist for {name}: {install_path}")
                continue

            manifest_file = plugin_dir / "manifest.json"
            init_file = plugin_dir / "__init__.py"
            wasm_file = plugin_dir / "main.wasm"

            if not init_file.exists() and not wasm_file.exists():
                logger.error(f"No entry point found in {plugin_dir}")
                continue

            # Security Scan
            privileged = False
            bypass_security = False
            if manifest_file.exists():
                try:
                    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                    if manifest_data.get("verified_source") == "official":
                        bypass_security = True
                    privileged = manifest_data.get("privileged") is True
                except Exception:
                    pass

            if wasm_file.exists():
                bypass_security = True

            if not bypass_security and not self._security_scan_package(plugin_dir, name, privileged=privileged):
                logger.warning(f"Plugin '{name}' rejected by security scanner.")
                continue

            # Load the package
            self._load_plugin_package(p_id, is_beta=(channel == 'beta'), absolute_install_path=str(plugin_dir.absolute()))

        logger.info(f"Plugin discovery complete. Loaded {len(self.loaded_blueprints)} blueprints.")

    def _security_scan_package(self, package_dir: Path, plugin_name: str, privileged: bool = False) -> bool:
        """
        Scan every .py file in *package_dir* with PluginSecurityScanner.

        Returns True if the package is clean, False on the first violation
        (fail-closed: any unreadable or unparseable source also returns False).
        All violations found across all files are logged before returning.
        """
        clean = True
        for py_file in sorted(package_dir.rglob("*.py")):
            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                logger.warning(
                    f"[SECURITY] Could not read '{py_file}' while scanning "
                    f"plugin '{plugin_name}': {exc}. Refusing to load."
                )
                return False  # fail closed

            try:
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError as exc:
                logger.warning(
                    f"[SECURITY] Syntax error in '{py_file}' for plugin "
                    f"'{plugin_name}': {exc}. Refusing to load."
                )
                return False  # fail closed

            scanner = PluginSecurityScanner()
            scanner.visit(tree)

            for line, description in scanner.violations:
                logger.critical(
                    f"[SECURITY] Refusing to load plugin '{plugin_name}'. "
                    f"Forbidden raw file I/O detected at line {line} "
                    f"in '{py_file.name}' ({description}). "
                    f"Plugins MUST use core.file_handling."
                )
                clean = False

        return clean

    def _update_db_version(self, plugin_id: int, version: str, capabilities_json: str = '{}'):
        try:
            from database.config_database import get_config_database
            db = get_config_database()
            conn = db._open_connection()
            try:
                c = conn.cursor()
                c.execute("""
                    UPDATE services 
                    SET version=?, capabilities=? 
                    WHERE plugin_id=?
                """, (version, capabilities_json, plugin_id))
                updated = c.rowcount
                conn.commit()
                logger.info(f"Stamped version {version} and capabilities for plugin_id {plugin_id}")
            finally:
                conn.close()
        except Exception as e:
            logger.error("An error occurred during framework execution.")
            logger.debug(f"Raw exception data: {e}", exc_info=True)
            logger.debug(f"Raw exception data: {e}", exc_info=True)

    def _load_plugin_package(self, plugin_id: int, is_beta: bool = False, is_disabled: bool = False, absolute_install_path: str = None):
        """
        Dynamically import a plugin package and register its exports.
        """
        with self._load_lock:
            try:
                # Query the database for the path if not provided
                if not absolute_install_path:
                    from database.config_database import get_config_database
                    db = get_config_database()
                    conn = db._open_connection()
                    try:
                        c = conn.cursor()
                        c.execute("SELECT absolute_install_path, name FROM services WHERE plugin_id=?", (plugin_id,))
                        row = c.fetchone()
                        if row and row[0]:
                            absolute_install_path = row[0]
                            plugin_name = row[1]
                        else:
                            raise ValueError(f"Plugin package for plugin_id {plugin_id} not found in database registry or has no path.")
                    finally:
                        conn.close()
                else:
                    plugin_name = str(plugin_id) # Fallback
                    try:
                        from database.config_database import get_config_database
                        db = get_config_database()
                        conn = db._open_connection()
                        try:
                            c = conn.cursor()
                            c.execute("SELECT name FROM services WHERE plugin_id=?", (plugin_id,))
                            row = c.fetchone()
                            if row and row[0]:
                                plugin_name = row[0]
                        finally:
                            conn.close()
                    except Exception:
                        pass

                from pathlib import Path
                package_dir = Path(absolute_install_path)

                if not package_dir.exists():
                    raise ValueError(f"Plugin package {plugin_id} path {package_dir} does not exist on disk")

                # Find the directory containing the 'plugins' folder
                plugins_root = Path(package_dir)
                found_plugins = False
                while plugins_root.parent != plugins_root:
                    if plugins_root.name == 'plugins':
                        found_plugins = True
                        break
                    plugins_root = plugins_root.parent

                if found_plugins:
                    plugins_root = plugins_root.parent # go one up from 'plugins'
                    if str(plugins_root) not in sys.path:
                        sys.path.insert(0, str(plugins_root))

                    try:
                        rel_parts = package_dir.relative_to(plugins_root).parts
                        module_path = ".".join(rel_parts)
                        clean_ns = ".".join(rel_parts[1:]) # skip 'plugins'
                    except Exception:
                        clean_ns = plugin_name
                        module_path = f"plugins.{clean_ns}.beta" if is_beta and not clean_ns.endswith(".beta") else f"plugins.{clean_ns}"
                else:
                    # Fallback for test environments without 'plugins' in path
                    plugins_root = Path(package_dir).parent.parent
                    if str(plugins_root) not in sys.path:
                        sys.path.insert(0, str(plugins_root))
                    clean_ns = plugin_name
                    module_path = f"plugins.{clean_ns}.beta" if is_beta and not clean_ns.endswith(".beta") else f"plugins.{clean_ns}"

                # 2. Extract metadata from manifest
                version = "Unknown"
                author = "Unknown"
                category = "provider"
                
                manifest_file = package_dir / "manifest.json"
                manifest_data = {}
                if manifest_file.exists():
                    try:
                        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                        version = manifest_data.get("version", "Unknown")
                        author = manifest_data.get("author", "Unknown")
                        category = manifest_data.get("category", "provider")
                    except Exception:
                        pass

                # Standardized ID Resolution
                provider_id = manifest_data.get("id") or f"plugin.{clean_ns}"

                # Handle Disabled State
                if is_disabled:
                    class DisabledPlugin(PluginBase):
                        name = provider_id
                        is_enabled = False
                    DisabledPlugin.version = version
                    DisabledPlugin.author = author
                    DisabledPlugin.category = category
                    
                    PluginRegistry.register(DisabledPlugin, name=provider_id, source_type='community')
                    self._update_db_version(plugin_id, version, capabilities_json='{}')
                    logger.info(f"Registered disabled plugin: {provider_id} (v{version})")
                    return True

                # Handle WASM Plugins
                wasm_file = package_dir / "main.wasm"
                if wasm_file.exists() and not (package_dir / "__init__.py").exists():
                    logger.info(f"Loading WASM plugin: {clean_ns}")
                    from core.plugin_sdk import WasmPluginWrapper
                    wrapper = WasmPluginWrapper(str(wasm_file.absolute()))
                    wrapper.plugin_id_int = generate_plugin_id(provider_id)
                    wrapper.version = version
                    wrapper.author = author
                    wrapper.category = category

                    class WasmClass:
                        plugin_id_int = wrapper.plugin_id_int
                        version = wrapper.version
                        author = wrapper.author
                        category = wrapper.category
                        _wrapper_instance = wrapper
                        def __init__(self): pass

                    PluginRegistry.register(WasmClass, name=provider_id, source_type='community')
                    self._update_db_version(plugin_id, version, capabilities_json='{}')
                    return True

                plugins_root = Path("/data/plugins")
                if str(plugins_root.parent) not in sys.path:
                    sys.path.insert(0, str(plugins_root.parent))
                if str(plugins_root) not in sys.path:
                    sys.path.insert(0, str(plugins_root))

                sys.path.insert(0, str(package_dir))
                try:
                    importlib.invalidate_caches()
                    module = importlib.import_module(module_path)

                    plugin_modules = set()
                    plugin_path_str = str(package_dir.resolve())
                    # Deterministic Module Tracking: Crawl directory
                    for py_file in package_dir.rglob("*.py"):
                        # Calculate relative path from package_dir
                        try:
                            rel_path = py_file.relative_to(package_dir)
                            # Convert path to namespace parts
                            parts = list(rel_path.parts)
                            if parts[-1] == "__init__.py":
                                parts.pop()
                            else:
                                parts[-1] = parts[-1][:-3] # remove .py
                            
                            # Construct namespace
                            if parts:
                                ns = f"plugins.{clean_ns}." + ".".join(parts)
                            else:
                                ns = f"plugins.{clean_ns}"
                            
                            plugin_modules.add(ns)
                        except Exception as path_e:
                            logger.warning(f"Failed to parse path for {py_file}: {path_e}")

                    try:
                        from database.config_database import get_config_database
                        db_conf = get_config_database()
                        conn = db_conf._open_connection()
                        try:
                            c = conn.cursor()
                            c.execute(
                                "UPDATE services SET loaded_modules = ? WHERE plugin_id = ?",
                                (json.dumps(list(plugin_modules)), plugin_id)
                            )
                            conn.commit()
                        finally:
                            conn.close()
                    except Exception as db_e:
                        logger.warning(f"Failed to persist dynamically tracked loaded modules in database for plugin ID {plugin_id}: {db_e}")
                except Exception as e:
                    logger.error("An error occurred during framework execution.")
                    logger.debug(f"Raw exception data: {e}", exc_info=True)
                    logger.debug(f"Raw exception data: {e}", exc_info=True)
                    raise

                # Registration
                if hasattr(module, 'ProviderClass'):
                    provider_cls = getattr(module, 'ProviderClass')
                    PluginRegistry.register(provider_cls, name=provider_id, source_type='community')
                    caps_json = '{}'
                    caps = getattr(provider_cls, 'capabilities', None)
                    if caps:
                        caps_json = json.dumps({
                            'name': getattr(caps, 'name', provider_id),
                            'supports_playlists': getattr(getattr(caps, 'supports_playlists', None), 'name', 'NONE'),
                            'search': getattr(caps, 'search', {}).__dict__ if hasattr(getattr(caps, 'search', None), '__dict__') else {},
                            'metadata': getattr(getattr(caps, 'metadata', None), 'name', 'MEDIUM'),
                            'supports_cover_art': getattr(caps, 'supports_cover_art', False),
                            'supports_lyrics': getattr(caps, 'supports_lyrics', False),
                            'supports_user_auth': getattr(caps, 'supports_user_auth', False),
                            'supports_library_scan': getattr(caps, 'supports_library_scan', False),
                            'supports_streaming': getattr(caps, 'supports_streaming', False),
                            'supports_downloads': getattr(caps, 'supports_downloads', False),
                            'pre_filters': getattr(caps, 'pre_filters', []) if hasattr(caps, 'pre_filters') else (['bitrate', 'format'] if getattr(caps, 'supports_pre_filtering', False) else []),
                            'playlist_algorithms': getattr(caps, 'playlist_algorithms', None),
                            'fingerprint_algorithms': getattr(caps, 'fingerprint_algorithms', []) if hasattr(caps, 'fingerprint_algorithms') else (['chromaprint'] if getattr(caps, 'supports_fingerprinting', False) else []),
                            'supports_metadata_fetch': getattr(caps, 'supports_metadata_fetch', False)
                        })
                    self._update_db_version(plugin_id, version, capabilities_json=caps_json)
                else:
                    found = False
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, PluginBase) and attr is not PluginBase:
                            PluginRegistry.register(attr, name=provider_id, source_type='community')
                            caps_json = '{}'
                            caps = getattr(attr, 'capabilities', None)
                            if caps:
                                caps_json = json.dumps({
                                    'name': getattr(caps, 'name', provider_id),
                                    'supports_playlists': getattr(getattr(caps, 'supports_playlists', None), 'name', 'NONE'),
                                    'search': getattr(caps, 'search', {}).__dict__ if hasattr(getattr(caps, 'search', None), '__dict__') else {},
                                    'metadata': getattr(getattr(caps, 'metadata', None), 'name', 'MEDIUM'),
                                    'supports_cover_art': getattr(caps, 'supports_cover_art', False),
                                    'supports_lyrics': getattr(caps, 'supports_lyrics', False),
                                    'supports_user_auth': getattr(caps, 'supports_user_auth', False),
                                    'supports_library_scan': getattr(caps, 'supports_library_scan', False),
                                    'supports_streaming': getattr(caps, 'supports_streaming', False),
                                    'supports_downloads': getattr(caps, 'supports_downloads', False),
                                    'pre_filters': getattr(caps, 'pre_filters', []) if hasattr(caps, 'pre_filters') else (['bitrate', 'format'] if getattr(caps, 'supports_pre_filtering', False) else []),
                                    'playlist_algorithms': getattr(caps, 'playlist_algorithms', None),
                                    'fingerprint_algorithms': getattr(caps, 'fingerprint_algorithms', []) if hasattr(caps, 'fingerprint_algorithms') else (['chromaprint'] if getattr(caps, 'supports_fingerprinting', False) else []),
                                    'supports_metadata_fetch': getattr(caps, 'supports_metadata_fetch', False)
                                })
                            self._update_db_version(plugin_id, version, capabilities_json=caps_json)
                            found = True
                            break
                    if not found:
                        logger.debug(f"No PluginBase found in {module_path}")

                # Core-Driven Inversion of Control (IoC) Startup Hooks
                try:
                    plugin_cls = PluginRegistry.get_plugin_class(provider_id)
                    if plugin_cls:
                        # Instantiate the plugin class
                        plugin_instance = plugin_cls()
                        if hasattr(plugin_instance, "on_plugin_startup"):
                            plugin_instance.on_plugin_startup(self.hook_manager, self.config_db)
                except Exception as init_err:
                    logger.error("Plugin initialization halted: Startup hook execution failed.")
                    logger.debug(f"Raw exception data: {init_err}", exc_info=True)

                # Sprint 6: Sync UI manifest into ui_components table
                try:
                    _sync_ui_components_to_db(plugin_id, str(package_dir.absolute()))
                except Exception as ui_err:
                    logger.warning("UI Registry operation failed due to an unexpected error.")
                    logger.debug(f"Raw exception data: {ui_err}", exc_info=True)

                # Tear down existing blueprints for this plugin
                try:
                    self.loaded_blueprints = [bp for bp in self.loaded_blueprints if not bp.name.startswith(f"{provider_id}_")]
                except Exception as e:
                    logger.warning("An error occurred during framework execution.")
                    logger.debug(f"Raw exception data: {e}", exc_info=True)
                    logger.debug(f"Raw exception data: {e}", exc_info=True)

                # Collect Blueprints
                for bp_attr in ('RouteBlueprint', 'RouteBlueprint2', 'RouteBlueprint3'):
                    blueprint = getattr(module, bp_attr, None)
                    if isinstance(blueprint, Blueprint):
                        blueprint.name = f"{provider_id}_{bp_attr.lower()}"
                        blueprint.url_prefix = f"/api/plugins/{plugin_id}"
                        self.loaded_blueprints.append(blueprint)


                # Persist loaded_modules to DB
                try:
                    loaded_mods = [m for m in sys.modules.keys() if m.startswith(module_path)]
                    from database.config_database import get_config_database
                    db = get_config_database()
                    conn = db._open_connection()
                    try:
                        conn.execute("UPDATE services SET loaded_modules = ? WHERE plugin_id = ?", (json.dumps(loaded_mods), plugin_id))
                        conn.commit()
                    finally:
                        conn.close()
                except Exception as db_err:
                    logger.debug(f"Failed to update loaded_modules for {plugin_id}: {db_err}")

                return True

            except Exception as e:
                logger.error("An error occurred during framework execution.")
                logger.debug(f"Raw exception data: {e}", exc_info=True)
                logger.debug(f"Raw exception data: {e}", exc_info=True)
                # Auto-disable on fatal load error
                try:
                    from database.config_database import get_config_database
                    db = get_config_database()
                    conn = db._open_connection()
                    try:
                        conn.execute("UPDATE services SET is_active = 0 WHERE plugin_id = ?", (plugin_id,))
                        conn.commit()
                    finally:
                        conn.close()
                except Exception: pass
                return False

    def get_all_blueprints(self) -> List[Blueprint]:
        return self.loaded_blueprints

    def get_plugin_by_capability(self, capability: Capability) -> Optional[PluginBase]:
        """
        Get the first available plugin with the given capability.
        Delegates to PluginRegistry.
        """
        return get_plugin_by_capability(capability)



def get_plugin_by_capability(capability: Capability) -> Optional[PluginBase]:
    """
    Get the first available provider with the given capability.
    Delegates to PluginRegistry.
    """
    providers = PluginRegistry.get_plugins_with_capability(capability)
    if providers:
        return providers[0]
    return None

def get_plugin(name: str) -> Optional[PluginBase]:
    """
    Get a plugin instance by name.
    """
    try:
        return PluginRegistry.create_instance(name)
    except Exception:
        return None



def get_all_plugins() -> list:
    from database.config_database import get_config_database
    import logging

    plugins_map = {}
    db = get_config_database()
    
    conn = db._open_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT name, plugin_id, absolute_install_path, description, version, is_active FROM services")
        rows = c.fetchall()
        
        for row in rows:
            name = row['name']
            if name.lower() == 'system':
                continue
                
            plugin_info = {
                "id": name,
                "plugin_id": row['plugin_id'],
                "name": name,
                "description": row['description'] or "Community plugin",
                "type": "community",
                "version": row['version'] or "Unknown",
                "abs_path": row['absolute_install_path'],
                "enabled": bool(row['is_active'])
            }
            plugins_map[name] = plugin_info
    except Exception as e:
        logging.getLogger("plugin_loader").error("Database query failed: Unable to fetch plugin registry state.")
        logging.getLogger("plugin_loader").debug(f"Raw exception data: {e}", exc_info=True)
        logging.getLogger("plugin_loader").debug(f"Raw exception data: {e}", exc_info=True)
    finally:
        conn.close()

    return list(plugins_map.values())


class PluginRegistry:
    """
    Central registry for all plugin classes. Allows registration, lookup, and listing.
    Supports both bundled (core) and community plugins with enable/disable functionality.
    """
    _plugins: Dict[int, Type[PluginBase]] = {}
    _plugin_sources: Dict[int, str] = {}  # metadata: plugin_id -> source_type
    _disabled_plugins: set = set()
    _quality_options: Dict[int, List[Dict[str, Any]]] = {}

    @classmethod
    def get_all(cls) -> Dict[int, Dict[str, Any]]:
        """Return all registered plugins and their metadata."""
        all_plugins = {}
        for p_id, plugin_cls in cls._plugins.items():
            all_plugins[p_id] = {
                'class': plugin_cls,
                'source_type': cls._plugin_sources.get(p_id, 'core')
            }
        return all_plugins

    @classmethod
    def get_plugins_with_capability(cls, capability: Capability, exclude_disabled: bool = True) -> List[PluginBase]:
        """
        Return a list of instantiated plugins that support the given capability.
        """
        plugins = []
        for p_id, plugin_cls in cls._plugins.items():
            if exclude_disabled and p_id in cls._disabled_plugins:
                continue

            # Check if class has capabilities attribute and if it contains the capability
            caps = getattr(plugin_cls, 'capabilities', None)
            # Normalize None -> empty iterable to avoid TypeError when doing 'in' checks
            if caps is None:
                caps = []

            # Some plugins expose a helper to convert to a list of Capability enums
            if hasattr(caps, 'to_enum_list'):
                caps = caps.to_enum_list() or []

            # Defensive: if caps is not iterable, skip this plugin
            try:
                contains = capability in caps
            except TypeError:
                contains = False

            if contains:
                try:
                    plugins.append(cls.create_instance(p_id))
                except Exception as e:
                    logger.error("An error occurred during framework execution.")
                    logger.debug(f"Raw exception data: {e}", exc_info=True)
                    logger.debug(f"Raw exception data: {e}", exc_info=True)
        return plugins

    @classmethod
    def get_plugins_by_type(cls, plugin_type: str, exclude_disabled: bool = True) -> List[int]:
        """
        Return a list of plugin IDs matching the given type.
        plugin_type: 'downloader', 'mediaserver', 'syncservice'
        """
        type_map = {
            'downloader': DownloaderProvider,
            'mediaserver': MediaServerProvider,
            'syncservice': SyncServiceProvider
        }
        base_type = type_map.get(plugin_type.lower())
        if not base_type:
            raise ValueError(f"Unknown plugin type: {plugin_type}")

        plugins = [p_id for p_id, cls_ in cls._plugins.items() if issubclass(cls_, base_type)]
        if exclude_disabled:
            plugins = [p_id for p_id in plugins if p_id not in cls._disabled_plugins]
        return plugins

    @classmethod
    def get_active_services_by_type(cls, service_type: str) -> List[int]:
        """
        Return a list of active (enabled and configured) plugin IDs for a given service role.
        Normalized service_type aliases: 'media_server', 'download', 'sync', 'metadata'
        """
        # Mapping common codebase aliases to internal base class keys
        normalized_map = {
            'media_server': 'mediaserver',
            'download': 'downloader',
            'sync': 'syncservice'
        }
        
        target_role = service_type.lower()
        mapped_type = normalized_map.get(target_role, target_role)

        # Special handling for metadata role (role based on capability rather than base class)
        if mapped_type == 'metadata':
            from core.enums import Capability
            active = []
            for p in cls.get_plugins_with_capability(Capability.FETCH_METADATA):
                # reg_name is now plugin_id string
                reg_name = getattr(p, '_registered_name', str(p.plugin_id_int) if hasattr(p, 'plugin_id_int') else None)
                if not reg_name: continue
                p_id = int(reg_name)
                
                if p_id not in cls._disabled_plugins:
                    # Verify configuration if possible
                    if hasattr(p, 'is_configured'):
                        if p.is_configured():
                            active.append(p_id)
                    else:
                        active.append(p_id)
            return active

        # Standard plugin-type lookup
        try:
            potential_ids = cls.get_plugins_by_type(mapped_type, exclude_disabled=True)
            active = []
            for p_id in potential_ids:
                try:
                    instance = cls.create_instance(p_id)
                    if hasattr(instance, 'is_configured'):
                        if instance.is_configured():
                            active.append(p_id)
                    else:
                        active.append(p_id)
                except Exception as e:
                    logger.error("An error occurred during framework execution.")
                    logger.debug(f"Raw exception data: {e}", exc_info=True)
                    logger.debug(f"Raw exception data: {e}", exc_info=True)
                    # If we can't even instantiate it, it's not active
                    continue
            return active
        except ValueError:
            # If the type is unknown to get_plugins_by_type, return empty list
            return []

    @classmethod
    def create_instance_by_type(cls, plugin_type: str, *args, **kwargs) -> List[PluginBase]:
        """
        Instantiate all plugins of a given type (excluding disabled ones).
        """
        p_ids = cls.get_plugins_by_type(plugin_type, exclude_disabled=True)
        instances = []
        for p_id in p_ids:
            try:
                instances.append(cls.create_instance(p_id, *args, **kwargs))
            except Exception as e:
                logger.error("An error occurred during framework execution.")
                logger.debug(f"Raw exception data: {e}", exc_info=True)
                logger.debug(f"Raw exception data: {e}", exc_info=True)
        return instances

    @classmethod
    def register(cls, plugin_cls: Type[PluginBase], name: Optional[str] = None, source_type: str = 'core'):
        """
        Register a plugin class.

        Args:
            plugin_cls: The class implementing PluginBase.
            name: Optional explicit name override.
            source_type: 'core' for bundled plugins, 'community' for plugins.
        """
        if not name:
            name = getattr(plugin_cls, 'name', None)

        if not name:
            raise ValueError("Plugin class must have a 'name' attribute or explicit name provided")

        plugin_id = generate_plugin_id(name.lower())
        cls._plugins[plugin_id] = plugin_cls
        cls._plugin_sources[plugin_id] = source_type
        logger.debug(f"Registered plugin '{name}' (source: {source_type})")

    @classmethod
    def get_plugin_class(cls, plugin_id: int) -> Optional[Type[PluginBase]]:
        if isinstance(plugin_id, str):
            if plugin_id.isdigit():
                plugin_id = int(plugin_id)
            else:
                plugin_id = generate_plugin_id(plugin_id.lower())
        return cls._plugins.get(plugin_id)

    @classmethod
    def list_plugins(cls):
        return list(cls._plugins.keys())

    @classmethod
    def get_plugin_source(cls, plugin_id: int) -> Optional[str]:
        if isinstance(plugin_id, str):
            if plugin_id.isdigit():
                plugin_id = int(plugin_id)
            else:
                plugin_id = generate_plugin_id(plugin_id.lower())
        return cls._plugin_sources.get(plugin_id)

    @classmethod
    def create_instance(cls, plugin_id: int, *args, **kwargs) -> PluginBase:
        # Phase 2: Integer strictness (allow string temporarily during migration)
        if isinstance(plugin_id, str):
            if plugin_id.isdigit():
                plugin_id = int(plugin_id)
            else:
                plugin_id = generate_plugin_id(plugin_id.lower())

        # Double check against config manager to ensure latest state
        from core.settings import config_manager

        # Check global disabled list (which might still store string names)
        disabled = config_manager.get_disabled_plugins()
        if disabled is None:
            disabled = []

        disabled_ids = [generate_plugin_id(d.lower()) for d in disabled]
        if plugin_id in disabled_ids:
             raise ValueError(f"Plugin ID '{plugin_id}' is disabled via config")

        if plugin_id in cls._disabled_plugins:
            raise ValueError(f"Plugin ID '{plugin_id}' is disabled")

        plugin_cls = cls.get_plugin_class(plugin_id)
        if not plugin_cls:
            raise ValueError(f"Plugin ID '{plugin_id}' not registered")

        instance = plugin_cls(*args, **kwargs)
        
        # Store the canonical registered ID on the instance for backend services
        instance._registered_name = str(plugin_id)
        instance.plugin_id_int = plugin_id
            
        return instance

    @classmethod
    def get_plugin(cls, plugin_id: int) -> Optional[PluginBase]:
        try:
            return cls.create_instance(plugin_id)
        except Exception:
            return None

    @classmethod
    def get_download_clients(cls) -> List[int]:
        """
        Return a list of plugin IDs that support downloads (excluding disabled ones).
        """
        clients = [p_id for p_id, cls_ in cls._plugins.items() if getattr(cls_, 'supports_downloads', False)]
        return [p_id for p_id in clients if p_id not in cls._disabled_plugins]

    @classmethod
    def disable_plugin(cls, plugin_id: int) -> bool:
        if isinstance(plugin_id, str):
            if plugin_id.isdigit():
                plugin_id = int(plugin_id)
            else:
                plugin_id = generate_plugin_id(plugin_id.lower())
        
        if plugin_id in cls._plugins:
            cls._disabled_plugins.add(plugin_id)
            logger.info(f"Plugin ID '{plugin_id}' disabled. Restart required to unload.")
            return True
        return False

    @classmethod
    def enable_plugin(cls, plugin_id: int) -> bool:
        if isinstance(plugin_id, str):
            if plugin_id.isdigit():
                plugin_id = int(plugin_id)
            else:
                plugin_id = generate_plugin_id(plugin_id.lower())
                
        if plugin_id in cls._disabled_plugins:
            cls._disabled_plugins.remove(plugin_id)
            logger.info(f"Plugin ID '{plugin_id}' enabled. Refresh the page to load it.")
            return True
        return False

    @classmethod
    def is_plugin_disabled(cls, plugin_id: int) -> bool:
        if isinstance(plugin_id, str):
            if plugin_id.isdigit():
                plugin_id = int(plugin_id)
            else:
                plugin_id = generate_plugin_id(plugin_id.lower())
                
        # Check in memory runtime disabled
        if plugin_id in cls._disabled_plugins:
            return True
            
        # Also check persistent config
        from core.settings import config_manager
        disabled = config_manager.get_disabled_plugins()
        if disabled:
            disabled_ids = [generate_plugin_id(d.lower()) for d in disabled]
            if plugin_id in disabled_ids:
                return True
                
        return False

    @classmethod
    def set_disabled_plugins(cls, disabled_list: List[str]) -> None:
        if disabled_list is None:
            disabled_list = []
        cls._disabled_plugins = set(name.lower() for name in disabled_list)
        if disabled_list:
            logger.info(f"Disabled plugins: {', '.join(disabled_list)}")

    @classmethod
    def get_disabled_plugins(cls) -> List[str]:
        return list(cls._disabled_plugins)
    
    @classmethod
    def register_quality_option(cls, plugin_id: str, option: Dict[str, Any]):
        """Register a custom quality configuration field for a plugin."""
        if plugin_id not in cls._quality_options:
            cls._quality_options[plugin_id] = []
        
        # Check for duplicates by name within this plugin
        if not any(opt['name'] == option['name'] for opt in cls._quality_options[plugin_id]):
            cls._quality_options[plugin_id].append(option)

    @classmethod
    def get_all_quality_options(cls) -> List[Dict[str, Any]]:
        """Retrieve all registered quality options across all plugins."""
        all_options = []
        for plugin_id, options in cls._quality_options.items():
            # Ensure each option carries its plugin_id context
            for opt in options:
                if 'plugin_id' not in opt:
                    opt['plugin_id'] = plugin_id
                all_options.append(opt)
        return all_options



class ServiceRegistry:
    """
    Phase 2: Unified Service Registry
    Dependency Injection container for core platform services (e.g. MatchingEngine).
    Allows plugins to override default platform behaviors.
    """
    _services: Dict[str, Any] = {}
    _defaults: Dict[str, Any] = {}
    # H3: class-level lock prevents TOCTOU races under Flask threading / gunicorn.
    _lock: threading.Lock = threading.Lock()

    @classmethod
    def register_default(cls, service_name: str, factory: Any) -> None:
        with cls._lock:
            cls._defaults[service_name] = factory
            if service_name not in cls._services:
                cls._services[service_name] = factory

    @classmethod
    def register_override(cls, service_name: str, factory: Any) -> None:
        with cls._lock:
            cls._services[service_name] = factory

    @classmethod
    def resolve(cls, service_name: str) -> Any:
        from core.settings import config_manager
        override_key = f"settings.active_{service_name}"
        active_override = config_manager.get(override_key)

        with cls._lock:
            if active_override and active_override in cls._services:
                return cls._services[active_override]
            return cls._services.get(service_name, cls._defaults.get(service_name))

def get_plugin_capabilities(plugin_id_or_name: str | int):
    """
    Return capabilities for a plugin by looking up its registered capabilities in the database.
    """
    import json
    from core.nexus_framework.plugin_SDK import ProviderCapabilities, SearchCapabilities, MetadataRichness, PlaylistSupport
    from database.config_database import get_config_database
    
    db = get_config_database()
    caps_json = '{}'
    try:
        with db._get_connection() as conn:
            c = conn.cursor()
            if isinstance(plugin_id_or_name, int):
                c.execute("SELECT capabilities FROM services WHERE plugin_id=?", (plugin_id_or_name,))
            else:
                c.execute("SELECT capabilities FROM services WHERE LOWER(name)=LOWER(?)", (plugin_id_or_name,))
            row = c.fetchone()
            if row and row['capabilities']:
                caps_json = row['capabilities']
    except Exception:
        pass
        
    try:
        caps_dict = json.loads(caps_json)
    except Exception:
        caps_dict = {}

    search_caps = caps_dict.get('search', {})
    search_obj = SearchCapabilities(
        tracks=search_caps.get('tracks', False),
        artists=search_caps.get('artists', False),
        albums=search_caps.get('albums', False),
        playlists=search_caps.get('playlists', False)
    )

    playlist_enum = getattr(PlaylistSupport, caps_dict.get('supports_playlists', 'NONE'), PlaylistSupport.NONE)
    metadata_enum = getattr(MetadataRichness, caps_dict.get('metadata', 'MEDIUM'), MetadataRichness.MEDIUM)

    return ProviderCapabilities(
        name=caps_dict.get('name', plugin_id_or_name),
        supports_playlists=playlist_enum,
        search=search_obj,
        metadata=metadata_enum,
        supports_cover_art=caps_dict.get('supports_cover_art', False),
        supports_lyrics=caps_dict.get('supports_lyrics', False),
        supports_user_auth=caps_dict.get('supports_user_auth', False),
        supports_library_scan=caps_dict.get('supports_library_scan', False),
        supports_streaming=caps_dict.get('supports_streaming', False),
        supports_downloads=caps_dict.get('supports_downloads', False),
        supports_pre_filtering=caps_dict.get('supports_pre_filtering', False),
        playlist_algorithms=caps_dict.get('playlist_algorithms', None),
        supports_fingerprinting=caps_dict.get('supports_fingerprinting', False),
        supports_metadata_fetch=caps_dict.get('supports_metadata_fetch', False)
    )
