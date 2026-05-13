import threading
"""Dynamic plugin loader for Echosync providers and plugins."""

import ast
import importlib
#import importlib.util
import os
import sys
import json
from pathlib import Path
from typing import Type, TypeVar, Protocol, List, Optional, Dict, Any

from core.plugin_venv import setup_plugin_venv

from flask import Blueprint

from core.enums import Capability

from core.plugin_SDK import PluginBase, DownloaderProvider, MediaServerProvider, SyncServiceProvider
from core.tiered_logger import get_logger
from core.settings import config_manager

logger = get_logger("plugin_loader")
import zlib

def generate_plugin_id(name: str) -> int:
    """Generate a consistent 32-bit integer ID from a plugin namespace."""
    return zlib.crc32(name.encode('utf-8')) & 0xFFFFFFFF

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
    "sqlite3": frozenset({"*"}),
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
            if base_module in ("os", "subprocess", "sqlite3", "sys", "importlib", "database", "inspect", "ctypes", "gc", "builtins"):
                if base_module in ("subprocess", "ctypes") and self.privileged:
                    continue
                self.violations.append((node.lineno, f"forbidden import '{alias.name}'"))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module in ("os", "subprocess", "sqlite3", "sys", "importlib", "database", "inspect", "ctypes", "gc", "builtins"):
                if base_module in ("subprocess", "ctypes") and self.privileged:
                    pass
                else:
                    self.violations.append((node.lineno, f"forbidden from-import '{node.module}'"))
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

    def _find_case_insensitive_path(self, base_path: Path, parts: List[str]) -> Optional[Path]:
        """Helper to find a directory path case-insensitively, part by part."""
        current = base_path
        for part in parts:
            if not current.exists():
                return None
            
            # Direct match first (most efficient)
            exact = current / part
            if exact.exists():
                current = exact
                continue
                
            # Case-insensitive search within the current directory
            match = None
            try:
                for item in current.iterdir():
                    if item.name.lower() == part.lower():
                        match = item
                        break
            except Exception:
                return None
            
            if match:
                current = match
            else:
                return None
        return current

    def reload_plugin(self, plugin_id: int):
        """Perform a true Zero-Downtime hot reload of a plugin."""
        logger.info(f"🔄 HOT-SWAP INITIATED: {plugin_id}")
        
        # 1. Resolve Namespace and Channel from DB
        from database.config_database import get_config_database
        db = get_config_database()
        base_ns = db.get_service_name(plugin_id)

        if not base_ns:
             raise ValueError(f"Plugin ID {plugin_id} not found in database for reload")

        # Clean namespace (remove @channel suffix for path resolution)
        clean_ns = base_ns.split('@')[0]
        
        # Determine channel: prioritize @beta suffix, then check config_manager
        channel = 'stable'
        if '@beta' in base_ns:
            channel = 'beta'
        else:
            channel = config_manager.get_plugin_channel(clean_ns) or 'stable'
        
        # Determine directory structure (Author.Plugin or Flat)
        parts = clean_ns.split('.')
        plugin_dir = self._find_case_insensitive_path(self.plugins_dir, parts)
        
        # Candidate 2: Flat fallback if author-nested doesn't exist
        if not plugin_dir or not plugin_dir.exists():
             plugin_dir = self._find_case_insensitive_path(self.plugins_dir, [parts[-1]])

        # Handle Beta Folder Nesting
        if channel == 'beta':
            beta_plugin_dir = plugin_dir / 'beta'
            if beta_plugin_dir.exists():
                plugin_dir = beta_plugin_dir
            else:
                logger.warning(f"Plugin {plugin_id} is on beta channel but {beta_plugin_dir} does not exist. Falling back to root: {plugin_dir}")

        if not plugin_dir.exists():
            # Final fallback check (very rare: plugin ID might be just the end name)
            if not plugin_dir.exists():
                 logger.error(f"Cannot reload {plugin_id}: path does not exist. Checked nested: {self.plugins_dir.joinpath(*parts)}, flat: {self.plugins_dir / parts[-1]}")
                 return

        logger.info(f"Reloading {plugin_id} ({channel}) from {plugin_dir}")

        # 2. Kill Workers
        try:
            from core.job_queue import job_queue
            job_queue.kill_jobs_by_plugin(plugin_id)
        except Exception as e:
            logger.warning(f"Failed to kill workers for {plugin_id}: {e}")

        # 3. Purge Memory (Recursive)
        # We purge both the potential namespace variants
        module_names = [f"plugins.{clean_ns}", f"plugins.{clean_ns.replace('.', '_')}"]
        
        for module_name in module_names:
            if module_name in sys.modules:
                logger.debug(f"Purging {module_name} and submodules from sys.modules")
                submodules = [m for m in list(sys.modules.keys()) if m.startswith(module_name + ".")]
                for m in submodules:
                    del sys.modules[m]
                del sys.modules[module_name]

        # 4. Reload Package
        try:
            disabled = config_manager.get_disabled_providers()
            is_disabled = clean_ns in disabled or str(plugin_id) in disabled
            
            success = self._load_plugin_package(
                clean_ns, 
                is_beta=(channel == 'beta'), 
                is_disabled=is_disabled
            )
            if success is False:
                raise Exception(f"Live-swap failed to load module for {plugin_id}")
            logger.info(f"✅ Successfully live-swapped: {plugin_id}")
        except Exception as e:
            logger.error(f"Live-swap failed for {plugin_id}: {e}", exc_info=True)
            raise

    def load_all(self):
        """Scan and load all plugins based on database definitions."""
        logger.info("Starting plugin discovery from database...")
        
        safe_mode = os.environ.get('ECHOSYNC_SAFE_MODE') == '1' or config_manager.get('safe_mode') == True
        if safe_mode:
            logger.critical("SAFE MODE is active. Skipping community plugin discovery.")
            return

        import sqlite3
        from database.config_database import get_config_database
        db = get_config_database()
        
        active_services = []
        try:
            with db._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                c.execute("SELECT friendly_name, plugin_id, absolute_install_path, loaded_modules FROM services WHERE is_active = 1")
                active_services = c.fetchall()
        except Exception as e:
            logger.error(f"Failed to query active services: {e}")
            return

        for row in active_services:

            p_id = row['plugin_id']
            install_path = row['absolute_install_path']
            
            # e.g., EchoSync.tidal@beta
            clean_ns = str(p_id)
            channel = 'stable'

            folder_path = clean_ns.replace('.', os.sep)
            plugin_dir = self.plugins_dir / folder_path
            
            # Fallback for flat structure
            if not plugin_dir.exists():
                plugin_dir = self.plugins_dir / clean_ns.split('.')[-1]

            if channel == 'beta':
                plugin_dir = plugin_dir / 'beta'

            if not plugin_dir.exists():
                logger.error(f"Plugin directory not found for {p_id}: {plugin_dir}")
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

            if not bypass_security and not self._security_scan_package(plugin_dir, clean_ns, privileged=privileged):
                logger.warning(f"Plugin '{clean_ns}' rejected by security scanner.")
                continue

            # Load the package
            self._load_plugin_package(clean_ns, is_beta=(channel == 'beta'))

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

    def _update_db_version(self, provider_id: str, version: str, clean_name: str):
        try:
            from database.config_database import get_config_database
            db = get_config_database()
            with db._get_connection() as conn:
                c = conn.cursor()
                # Use a flexible match for clean_name/provider_id to catch mismatches in plugin. vs core. prefixes
                c.execute("""
                    UPDATE services 
                    SET version=? 
                    WHERE LOWER(name)=LOWER(?) OR LOWER(friendly_name)=LOWER(?) OR LOWER(name)=LOWER(?) OR LOWER(friendly_name)=LOWER(?)
                """, (version, clean_name, provider_id, provider_id, clean_name))
                updated = c.rowcount
                conn.commit()
                logger.info(f"Stamped version {version} for {provider_id}")
        except Exception as e:
            logger.error(f"Failed to update version in DB for {provider_id}: {e}")

    def _load_plugin_package(self, plugin_id: int, is_beta: bool = False, is_disabled: bool = False):
        """
        Dynamically import a plugin package and register its exports.
        """
        with self._load_lock:
            # Normalize namespace for module and path
            clean_ns = str(plugin_id)
            
            if is_beta:
                module_path = f"plugins.{clean_ns}.beta"
            else:
                module_path = f"plugins.{clean_ns}"

            try:
                # 1. Resolve Path
                parts = clean_ns.split('.')
                package_dir = self._find_case_insensitive_path(self.plugins_dir, parts)
                
                if not package_dir or not package_dir.exists():
                    package_dir = self._find_case_insensitive_path(self.plugins_dir, [parts[-1]])
                
                # If both failed, we have a missing plugin
                if not package_dir:
                     raise ValueError(f"Plugin package {plugin_id} not found in {self.plugins_dir}")
                
                # DERIVE CORRECT CASING FROM DISK
                # This ensures module_path matches the filesystem exactly, preventing case-sensitive import errors
                try:
                    relative_path = package_dir.relative_to(self.plugins_dir)
                    actual_ns = ".".join(relative_path.parts)
                    if is_beta:
                        module_path = f"plugins.{actual_ns}.beta"
                    else:
                        module_path = f"plugins.{actual_ns}"
                    logger.debug(f"Resolved module path casing: {module_path}")
                except Exception as e:
                    logger.warning(f"Could not derive relative path for {package_dir}: {e}")

                if is_beta:
                    package_dir = package_dir / "beta"
                
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
                    self._update_db_version(provider_id, version, clean_ns)
                    logger.info(f"Registered disabled plugin: {provider_id} (v{version})")
                    return

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
                    self._update_db_version(provider_id, version, clean_ns)
                    return

                # Dynamic import with Namespace Bridging
                plugins_parent_str = str(self.plugins_dir.parent)
                added_to_path = False
                if plugins_parent_str not in sys.path:
                    sys.path.insert(0, plugins_parent_str)
                    added_to_path = True
                
                try:
                    # MISSION: Dynamic Import Pathing Patch (Namespace Injection)
                    base_module_name = f"plugins.{clean_ns}"
                    try:
                        importlib.invalidate_caches()
                        base_module = importlib.import_module(base_module_name)

                        channel_dir = str(package_dir.absolute())
                        if hasattr(base_module, '__path__'):
                            if not isinstance(base_module.__path__, list):
                                base_module.__path__ = list(base_module.__path__)
                            
                            if channel_dir not in base_module.__path__:
                                base_module.__path__.insert(0, channel_dir)
                                importlib.invalidate_caches()
                                logger.debug(f"Path Patch: Injected {channel_dir} into {base_module_name}")
                    except Exception as bridge_err:
                        logger.debug(f"Path Patch failed for {base_module_name}: {bridge_err}")

                    # Micro-Venv Injection
                    micro_venv_dir = package_dir / "micro-venv"
                    micro_venv_str = str(micro_venv_dir)
                    added_micro_venv = False
                    if micro_venv_dir.exists():
                        sys.path.insert(0, micro_venv_str)
                        added_micro_venv = True

                    try:
                        module = importlib.import_module(module_path)
                    except Exception as import_e:
                        logger.error(f"Failed to import {module_path}: {import_e}")
                        return False
                    finally:
                        if added_micro_venv:
                            sys.path.remove(micro_venv_str)
                finally:
                    if added_to_path:
                        sys.path.remove(plugins_parent_str)

                # Registration
                if hasattr(module, 'ProviderClass'):
                    provider_cls = getattr(module, 'ProviderClass')
                    PluginRegistry.register(provider_cls, name=provider_id, source_type='community')
                    self._update_db_version(provider_id, version, clean_ns)
                else:
                    found = False
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, PluginBase) and attr is not PluginBase:
                            provider_instance = attr()
                            provider_instance.name = provider_id
                            PluginRegistry.register_provider(provider_instance)
                            found = True
                            break
                    if not found:
                        logger.debug(f"No PluginBase found in {module_path}")

                # Collect Blueprints
                for bp_attr in ('RouteBlueprint', 'RouteBlueprint2', 'RouteBlueprint3'):
                    blueprint = getattr(module, bp_attr, None)
                    if isinstance(blueprint, Blueprint):
                        blueprint.name = f"{provider_id}_{bp_attr.lower()}"
                        blueprint.url_prefix = f"/api/plugins/{clean_ns}"
                        self.loaded_blueprints.append(blueprint)

            except Exception as e:
                logger.error(f"Error loading plugin {plugin_id}: {e}", exc_info=True)
                # Auto-disable on fatal load error
                try:
                    from database.config_database import get_config_database
                    db = get_config_database()
                    with db._get_connection() as conn:
                        conn.execute("UPDATE services SET is_active = 0 WHERE plugin_id = ?", (plugin_id,))
                except Exception: pass

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
    providers = PluginRegistry.get_providers_with_capability(capability)
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
    plugins_map = {}
    community_dir = Path(config_manager.get_plugins_dir())

    if not community_dir.exists():
        return []

    # 1. Identify all plugin candidates (Nexus Schema: plugins/{author}/{plugin})
    candidates = []
    for item in community_dir.iterdir():
        if not item.is_dir() or item.name.startswith('_'):
            continue
        
        # Case 1: Author/Plugin structure
        found_nested = False
        for subitem in item.iterdir():
            if subitem.is_dir() and not subitem.name.startswith('_'):
                if (subitem / "manifest.json").exists() or (subitem / "__init__.py").exists() or (subitem / "main.wasm").exists():
                    candidates.append((subitem, f"{item.name}.{subitem.name}"))
                    found_nested = True
        
        # Case 2: Flat structure (legacy/fallback)
        if not found_nested:
            if (item / "manifest.json").exists() or (item / "__init__.py").exists() or (item / "main.wasm").exists():
                candidates.append((item, item.name))

    for item, p_id in candidates:
        current_item = item
        channel = config_manager.get_plugin_channel(p_id)
        if channel == 'beta' and (item / 'beta').exists():
            current_item = item / 'beta'

        plugin_info = {
            "id": p_id,
            "name": str(p_id),
            "description": "Community plugin",
            "type": "community",

            "abs_path": str(current_item.absolute())
        }

        json_file = current_item / "manifest.json"
        if json_file.exists():
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                plugin_info.update({
                    "name": data.get("name", plugin_info["name"]),
                    "description": data.get("description", plugin_info["description"]),
                    "version": data.get("version", "Unknown"),
                    "author": data.get("author", "Unknown"),
                    "id": data.get("id", plugin_info["id"])
                })
            except Exception:
                pass

        ui_manifest_file = current_item / "ui_manifest.json"
        if ui_manifest_file.exists():
            try:
                plugin_info["ui_manifest"] = json.loads(ui_manifest_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        plugins_map[plugin_info["id"]] = plugin_info

    disabled = config_manager.get_disabled_providers()
    final_plugins = list(plugins_map.values())
    for p in final_plugins:
        p["enabled"] = p["id"].lower() not in [d.lower() for d in disabled]

    return final_plugins


class PluginRegistry:
    """
    Central registry for all plugin classes. Allows registration, lookup, and listing.
    Supports both bundled (core) and community plugins with enable/disable functionality.
    """
    _providers: Dict[str, Type[PluginBase]] = {}
    _provider_sources: Dict[str, str] = {}  # metadata: provider_name -> source_type
    _disabled_providers: set = set()
    _quality_options: Dict[str, List[Dict[str, Any]]] = {}

    @classmethod
    def get_all(cls) -> Dict[str, Dict[str, Any]]:
        """Return all registered plugins and their metadata."""
        all_plugins = {}
        for name, provider_cls in cls._providers.items():
            all_plugins[name] = {
                'class': provider_cls,
                'source_type': cls._provider_sources.get(name, 'core')
            }
        return all_plugins

    @classmethod
    def get_providers_with_capability(cls, capability: Capability, exclude_disabled: bool = True) -> List[PluginBase]:
        """
        Return a list of instantiated providers that support the given capability.
        """
        providers = []
        for name, provider_cls in cls._providers.items():
            if exclude_disabled and name.lower() in cls._disabled_providers:
                continue

            # Check if class has capabilities attribute and if it contains the capability
            caps = getattr(provider_cls, 'capabilities', None)
            # Normalize None -> empty iterable to avoid TypeError when doing 'in' checks
            if caps is None:
                caps = []

            # Some providers expose a helper to convert to a list of Capability enums
            if hasattr(caps, 'to_enum_list'):
                caps = caps.to_enum_list() or []

            # Defensive: if caps is not iterable, skip this provider
            try:
                contains = capability in caps
            except TypeError:
                contains = False

            if contains:
                try:
                    providers.append(cls.create_instance(name))
                except Exception as e:
                    logger.error(f"Failed to instantiate provider '{name}': {e}")
        return providers

    @classmethod
    def get_providers_by_type(cls, provider_type: str, exclude_disabled: bool = True) -> List[str]:
        """
        Return a list of provider names matching the given type.
        provider_type: 'downloader', 'mediaserver', 'syncservice'
        """
        type_map = {
            'downloader': DownloaderProvider,
            'mediaserver': MediaServerProvider,
            'syncservice': SyncServiceProvider
        }
        base_type = type_map.get(provider_type.lower())
        if not base_type:
            raise ValueError(f"Unknown provider type: {provider_type}")

        providers = [name for name, cls_ in cls._providers.items() if issubclass(cls_, base_type)]
        if exclude_disabled:
            providers = [name for name in providers if name.lower() not in cls._disabled_providers]
        return providers

    @classmethod
    def get_active_services_by_type(cls, service_type: str) -> List[str]:
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
            for p in cls.get_providers_with_capability(Capability.FETCH_METADATA):
                if p.name.lower() not in cls._disabled_providers:
                    # Verify configuration if possible
                    if hasattr(p, 'is_configured'):
                        if p.is_configured():
                            active.append(p.name)
                    else:
                        active.append(p.name)
            return active

        # Standard provider-type lookup
        try:
            potential_names = cls.get_providers_by_type(mapped_type, exclude_disabled=True)
            active = []
            for name in potential_names:
                try:
                    instance = cls.create_instance(name)
                    if hasattr(instance, 'is_configured'):
                        if instance.is_configured():
                            active.append(name)
                    else:
                        active.append(name)
                except Exception as e:
                    logger.error(f"Failed to check configuration for active service {name}: {e}")
                    # If we can't even instantiate it, it's not active
                    continue
            return active
        except ValueError:
            # If the type is unknown to get_providers_by_type, return empty list
            return []

    @classmethod
    def create_instance_by_type(cls, provider_type: str, *args, **kwargs) -> List[PluginBase]:
        """
        Instantiate all providers of a given type (excluding disabled ones).
        """
        names = cls.get_providers_by_type(provider_type, exclude_disabled=True)
        instances = []
        for name in names:
            try:
                instances.append(cls.create_instance(name, *args, **kwargs))
            except Exception as e:
                logger.error(f"Failed to instantiate provider '{name}': {e}")
        return instances

    @classmethod
    def register(cls, provider_cls: Type[PluginBase], name: Optional[str] = None, source_type: str = 'core'):
        """
        Register a provider class.

        Args:
            provider_cls: The class implementing PluginBase.
            name: Optional explicit name override.
            source_type: 'core' for bundled providers, 'community' for plugins.
        """
        if not name:
            name = getattr(provider_cls, 'name', None)

        if not name:
            raise ValueError("Provider class must have a 'name' attribute or explicit name provided")

        cls._providers[name.lower()] = provider_cls
        cls._provider_sources[name.lower()] = source_type
        logger.debug(f"Registered provider '{name}' (source: {source_type})")

    @classmethod
    def get_provider_class(cls, name: str) -> Optional[Type[PluginBase]]:
        return cls._providers.get(name.lower())

    @classmethod
    def list_providers(cls):
        return list(cls._providers.keys())

    @classmethod
    def get_provider_source(cls, name: str) -> Optional[str]:
        return cls._provider_sources.get(name.lower())

    @classmethod
    def create_instance(cls, name, *args, **kwargs) -> PluginBase:
        # Phase 2: Translation Bridge
        # If the incoming identifier is an integer (plugin_id), resolve it to its namespace
        original_name = name
        try:
            # Check if name is an int or a string representation of an int
            if isinstance(name, int) or (isinstance(name, str) and name.isdigit()):
                plugin_id = int(name)
                from database.config_database import get_config_database
                db = get_config_database()
                resolved_name = db.get_service_name(plugin_id)
                if not resolved_name:
                    raise ValueError(f"Provider with plugin_id '{plugin_id}' not found in database")
                name = resolved_name
        except Exception as e:
            if isinstance(e, ValueError) and "not found in database" in str(e):
                raise
            import logging
            logging.getLogger(__name__).warning(f"Failed to resolve integer plugin_id '{original_name}': {e}")

        # Double check against config manager to ensure latest state
        # (The set_disabled_providers might be stale if config reloaded)
        from core.settings import config_manager

        # Check global disabled list
        disabled = config_manager.get_disabled_providers()
        if disabled is None:
            disabled = []

        if name.lower() in [d.lower() for d in disabled]:
             raise ValueError(f"Provider '{name}' is disabled via config")

        if name.lower() in cls._disabled_providers:
            raise ValueError(f"Provider '{name}' is disabled")

        provider_cls = cls.get_provider_class(name)
        if not provider_cls:
            raise ValueError(f"Provider '{name}' not registered")
        return provider_cls(*args, **kwargs)

    @classmethod
    def get_download_clients(cls) -> List[str]:
        """
        Return a list of provider names that support downloads (excluding disabled ones).
        """
        clients = [name for name, cls_ in cls._providers.items() if getattr(cls_, 'supports_downloads', False)]
        return [name for name in clients if name.lower() not in cls._disabled_providers]

    @classmethod
    def disable_provider(cls, name: str) -> bool:
        if name.lower() in cls._providers:
            cls._disabled_providers.add(name.lower())
            logger.info(f"Provider '{name}' disabled. Restart required to unload.")
            return True
        return False

    @classmethod
    def enable_provider(cls, name: str) -> bool:
        if name.lower() in cls._providers:
            cls._disabled_providers.discard(name.lower())
            logger.info(f"Provider '{name}' enabled. Restart required to load.")
            return True
        return False

    @classmethod
    def is_provider_disabled(cls, name: str) -> bool:
        if getattr(cls, '_disabled_providers', None) is None:
            cls._disabled_providers = set()
        return name.lower() in cls._disabled_providers

    @classmethod
    def set_disabled_providers(cls, disabled_list: List[str]) -> None:
        if disabled_list is None:
            disabled_list = []
        cls._disabled_providers = set(name.lower() for name in disabled_list)
        if disabled_list:
            logger.info(f"Disabled providers: {', '.join(disabled_list)}")

    @classmethod
    def get_disabled_providers(cls) -> List[str]:
        return list(cls._disabled_providers)
    
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

def get_plugin_capabilities(plugin_name: str):
    """
    Return capabilities for a plugin by looking up the plugin class dynamically.
    Gracefully handles plugins that don't declare explicit capabilities.
    """
    from core.plugin_SDK import ProviderCapabilities
    provider_cls = PluginRegistry.get_provider_class(plugin_name)
    if not provider_cls:
        import logging
        logging.getLogger(__name__).warning(f"Plugin '{plugin_name}' not found in registry, defaulting to empty capabilities.")
        return ProviderCapabilities(name=plugin_name, supports_playlists=None, search=None, metadata=None)

    return getattr(provider_cls, 'capabilities', ProviderCapabilities(name=plugin_name, supports_playlists=None, search=None, metadata=None))

# Backward compatibility aliases for legacy Provider architecture
ProviderRegistry = PluginRegistry
get_provider_capabilities = get_plugin_capabilities
get_provider = get_plugin
provider_registry = PluginRegistry # Discovery engine expects this
