"""
PluginLoader â€” SoulSync plugin loading platform.

Architecture
============

Boot Sequence & Safe Mode Guardian
------------------------------------
Every boot starts by looking for a sentinel file::

    <config_dir>/.safe_mode.lock

* **Lock absent** (normal boot): create the lock, then load all plugins.
  If every plugin loads cleanly, the app calls ``finalize_boot()`` which
  deletes the lock.

* **Lock present** (crash-recovery boot): the *previous* boot crashed mid-
  load. Enter safe mode: log a critical warning, delete the lock so the
  *next* boot tries normal loading again, and skip **all** community plugins.
  Core providers (``providers/``) are still loaded because they are first-
  party and not subject to the community plugin sandboxing rules.

This is a classic canary-file pattern: the lock being *present* signals
"someone died holding this" rather than "safe mode was requested".

Community Plugin Loading
------------------------
For each subdirectory in ``<plugins_dir>/``:

1. Read ``manifest.json`` (required; plugin is skipped if absent/invalid).
2. Run :class:`core.plugins.security.PluginScanner` on every ``.py`` file:
   rejects forbidden ``import`` / ``from â€¦ import`` statements.
3. Run :class:`PluginSecurityScanner` on every ``.py`` file: rejects
   forbidden raw-I/O *call* sites (defence-in-depth layer 2).
4. Import the plugin module named by ``manifest["entrypoint"]``
   (default ``"__init__"``).
5. Call ``module.setup(hook_manager)`` so the plugin can register its
   filters and overrides.

If a community plugin causes **any** exception during steps 1-5, the
exception is caught and logged, ``self._boot_clean`` is set to ``False``,
and loading continues with the next plugin.  Because ``_boot_clean`` is
``False``, ``finalize_boot()`` will **not** delete the lock file, so the
**next** boot automatically enters safe mode.

Hook Manager & Overrides
------------------------
After loading, core systems query the hook manager::

    title = hook_manager.apply_filters("normalize_title", raw_title)
    engine = hook_manager.get_override("SuggestionEngine") or DefaultEngine()

See :mod:`core.plugins.hook_manager` for full API documentation.
"""

import ast
import importlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Blueprint

from core.enums import Capability
from core.plugins.hook_manager import HookManager, hook_manager
from core.plugins.security import (
    PluginScanner,
    SecurityViolationError,
    scan_file as _import_scan_file,
)
from core.provider import ProviderRegistry
from core.provider_base import ProviderBase
from core.settings import config_manager
from core.tiered_logger import get_logger

logger = get_logger("plugin_loader")

# ---------------------------------------------------------------------------
# Layer-2 call-site security scanner (preserved from original implementation)
# ---------------------------------------------------------------------------
# This scanner detects *uses* of forbidden callables regardless of how they
# were imported â€” complementing the import-level PluginScanner.

# Bare builtin calls that bypass the LocalFileHandler gateway.
_FORBIDDEN_BARE_CALLS: frozenset[str] = frozenset({"open"})

# module.method() call patterns.
_FORBIDDEN_MODULE_CALLS: dict[str, frozenset[str]] = {
    "os":     frozenset({"remove", "unlink", "rename"}),
    "shutil": frozenset({"move", "copy", "rmtree"}),
}

# Method names on *any* receiver (pathlib.Path is the primary target; the
# conservative match is intentional â€” plugins must route all I/O through
# LocalFileHandler).
_FORBIDDEN_METHOD_CALLS: frozenset[str] = frozenset({"unlink", "write_text", "open"})


