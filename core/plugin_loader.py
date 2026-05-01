"""Dynamic plugin loader for Echosync providers and plugins."""

import ast
import importlib
#import importlib.util
import os
import sys
import json
from pathlib import Path
from typing import List, Optional

from core.plugin_venv import setup_plugin_venv

from flask import Blueprint

from core.enums import Capability
from core.provider import ProviderRegistry
from core.provider_base import ProviderBase
from core.tiered_logger import get_logger
from core.settings import config_manager

logger = get_logger("plugin_loader")

# ---------------------------------------------------------------------------
# Zero-Trust Plugin Security Scanner
# ---------------------------------------------------------------------------
# Forbidden bare-name calls (Python builtins used for direct file I/O)
_FORBIDDEN_BARE_CALLS: frozenset = frozenset({"open", "__import__", "eval", "exec", "getattr", "setattr", "globals", "locals"})

# Forbidden module.method() patterns
_FORBIDDEN_MODULE_CALLS: dict = {
    "os":     frozenset({"remove", "unlink", "rename"}),
    "shutil": frozenset({"move", "copy", "rmtree"}),
    # M1: removed the dead "__import__" entry — importlib has no such attribute.
    # The bare __import__('os') vector is already blocked by _FORBIDDEN_BARE_CALLS.
    "importlib": frozenset({"import_module", "reload"}),
    "builtins": frozenset({"eval", "exec", "getattr", "setattr"}),
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
                if base_module == "subprocess" and self.privileged:
                    continue
                self.violations.append((node.lineno, f"forbidden import '{alias.name}'"))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base_module = node.module.split('.')[0]
            if base_module in ("os", "subprocess", "sqlite3", "sys", "importlib", "database", "inspect", "ctypes", "gc", "builtins"):
                if not (base_module == "subprocess" and self.privileged):
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
                if forbidden_attrs and attr in forbidden_attrs:
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
    Registers them with the ProviderRegistry and collects Flask blueprints.
    """

    def __init__(self, app_root: Path):
        self.app_root = app_root
        self.providers_dir = app_root / "plugins"
        self.plugins_dir = config_manager.get_plugins_dir()
        self.loaded_blueprints: List[Blueprint] = []

    def load_all(self):
        """Scan and load all providers and plugins."""
        logger.info("Starting plugin discovery...")
        logger.debug(f"Using plugins directory: {self.plugins_dir}")

        safe_mode = os.environ.get('ECHOSYNC_SAFE_MODE') == '1'

        # Collect requirements before loading
        all_requirements = set()

        def _collect_requirements(directory: Path, source_type: str):
            if not directory.exists() or safe_mode and source_type == 'community':
                return
            for item in directory.iterdir():
                if not item.is_dir() or item.name.startswith('_'):
                    continue
                # Skip if disabled in config
                if source_type == 'community':
                    disabled = config_manager.get_disabled_providers()
                    if f"plugin.{item.name}" in disabled or item.name in disabled:
                        continue
                                
                current_item = item
                if source_type == 'community':
                    # Support Side-by-Side Architecture or Root Overwrite
                    channel = config_manager.get_plugin_channel(item.name)
                    # If we have a beta subfolder, use it, otherwise the root contains the swapped artifact
                    if channel == 'beta' and (item / 'beta').exists():
                        current_item = item / 'beta'

                manifest_file = current_item / "manifest.json"
                if manifest_file.exists():
                    try:
                        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                        reqs = manifest_data.get("requirements", [])
                        for req in reqs:
                            all_requirements.add(req)
                    except Exception as e:
                        logger.error(f"Failed to read manifest for {item.name} to collect requirements: {e}")

        # 0. Set up Plugin VENV and install dependencies
        try:
            _collect_requirements(self.plugins_dir, source_type='community')
            # Assuming core plugins could theoretically have requirements too
            _collect_requirements(self.providers_dir, source_type='core')

            setup_plugin_venv(self.plugins_dir, all_requirements)
        except Exception as e:
            logger.critical(f"Failed to setup plugin virtual environment: {e}")
            sys.exit(1) # Fatal error if we can't setup venv

        # 1. Load Core Providers
        self._scan_directory(self.providers_dir, source_type='core')

        # 2. Load Community Plugins (if directory exists)
        if safe_mode:
            logger.critical("SAFE MODE is active. Skipping discovery of community plugins.")
        elif self.plugins_dir.exists():
            self._scan_directory(self.plugins_dir, source_type='community')
        else:
            logger.debug("No plugins/ directory found. Skipping community plugins.")

        logger.info(f"Plugin discovery complete. Loaded {len(self.loaded_blueprints)} blueprints.")

    def _scan_directory(self, directory: Path, source_type: str):
        """
        Scan a directory for provider packages.

        Args:
            directory: The directory to scan (e.g., providers/).
            source_type: 'core' or 'community'.
        """
        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            return

        # Ensure the directory is in sys.path so imports work
        str_dir = str(directory.parent)
        if str_dir not in sys.path:
            sys.path.insert(0, str_dir)

        for item in directory.iterdir():
            if not item.is_dir() or item.name.startswith('_'):
                continue

            provider_name = item.name
            
            # Check if disabled in config
            disabled = config_manager.get_disabled_providers()
            is_disabled = f"plugin.{provider_name}" in disabled or provider_name in disabled

            # Channel logic for all plugins
            current_item = item
            is_beta = False

            channel = config_manager.get_plugin_channel(provider_name)
            if channel == 'beta' and (item / 'beta').exists():
                current_item = item / 'beta'
                is_beta = True

            init_file = current_item / "__init__.py"

            if not init_file.exists():
                logger.debug(f"Skipping {provider_name}: no __init__.py found in {current_item}")
                continue

            # Zero-Trust gate: scan community plugin source before importing


            if source_type == 'community':


                bypass_security = False
                manifest_data = None
                manifest_file = current_item / "manifest.json"


                if manifest_file.exists():


                    try:


                        import json


                        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))


                        if manifest_data.get("author") == "EchoSync" and manifest_data.get("verified_source") == "official":
                            bypass_security = True
                            logger.info(f"Bypassing security scan for official plugin: {provider_name}")
                        privileged = manifest_data.get("privileged") is True


                    except Exception as e:


                        logger.error(f"Failed to read manifest for {provider_name} during security check: {e}")





                privileged = manifest_data.get("privileged") is True if manifest_data else False
                if not bypass_security and not self._security_scan_package(current_item, provider_name, privileged=privileged):


                    logger.warning(


                        f"Plugin '{provider_name}' rejected by security scanner. Skipping."


                    )


                    continue

            self._load_provider_package(provider_name, directory.name, source_type, is_beta=is_beta, is_disabled=is_disabled)

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

    def _load_provider_package(self, name: str, parent_dir_name: str, source_type: str, is_beta: bool = False, is_disabled: bool = False):
        """
        Dynamically import a provider package and register its exports.

        Args:
            name: The package name (e.g., 'plex').
            parent_dir_name: The parent directory name (e.g., 'providers' or 'plugins').
            source_type: 'core' or 'community'.
            is_beta: True if loading from the 'beta' subfolder.
            is_disabled: True if the plugin is marked as disabled in config.
        """
        if is_beta:
            module_path = f"{parent_dir_name}.{name}.beta"
        else:
            module_path = f"{parent_dir_name}.{name}"
        try:
            # 0. Try to extract metadata from manifest before loading class
            version = "Unknown"
            author = "Unknown"
            category = "provider"
            package_dir = self.app_root / parent_dir_name / name
            if is_beta:
                package_dir = package_dir / "beta"
            
            manifest_file = package_dir / "manifest.json"
            if manifest_file.exists():
                try:
                    manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
                    version = manifest_data.get("version", "Unknown")
                    author = manifest_data.get("author", "Unknown")
                    category = manifest_data.get("category", "provider")
                except Exception:
                    pass

            # If disabled, register a placeholder and return early
            if is_disabled:
                from core.provider import DisabledProvider
                provider_id = f"plugin.{name}" if source_type == 'community' else name
                
                # Create a specific subclass for this disabled provider to hold its metadata
                class specific_disabled(DisabledProvider):
                    pass
                specific_disabled.version = version
                specific_disabled.author = author
                specific_disabled.category = category
                
                ProviderRegistry.register(specific_disabled, name=provider_id, source_type=source_type)
                logger.info(f"Registered disabled provider: {provider_id} (v{version})")
                return

            # Dynamic import
            module = importlib.import_module(module_path)
            
            # 1. Register Provider Class (if present)
            if source_type == 'community':
                provider_id = f"plugin.{name}"
            else:
                provider_id = name

            if hasattr(module, 'ProviderClass'):
                provider_cls = getattr(module, 'ProviderClass')
                ProviderRegistry.register(provider_cls, name=provider_id, source_type=source_type)
                logger.debug(f"Registered ProviderClass for {provider_id} (v{version})")
            else:
                # Fallback: Look for any ProviderBase subclass if not explicitly exported
                found = False
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, ProviderBase) and attr is not ProviderBase:
                        attr.version = version
                        attr.author = author
                        ProviderRegistry.register(attr, name=provider_id, source_type=source_type)
                        found = True
                        break
                if not found:
                    logger.debug(f"No ProviderClass found in {module_path}")

            # 2. Collect Route Blueprints (primary + optional extras: RouteBlueprint2, RouteBlueprint3 …)

            for bp_attr in ('RouteBlueprint', 'RouteBlueprint2', 'RouteBlueprint3'):
                blueprint = getattr(module, bp_attr, None)
                if blueprint is None:
                    continue
                if isinstance(blueprint, Blueprint):
                    # Enforce blueprint namespace and URL prefix to avoid collisions
                    plugin_id = name
                    if bp_attr != 'RouteBlueprint':
                        # Append the suffix for secondary blueprints
                        plugin_id += f"_{bp_attr.lower().replace('routeblueprint', '')}"

                    blueprint.name = plugin_id
                    blueprint.url_prefix = f"/api/plugins/{name}"

                    self.loaded_blueprints.append(blueprint)
                    logger.debug(f"Collected {bp_attr} for {name} with namespace {plugin_id}")
                else:
                    logger.warning(f"Invalid {bp_attr} in {name}: expected flask.Blueprint, got {type(blueprint)}")

        except Exception as e:
            logger.error(f"Error loading plugin {module_path}: {e}", exc_info=True)
            if name in ['local_server', 'local_metadata']:
                logger.critical(f"FATAL: Core plugin '{name}' failed to load. This will cause cascading failures. Shutting down.")
                sys.exit(1)
            else:
                logger.warning(f"Sandboxing: Disabling community plugin '{name}' due to load error.")
                # The config prefix for plugins is typically just the name or 'plugin.name'.
                # According to get_all_plugins in the same file, plugins have IDs like 'plugin.{name}'.
                # Let's disable the name directly. The config manager usually checks both or just 'name'.
                config_manager.disable_provider(f"plugin.{name}")
                config_manager.disable_provider(name) # Just to be safe based on how disable works


    def get_all_blueprints(self) -> List[Blueprint]:
        return self.loaded_blueprints

    def get_provider(self, capability: Capability) -> Optional[ProviderBase]:
        """
        Get the first available provider with the given capability.
        Delegates to ProviderRegistry.
        """
        return get_provider(capability)


def get_provider(capability: Capability) -> Optional[ProviderBase]:
    """
    Get the first available provider with the given capability.
    Delegates to ProviderRegistry.
    """
    providers = ProviderRegistry.get_providers_with_capability(capability)
    if providers:
        return providers[0]
    return None


def get_all_plugins() -> list:
    import json
    from pathlib import Path
    from core.settings import config_manager

    plugins = []
    
    core_dir = Path(__file__).parent.parent / "plugins"
    community_dir = config_manager.get_plugins_dir()

    for source_type, directory in [('core', core_dir), ('community', community_dir)]:
        if not directory.exists():
            continue

        for item in directory.iterdir():
            if not item.is_dir() or item.name.startswith('_'):
                continue

            current_item = item
            # Use the folder name for channel check, same as _scan_directory
            channel = config_manager.get_plugin_channel(item.name)
            if channel == 'beta' and (item / 'beta').exists():
                current_item = item / 'beta'

            plugin_info = {
                "id": f"{source_type}.{item.name}" if source_type == 'core' else f"plugin.{item.name}",
                "name": item.name.capitalize() if source_type == 'core' else item.name,
                "description": f"Core provider for {item.name}" if source_type == 'core' else "Community plugin",
                "type": source_type,
                "folder_name": item.name
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

            plugins.append(plugin_info)

    # Determine enabled status based on config
    disabled = config_manager.get_disabled_providers()
    for p in plugins:
        # Check against full ID (e.g. plugin.plex or plex)
        p["enabled"] = p["id"].lower() not in [d.lower() for d in disabled]

    return plugins
