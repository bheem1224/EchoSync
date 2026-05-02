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

from core.plugin_SDK import PluginBase
from core.tiered_logger import get_logger
from core.settings import config_manager

logger = get_logger("plugin_loader")

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
    Registers them with the ProviderRegistry and collects Flask blueprints.
    """

    def __init__(self, app_root: Path):
        self.app_root = app_root
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

            setup_plugin_venv(self.plugins_dir, all_requirements)
        except Exception as e:
            logger.critical(f"Failed to setup plugin virtual environment: {e}")
            sys.exit(1) # Fatal error if we can't setup venv

        # 1. Load Core Providers

        # 2. Load Community Plugins (if directory exists)
        if safe_mode:
            logger.critical("SAFE MODE is active. Skipping discovery of community plugins.")
        elif self.plugins_dir.exists():
            self._scan_directory(self.plugins_dir)
        else:
            logger.debug("No plugins/ directory found. Skipping community plugins.")

        logger.info(f"Plugin discovery complete. Loaded {len(self.loaded_blueprints)} blueprints.")

    def _scan_directory(self, directory: Path):
        """
        Scan a directory for plugin packages.
        Enforces strict namespace formatting {source}.{author}.{plugin_name}.
        """
        import sys
        import importlib.util
        from core.security import is_privileged_or_verified

        for item in directory.iterdir():
            if not item.is_dir() or item.name.startswith('__'):
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
            wasm_file = current_item / "main.wasm"

            if not init_file.exists() and not wasm_file.exists():
                logger.debug(f"Skipping {provider_name}: no __init__.py or main.wasm found in {current_item}")
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

                # WASM Fast Track
                if wasm_file.exists() and not init_file.exists():
                    logger.info(f"WASM plugin detected: {provider_name}. Bypassing AST security scan.")
                    bypass_security = True

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

            if source_type == 'community':
                provider_id = f"plugin.{name}"
            else:
                provider_id = name

            # Handle WASM Plugins
            wasm_file = package_dir / "main.wasm"
            if wasm_file.exists() and not (package_dir / "__init__.py").exists():
                logger.info(f"Loading WASM plugin: {name}")
                from core.plugin_sdk import WasmPluginWrapper
                wrapper = WasmPluginWrapper(str(wasm_file.absolute()))
                wrapper.plugin_id_int = generate_plugin_id(provider_id)
                wrapper.version = version
                wrapper.author = author
                wrapper.category = category

                # In order to fit the ProviderRegistry generic type expectations, we wrap it in a mock class
                class WasmClass:
                    plugin_id_int = wrapper.plugin_id_int
                    version = wrapper.version
                    author = wrapper.author
                    category = wrapper.category
                    _wrapper_instance = wrapper

                    def __init__(self):
                        pass

                ProviderRegistry.register(WasmClass, name=provider_id, source_type=source_type)
                logger.info(f"Registered WASM plugin: {provider_id}")
                return

            # Dynamic import
            module = importlib.import_module(module_path)

            # 1. Register Provider Class (if present)
            if hasattr(module, 'ProviderClass'):
                provider_cls = getattr(module, 'ProviderClass')
                ProviderRegistry.register(provider_cls, name=provider_id, source_type=source_type)
                logger.debug(f"Registered ProviderClass for {provider_id} (v{version})")
            else:
                # Fallback: Look for any ProviderBase subclass if not explicitly exported
                found = False
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, PluginBase) and attr is not PluginBase and attr.__name__ != "DisabledProvider":
                        try:
                            # Instantiate and register
                            provider_instance = attr()

                            # Auto-set the fully qualified name if it didn't
                            if hasattr(provider_instance, 'name') and provider_instance.name != plugin_id:
                                logger.debug(f"Overriding plugin internal name '{provider_instance.name}' to strict namespace '{plugin_id}'")
                                provider_instance.name = plugin_id

                            PluginRegistry.register_provider(provider_instance)
                            logger.info(f"Loaded Plugin: {plugin_id} ({attr.__name__})")
                            found = True
                            break
                        except Exception as e:
                            logger.error(f"Failed to instantiate {attr.__name__} in {plugin_id}: {e}")
                if not found:
                    logger.debug(f"No PluginBase class found in {module_path}")

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
            config_manager.disable_provider(plugin_id)
        finally:
            # Cleanup vendored path
            if added_vendor_path and str(vendor_dir) in sys.path:
                sys.path.remove(str(vendor_dir))

    def get_all_blueprints(self) -> List[Blueprint]:
        return self.loaded_blueprints

    def get_provider(self, capability: Capability) -> Optional[PluginBase]:
        """
        Get the first available provider with the given capability.
        Delegates to ProviderRegistry.
        """
        return get_provider(capability)


def get_provider(capability: Capability) -> Optional[PluginBase]:
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


class PluginRegistry:
    """
    Central registry for all provider classes. Allows registration, lookup, and listing.
    Supports both bundled providers and community plugins with enable/disable functionality.
    """
    _providers: Dict[str, Type[PluginBase]] = {}
    _provider_sources: Dict[str, str] = {}  # metadata: provider_name -> source_type
    _disabled_providers: set = set()

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
    def create_instance(cls, name: str, *args, **kwargs) -> PluginBase:
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

def get_provider_capabilities(provider: str):
    """
    Return capabilities for a provider by looking up the provider class dynamically.
    Gracefully handles providers that don't declare explicit capabilities.
    """
    from core.plugin_SDK import ProviderCapabilities
    provider_cls = PluginRegistry.get_provider_class(provider)
    if not provider_cls:
        import logging
        logging.getLogger(__name__).warning(f"Provider '{provider}' not found in registry, defaulting to empty capabilities.")
        return ProviderCapabilities(name=provider, supports_playlists=None, search=None, metadata=None)

    return getattr(provider_cls, 'capabilities', ProviderCapabilities(name=provider, supports_playlists=None, search=None, metadata=None))
