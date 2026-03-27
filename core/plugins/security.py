"""
PluginScanner — AST-based import security analysis for community plugins.

Before importlib ever touches a plugin's source code, this scanner walks the
parse tree of every ``.py`` file, checking for import statements that would
grant the plugin unrestricted access to dangerous OS facilities.

Policy
------
A plugin file is **rejected** (``SecurityViolationError`` raised) if it
contains any ``Import`` or ``ImportFrom`` AST node whose resolved qualified
name appears in :data:`BANNED_IMPORTS`.

Recognised import patterns and how they are matched
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+--------------------------------------+----------------------------+----------+
| Python statement                     | Checked qualified name     | Blocked? |
+======================================+============================+==========+
| ``import subprocess``                | ``"subprocess"``           | Yes      |
+--------------------------------------+----------------------------+----------+
| ``import subprocess as sp``          | ``"subprocess"`` (asname   | Yes      |
|                                      | is irrelevant)             |          |
+--------------------------------------+----------------------------+----------+
| ``from subprocess import Popen``     | ``"subprocess"`` (module   | Yes      |
|                                      | is banned → whole import   |          |
|                                      | is rejected)               |          |
+--------------------------------------+----------------------------+----------+
| ``from os import system``            | ``"os.system"``            | Yes      |
+--------------------------------------+----------------------------+----------+
| ``from os import path``              | ``"os.path"``              | No       |
+--------------------------------------+----------------------------+----------+
| ``from shutil import rmtree``        | ``"shutil.rmtree"``        | Yes      |
+--------------------------------------+----------------------------+----------+
| ``from sys import exit``             | ``"sys.exit"``             | Yes      |
+--------------------------------------+----------------------------+----------+
| ``import importlib.util``            | ``"importlib.util"``       | Yes      |
+--------------------------------------+----------------------------+----------+

Limitations
~~~~~~~~~~~
The scanner operates on **syntax only** and cannot resolve:

* Aliases that hide module identity at runtime (``import os as _o``).
* Dynamic imports via ``__import__("subprocess")`` or ``importlib.import_module``.
* C-extension code.

Runtime sandboxing (Docker / seccomp / AppArmor) MUST provide the final
enforcement layer.  This scanner is a first line of defence that catches
the most common attack vectors and provides developers with clear rejection
messages at load time.

The existing call-level ``PluginSecurityScanner`` in ``core/plugin_loader.py``
complements this scanner by detecting *uses* of forbidden callables even when
they arrive through non-import paths.
"""

import ast
from pathlib import Path

from core.tiered_logger import get_logger

logger = get_logger("plugin_security")


# ---------------------------------------------------------------------------
# Configurable ban list
# ---------------------------------------------------------------------------
# Entries are interpreted as follows:
#
#   "subprocess"       → rejects   `import subprocess`
#                                   `import subprocess as X`
#                                   `from subprocess import <anything>`
#
#   "os.system"        → rejects   `from os import system`
#                        NOTE: bare `import os` is NOT banned — os.path is
#                        legitimately needed by many plugins.  The call-level
#                        scanner in plugin_loader.py catches os.system() usage.
#
#   "shutil.rmtree"    → rejects   `from shutil import rmtree`
#
#   "sys.exit"         → rejects   `from sys import exit`

BANNED_IMPORTS: frozenset[str] = frozenset({
    # ── Full module bans ────────────────────────────────────────────────────
    # Any import touching these modules is rejected outright.
    "subprocess",           # shell execution
    "multiprocessing",      # process spawning / shared memory
    "ctypes",               # direct memory / native code access
    "importlib",            # dynamic import bypass of this very scanner
    "importlib.util",       # importlib sub-namespace

    # ── Targeted function bans (module.symbol) ──────────────────────────────
    # These only block `from <module> import <symbol>`; bare `import <module>`
    # is still allowed when the module as a whole is not in the full-ban set.
    "os.system",
    "os.popen",
    "os.execv",
    "os.execve",
    "os.execvp",
    "os.execvpe",
    "os.fork",
    "os.forkpty",
    "os.kill",
    "os.killpg",
    "os.startfile",         # Windows shell launch
    "shutil.rmtree",
    "shutil.move",          # potential data exfiltration
    "shutil.copy",
    "shutil.copy2",
    "sys.exit",
    "sys.modules",          # module cache poisoning

    # ── builtins that bypass import machinery ───────────────────────────────
    # Caught only when explicitly re-imported via `from builtins import …`.
    # Bare calls like eval() are handled by the call-level scanner.
    "builtins.eval",
    "builtins.exec",
    "builtins.compile",
    "builtins.__import__",
})


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class SecurityViolationError(Exception):
    """
    Raised when a plugin source file contains one or more banned imports.

    Attributes:
        filepath:    Absolute path of the file that was scanned.
        violations:  Non-empty list of ``(line_number, description)`` tuples.
    """

    def __init__(self, filepath: str, violations: list[tuple[int, str]]) -> None:
        self.filepath = filepath
        self.violations = violations
        details = "; ".join(f"line {ln}: {desc}" for ln, desc in violations)
        super().__init__(f"Security violation in '{filepath}': {details}")