class PluginSecurityScanner(ast.NodeVisitor):
    """
    Layer-2 AST pre-load scanner: detects forbidden raw file-I/O *call sites*.

    Forbidden patterns
    ------------------
    * ``open(...)``                â€” bare builtin
    * ``os.remove/unlink/rename`` â€” direct OS-level operations
    * ``shutil.move/copy/rmtree`` â€” destructive shutil operations
    * ``<any>.unlink()``          â€” pathlib.Path.unlink
    * ``<any>.write_text()``      â€” pathlib.Path.write_text
    * ``<any>.open()``            â€” pathlib.Path.open / builtin via attribute
    """

    def __init__(self) -> None:
        self.violations: list[tuple[int, str]] = []

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func

        if isinstance(func, ast.Name):
            if func.id in _FORBIDDEN_BARE_CALLS:
                self.violations.append((node.lineno, f"bare call to {func.id}()"))

        elif isinstance(func, ast.Attribute):
            attr = func.attr
            receiver = func.value

            if isinstance(receiver, ast.Name):
                forbidden_attrs = _FORBIDDEN_MODULE_CALLS.get(receiver.id)
                if forbidden_attrs and attr in forbidden_attrs:
                    self.violations.append(
                        (node.lineno, f"{receiver.id}.{attr}()")
                    )

            if attr in _FORBIDDEN_METHOD_CALLS:
                self.violations.append((node.lineno, f".{attr}() method call"))

        self.generic_visit(node)


# ---------------------------------------------------------------------------
# Safe-mode lock file path
# ---------------------------------------------------------------------------

def _lock_path() -> Path:
    """Return the absolute path of the safe-mode sentinel lock file."""
    return config_manager.config_dir / ".safe_mode.lock"


# ---------------------------------------------------------------------------
# PluginLoader
# ---------------------------------------------------------------------------

