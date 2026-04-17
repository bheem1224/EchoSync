"""
Tests for the Zero-Trust AST Plugin Security Scanner.

Covers two orthogonal categories:
  BLOCK  — code that the scanner must flag as a violation.
  ALLOW  — code that is fully legitimate and must NOT produce false positives
            (e.g. normal stdlib imports, internal Echosync imports).

The scanner operates entirely on source strings parsed with ast.parse(), so no
real files or imports are required — every test is pure unit-level.
"""

import ast
import textwrap

import pytest

from core.plugin_loader import PluginSecurityScanner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scan(source: str) -> list:
    """Parse *source* and return the list of (lineno, description) violations."""
    source = textwrap.dedent(source)
    tree = ast.parse(source)
    scanner = PluginSecurityScanner()
    scanner.visit(tree)
    return scanner.violations


def _has_violation(violations: list, fragment: str) -> bool:
    """Return True if any violation description contains *fragment*."""
    return any(fragment in desc for _, desc in violations)


# ===========================================================================
# BLOCK: imports that must raise violations
# ===========================================================================

class TestForbiddenImports:
    """Bare `import X` statements that must be caught."""

    def test_blocks_import_os(self):
        violations = _scan("import os")
        assert violations, "Expected a violation for 'import os'"
        assert _has_violation(violations, "os")

    def test_blocks_import_subprocess(self):
        violations = _scan("import subprocess")
        assert violations, "Expected a violation for 'import subprocess'"
        assert _has_violation(violations, "subprocess")

    def test_blocks_import_sqlite3(self):
        violations = _scan("import sqlite3")
        assert violations, "Expected a violation for 'import sqlite3'"
        assert _has_violation(violations, "sqlite3")

    def test_blocks_import_sys(self):
        violations = _scan("import sys")
        assert violations, "Expected a violation for 'import sys'"
        assert _has_violation(violations, "sys")

    def test_blocks_import_importlib(self):
        violations = _scan("import importlib")
        assert violations, "Expected a violation for 'import importlib'"
        assert _has_violation(violations, "importlib")

    def test_blocks_import_os_path_submodule(self):
        """'import os.path' must be caught via the .split('.')[0] fix."""
        violations = _scan("import os.path")
        assert violations, "Expected a violation for 'import os.path'"
        assert _has_violation(violations, "os.path")


class TestForbiddenFromImports:
    """from X import Y statements that must be caught."""

    def test_blocks_from_os_path_import_join(self):
        """Previously bypassed the scanner before the submodule fix."""
        violations = _scan("from os.path import join")
        assert violations, "Expected a violation for 'from os.path import join'"
        assert _has_violation(violations, "os.path")

    def test_blocks_from_os_import_remove(self):
        violations = _scan("from os import remove")
        assert violations, "Expected a violation for 'from os import remove'"
        assert _has_violation(violations, "os")

    def test_blocks_from_subprocess_import_run(self):
        violations = _scan("from subprocess import run")
        assert violations, "Expected a violation for 'from subprocess import run'"
        assert _has_violation(violations, "subprocess")

    def test_blocks_from_sys_import_exit(self):
        violations = _scan("from sys import exit")
        assert violations, "Expected a violation for 'from sys import exit'"
        assert _has_violation(violations, "sys")

    def test_blocks_from_importlib_import_import_module(self):
        violations = _scan("from importlib import import_module")
        assert violations, "Expected a violation for 'from importlib import import_module'"
        assert _has_violation(violations, "importlib")

    def test_blocks_from_os_environ_import(self):
        """os.environ submodule path must be caught."""
        violations = _scan("from os.environ import get")
        assert violations, "Expected a violation for 'from os.environ import get'"
        assert _has_violation(violations, "os.environ")


class TestForbiddenCallPatterns:
    """Call expressions that must be caught."""

    def test_blocks_dunder_import_os(self):
        """Previously bypassed the scanner before __import__ was added to _FORBIDDEN_BARE_CALLS."""
        violations = _scan("__import__('os').remove('/file')")
        assert violations, "Expected a violation for __import__('os')"
        assert _has_violation(violations, "__import__")

    def test_blocks_dunder_import_subprocess(self):
        violations = _scan("__import__('subprocess').run(['rm', '-rf', '/'])")
        assert violations, "Expected a violation for __import__('subprocess')"
        assert _has_violation(violations, "__import__")

    def test_blocks_importlib_import_module(self):
        source = """\
            import importlib
            importlib.import_module('os')
        """
        violations = _scan(source)
        # At minimum the bare 'import importlib' triggers a violation.
        assert violations

    def test_blocks_open_bare_call(self):
        violations = _scan("open('/etc/passwd', 'r')")
        assert violations, "Expected a violation for bare open()"
        assert _has_violation(violations, "open")

    def test_blocks_os_remove(self):
        violations = _scan("os.remove('/critical/file')")
        assert violations, "Expected a violation for os.remove()"
        assert _has_violation(violations, "os.remove")

    def test_blocks_shutil_rmtree(self):
        violations = _scan("shutil.rmtree('/data')")
        assert violations, "Expected a violation for shutil.rmtree()"
        assert _has_violation(violations, "rmtree")

    def test_blocks_pathlib_unlink(self):
        violations = _scan("some_path.unlink()")
        assert violations, "Expected a violation for .unlink()"
        assert _has_violation(violations, "unlink")

    def test_blocks_pathlib_write_text(self):
        violations = _scan("some_path.write_text('malicious')")
        assert violations, "Expected a violation for .write_text()"
        assert _has_violation(violations, "write_text")


