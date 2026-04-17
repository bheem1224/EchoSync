"""Dynamic plugin loader for Echosync providers and plugins."""

import ast
import importlib
import importlib.util
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

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
_FORBIDDEN_BARE_CALLS: frozenset = frozenset({"open", "__import__"})

# Forbidden module.method() patterns
_FORBIDDEN_MODULE_CALLS: dict = {
    "os":     frozenset({"remove", "unlink", "rename"}),
    "shutil": frozenset({"move", "copy", "rmtree"}),
    # M1: removed the dead "__import__" entry — importlib has no such attribute.
    # The bare __import__('os') vector is already blocked by _FORBIDDEN_BARE_CALLS.
    "importlib": frozenset({"import_module", "reload"}),
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

    def __init__(self) -> None:
        # Each entry is (line_number, human_readable_description)
        self.violations: list = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.split('.')[0] in ("os", "subprocess", "sqlite3", "sys", "importlib"):
                self.violations.append((node.lineno, f"forbidden import '{alias.name}'"))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module and node.module.split('.')[0] in ("os", "subprocess", "sqlite3", "sys", "importlib"):
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
        self.providers_dir = app_root / "providers"
        self.plugins_dir = config_manager.get_plugins_dir()
        self.loaded_blueprints: List[Blueprint] = []

    def load_all(self):
        """Scan and load all providers and plugins."""
        logger.info("Starting plugin discovery...")
        logger.debug(f"Using plugins directory: {self.plugins_dir}")

        safe_mode = os.environ.get('ECHOSYNC_SAFE_MODE') == '1'

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
            init_file = item / "__init__.py"

            if not init_file.exists():
                logger.debug(f"Skipping {provider_name}: no __init__.py found")
                continue

            # Zero-Trust gate: scan community plugin source before importing
            if source_type == 'community':
                if not self._security_scan_package(item, provider_name):
                    logger.warning(
                        f"Plugin '{provider_name}' rejected by security scanner. Skipping."
                    )
                    continue

            self._load_provider_package(provider_name, directory.name, source_type)

    def _security_scan_package(self, package_dir: Path, plugin_name: str) -> bool:
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

    def _load_provider_package(self, name: str, parent_dir_name: str, source_type: str):
        """
        Dynamically import a provider package and register its exports.

        Args:
            name: The package name (e.g., 'plex').
            parent_dir_name: The parent directory name (e.g., 'providers' or 'plugins').
            source_type: 'core' or 'community'.
        """
        module_path = f"{parent_dir_name}.{name}"
        try:
            # Dynamic import
            module = importlib.import_module(module_path)

            # 1. Register Provider Class
            provider_class = getattr(module, 'ProviderClass', None)
            if provider_class and issubclass(provider_class, ProviderBase):
                # Check for registry conflicts or disabling logic if needed
                ProviderRegistry.register(provider_class, source_type=source_type)

                # Instantiate immediately to trigger any self-setup if needed
                # (Though strictly speaking, we might want to delay instantiation until needed,
                # existing logic often instantiates them. We will stick to registration for now
                # and let the app instantiate them via registry if needed, OR we can instantiate here
                # if that was the legacy behavior. The legacy behavior was explicit instantiation in _init_provider_clients.
                # BUT, ProviderRegistry.create_instance() is used later.
                # HOWEVER, some providers might need instantiation to set up listeners?
                # Let's check memory: "Instantiate provider clients so they self-register in plugin_registry" was the old way.
                # Now we register the CLASS directly. Instantiation happens when used.
                # BUT, we might want to instantiate them to verify config?
                # For now, just register the class.
                pass
            else:
                # Fallback: Look for any ProviderBase subclass if not explicitly exported
                # (Useful for transition or plugins that don't follow the new spec yet)
                found = False
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, ProviderBase) and attr is not ProviderBase:
                        ProviderRegistry.register(attr, source_type=source_type)
                        found = True
                        break
                if not found:
                    logger.debug(f"No ProviderClass found in {module_path}")

            # 2. Collect Route Blueprint
            blueprint = getattr(module, 'RouteBlueprint', None)
            if isinstance(blueprint, Blueprint):
                self.loaded_blueprints.append(blueprint)
                logger.debug(f"Collected blueprint for {name}")
            elif blueprint is not None:
                logger.warning(f"Invalid RouteBlueprint in {name}: expected flask.Blueprint, got {type(blueprint)}")

        except ImportError as e:
            logger.error(f"Failed to import {module_path}: {e}")
            # Graceful failure: Log and continue
        except Exception as e:
            logger.error(f"Unexpected error loading {module_path}: {e}", exc_info=True)

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
    import os
    import json
    from pathlib import Path
    from core.settings import config_manager
    from core.provider import ProviderRegistry

    plugins = []

    # Get Core Providers
    providers_dir = Path(__file__).parent.parent / "providers"
    if providers_dir.exists():
        for item in providers_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                plugins.append({
                    "id": f"core.{item.name}",
                    "name": item.name.capitalize(),
                    "description": f"Core provider for {item.name}",
                    "type": "core"
                })

    # Get Community Plugins
    plugins_dir = config_manager.get_plugins_dir()
    if plugins_dir.exists():
        for item in plugins_dir.iterdir():
            if item.is_dir() and not item.name.startswith('_'):
                plugin_info = {
                    "id": f"plugin.{item.name}",
                    "name": item.name,
                    "description": "Community plugin",
                    "type": "community"
                }

                json_file = item / "plugin.json"
                if json_file.exists():
                    try:
                        data = json.loads(json_file.read_text(encoding="utf-8"))
                        plugin_info.update({
                            "name": data.get("name", item.name),
                            "description": data.get("description", plugin_info["description"]),
                            "version": data.get("version", "Unknown"),
                            "author": data.get("author", "Unknown"),
                            "id": data.get("id", plugin_info["id"])
                        })
                    except Exception:
                        pass
                plugins.append(plugin_info)

    # Determine enabled status based on config
    disabled = config_manager.get_disabled_providers()
    for p in plugins:
        p["enabled"] = p["id"] not in disabled

    return plugins
