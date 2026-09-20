import threading

"""Dynamic plugin loader for Echosync providers and plugins."""

import ast
import importlib
import json
import os
import sys
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, Request


async def enforce_plugin_passport(request: Request):
    """Zero-Trust Passport Enforcer for Plugin Sub-Applications."""


from pathlib import Path

from flask import Blueprint

from core.enums import Capability
from core.nexus_framework.plugin_SDK import (
    DownloaderProvider,
    MediaServerProvider,
    PluginBase,
    SyncServiceProvider,
)
from core.settings import config_manager
from core.tiered_logger import get_logger
from database.config_database import retry_sqlite_io

logger = get_logger("plugin_loader")
import sqlite3
import zlib


def compute_plugin_crc32(namespace: str) -> int:
    """Compute deterministic CRC32 32-bit integer for a fully qualified namespace."""
    clean_ns = str(namespace).strip().lower()
    return zlib.crc32(clean_ns.encode("utf-8")) & 0xFFFFFFFF


def _hydrate_manifest_permissions(plugin_id: int, manifest_permissions: Any) -> Any:
    """Restore permissions only when the registry record has been blanked."""
    if not manifest_permissions:
        return manifest_permissions

    from core.task_manager import db_write_lease
    from database.config_database import get_config_database

    db = get_config_database()
    with db_write_lease(task_name=f"hydrate_plugin_permissions_{plugin_id}"), db._open_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT permissions FROM services WHERE plugin_id=?", (plugin_id,))
        row = cursor.fetchone()
        raw_permissions = row[0] if row else None
        if raw_permissions not in (None, "", "{}", "[]"):
            try:
                if json.loads(raw_permissions):
                    return json.loads(raw_permissions)
            except (TypeError, json.JSONDecodeError):
                pass
        serialized = json.dumps(manifest_permissions)
        cursor.execute(
            "UPDATE services SET permissions=? WHERE plugin_id=?",
            (serialized, plugin_id),
        )
        conn.commit()
    return manifest_permissions


def generate_plugin_id(name: str) -> int:
    """Generate a consistent 32-bit integer ID from a plugin name."""
    if isinstance(name, str) and "@" in name:
        name = name.split("@")[0]
    return compute_plugin_crc32(str(name))


def resolve_plugin_directory(
    name: str,
    channel_preference: str = "inherit",
    absolute_install_path: str | None = None,
) -> tuple[Path, str]:
    """Resolve an installed plugin directory without assuming stable exists."""
    effective_channel = (
        config_manager.get("system.channel_preference", "stable")
        if channel_preference == "inherit"
        else channel_preference
    )
    if not effective_channel:
        effective_channel = "stable"

    base_dir: Path | None = None
    if absolute_install_path:
        p = Path(absolute_install_path)
        if p.name in ("beta", "stable"):
            base_dir = p.parent
        else:
            base_dir = p
    else:
        try:
            p_dir = Path(config_manager.get_plugins_dir())
        except Exception:
            p_dir = Path("/data/plugins/EchoSync")
        if "." in name and not (p_dir / name).exists():
            parts = name.split(".", 1)
            candidate_base = p_dir / parts[0] / parts[1]
            if candidate_base.exists():
                base_dir = candidate_base
            else:
                base_dir = p_dir / name
        elif not (p_dir / name).exists() and (p_dir / "EchoSync" / name).exists():
            base_dir = p_dir / "EchoSync" / name
        else:
            base_dir = p_dir / name

    candidates: list[tuple[Path, str]] = [
        (base_dir / effective_channel, effective_channel),
        (base_dir, "root"),
        (base_dir / "stable", "stable"),
        (base_dir / "beta", "beta"),
    ]
    seen: set[Path] = set()
    for path, channel in candidates:
        if path in seen:
            continue
        seen.add(path)
        if path.exists() and ((path / "plugin.json").is_file() or (path / "manifest.json").is_file()):
            return path, channel

    return base_dir / effective_channel, effective_channel


def get_relative_entry_path(url_or_path: str) -> str:
    """
    Extracts the relative path within the plugin's install directory from
    absolute paths, relative paths, or URL paths (e.g. `/api/v1/system/plugins/spotify/static/bundle.js` -> `static/bundle.js`).
    """
    if not url_or_path:
        return ""
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        return url_or_path

    # Normalize slashes
    normalized = url_or_path.replace("\\", "/").lstrip("/")
    parts = normalized.split("/")

    # 1. Check for /api/v1/system/plugins/<plugin_id>/<relative_path>
    if len(parts) >= 5 and parts[0] == "api" and parts[1] == "v1" and parts[2] == "system" and parts[3] == "plugins":
        return "/".join(parts[5:])
    # 2. Check for /api/system/plugins/<plugin_id>/<relative_path>
    elif len(parts) >= 4 and parts[0] == "api" and parts[1] == "system" and parts[2] == "plugins":
        return "/".join(parts[4:])
    # 3. Check for /api/plugins/<plugin_id>/<relative_path>
    elif len(parts) >= 3 and parts[0] == "api" and parts[1] == "plugins":
        return "/".join(parts[3:])
    # 4. Check for /plugins/<plugin_id>/<relative_path>
    elif len(parts) >= 2 and parts[0] == "plugins":
        return "/".join(parts[2:])

    return normalized


def _sync_ui_components_to_db(plugin_id: int, install_path: str, is_core: bool = False) -> None:
    """Read ui_manifest.json once and UPSERT component definitions into ui_components.

    Called during plugin boot and installation.  Handles orphan cleanup for
    components that are no longer declared in the manifest.
    """
    from database import execute_write
    from database.config_database import get_config_database

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
    bundle_url = raw_assets.get("js") or raw_assets.get("bundle.js") or raw_assets.get("main") or default_bundle

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
        cursor.execute("SELECT tag_name FROM ui_components WHERE plugin_id = ?", (plugin_id,))
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
_FORBIDDEN_BARE_CALLS: frozenset = frozenset(
    {
        "open",
        "__import__",
        "eval",
        "exec",
        "getattr",
        "setattr",
        "globals",
        "locals",
        "compile",
        "delattr",
        "memoryview",
        "input",
    }
)