class PluginLoader:
    """
    Discovers, security-scans, and loads SoulSync providers and community plugins.

    Lifecycle::

        loader = PluginLoader(app_root=Path("."))
        loader.load_all()                 # boot sequence runs here
        app.register_blueprints(loader.get_all_blueprints())
        # â€¦ after the Flask event loop has started successfully:
        loader.finalize_boot()            # removes the lock file

    Attributes:
        safe_mode (bool):   ``True`` when a crash-recovery boot was detected.
        hook_manager:       The process-wide :class:`HookManager` instance;
                            exposed here for convenience.
    """

    def __init__(self, app_root: Path) -> None:
        self.app_root = app_root
        self.providers_dir = app_root / "providers"
        self.plugins_dir = config_manager.get_plugins_dir()
        self.provider_blueprints: List[tuple[str, Blueprint]] = []
        self.plugin_blueprints: List[Blueprint] = []
        self.hook_manager: HookManager = hook_manager

        # True once any community plugin raises during load.
        # Prevents finalize_boot() from deleting the lock.
        self._boot_clean: bool = True

        # â”€â”€ Safe Mode Guardian â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        lock = _lock_path()

        if lock.exists():
            # The previous boot crashed mid-load.  Activate safe mode for
            # this boot, then delete the lock so the *next* boot tries again.
            self.safe_mode = True
            logger.critical(
                "SAFE MODE ACTIVATED: '.safe_mode.lock' detected in '%s'. "
                "The previous boot crashed during plugin loading.  "
                "All community plugins will be skipped this boot.",
                config_manager.config_dir,
            )
            try:
                lock.unlink()
                logger.info("Safe-mode lock file removed (will retry plugins on next boot).")
            except OSError as exc:
                logger.error("Could not remove safe-mode lock file: %s", exc)
        else:
            self.safe_mode = False
            # â”€â”€ Normal boot: arm the lock before touching any plugin code â”€â”€
            try:
                lock.touch(exist_ok=True)
                logger.debug("Safe-mode lock file created: %s", lock)
            except OSError as exc:
                # Non-fatal: losing crash-protection is bad but shouldn't
                # prevent the app from starting.
                logger.warning(
                    "Could not create safe-mode lock file '%s': %s. "
                    "Crash-recovery protection is DISABLED for this boot.",
                    lock,
                    exc,
                )

    # â”€â”€ Public API â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def load_all(self) -> None:
        """
        Run the full discovery and loading sequence.

        1. Load core providers from ``providers/`` (always; safe mode does NOT
           affect first-party providers).
        2. Load community plugins from ``plugins/`` (skipped in safe mode).
        """
        logger.info(
            "Starting plugin discovery (safe_mode=%s)...", self.safe_mode
        )
        logger.debug("Providers directory: %s", self.providers_dir)
        logger.debug("Plugins  directory:  %s", self.plugins_dir)

        # â”€â”€ 1. Core providers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self._scan_core_providers()

        # â”€â”€ 2. Community plugins â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        if self.safe_mode:
            logger.warning(
                "Safe mode is active â€” skipping all community plugins."
            )
        elif not self.plugins_dir.exists():
            logger.debug(
                "Plugins directory '%s' does not exist â€” no community plugins to load.",
                self.plugins_dir,
            )
        else:
            self._load_community_plugins()

        logger.info(
            "Plugin discovery complete. "
            "Blueprints loaded: %d. Safe mode: %s. Boot clean: %s.",
            len(self.provider_blueprints) + len(self.plugin_blueprints),
            self.safe_mode,
            self._boot_clean,
        )

    def finalize_boot(self) -> None:
        """
        Signal that the application has started successfully.

        Deletes the safe-mode lock file so the *next* boot is a normal boot.
        This method MUST be called by the application after its main event
        loop is running â€” typically at the end of ``app.run()`` startup.

        If ``finalize_boot()`` is never called (e.g. because the process is
        killed by the OS or crashes before the event loop starts), the lock
        file persists and the next boot enters safe mode automatically.

        If any plugin crashed during this boot (``self._boot_clean is False``),
        the lock is intentionally NOT deleted so the next boot enters safe mode.
        """
        if self.safe_mode:
            # Lock was already deleted in __init__; nothing to do.
            logger.debug("finalize_boot: safe-mode boot â€” lock already handled.")
            return

        if not self._boot_clean:
            logger.warning(
                "finalize_boot: one or more community plugins crashed during "
                "this boot.  The safe-mode lock file will NOT be removed.  "
                "The next boot will enter safe mode to protect against repeated crashes."
            )
            return

        lock = _lock_path()
        try:
            lock.unlink(missing_ok=True)
            logger.info(
                "finalize_boot: safe-mode lock removed â€” application started cleanly."
            )
        except OSError as exc:
            logger.warning("finalize_boot: could not remove lock file: %s", exc)

    def get_all_blueprints(self) -> List[Blueprint]:
        """Return all Flask blueprints collected during :meth:`load_all`."""
        return [bp for _, bp in self.provider_blueprints] + self.plugin_blueprints

    def get_provider_blueprints(self) -> List[tuple[str, Blueprint]]:
        """Return provider blueprints as ``(provider_name, blueprint)`` tuples."""
        return self.provider_blueprints

    def get_plugin_blueprints(self) -> List[Blueprint]:
        """Return community plugin Flask blueprints."""
        return self.plugin_blueprints

    def get_provider(self, capability: "Capability") -> Optional[ProviderBase]:
        """Get the first available provider with *capability* via ProviderRegistry."""
        return get_provider(capability)

    # â”€â”€ Core provider loading (unchanged semantics from original) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _scan_core_providers(self) -> None:
        """Load first-party providers from the ``providers/`` directory."""
        self._scan_directory(self.providers_dir, source_type="core")

    def _scan_directory(self, directory: Path, source_type: str) -> None:
        """
        Scan *directory* for provider sub-packages and load each one found.

        A sub-package is a directory that contains ``__init__.py``.
        Directories starting with ``_`` are skipped.
        """
        if not directory.exists():
            logger.warning("Directory not found: %s", directory)
            return

        # Ensure parent is importable.
        str_parent = str(directory.parent)
        if str_parent not in sys.path:
            sys.path.insert(0, str_parent)

        for item in directory.iterdir():
            if not item.is_dir() or item.name.startswith("_"):
                continue
            if not (item / "__init__.py").exists():
                logger.debug("Skipping %s: no __init__.py", item.name)
                continue

            if source_type == "community":
                # Apply security scans before import.
                if not self._security_scan_package(item, item.name):
                    logger.warning(
                        "Provider/plugin '%s' rejected by security scan â€” skipping.",
                        item.name,
                    )
                    continue

            self._load_provider_package(item.name, directory.name, source_type)

    def _security_scan_package(self, package_dir: Path, plugin_name: str) -> bool:
        """
        Run **both** security scanners on every ``.py`` file in *package_dir*.

        Layer 1 â€” Import scan (:class:`PluginScanner` from ``security.py``):
            Rejects forbidden ``import`` / ``from â€¦ import`` statements.

        Layer 2 â€” Call-site scan (:class:`PluginSecurityScanner`):
            Rejects forbidden raw file-I/O call patterns.

        Returns ``True`` if the package is clean, ``False`` on the first
        violation.  Any unreadable or unparseable source file also returns
        ``False`` (fail-closed).
        """
        clean = True

        for py_file in sorted(package_dir.rglob("*.py")):
            # â”€â”€ Read source â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                logger.warning(
                    "[SECURITY] Could not read '%s' in plugin '%s': %s â€” refusing to load.",
                    py_file,
                    plugin_name,
                    exc,
                )
                return False

            # â”€â”€ Parse â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            try:
                tree = ast.parse(source, filename=str(py_file))
            except SyntaxError as exc:
                logger.warning(
                    "[SECURITY] Syntax error in '%s' (plugin '%s'): %s â€” refusing to load.",
                    py_file,
                    plugin_name,
                    exc,
                )
                return False

            # â”€â”€ Layer 1: import-level ban list â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            import_scanner = PluginScanner()
            import_scanner.visit(tree)
            for line, desc in import_scanner.violations:
                logger.critical(
                    "[SECURITY] Plugin '%s' rejected â€” banned import at line %d "
                    "in '%s': %s",
                    plugin_name,
                    line,
                    py_file.name,
                    desc,
                )
                clean = False

            # â”€â”€ Layer 2: call-site raw-I/O ban â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            call_scanner = PluginSecurityScanner()
            call_scanner.visit(tree)
            for line, desc in call_scanner.violations:
                logger.critical(
                    "[SECURITY] Plugin '%s' rejected â€” forbidden raw I/O call at "
                    "line %d in '%s': %s. Plugins MUST use core.file_handling.",
                    plugin_name,
                    line,
                    py_file.name,
                    desc,
                )
                clean = False

        return clean

    def _load_provider_package(
        self, name: str, parent_dir_name: str, source_type: str
    ) -> None:
        """
        Dynamically import a provider package and register its exports.

        Args:
            name:             Package name, e.g. ``"plex"``.
            parent_dir_name:  Parent directory name, e.g. ``"providers"``.
            source_type:      ``"core"`` or ``"community"``.
        """
        module_path = f"{parent_dir_name}.{name}"
        try:
            module = importlib.import_module(module_path)

            # â”€â”€ Register ProviderClass â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            provider_class = getattr(module, "ProviderClass", None)
            if provider_class and issubclass(provider_class, ProviderBase):
                ProviderRegistry.register(provider_class, source_type=source_type)
            else:
                # Fallback: auto-detect any ProviderBase subclass exported.
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, ProviderBase)
                        and attr is not ProviderBase
                    ):
                        ProviderRegistry.register(attr, source_type=source_type)
                        break
                else:
                    logger.debug("No ProviderClass found in %s", module_path)

            # â”€â”€ Collect Flask Blueprint â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            blueprint = getattr(module, "RouteBlueprint", None)
            if isinstance(blueprint, Blueprint):
                self.provider_blueprints.append((name, blueprint))
                logger.debug("Collected blueprint for %s", name)
            elif blueprint is not None:
                logger.warning(
                    "Invalid RouteBlueprint in %s: expected flask.Blueprint, got %s",
                    name,
                    type(blueprint),
                )

        except ImportError as exc:
            logger.error("Failed to import %s: %s", module_path, exc)
        except Exception as exc:
            logger.error(
                "Unexpected error loading %s: %s", module_path, exc, exc_info=True
            )

    # â”€â”€ Community plugin loading â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _load_community_plugins(self) -> None:
        """
        Discover and load every valid plugin package under :attr:`plugins_dir`.

        Each plugin directory must contain a ``manifest.json`` file.
        Security scanning, import, and ``setup()`` invocation all happen here.

        The **entire loop** is wrapped in a broad ``try/except`` so that even
        an unexpected error deep in one plugin's initialisation cannot crash
        the loader process.  When **any** plugin fails, ``self._boot_clean``
        is set to ``False``; this prevents :meth:`finalize_boot` from removing
        the lock file, so the next boot enters safe mode.
        """
        # Ensure the plugins directory parent is on sys.path.
        str_parent = str(self.plugins_dir.parent)
        if str_parent not in sys.path:
            sys.path.insert(0, str_parent)

        try:
            for plugin_dir in sorted(self.plugins_dir.iterdir()):
                if not plugin_dir.is_dir() or plugin_dir.name.startswith("_"):
                    continue

                # Read manifest first so dependency installation can happen
                # before any AST/security scan and import operations.
                manifest = self._read_manifest(plugin_dir, plugin_dir.name)
                if manifest is None:
                    continue

                dependencies = manifest.get("dependencies", [])
                if not isinstance(dependencies, list):
                    logger.warning(
                        "Plugin '%s': manifest 'dependencies' must be a list; skipping.",
                        plugin_dir.name,
                    )
                    continue

                if dependencies and not self._install_dependencies(plugin_dir.name, dependencies):
                    logger.critical(
                        "Plugin '%s': dependency installation failed; skipping plugin load.",
                        plugin_dir.name,
                    )
                    continue

                self._load_single_community_plugin(plugin_dir, manifest=manifest)
        except Exception as exc:
            # Outer catch for truly unexpected errors (e.g. filesystem failure
            # mid-iteration).  Keep lock alive.
            self._boot_clean = False
            logger.critical(
                "Fatal error during community plugin discovery loop: %s.  "
                "Safe mode will be active on the next boot.",
                exc,
                exc_info=True,
            )

    def _install_dependencies(self, plugin_name: str, dependencies: list[str]) -> bool:
        """Install plugin dependencies via uv before plugin import."""
        if not dependencies:
            return True

        try:
            result = subprocess.run(
                ["uv", "pip", "install"] + dependencies,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            logger.critical(
                "Plugin '%s': dependency installation timed out after 300 seconds.",
                plugin_name,
            )
            return False
        except Exception as exc:
            logger.critical(
                "Plugin '%s': dependency installation crashed: %s",
                plugin_name,
                exc,
                exc_info=True,
            )
            return False

        if result.returncode == 0:
            logger.info(
                "Plugin '%s': installed %d dependency(s) successfully.",
                plugin_name,
                len(dependencies),
            )
            return True

        logger.critical(
            "Plugin '%s': dependency installation failed: %s",
            plugin_name,
            result.stderr,
        )
        return False

    def _load_single_community_plugin(
        self,
        plugin_dir: Path,
        manifest: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Load one community plugin.  Any exception marks the boot as dirty.

        Steps
        -----
        1. Read and validate ``manifest.json``.
        2. Run layer-1 (import) + layer-2 (call-site) security scanners.
        3. Import the entrypoint module via :mod:`importlib`.
        4. Call ``module.setup(hook_manager)``.
        5. Collect any ``RouteBlueprint``.
        """
        plugin_name = plugin_dir.name
        try:
            # â”€â”€ Step 1: Read manifest â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            manifest = manifest or self._read_manifest(plugin_dir, plugin_name)
            if manifest is None:
                return  # already logged; skip without marking boot dirty

            declared_name = manifest.get("name", plugin_name)
            entrypoint = manifest.get("entrypoint", "__init__")
            version = manifest.get("version", "unknown")
            logger.info(
                "Loading community plugin '%s' v%s (entrypoint: %s.%s)",
                declared_name,
                version,
                plugin_dir.name,
                entrypoint,
            )

            # â”€â”€ Step 2: Security scan â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            if not self._security_scan_package(plugin_dir, plugin_name):
                logger.warning(
                    "Plugin '%s' failed security scan â€” skipping (boot remains clean).",
                    plugin_name,
                )
                # A security rejection is not a crash; don't mark boot dirty.
                return

            # â”€â”€ Step 3: Import â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            # Ensure the plugins/ parent is importable.
            str_plugins_parent = str(self.plugins_dir.parent)
            if str_plugins_parent not in sys.path:
                sys.path.insert(0, str_plugins_parent)

            if entrypoint == "__init__":
                module_path = f"{self.plugins_dir.name}.{plugin_dir.name}"
            else:
                module_path = f"{self.plugins_dir.name}.{plugin_dir.name}.{entrypoint}"

            module = importlib.import_module(module_path)

            # â”€â”€ Step 4: Call setup(hook_manager) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            setup_fn = getattr(module, "setup", None)
            if callable(setup_fn):
                setup_fn(self.hook_manager)
                logger.info(
                    "Plugin '%s': setup() completed successfully.", declared_name
                )
            else:
                logger.warning(
                    "Plugin '%s': no setup() function found in '%s'. "
                    "The plugin will not register any hooks or overrides.",
                    declared_name,
                    module_path,
                )

            # â”€â”€ Step 5: Collect Flask blueprint â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            blueprint = getattr(module, "RouteBlueprint", None)
            if isinstance(blueprint, Blueprint):
                self.plugin_blueprints.append(blueprint)
                logger.debug(
                    "Plugin '%s': collected RouteBlueprint.", declared_name
                )
            elif blueprint is not None:
                logger.warning(
                    "Plugin '%s': RouteBlueprint is not a flask.Blueprint (got %s).",
                    declared_name,
                    type(blueprint),
                )

        except SecurityViolationError:
            # Already logged in detail by the scanner; do NOT mark boot dirty
            # (security rejects are deliberate, not crashes).
            logger.warning(
                "Plugin '%s' rejected due to security violation.", plugin_name
            )

        except Exception as exc:
            # â”€â”€ CRASH: mark boot dirty â€” lock file stays alive â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            self._boot_clean = False
            logger.critical(
                "Plugin '%s' caused a fatal crash during loading: %s.  "
                "The safe-mode lock file will NOT be removed.  "
                "Safe mode will be active on the next boot.",
                plugin_name,
                exc,
                exc_info=True,
            )

    def _read_manifest(
        self, plugin_dir: Path, plugin_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Read and lightly validate ``manifest.json`` from *plugin_dir*.

        Returns the manifest dict on success, or ``None`` if the manifest is
        absent, unreadable, or missing required fields.  Missing manifests are
        logged at DEBUG level (expected for partially-installed plugins) while
        malformed ones are logged at WARNING.
        """
        manifest_path = plugin_dir / "manifest.json"

        if not manifest_path.exists():
            logger.debug(
                "Plugin directory '%s' has no manifest.json â€” skipping.",
                plugin_name,
            )
            return None

        try:
            raw = manifest_path.read_text(encoding="utf-8")
            manifest: Dict[str, Any] = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Could not read manifest.json for plugin '%s': %s â€” skipping.",
                plugin_name,
                exc,
            )
            return None

        # Require at least 'name' and 'version'.
        missing = [f for f in ("name", "version") if f not in manifest]
        if missing:
            logger.warning(
                "manifest.json for plugin '%s' is missing required fields %s â€” skipping.",
                plugin_name,
                missing,
            )
            return None

        return manifest


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

def get_provider(capability: "Capability") -> Optional[ProviderBase]:
    """Get the first available provider with *capability* via ProviderRegistry."""
    providers = ProviderRegistry.get_providers_with_capability(capability)
    if providers:
        return providers[0]
    return None