# ===========================================================================
# ALLOW: imports and code that must NOT produce false positives
# ===========================================================================

class TestAllowedImports:
    """Legitimate imports that the scanner must never flag."""

    def test_allows_import_re(self):
        assert _scan("import re") == []

    def test_allows_import_json(self):
        assert _scan("import json") == []

    def test_allows_import_typing(self):
        assert _scan("from typing import List, Optional, Dict") == []

    def test_allows_import_dataclasses(self):
        assert _scan("from dataclasses import dataclass, field") == []

    def test_allows_import_pathlib(self):
        # Importing pathlib itself is fine; only the .unlink()/.write_text() calls are blocked.
        assert _scan("from pathlib import Path") == []

    def test_allows_import_logging(self):
        assert _scan("import logging") == []

    def test_allows_import_datetime(self):
        assert _scan("from datetime import datetime, timezone") == []

    def test_allows_import_enum(self):
        assert _scan("from enum import Enum") == []

    def test_allows_import_abc(self):
        assert _scan("from abc import ABC, abstractmethod") == []


class TestAllowedInternalEchosyncImports:
    """Echosync-internal from-import patterns that must never be flagged."""

    def test_allows_from_core_hook_manager(self):
        assert _scan("from core.hook_manager import hook_manager") == []

    def test_allows_from_core_provider_base(self):
        assert _scan("from core.provider_base import ProviderBase") == []

    def test_allows_from_core_enums(self):
        assert _scan("from core.enums import Capability") == []

    def test_allows_from_core_tiered_logger(self):
        assert _scan("from core.tiered_logger import get_logger") == []

    def test_allows_from_core_settings(self):
        assert _scan("from core.settings import config_manager") == []

    def test_allows_from_core_matching_engine(self):
        assert _scan(
            "from core.matching_engine.echo_sync_track import EchosyncTrack"
        ) == []

    def test_allows_multi_line_internal_plugin_skeleton(self):
        """
        Simulates a realistic, well-formed community plugin: multiple internal
        imports, a hook function, and an init block — all must be violation-free.
        """
        source = """\
            from typing import List, Any
            import re
            from core.hook_manager import hook_manager
            from core.tiered_logger import get_logger

            logger = get_logger("plugin.example")

            def _on_pre_provider_search(query: str) -> Any:
                if not isinstance(query, str):
                    return query
                return query.strip().lower()

            def initialize_plugin():
                hook_manager.add_filter('pre_provider_search', _on_pre_provider_search)

            initialize_plugin()
        """
        assert _scan(source) == [], "Legitimate plugin skeleton must not produce violations"


class TestScannerIsolation:
    """Edge cases and boundary conditions."""

    def test_empty_source_produces_no_violations(self):
        assert _scan("") == []

    def test_comment_only_source_produces_no_violations(self):
        assert _scan("# import os  — this is just a comment") == []

    def test_string_literal_os_produces_no_violations(self):
        """A string containing 'os' must never be flagged — only AST nodes matter."""
        assert _scan('x = "import os"') == []
        assert _scan("x = 'from os import path'") == []

    def test_multiple_violations_all_reported(self):
        """Scanner must keep walking after the first hit — all violations reported."""
        source = """\
            import os
            import subprocess
            open('/etc/passwd')
        """
        violations = _scan(source)
        assert len(violations) >= 3, (
            f"Expected at least 3 violations, got {len(violations)}: {violations}"
        )

    def test_from_import_with_none_module_does_not_crash(self):
        """
        Relative imports (`from . import x`) produce node.module == None.
        The scanner must not raise AttributeError on those nodes.
        """
        source = "from . import utils"
        # Should not raise; violations list may be empty or flagged depending on
        # policy, but it must not crash.
        try:
            result = _scan(source)
            # Relative imports are not explicitly blocked, so we expect no violation.
            assert isinstance(result, list)
        except AttributeError as exc:
            pytest.fail(f"Scanner raised AttributeError on relative import: {exc}")