# ---------------------------------------------------------------------------
# AST visitor
# ---------------------------------------------------------------------------

class PluginScanner(ast.NodeVisitor):
    """
    AST visitor that populates :attr:`violations` for a single parsed module.

    Typical usage via :func:`scan_file`::

        scan_file("/path/to/plugin/main.py")   # raises SecurityViolationError

    Direct usage when you already hold a parse tree::

        scanner = PluginScanner()
        scanner.visit(tree)
        if scanner.violations:
            ...
    """

    def __init__(self) -> None:
        # Each entry is (1-based line number, human_readable_description)
        self.violations: list[tuple[int, str]] = []

    # ── AST node handlers ──────────────────────────────────────────────────

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        """
        Handle ``import X`` and ``import X as Y``.

        Checks:
        * Exact module name in ``BANNED_IMPORTS`` (e.g. ``"subprocess"``).
        * Module name is a dotted sub-path of a fully-banned module
          (e.g. ``import importlib.util`` → module ``"importlib.util"`` banned).
        """
        for alias in node.names:
            module_name = alias.name  # asname (alias.asname) is irrelevant
            if module_name in BANNED_IMPORTS:
                self.violations.append(
                    (node.lineno, f"import {module_name}")
                )
                continue

            # Catch sub-modules of a fully-banned module:
            #   import importlib.util  →  "importlib.util" not in set but
            #   "importlib" IS in set → reject.
            if any(
                module_name == banned or module_name.startswith(banned + ".")
                for banned in BANNED_IMPORTS
                if "." not in banned
            ):
                self.violations.append(
                    (node.lineno, f"import {module_name} (parent module is banned)")
                )

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        """
        Handle ``from X import Y`` and ``from X import Y as Z``.

        Checks each imported symbol against two forms:
        * ``"module"`` in ``BANNED_IMPORTS``         → full module ban
          (e.g. ``from subprocess import Popen``)
        * ``"module.symbol"`` in ``BANNED_IMPORTS``  → targeted function ban
          (e.g. ``from os import system``)
        """
        module = node.module or ""

        # Full module is banned → reject every symbol imported from it.
        if module in BANNED_IMPORTS:
            for alias in node.names:
                self.violations.append((
                    node.lineno,
                    f"from {module} import {alias.name} "
                    f"(module '{module}' is banned)",
                ))
            self.generic_visit(node)
            return

        # Targeted symbol-level check.
        for alias in node.names:
            symbol = alias.name          # asname is irrelevant for policy
            qualified = f"{module}.{symbol}" if module else symbol
            if qualified in BANNED_IMPORTS:
                self.violations.append(
                    (node.lineno, f"from {module} import {symbol}")
                )

        self.generic_visit(node)


# ---------------------------------------------------------------------------
# Public helper
# ---------------------------------------------------------------------------

def scan_file(filepath: str) -> None:
    """
    Parse and scan *filepath* for banned imports.

    On a clean file this function returns ``None`` silently.

    Args:
        filepath:  Path to a Python source file (``str`` or path-like).

    Raises:
        SecurityViolationError:
            One or more banned import statements were found.  The exception
            carries a ``violations`` list of ``(line_no, description)`` tuples
            and has already been logged at CRITICAL level for each violation.
        OSError:
            The file could not be opened or read.  Callers should treat this
            as a scan failure and refuse to load the plugin.
        SyntaxError:
            The file contains invalid Python.  Propagated as-is; callers
            should treat as a scan failure and refuse to load.
    """
    path = Path(filepath)
    source = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(source, filename=str(path))

    scanner = PluginScanner()
    scanner.visit(tree)

    if scanner.violations:
        for line_no, description in scanner.violations:
            logger.critical(
                "[SECURITY] Banned import at line %d in '%s': %s",
                line_no,
                path.name,
                description,
            )
        raise SecurityViolationError(str(path), scanner.violations)

    logger.debug("[SECURITY] Clean import scan: %s", path.name)