# Forbidden module.method() patterns
_FORBIDDEN_MODULE_CALLS: dict = {
    "os": frozenset(
        {
            "system",
            "popen",
            "fdopen",
            "kill",
            "execve",
            "spawn",
            "remove",
            "unlink",
            "rename",
            "rmdir",
            "mkdir",
            "chmod",
            "chown",
            "symlink",
            "link",
            "environ",
        }
    ),
    "shutil": frozenset({"move", "copy", "rmtree"}),
    "importlib": frozenset({"import_module", "reload"}),
    "builtins": frozenset(
        {
            "eval",
            "exec",
            "getattr",
            "setattr",
            "delattr",
            "open",
            "compile",
            "__import__",
            "globals",
            "locals",
            "memoryview",
            "input",
        }
    ),
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
# of receiver type.  All legitimate I/O must go through Gatekeeper.
_FORBIDDEN_METHOD_CALLS: frozenset = frozenset({"unlink", "write_text", "open"})


class PluginSecurityScanner(ast.NodeVisitor):
    """
    AST-based pre-load security scanner for community plugins.

    Walks the parse tree of each .py source file *before* importlib touches it
    and flags any raw file-I/O calls that bypass the Gatekeeper gateway.

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
        forbidden_attrs = {
            "__class__",
            "__base__",
            "__subclasses__",
            "__mro__",
            "__dict__",
            "__globals__",
            "__traceback__",
        }
        if node.attr in forbidden_attrs:
            self.violations.append((node.lineno, f"access to forbidden attribute '{node.attr}'"))
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id == "__builtins__":
            self.violations.append((node.lineno, "access to __builtins__ is forbidden"))
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            base_module = alias.name.split(".")[0]
            if base_module in (
                "os",
                "subprocess",
                "sys",
                "importlib",
                "database",
                "inspect",
                "ctypes",
                "gc",
                "builtins",
            ):
                if base_module == "database" and self.privileged:
                    continue  # Allow core database if privileged
                if base_module in ("subprocess", "ctypes") and self.privileged:
                    continue
                self.violations.append((node.lineno, f"forbidden import '{alias.name}'"))
            elif alias.name.startswith("core.file_handling.storage") and not self.privileged:
                self.violations.append(
                    (
                        node.lineno,
                        "forbidden import of core storage service; use the SDK instead",
                    )
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base_module = node.module.split(".")[0]
            if base_module in (
                "os",
                "subprocess",
                "sys",
                "importlib",
                "database",
                "inspect",
                "ctypes",
                "gc",
                "builtins",
            ):
                if base_module == "database" and self.privileged:
                    pass  # Allow core database if privileged
                elif base_module in ("subprocess", "ctypes") and self.privileged:
                    pass
                else:
                    self.violations.append((node.lineno, f"forbidden from-import '{node.module}'"))
            elif not self.privileged:
                is_storage = node.module == "core.file_handling.storage" or (
                    node.module == "core.file_handling" and any(alias.name == "storage" for alias in node.names)
                )
                if is_storage:
                    self.violations.append(
                        (
                            node.lineno,
                            "forbidden import of core storage service; use the SDK instead",
                        )
                    )
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, str):
            if "config.db" in node.value:
                self.violations.append((node.lineno, "forbidden string literal containing 'config.db'"))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func = node.func

        if isinstance(func, ast.Name):
            # Pattern 1: bare open(...)
            if func.id in _FORBIDDEN_BARE_CALLS:
                self.violations.append((node.lineno, f"bare call to {func.id}()"))

        elif isinstance(func, ast.Attribute):
            attr = func.attr
            receiver = func.value

            # Pattern 2: module.method() — e.g. os.remove(), shutil.move()
            if isinstance(receiver, ast.Name):
                module = receiver.id
                forbidden_attrs = _FORBIDDEN_MODULE_CALLS.get(module)
                if forbidden_attrs and ("*" in forbidden_attrs or attr in forbidden_attrs):
                    self.violations.append((node.lineno, f"{module}.{attr}()"))

            # Pattern 3: .unlink() / .write_text() / .open() on any receiver
            # (pathlib.Path is the primary target; conservative match is
            # intentional — plugins must not perform raw I/O at all)
            if attr in _FORBIDDEN_METHOD_CALLS:
                self.violations.append((node.lineno, f".{attr}() method call"))

        # Recurse into all child expressions
        self.generic_visit(node)


class PluginLoader:
    """
    Scans and loads providers from 'providers/' (core) and 'plugins/' (community).
    Registers them with the PluginRegistry and collects Flask blueprints.
    """

    _load_lock = threading.Lock()

    def __init__(self, app_root: Path, main_app=None):
        self.app_root = Path(app_root)
        self.main_app = main_app
        self.plugins_dir = Path(config_manager.get_plugins_dir())
        self.loaded_blueprints: list[Blueprint] = []
        from core.hook_manager import hook_manager
        from database.config_database import get_config_database

        self.hook_manager = hook_manager
        self.config_db = get_config_database()

    def unload_plugin(self, plugin_id: int):
        """Unload a plugin, unmount its FastAPI sub-application, and purge it from memory."""
        logger.info(f"Unloading plugin {plugin_id}")

        # 1. Unmount from FastAPI
        try:
            if hasattr(self, "main_app") and self.main_app:
                mount_path = f"/api/v1/plugins/{plugin_id}"
                # Iterate backwards to safely remove mounts
                for i in range(len(self.main_app.routes) - 1, -1, -1):
                    route = self.main_app.routes[i]
                    if getattr(route, "path", None) == mount_path and route.__class__.__name__ == "Mount":
                        del self.main_app.routes[i]
                        logger.info(f"Unmounted FastAPI sub-application at {mount_path}")
        except Exception as e:
            logger.error(f"Failed to unmount routes during unload_plugin for {plugin_id}: {e}")

        # 2. Kill Workers
        try:
            from core.job_queue import job_queue
            from core.task_manager import (
                supervisor,
            )

            job_queue.kill_jobs_by_plugin(plugin_id)
            supervisor.terminate_owner_processes(str(plugin_id))

            # Note: We need clean_ns to cleanly terminate namespaced processes, but
            # if we don't have it here, terminating by string ID is the fallback.
            # Usually the supervisor cleans up all children by tracking the plugin_id.
        except Exception:
            logger.warning(f"Failed to kill workers for {plugin_id} during unload.")

        # 3. Purge Memory (Comprehensive Memory & Namespace Unload)
        try:
            modules_to_purge = set()
            from database.config_database import get_config_database

            db = get_config_database()
            conn = db._open_connection()
            try:
                c = conn.cursor()
                c.execute(
                    "SELECT loaded_modules, name, absolute_install_path FROM services WHERE plugin_id=?",
                    (plugin_id,),
                )
                row = c.fetchone()
                if row:
                    if row[0]:
                        import json

                        try:
                            modules_to_purge.update(json.loads(row[0]))
                        except Exception:
                            pass

                    p_name = (row[1] or "").split("@")[0]
                    clean_name = p_name.lower().replace("echosync.", "").replace("echosync/", "").strip()
                    ns_prefixes = {
                        f"plugins.{p_name.lower()}",
                        f"plugins.echosync.{clean_name}",
                        f"echosync.{clean_name}",
                        f"plugins.{clean_name}",
                        p_name.lower(),
                        clean_name,
                    }

                    p_path = Path(row[2]) if row[2] else None
                    resolved_p_path = str(p_path.resolve()) if p_path and p_path.exists() else None

                    for mod_name, mod_obj in list(sys.modules.items()):
                        mod_lower = mod_name.lower()
                        if any(mod_lower == pfx or mod_lower.startswith(f"{pfx}.") for pfx in ns_prefixes):
                            modules_to_purge.add(mod_name)
                            continue
                        if resolved_p_path:
                            mod_file = getattr(mod_obj, "__file__", None)
                            if mod_file:
                                try:
                                    if str(Path(mod_file).resolve()).startswith(resolved_p_path):
                                        modules_to_purge.add(mod_name)
                                except Exception:
                                    pass
            finally:
                conn.close()

            logger.info(f"Purging {len(modules_to_purge)} modules for plugin {plugin_id} from sys.modules")
            for mod_ns in modules_to_purge:
                sys.modules.pop(mod_ns, None)

            import importlib

            importlib.invalidate_caches()
            PluginRegistry.unregister(plugin_id)
        except Exception as e:
            logger.error(f"Failed during memory purge during unload: {e}")

    def reload_plugin(self, plugin_id: int, absolute_install_path: str | None = None):
        """Perform a true Zero-Downtime hot reload of a plugin."""
        logger.info(f"🔄 HOT-SWAP INITIATED: {plugin_id}")

        # 1. Resolve Namespace and Channel from DB
        from pathlib import Path

        from database.config_database import get_config_database

        db = get_config_database()

        conn = db._open_connection()
        try:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            try:
                c.execute(
                    "SELECT absolute_install_path, name, channel_preference, beta_opt_in FROM services WHERE plugin_id=?",
                    (plugin_id,),
                )
            except sqlite3.OperationalError:
                c.execute(
                    "SELECT absolute_install_path, name, beta_opt_in FROM services WHERE plugin_id=?",
                    (plugin_id,),
                )
            row = c.fetchone()
            if row and row["name"]:
                install_path = row["absolute_install_path"]
                base_ns = row["name"]
                row_keys = row.keys() if hasattr(row, "keys") else []
                pref = (
                    row["channel_preference"]
                    if "channel_preference" in row_keys and row["channel_preference"]
                    else None
                )
                if not pref:
                    beta_opt = row["beta_opt_in"] if "beta_opt_in" in row_keys else None
                    pref = "beta" if beta_opt == 1 else "stable" if beta_opt == 0 else "inherit"
            else:
                raise ValueError(f"Plugin ID {plugin_id} not found in database for reload or missing name/path")
        finally:
            conn.close()

        clean_ns = base_ns.split("@")[0]
        if absolute_install_path:
            plugin_dir = Path(absolute_install_path)
            channel = "beta" if plugin_dir.name == "beta" else "stable"
        else:
            plugin_dir, channel = resolve_plugin_directory(
                name=clean_ns,
                channel_preference=pref,
                absolute_install_path=install_path,
            )

        if not plugin_dir.exists() or not (
            (plugin_dir / "plugin.json").is_file() or (plugin_dir / "manifest.json").is_file()
        ):
            raise FileNotFoundError(
                f"No valid plugin directory found for {clean_ns}; checked {plugin_dir} "
                f"(channel={channel}, install_path={install_path!r})"
            )

        if not absolute_install_path and str(plugin_dir.resolve()) != str(install_path):
            from core.task_manager import db_write_lease

            with db_write_lease(task_name=f"update_plugin_path_{plugin_id}"):
                with db._open_connection() as update_conn:
                    update_conn.execute(
                        "UPDATE services SET absolute_install_path=? WHERE plugin_id=?",
                        (str(plugin_dir.resolve()), plugin_id),
                    )
                    update_conn.commit()

        logger.info(f"Reloading {plugin_id} ({channel}) from {plugin_dir}")

        # 2. Kill Workers
        try:
            from core.job_queue import job_queue
            from core.task_manager import (
                PluginLifecycleState,
                plugin_state_manager,
                supervisor,
            )

            job_queue.kill_jobs_by_plugin(plugin_id)
            supervisor.terminate_owner_processes(str(plugin_id))
            supervisor.terminate_owner_processes(clean_ns)
            plugin_state_manager.set_state(clean_ns, PluginLifecycleState.INITIALIZING, "Hot reload initiated")
        except Exception as e:
            logger.warning("Failed to kill workers for the target plugin.")
            logger.debug(f"Raw exception data: {e}", exc_info=True)

        # 3. Purge Memory (Comprehensive Memory & Namespace Unload)
        try:
            modules_to_purge = set()
            conn = db._open_connection()
            try:
                c = conn.cursor()
                c.execute(
                    "SELECT loaded_modules FROM services WHERE plugin_id=?",
                    (plugin_id,),
                )
                row = c.fetchone()
                if row and row[0]:
                    import json

                    try:
                        modules_to_purge.update(json.loads(row[0]))
                    except Exception:
                        pass
            finally:
                conn.close()

            clean_name = clean_ns.lower().replace("echosync.", "").replace("echosync/", "").strip()
            ns_prefixes = {
                f"plugins.{clean_ns.lower()}",
                f"plugins.echosync.{clean_name}",
                f"echosync.{clean_name}",
                f"plugins.{clean_name}",
                clean_ns.lower(),
                clean_name,
            }
            resolved_plugin_dir = str(plugin_dir.resolve())

            for mod_name, mod_obj in list(sys.modules.items()):
                mod_lower = mod_name.lower()
                if any(mod_lower == pfx or mod_lower.startswith(f"{pfx}.") for pfx in ns_prefixes):
                    modules_to_purge.add(mod_name)
                    continue
                mod_file = getattr(mod_obj, "__file__", None)
                if mod_file:
                    try:
                        if str(Path(mod_file).resolve()).startswith(resolved_plugin_dir):
                            modules_to_purge.add(mod_name)
                    except Exception:
                        pass

            logger.info(f"Purging {len(modules_to_purge)} modules for {plugin_id} from sys.modules")
            for mod_ns in modules_to_purge:
                sys.modules.pop(mod_ns, None)

            import importlib

            importlib.invalidate_caches()
            PluginRegistry.unregister(plugin_id)
        except Exception as e:
            logger.error(f"Failed during memory purge during reload: {e}")

        # 4. Reload Package
        try:
            disabled = config_manager.get_disabled_plugins()
            is_disabled = clean_ns in disabled or str(plugin_id) in disabled

            success = self._load_plugin_package(
                plugin_id,
                is_beta=(channel == "beta"),
                is_disabled=is_disabled,
                absolute_install_path=str(plugin_dir.absolute()),
            )
            if success is False:
                raise Exception(f"Live-swap failed to load module for {plugin_id}")
            from core.task_manager import PluginLifecycleState, plugin_state_manager

            plugin_state_manager.set_state(clean_ns, PluginLifecycleState.READY, "Hot reload successful")
            logger.info(f"✅ Successfully live-swapped: {plugin_id}")
        except Exception as e:
            try:
                from core.task_manager import (
                    PluginLifecycleState,
                    plugin_state_manager,
                    supervisor,
                )

                supervisor.terminate_owner_processes(str(plugin_id))
                supervisor.terminate_owner_processes(clean_ns)
                plugin_state_manager.set_state(clean_ns, PluginLifecycleState.ERROR, f"Hot reload failed: {e}")
            except Exception:
                pass
            logger.error("An error occurred during framework execution.")
            logger.debug(f"Raw exception data: {e}", exc_info=True)
            raise

    def reconcile_services(self):
        """
        Authoritative startup reconciliation to enforce schema integrity,
        prune orphaned records, and garbage collect physical files.
        """
        logger.info("Starting authoritative services registry reconciliation...")
        import json
        import shutil
        import sqlite3

        from database.config_database import get_config_database

        db = get_config_database()

        from core.task_manager import db_write_lease

        plugins_dir = Path(config_manager.get_plugins_dir())
        core_services = {"system"}
        app_root = self.app_root
        core_path = str((app_root / "core").resolve())

        def has_valid_entry_point(path: Path) -> bool:
            return (path / "manifest.json").exists() or (path / "__init__.py").exists() or (path / "main.wasm").exists()

        active_db_paths = set()

        # 1. Discover physical plugins on disk and map canonical CRC32 keys
        canonical_plugins: dict[int, tuple[dict, Path]] = {}
        path_to_canonical_crc: dict[str, int] = {}
        alias_to_canonical_crc: dict[str, int] = {}

        if plugins_dir.exists():
            for author_item in list(plugins_dir.iterdir()):
                if not author_item.is_dir() or author_item.name.startswith("_") or author_item.name.lower() == "system":
                    continue
                for plugin_item in list(author_item.iterdir()):
                    if not plugin_item.is_dir():
                        continue
                    m_file = plugin_item / "manifest.json"
                    if m_file.exists():
                        try:
                            m_data = json.loads(m_file.read_text(encoding="utf-8"))
                            m_id = str(m_data.get("id") or f"{author_item.name}.{plugin_item.name}").strip()
                            c_crc = compute_plugin_crc32(m_id)
                            res_path = str(plugin_item.resolve())
                            canonical_plugins[c_crc] = (m_data, plugin_item)
                            path_to_canonical_crc[res_path] = c_crc
                            alias_to_canonical_crc[m_id.lower()] = c_crc
                            if m_data.get("name"):
                                alias_to_canonical_crc[m_data["name"].strip().lower()] = c_crc
                            if m_data.get("display_name"):
                                alias_to_canonical_crc[m_data["display_name"].strip().lower()] = c_crc
                            alias_to_canonical_crc[f"{author_item.name}.{plugin_item.name}".lower()] = c_crc
                            alias_to_canonical_crc[plugin_item.name.lower()] = c_crc
                        except Exception as e:
                            logger.error(f"Error reading manifest for {plugin_item}: {e}")

        with db_write_lease(task_name="reconcile_services"):
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

                seen_canonical_ids = set()
                seen_names = set()

                for row in existing_rows:
                    db_id = row["id"]
                    name = row["name"]
                    p_id = row["plugin_id"]
                    install_path = row["absolute_install_path"]

                    # Core Service handling
                    if name.lower() in core_services:
                        if "system" in seen_names:
                            c.execute("DELETE FROM services WHERE id=?", (db_id,))
                            continue
                        seen_names.add("system")
                        target_plugin_id = compute_plugin_crc32(name)
                        c.execute(
                            """
                            UPDATE services 
                            SET plugin_id=?, absolute_install_path=?, version=?, service_type=?, is_active=?, 
                                description=?, beta_opt_in=?, verified_source=?, privileged_mode=?, permissions=?, 
                                updated_at=strftime('%s','now')
                            WHERE id=?
                        """,
                            (
                                target_plugin_id,
                                core_path,
                                "2.5.2",
                                "system",
                                1,
                                f"{name.capitalize()} service",
                                0,
                                1,
                                1,
                                "[]",
                                db_id,
                            ),
                        )
                        continue

                    # Check if install_path or name resolves to a known canonical plugin on disk
                    matched_canonical_crc = None
                    if p_id is not None and p_id in canonical_plugins:
                        matched_canonical_crc = p_id
                    elif install_path:
                        try:
                            resolved_install_str = str(Path(install_path).resolve())
                            matched_canonical_crc = path_to_canonical_crc.get(resolved_install_str)
                        except Exception:
                            pass
                    if not matched_canonical_crc and name:
                        matched_canonical_crc = alias_to_canonical_crc.get(name.strip().lower())

                    if matched_canonical_crc is not None:
                        # This record matches a physical canonical plugin
                        if p_id == matched_canonical_crc:
                            # It is the canonical row
                            if matched_canonical_crc in seen_canonical_ids:
                                logger.warning(
                                    f"Authoritative Pruning: Deleting duplicate canonical service {name} (ID: {db_id})"
                                )
                                c.execute("DELETE FROM services WHERE id=?", (db_id,))
                                c.execute("DELETE FROM service_config WHERE service_id=?", (db_id,))
                                if p_id is not None:
                                    c.execute("DELETE FROM ui_components WHERE plugin_id=?", (p_id,))
                                continue

                            seen_canonical_ids.add(matched_canonical_crc)
                            m_data, plugin_item = canonical_plugins[matched_canonical_crc]
                            active_db_paths.add(str(plugin_item.resolve()))

                            # Check disabled config
                            disabled_plugins = config_manager.get_disabled_plugins() or []
                            disabled_ids = set()
                            for d in disabled_plugins:
                                d_str = str(d).strip()
                                if not d_str:
                                    continue
                                if d_str.isdigit():
                                    disabled_ids.add(int(d_str))
                                else:
                                    clean_d = d_str.lower().replace("echosync.", "").replace("echosync/", "").strip()
                                    disabled_ids.add(compute_plugin_crc32(d_str))
                                    disabled_ids.add(compute_plugin_crc32(clean_d))
                                    disabled_ids.add(compute_plugin_crc32(f"echosync.{clean_d}"))

                            is_disabled = matched_canonical_crc in disabled_ids
                            target_active = 0 if is_disabled else 1
                            raw_perms = row["permissions"]
                            parsed_perms = None
                            if raw_perms:
                                try:
                                    parsed_perms = json.loads(raw_perms)
                                except Exception:
                                    parsed_perms = None

                            needs_seed = False
                            if not parsed_perms:
                                needs_seed = True
                            elif isinstance(parsed_perms, list):
                                if "database.read_library" not in parsed_perms:
                                    needs_seed = True
                            elif isinstance(parsed_perms, dict):
                                db_perms = parsed_perms.get("database", {})
                                if not (
                                    isinstance(db_perms, dict) and db_perms.get("read_library")
                                ) and not parsed_perms.get("database.read_library"):
                                    needs_seed = True

                            if needs_seed:
                                from core.nexus_framework.permissions import seed_base_permissions

                                seeded_perms = seed_base_permissions(parsed_perms)
                                c.execute(
                                    "UPDATE services SET is_active = ?, absolute_install_path = ?, permissions = ? WHERE id = ?",
                                    (target_active, str(plugin_item.resolve()), json.dumps(seeded_perms), db_id),
                                )
                            else:
                                c.execute(
                                    "UPDATE services SET is_active = ?, absolute_install_path = ? WHERE id = ?",
                                    (target_active, str(plugin_item.resolve()), db_id),
                                )
                        else:
                            # Obsolete duplicate row with outdated or non-canonical CRC32
                            logger.warning(
                                f"Authoritative Pruning: Deleting obsolete non-canonical duplicate service {name} (ID: {db_id}, plugin_id: {p_id}, canonical: {matched_canonical_crc})"
                            )
                            c.execute("DELETE FROM services WHERE id=?", (db_id,))
                            c.execute("DELETE FROM service_config WHERE service_id=?", (db_id,))
                            if p_id is not None:
                                c.execute("DELETE FROM ui_components WHERE plugin_id=?", (p_id,))
                            continue
                    else:
                        # Row does not match any physical plugin in canonical_plugins
                        is_valid_sideload = False
                        if install_path:
                            resolved_install = Path(install_path)
                            if resolved_install.exists() and has_valid_entry_point(resolved_install):
                                is_valid_sideload = True
                                active_db_paths.add(str(resolved_install.resolve()))

                        if is_valid_sideload:
                            logger.info(f"Classifying unlisted local service {name} (ID: {db_id}) as sideload.")
                            raw_perms = row["permissions"]
                            parsed_perms = None
                            if raw_perms:
                                try:
                                    parsed_perms = json.loads(raw_perms)
                                except Exception:
                                    parsed_perms = None
                            from core.nexus_framework.permissions import seed_base_permissions

                            seeded_perms = seed_base_permissions(parsed_perms)
                            c.execute(
                                "UPDATE services SET service_type = 'sideload', beta_opt_in = 0, permissions = ? WHERE id = ?",
                                (json.dumps(seeded_perms), db_id),
                            )
                        else:
                            logger.warning(
                                f"Authoritative Pruning: Deleting invalid/orphaned database record: {name} (ID: {db_id})"
                            )
                            c.execute("DELETE FROM services WHERE id=?", (db_id,))
                            c.execute("DELETE FROM service_config WHERE service_id=?", (db_id,))
                            if p_id is not None:
                                c.execute("DELETE FROM ui_components WHERE plugin_id=?", (p_id,))
                            continue

                # Bootstrap any missing canonical physical plugins
                for c_crc, (m_data, plugin_item) in canonical_plugins.items():
                    if c_crc not in seen_canonical_ids:
                        logger.info(
                            f"Registering missing canonical plugin {m_data.get('id', plugin_item.name)} (CRC32: {c_crc})"
                        )
                        from core.nexus_framework.permissions import seed_base_permissions

                        seeded_manifest_perms = seed_base_permissions(m_data.get("permissions", {}))
                        c.execute(
                            """
                            INSERT INTO services(name, plugin_id, service_type, description, absolute_install_path, version, is_active, 
                                                 beta_opt_in, verified_source, privileged_mode, permissions, created_at, updated_at)
                            VALUES(?, ?, ?, ?, ?, ?, 1, 0, ?, ?, ?, strftime('%s','now'), strftime('%s','now'))
                        """,
                            (
                                m_data.get("name", plugin_item.name),
                                c_crc,
                                m_data.get("type") or m_data.get("category", "provider"),
                                m_data.get("description", ""),
                                str(plugin_item.resolve()),
                                m_data.get("version", "1.0.0"),
                                1 if m_data.get("verified_source") == "official" else 0,
                                1 if m_data.get("privileged") or m_data.get("privileged_mode") else 0,
                                json.dumps(seeded_manifest_perms),
                            ),
                        )
                        active_db_paths.add(str(plugin_item.resolve()))

                # Ensure all core services are present
                for name in core_services:
                    target_plugin_id = compute_plugin_crc32(name)
                    c.execute("SELECT id FROM services WHERE plugin_id=?", (target_plugin_id,))
                    if not c.fetchone():
                        logger.info(f"Bootstrapping missing core service: {name}")
                        c.execute(
                            """
                            INSERT INTO services(name, plugin_id, service_type, description, absolute_install_path, version, is_active, 
                                                 beta_opt_in, verified_source, privileged_mode, permissions, created_at, updated_at)
                            VALUES(?, ?, 'system', ?, ?, '2.5.2', 1, 0, 1, 1, '[]', strftime('%s','now'), strftime('%s','now'))
                        """,
                            (
                                name,
                                target_plugin_id,
                                f"{name.capitalize()} service",
                                core_path,
                            ),
                        )
                conn.commit()
            finally:
                conn.close()

        # Startup Garbage Collection Sweep
        if os.getenv("DEV_MODE", "").lower() == "true":
            logger.info("[system] - DEV_MODE is active. Skipping plugin folder garbage collection.")
        elif plugins_dir.exists():
            for author_item in list(plugins_dir.iterdir()):
                if not author_item.is_dir() or author_item.name.startswith("_") or author_item.name.lower() == "system":
                    continue

                is_empty = True
                has_active_children = False

                for plugin_item in list(author_item.iterdir()):
                    is_empty = False
                    if str(plugin_item.resolve()) in active_db_paths:
                        has_active_children = True
                    elif plugin_item.is_dir():
                        # check manifest for dev_mode shield
                        manifest_file = plugin_item / "manifest.json"
                        if manifest_file.exists():
                            try:
                                manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                                if manifest_data.get("dev_mode") is True:
                                    logger.info(
                                        f"[system] - Plugin '{plugin_item.name}' is in dev_mode. Bypassing garbage collection."
                                    )
                                    has_active_children = True
                            except Exception:
                                pass

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

        safe_mode = os.environ.get("ECHOSYNC_SAFE_MODE") == "1" or config_manager.get("safe_mode") == True
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
                try:
                    c.execute(
                        "SELECT name, plugin_id, absolute_install_path, loaded_modules, channel_preference, beta_opt_in FROM services WHERE is_active = 1"
                    )
                except sqlite3.OperationalError:
                    c.execute(
                        "SELECT name, plugin_id, absolute_install_path, loaded_modules, beta_opt_in FROM services WHERE is_active = 1"
                    )
                active_services = c.fetchall()
            finally:
                conn.close()
        except Exception as e:
            logger.error("Failed to query active services from the database.")
            logger.debug(f"Raw exception data: {e}", exc_info=True)
            return

        for row in active_services:
            p_id = row["plugin_id"]
            name = row["name"]
            install_path = row["absolute_install_path"]

            row_keys = row.keys() if hasattr(row, "keys") else []
            pref = row["channel_preference"] if "channel_preference" in row_keys and row["channel_preference"] else None
            if not pref:
                beta_opt = row["beta_opt_in"] if "beta_opt_in" in row_keys else None
                pref = "beta" if beta_opt == 1 else "stable" if beta_opt == 0 else "inherit"

            # Skip core/built-in services (only 'system' is core now, others are community)
            if name.lower() in {"system"}:
                continue

            # Determine plugin directory and channel via canonical resolution
            plugin_dir, channel = resolve_plugin_directory(
                name=name,
                channel_preference=pref,
                absolute_install_path=install_path,
            )

            if not plugin_dir.exists():
                logger.error(f"Plugin directory not specified or does not exist for {name}: {plugin_dir}")
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
                    privileged = (
                        manifest_data.get("privileged") is True
                        or manifest_data.get("privileged_mode") is True
                        or (
                            isinstance(manifest_data.get("permissions"), dict)
                            and manifest_data.get("permissions", {}).get("privileged_mode") is True
                        )
                    )
                except Exception:
                    pass

            if wasm_file.exists():
                bypass_security = True

            if not bypass_security and not self._security_scan_package(plugin_dir, name, privileged=privileged):
                logger.warning(f"Plugin '{name}' rejected by security scanner.")
                continue

            # Load the package
            self._load_plugin_package(
                p_id,
                is_beta=(channel == "beta"),
                absolute_install_path=str(plugin_dir.absolute()),
            )

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
                    f"[SECURITY] Syntax error in '{py_file}' for plugin '{plugin_name}': {exc}. Refusing to load."
                )
                return False  # fail closed

            scanner = PluginSecurityScanner(privileged=privileged)
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

    def _update_db_version(self, plugin_id: int, version: str, capabilities_json: str = "{}"):
        try:
            from database.config_database import get_config_database

            db = get_config_database()
            conn = db._open_connection()
            try:
                c = conn.cursor()
                c.execute(
                    """
                    UPDATE services 
                    SET version=?, capabilities=? 
                    WHERE plugin_id=?
                """,
                    (version, capabilities_json, plugin_id),
                )
                updated = c.rowcount
                conn.commit()
                logger.info(f"Stamped version {version} and capabilities for plugin_id {plugin_id}")
            finally:
                conn.close()
        except Exception as e:
            logger.error("An error occurred during framework execution.")
            logger.debug(f"Raw exception data: {e}", exc_info=True)
            logger.debug(f"Raw exception data: {e}", exc_info=True)

    def _load_plugin_package(
        self,
        plugin_id: int,
        is_beta: bool = False,
        is_disabled: bool = False,
        absolute_install_path: str = None,
    ):
        """
        Dynamically import a plugin package and register its exports.
        """
        with self._load_lock:
            try:
                if isinstance(plugin_id, str):
                    if plugin_id.isdigit():
                        plugin_id = int(plugin_id)
                    else:
                        plugin_id = generate_plugin_id(plugin_id.lower())

                # Query the database for the path if not provided
                if not absolute_install_path:
                    from database.config_database import get_config_database

                    db = get_config_database()
                    conn = db._open_connection()
                    try:
                        c = conn.cursor()
                        c.execute(
                            "SELECT absolute_install_path, name FROM services WHERE plugin_id=?",
                            (plugin_id,),
                        )
                        row = c.fetchone()
                        if row and row[0]:
                            absolute_install_path = row[0]
                            plugin_name = row[1]
                        else:
                            raise ValueError(
                                f"Plugin package for plugin_id {plugin_id} not found in database registry or has no path."
                            )
                    finally:
                        conn.close()
                else:
                    plugin_name = str(plugin_id)  # Fallback
                    try:
                        from database.config_database import get_config_database

                        db = get_config_database()
                        conn = db._open_connection()
                        try:
                            c = conn.cursor()
                            c.execute(
                                "SELECT name FROM services WHERE plugin_id=?",
                                (plugin_id,),
                            )
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
                    if plugins_root.name == "plugins":
                        found_plugins = True
                        break
                    plugins_root = plugins_root.parent

                if found_plugins:
                    plugins_root = plugins_root.parent  # go one up from 'plugins'
                    if str(plugins_root) not in sys.path:
                        sys.path.insert(0, str(plugins_root))

                    try:
                        rel_parts = package_dir.relative_to(plugins_root).parts
                        module_path = ".".join(rel_parts)
                        clean_ns = ".".join(rel_parts[1:])  # skip 'plugins'
                    except Exception:
                        clean_ns = plugin_name
                        module_path = (
                            f"plugins.{clean_ns}.beta"
                            if is_beta and not clean_ns.endswith(".beta")
                            else f"plugins.{clean_ns}"
                        )
                else:
                    # Fallback for test environments without 'plugins' in path
                    plugins_root = Path(package_dir).parent.parent
                    if str(plugins_root) not in sys.path:
                        sys.path.insert(0, str(plugins_root))
                    clean_ns = plugin_name
                    module_path = (
                        f"plugins.{clean_ns}.beta"
                        if is_beta and not clean_ns.endswith(".beta")
                        else f"plugins.{clean_ns}"
                    )

                # 2. Extract metadata from manifest
                version = "Unknown"
                author = "Unknown"
                category = "provider"

                manifest_file = package_dir / "manifest.json"
                if not manifest_file.exists():
                    manifest_file = package_dir / "plugin.json"
                manifest_data = {}
                if manifest_file.exists():
                    try:
                        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                        version = manifest_data.get("version", "Unknown")
                        author = manifest_data.get("author", "Unknown")
                        category = manifest_data.get("category", "provider")
                    except Exception:
                        pass

                manifest_permissions = manifest_data.get("permissions", [])
                if is_beta:
                    beta_manifest = package_dir / "beta" / "manifest.json"
                    if beta_manifest.exists():
                        try:
                            beta_data = json.loads(beta_manifest.read_text(encoding="utf-8"))
                            manifest_permissions = beta_data.get("permissions", manifest_permissions)
                        except Exception:
                            pass
                hydrated_permissions = _hydrate_manifest_permissions(plugin_id, manifest_permissions)

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
                    DisabledPlugin.permissions = hydrated_permissions

                    PluginRegistry.register(DisabledPlugin, name=provider_id, source_type="community")
                    self._update_db_version(plugin_id, version, capabilities_json="{}")
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
                        permissions = hydrated_permissions
                        _wrapper_instance = wrapper

                        def __init__(self):
                            pass

                    PluginRegistry.register(WasmClass, name=provider_id, source_type="community")
                    self._update_db_version(plugin_id, version, capabilities_json="{}")
                    return True

                plugins_root = Path(config_manager.get_plugins_dir())
                if str(plugins_root.parent) not in sys.path:
                    sys.path.insert(0, str(plugins_root.parent))
                if str(plugins_root) not in sys.path:
                    sys.path.insert(0, str(plugins_root))

                sys.path.insert(0, str(package_dir))

                plugins_root_resolved = str(plugins_root.resolve())
                if "plugins" in sys.modules and hasattr(sys.modules["plugins"], "__path__"):
                    plugin_paths = sys.modules["plugins"].__path__
                    if plugins_root_resolved not in plugin_paths:
                        plugin_paths.insert(0, plugins_root_resolved)
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
                                parts[-1] = parts[-1][:-3]  # remove .py

                            # Construct namespace
                            if parts:
                                ns = f"plugins.{clean_ns}." + ".".join(parts)
                            else:
                                ns = f"plugins.{clean_ns}"

                            plugin_modules.add(ns)
                        except Exception as path_e:
                            logger.warning(f"Failed to parse path for {py_file}: {path_e}")

                    # Retain tracked modules in memory to consolidate with imported sys.modules later
                except Exception as e:
                    logger.error("An error occurred during framework execution.")
                    logger.debug(f"Raw exception data: {e}", exc_info=True)
                    logger.debug(f"Raw exception data: {e}", exc_info=True)
                    raise

                # Registration
                if hasattr(module, "ProviderClass"):
                    provider_cls = module.ProviderClass
                    provider_cls.permissions = hydrated_permissions
                    PluginRegistry.register(provider_cls, name=provider_id, source_type="community")
                    caps_json = "{}"
                    caps = getattr(provider_cls, "capabilities", None)
                    if caps:
                        caps_json = json.dumps(
                            {
                                "name": getattr(caps, "name", provider_id),
                                "supports_playlists": getattr(
                                    getattr(caps, "supports_playlists", None),
                                    "name",
                                    "NONE",
                                ),
                                "search": getattr(caps, "search", {}).__dict__
                                if hasattr(getattr(caps, "search", None), "__dict__")
                                else {},
                                "metadata": getattr(getattr(caps, "metadata", None), "name", "MEDIUM"),
                                "supports_cover_art": getattr(caps, "supports_cover_art", False),
                                "supports_lyrics": getattr(caps, "supports_lyrics", False),
                                "supports_user_auth": getattr(caps, "supports_user_auth", False),
                                "supports_library_scan": getattr(caps, "supports_library_scan", False),
                                "supports_streaming": getattr(caps, "supports_streaming", False),
                                "supports_downloads": getattr(caps, "supports_downloads", False),
                                "pre_filters": getattr(caps, "pre_filters", [])
                                if hasattr(caps, "pre_filters")
                                else (["bitrate", "format"] if getattr(caps, "supports_pre_filtering", False) else []),
                                "playlist_algorithms": getattr(caps, "playlist_algorithms", None),
                                "fingerprint_algorithms": getattr(caps, "fingerprint_algorithms", [])
                                if hasattr(caps, "fingerprint_algorithms")
                                else (["chromaprint"] if getattr(caps, "supports_fingerprinting", False) else []),
                                "supports_metadata_fetch": getattr(caps, "supports_metadata_fetch", False),
                            }
                        )
                    self._update_db_version(plugin_id, version, capabilities_json=caps_json)
                else:
                    found = False
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, PluginBase) and attr is not PluginBase:
                            attr.permissions = hydrated_permissions
                            PluginRegistry.register(attr, name=provider_id, source_type="community")
                            caps_json = "{}"
                            caps = getattr(attr, "capabilities", None)
                            if caps:
                                caps_json = json.dumps(
                                    {
                                        "name": getattr(caps, "name", provider_id),
                                        "supports_playlists": getattr(
                                            getattr(caps, "supports_playlists", None),
                                            "name",
                                            "NONE",
                                        ),
                                        "search": getattr(caps, "search", {}).__dict__
                                        if hasattr(getattr(caps, "search", None), "__dict__")
                                        else {},
                                        "metadata": getattr(
                                            getattr(caps, "metadata", None),
                                            "name",
                                            "MEDIUM",
                                        ),
                                        "supports_cover_art": getattr(caps, "supports_cover_art", False),
                                        "supports_lyrics": getattr(caps, "supports_lyrics", False),
                                        "supports_user_auth": getattr(caps, "supports_user_auth", False),
                                        "supports_library_scan": getattr(caps, "supports_library_scan", False),
                                        "supports_streaming": getattr(caps, "supports_streaming", False),
                                        "supports_downloads": getattr(caps, "supports_downloads", False),
                                        "pre_filters": getattr(caps, "pre_filters", [])
                                        if hasattr(caps, "pre_filters")
                                        else (
                                            ["bitrate", "format"]
                                            if getattr(caps, "supports_pre_filtering", False)
                                            else []
                                        ),
                                        "playlist_algorithms": getattr(caps, "playlist_algorithms", None),
                                        "fingerprint_algorithms": getattr(caps, "fingerprint_algorithms", [])
                                        if hasattr(caps, "fingerprint_algorithms")
                                        else (
                                            ["chromaprint"] if getattr(caps, "supports_fingerprinting", False) else []
                                        ),
                                        "supports_metadata_fetch": getattr(caps, "supports_metadata_fetch", False),
                                    }
                                )
                            self._update_db_version(plugin_id, version, capabilities_json=caps_json)
                            found = True
                            break
                    if not found:
                        logger.debug(f"No PluginBase found in {module_path}")

                # Core-Driven Inversion of Control (IoC) Startup Hooks
                plugin_instance = None
                plugin_cls = None
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

                # Tear down existing FastAPI mounts for this plugin
                try:
                    if hasattr(self, "main_app") and self.main_app:
                        target_paths = {
                            f"/api/v1/plugins/{plugin_id}",
                            f"/api/v1/plugins/{clean_ns.lower()}",
                            f"/api/plugins/{plugin_id}",
                            f"/api/plugins/{clean_ns.lower()}",
                        }
                        # Iterate backwards to safely remove mounts
                        for i in range(len(self.main_app.routes) - 1, -1, -1):
                            route = self.main_app.routes[i]
                            # Use duck typing to find the Mount
                            if getattr(route, "path", None) in target_paths and route.__class__.__name__ == "Mount":
                                del self.main_app.routes[i]
                except Exception as e:
                    logger.warning("Failed to tear down existing routes for this plugin.")
                    logger.debug(f"Raw exception data: {e}", exc_info=True)

                # Collect FastAPI Routers and legacy Flask Blueprints
                from flask import Blueprint as FlaskBlueprint

                plugin_routers = []
                flask_blueprints = []
                seen_router_ids = set()
                for attr_name in dir(module):
                    attr_val = getattr(module, attr_name)
                    if isinstance(attr_val, APIRouter):
                        if id(attr_val) not in seen_router_ids:
                            seen_router_ids.add(id(attr_val))
                            logger.info(f"Found APIRouter {attr_name} in {module_path}")
                            plugin_routers.append(attr_val)
                    elif isinstance(attr_val, FlaskBlueprint) and not isinstance(attr_val, bool):
                        flask_blueprints.append(attr_val)
                logger.info(f"Plugin routers collected: {len(plugin_routers)}")

                if flask_blueprints and not plugin_routers:
                    name = manifest_data.get("name") or getattr(plugin_cls, "name", None) or plugin_name or provider_id
                    if not plugin_instance:
                        if not plugin_cls:
                            plugin_cls = PluginRegistry.get_plugin_class(provider_id)
                        if plugin_cls:
                            try:
                                plugin_instance = plugin_cls()
                            except Exception:
                                pass
                    if plugin_instance:
                        plugin_instance.router_status = "DEPRECATED_FLASK_UNSUPPORTED"
                    if plugin_cls:
                        plugin_cls.router_status = "DEPRECATED_FLASK_UNSUPPORTED"
                    logger.warning(
                        f"WARNING: Plugin '{name}' exposes a deprecated Flask Blueprint. Routes will not be mounted. Please update plugin via the store to a FastAPI-compatible version."
                    )

                if hasattr(self, "main_app") and self.main_app:
                    mount_prefixes = [
                        f"/api/v1/plugins/{plugin_id}",
                        f"/api/plugins/{plugin_id}",
                    ]
                    if clean_ns and clean_ns.lower() != str(plugin_id).lower():
                        mount_prefixes.extend(
                            [
                                f"/api/v1/plugins/{clean_ns.lower()}",
                                f"/api/plugins/{clean_ns.lower()}",
                            ]
                        )

                    if plugin_routers:
                        plugin_app = FastAPI(
                            title=f"Plugin: {provider_id}",
                            dependencies=[Depends(enforce_plugin_passport)],
                        )
                        for router in plugin_routers:
                            plugin_app.include_router(router)
                            for route in getattr(router, "routes", []):
                                if getattr(route, "path", None) == "/":
                                    plugin_app.add_api_route(
                                        "",
                                        route.endpoint,
                                        methods=route.methods,
                                        include_in_schema=False,
                                        response_model=getattr(route, "response_model", None),
                                    )

                        for pfx in mount_prefixes:
                            self.main_app.mount(pfx, plugin_app)
                            PluginRegistry._mounted_subapps[pfx.lower().rstrip("/")] = plugin_app
                            # Reorder routes so plugin mounts precede the SPA StaticFiles mount ('/')
                            mount_route = self.main_app.routes.pop()
                            insert_idx = len(self.main_app.routes)
                            for idx, r in enumerate(self.main_app.routes):
                                if getattr(r, "path", None) == "" and getattr(r, "name", None) == "static":
                                    insert_idx = idx
                                    break
                            self.main_app.routes.insert(insert_idx, mount_route)
                        logger.info(f"Mounted FastAPI sub-application for {plugin_id} at {mount_prefixes}")

                # Persist combined loaded_modules to DB (Single-Shot Write)
                try:
                    loaded_mods = set(m for m in sys.modules.keys() if m.startswith(module_path))
                    if "plugin_modules" in locals() or "plugin_modules" in globals():
                        loaded_mods.update(plugin_modules)
                    from database import execute_write_sql
                    from database.config_database import get_config_database

                    db = get_config_database()
                    execute_write_sql(
                        str(db.database_path),
                        "UPDATE services SET loaded_modules = ? WHERE plugin_id = ?",
                        (json.dumps(list(loaded_mods)), plugin_id),
                    )
                except Exception as db_err:
                    logger.debug(f"Failed to update loaded_modules for {plugin_id}: {db_err}")

                return True

            except Exception as e:
                logger.error("An error occurred during framework execution.")
                logger.error(f"Raw exception data: {e}", exc_info=True)
                # Auto-disable on fatal load error
                try:
                    from database import execute_write_sql
                    from database.config_database import get_config_database

                    db = get_config_database()
                    execute_write_sql(
                        str(db.database_path),
                        "UPDATE services SET is_active = 0 WHERE plugin_id = ?",
                        (plugin_id,),
                    )
                except Exception:
                    pass
                return False

    def get_all_blueprints(self) -> list[Blueprint]:
        return self.loaded_blueprints

    def get_plugin_by_capability(self, capability: Capability) -> PluginBase | None:
        """
        Get the first available plugin with the given capability.
        Delegates to PluginRegistry.
        """
        return get_plugin_by_capability(capability)


def get_plugin_by_capability(capability: Capability) -> PluginBase | None:
    """
    Get the first available provider with the given capability.
    Delegates to PluginRegistry.
    """
    providers = PluginRegistry.get_plugins_with_capability(capability)
    if providers:
        return providers[0]
    return None


def get_plugin(name: str) -> PluginBase | None:
    """
    Get a plugin instance by name.
    """
    try:
        return PluginRegistry.create_instance(name)
    except Exception:
        return None


@retry_sqlite_io(max_retries=5, base_delay=0.05, max_delay=1.0)
def get_all_plugins() -> list:
    import json
    import logging

    from database.config_database import get_config_database

    plugins_map = {}
    db = get_config_database()

    with db._get_connection() as conn:
        c = conn.cursor()
        try:
            c.execute(
                "SELECT name, plugin_id, absolute_install_path, description, version, is_active, capabilities, channel_preference, beta_opt_in FROM services"
            )
            rows = c.fetchall()
        except sqlite3.OperationalError:
            try:
                c.execute(
                    "SELECT name, plugin_id, absolute_install_path, description, version, is_active, capabilities, beta_opt_in FROM services"
                )
                rows = c.fetchall()
            except sqlite3.OperationalError as oe:
                err_msg = str(oe).lower()
                if any(token in err_msg for token in ("disk i/o error", "locked", "busy")):
                    raise
                logging.getLogger("plugin_loader").error(
                    "Database query failed: Unable to fetch plugin registry state."
                )
                logging.getLogger("plugin_loader").debug(f"Raw exception data: {oe}", exc_info=True)
                return []
            except Exception as e:
                logging.getLogger("plugin_loader").error(
                    "Database query failed: Unable to fetch plugin registry state."
                )
                logging.getLogger("plugin_loader").debug(f"Raw exception data: {e}", exc_info=True)
                return []
        except Exception as e:
            logging.getLogger("plugin_loader").error("Database query failed: Unable to fetch plugin registry state.")
            logging.getLogger("plugin_loader").debug(f"Raw exception data: {e}", exc_info=True)
            return []

        for row in rows:
            name = row["name"]
            if name.lower() == "system":
                continue

            try:
                caps = json.loads(row["capabilities"]) if row["capabilities"] else {}
            except Exception:
                caps = {}

            is_core_service = (
                not row["absolute_install_path"]
                or name.lower() in ("system", "core")
                or str(row["absolute_install_path"]).endswith(os.sep + "core")
            )

            row_keys = row.keys() if hasattr(row, "keys") else []
            pref = row["channel_preference"] if "channel_preference" in row_keys and row["channel_preference"] else None
            if not pref:
                beta_val = row["beta_opt_in"] if "beta_opt_in" in row_keys else None
                pref = "beta" if beta_val == 1 else "stable" if beta_val == 0 else "inherit"
            channel_preference = pref
            plugin_info = {
                "id": name,
                "plugin_id": row["plugin_id"],
                "name": name,
                "description": row["description"] or "Community plugin",
                "type": "core" if is_core_service else "community",
                "is_core": is_core_service,
                "version": row["version"] or "Unknown",
                "abs_path": row["absolute_install_path"],
                "enabled": bool(row["is_active"]),
                "capabilities": caps,
                "beta_opt_in": channel_preference,
                "channel_preference": channel_preference,
            }
            plugins_map[name] = plugin_info

    return list(plugins_map.values())


class PluginRegistry:
    """
    Central registry for all plugin classes. Allows registration, lookup, and listing.
    Supports both bundled (core) and community plugins with enable/disable functionality.
    """

    _plugins: dict[int, type[PluginBase]] = {}
    _plugin_sources: dict[int, str] = {}  # metadata: plugin_id -> source_type
    _disabled_plugins: set = set()
    _quality_options: dict[int, list[dict[str, Any]]] = {}
    _mounted_subapps: dict[str, Any] = {}

    @classmethod
    def get_all(cls) -> dict[int, dict[str, Any]]:
        """Return all registered plugins and their metadata."""
        all_plugins = {}
        for p_id, plugin_cls in cls._plugins.items():
            all_plugins[p_id] = {
                "class": plugin_cls,
                "source_type": cls._plugin_sources.get(p_id, "core"),
            }
        return all_plugins

    @classmethod
    def get_plugins_with_capability(cls, capability: Capability, exclude_disabled: bool = True) -> list[PluginBase]:
        """
        Return a list of instantiated plugins that support the given capability.
        """
        plugins = []
        for p_id, plugin_cls in cls._plugins.items():
            if exclude_disabled and p_id in cls._disabled_plugins:
                continue

            # Check if class has capabilities attribute and if it contains the capability
            caps = getattr(plugin_cls, "capabilities", None)

            # Since capabilities can be a property on the class, we may get a property object back.
            if isinstance(caps, property):
                try:
                    # Instantiate to evaluate property if needed
                    instance = cls.create_instance(p_id)
                    if instance:
                        caps = getattr(instance, "capabilities", None)
                except Exception as e:
                    import logging

                    logging.getLogger().error("Error getting capabilities property: " + str(e))
                    caps = None

            # Normalize None -> empty iterable to avoid TypeError when doing 'in' checks
            if caps is None:
                caps = []

            # Some plugins expose a helper to convert to a list of Capability enums
            if hasattr(caps, "to_enum_list"):
                caps = caps.to_enum_list() or []

            # Defensive: if caps is not iterable, skip this plugin
            try:
                contains = capability in caps
            except TypeError:
                contains = False

            if contains:
                try:
                    # Reuse instance if we already created it
                    if "instance" in locals() and instance:
                        plugins.append(instance)
                    else:
                        try:
                            inst = cls.create_instance(p_id)
                        except ValueError:
                            # if it's an ad-hoc added plugin like in tests
                            if isinstance(p_id, str) and p_id in cls._plugins:
                                inst = cls._plugins[p_id]()
                            else:
                                inst = None
                        if inst:
                            plugins.append(inst)
                except Exception as e:
                    logger.error("An error occurred during framework execution.")
                    logger.debug(f"Raw exception data: {e}", exc_info=True)
        return plugins

    @classmethod
    def get_plugins_by_type(cls, plugin_type: str, exclude_disabled: bool = True) -> list[int]:
        """
        Return a list of plugin IDs matching the given type.
        plugin_type: 'downloader', 'mediaserver', 'syncservice'
        """
        type_map = {
            "downloader": DownloaderProvider,
            "mediaserver": MediaServerProvider,
            "syncservice": SyncServiceProvider,
        }
        base_type = type_map.get(plugin_type.lower())
        if not base_type:
            raise ValueError(f"Unknown plugin type: {plugin_type}")

        plugins = [p_id for p_id, cls_ in cls._plugins.items() if issubclass(cls_, base_type)]
        if exclude_disabled:
            plugins = [p_id for p_id in plugins if p_id not in cls._disabled_plugins]
        return plugins

    @classmethod
    def get_active_services_by_type(cls, service_type: str) -> list[int]:
        """
        Return a list of active (enabled and configured) plugin IDs for a given service role.
        Normalized service_type aliases: 'media_server', 'download', 'sync', 'metadata'
        """
        # Mapping common codebase aliases to internal base class keys
        normalized_map = {
            "media_server": "mediaserver",
            "download": "downloader",
            "sync": "syncservice",
        }

        target_role = service_type.lower()
        mapped_type = normalized_map.get(target_role, target_role)

        # Special handling for metadata role (role based on capability rather than base class)
        if mapped_type == "metadata":
            from core.enums import Capability

            active = []
            for p in cls.get_plugins_with_capability(Capability.FETCH_METADATA):
                # reg_name is now plugin_id string
                reg_name = getattr(
                    p,
                    "_registered_name",
                    str(p.plugin_id_int) if hasattr(p, "plugin_id_int") else None,
                )
                if not reg_name:
                    continue
                p_id = int(reg_name)

                if p_id not in cls._disabled_plugins:
                    # Verify configuration if possible
                    if hasattr(p, "is_configured"):
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
                    if hasattr(instance, "is_configured"):
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
    def create_instance_by_type(cls, plugin_type: str, *args, **kwargs) -> list[PluginBase]:
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
    def register(
        cls,
        plugin_cls: type[PluginBase],
        name: str | None = None,
        source_type: str = "core",
    ):
        """
        Register a plugin class.

        Args:
            plugin_cls: The class implementing PluginBase.
            name: Optional explicit name override.
            source_type: 'core' for bundled plugins, 'community' for plugins.
        """
        if not name:
            name = getattr(plugin_cls, "name", None)

        if not name:
            raise ValueError("Plugin class must have a 'name' attribute or explicit name provided")

        plugin_id = generate_plugin_id(name.lower())
        cls._plugins[plugin_id] = plugin_cls
        cls._plugin_sources[plugin_id] = source_type
        logger.debug(f"Registered plugin '{name}' (source: {source_type})")

    @classmethod
    def unregister(cls, plugin_id: int):
        """Unregister a plugin class and remove from registry."""
        if isinstance(plugin_id, str):
            if plugin_id.isdigit():
                plugin_id = int(plugin_id)
            else:
                plugin_id = generate_plugin_id(plugin_id.lower())
        cls._plugins.pop(plugin_id, None)
        cls._plugin_sources.pop(plugin_id, None)
        logger.debug(f"Unregistered plugin ID '{plugin_id}' from PluginRegistry")

    @classmethod
    def get_plugin_class(cls, plugin_id: int) -> type[PluginBase] | None:
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
    def get_plugin_source(cls, plugin_id: int) -> str | None:
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
        if hasattr(plugin_cls, "router_status") and not hasattr(instance, "router_status"):
            instance.router_status = plugin_cls.router_status

        return instance

    @classmethod
    def get_plugin(cls, plugin_id: int) -> PluginBase | None:
        try:
            return cls.create_instance(plugin_id)
        except Exception:
            return None

    @classmethod
    def get_download_clients(cls) -> list[int]:
        """
        Return a list of plugin IDs that support downloads (excluding disabled ones).
        """
        clients = [p_id for p_id, cls_ in cls._plugins.items() if getattr(cls_, "supports_downloads", False)]
        return [p_id for p_id in clients if p_id not in cls._disabled_plugins]

    @classmethod
    def disable_plugin(cls, plugin_id: int) -> bool:
        orig_id = str(plugin_id)
        if isinstance(plugin_id, str):
            if plugin_id.isdigit():
                plugin_id = int(plugin_id)
            else:
                plugin_id = generate_plugin_id(plugin_id.lower())

        if plugin_id in cls._plugins:
            cls._disabled_plugins.add(plugin_id)
            try:
                from core.task_manager import (
                    PluginLifecycleState,
                    plugin_state_manager,
                    supervisor,
                )

                plugin_cls = cls._plugins.get(plugin_id)
                plugin_name = getattr(plugin_cls, "name", None) if plugin_cls else None

                supervisor.terminate_owner_processes(orig_id)
                supervisor.terminate_owner_processes(str(plugin_id))
                if plugin_name:
                    supervisor.terminate_owner_processes(plugin_name)
                    plugin_state_manager.set_state(
                        plugin_name,
                        PluginLifecycleState.UNCONFIGURED,
                        "Plugin disabled",
                    )

                plugin_state_manager.set_state(orig_id, PluginLifecycleState.UNCONFIGURED, "Plugin disabled")
            except Exception as e:
                logger.error(f"Error terminating processes/updating state for disabled plugin {plugin_id}: {e}")

            logger.info(f"Plugin ID '{plugin_id}' disabled.")
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
            disabled_ids = [int(d) if str(d).isdigit() else generate_plugin_id(str(d).lower()) for d in disabled]
            if plugin_id in disabled_ids:
                return True

        return False

    @classmethod
    def set_disabled_plugins(cls, disabled_list: list[str]) -> None:
        if disabled_list is None:
            disabled_list = []
        cls._disabled_plugins = set(
            int(d) if str(d).isdigit() else generate_plugin_id(str(d).lower()) for d in disabled_list
        )
        if disabled_list:
            logger.info(f"Disabled plugins: {', '.join(str(d) for d in disabled_list)}")

    @classmethod
    def get_disabled_plugins(cls) -> list[str]:
        return list(cls._disabled_plugins)

    @classmethod
    def register_quality_option(cls, plugin_id: str, option: dict[str, Any]):
        """Register a custom quality configuration field for a plugin."""
        if plugin_id not in cls._quality_options:
            cls._quality_options[plugin_id] = []

        # Check for duplicates by name within this plugin
        if not any(opt["name"] == option["name"] for opt in cls._quality_options[plugin_id]):
            cls._quality_options[plugin_id].append(option)

    @classmethod
    def get_all_quality_options(cls) -> list[dict[str, Any]]:
        """Retrieve all registered quality options across all plugins."""
        all_options = []
        for plugin_id, options in cls._quality_options.items():
            # Ensure each option carries its plugin_id context
            for opt in options:
                if "plugin_id" not in opt:
                    opt["plugin_id"] = plugin_id
                all_options.append(opt)
        return all_options


class ServiceRegistry:
    """
    Phase 2: Unified Service Registry
    Dependency Injection container for core platform services (e.g. MatchingEngine).
    Allows plugins to override default platform behaviors.
    """

    _services: dict[str, Any] = {}
    _defaults: dict[str, Any] = {}
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


@retry_sqlite_io(max_retries=5, base_delay=0.05, max_delay=1.0)
def get_plugin_capabilities(plugin_id_or_name: str | int):
    """
    Return capabilities for a plugin by looking up its registered capabilities in the database.
    """
    import json

    from core.nexus_framework.plugin_SDK import (
        MetadataRichness,
        PlaylistSupport,
        ProviderCapabilities,
        SearchCapabilities,
    )
    from database.config_database import get_config_database

    db = get_config_database()
    caps_json = "{}"
    try:
        with db._get_connection() as conn:
            c = conn.cursor()
            if isinstance(plugin_id_or_name, int):
                c.execute(
                    "SELECT capabilities FROM services WHERE plugin_id=?",
                    (plugin_id_or_name,),
                )
            else:
                c.execute(
                    "SELECT capabilities FROM services WHERE LOWER(name)=LOWER(?)",
                    (plugin_id_or_name,),
                )
            row = c.fetchone()
            if row and row["capabilities"]:
                caps_json = row["capabilities"]
    except sqlite3.OperationalError as oe:
        err_msg = str(oe).lower()
        if any(token in err_msg for token in ("disk i/o error", "locked", "busy")):
            raise
    except Exception:
        pass

    try:
        caps_dict = json.loads(caps_json)
    except Exception:
        caps_dict = {}

    search_caps = caps_dict.get("search", {})
    search_obj = SearchCapabilities(
        tracks=search_caps.get("tracks", False),
        artists=search_caps.get("artists", False),
        albums=search_caps.get("albums", False),
        playlists=search_caps.get("playlists", False),
    )

    playlist_enum = getattr(
        PlaylistSupport,
        caps_dict.get("supports_playlists", "NONE"),
        PlaylistSupport.NONE,
    )
    metadata_enum = getattr(MetadataRichness, caps_dict.get("metadata", "MEDIUM"), MetadataRichness.MEDIUM)

    return ProviderCapabilities(
        name=caps_dict.get("name", plugin_id_or_name),
        supports_playlists=playlist_enum,
        search=search_obj,
        metadata=metadata_enum,
        supports_cover_art=caps_dict.get("supports_cover_art", False),
        supports_lyrics=caps_dict.get("supports_lyrics", False),
        supports_user_auth=caps_dict.get("supports_user_auth", False),
        supports_library_scan=caps_dict.get("supports_library_scan", False),
        supports_streaming=caps_dict.get("supports_streaming", False),
        supports_downloads=caps_dict.get("supports_downloads", False),
        supports_pre_filtering=caps_dict.get("supports_pre_filtering", False),
        playlist_algorithms=caps_dict.get("playlist_algorithms", None),
        supports_fingerprinting=caps_dict.get("supports_fingerprinting", False),
        supports_metadata_fetch=caps_dict.get("supports_metadata_fetch", False),
    )
