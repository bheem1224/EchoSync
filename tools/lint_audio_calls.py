"""
tools/lint_audio_calls.py — AST-based linter for rogue tag-reader imports.

Scans core/, plugins/, and services/ for any file that imports mutagen,
tinytag, or taglib directly, EXCEPT the blessed whitelisted modules that
are the legitimate owners of those dependencies.

Usage
-----
    python tools/lint_audio_calls.py            # scan all dirs
    python tools/lint_audio_calls.py --fix      # print refactor hints
    python tools/lint_audio_calls.py --strict   # exit code 1 if violations

Exit codes
----------
    0  No violations found.
    1  One or more violations found (only when --strict is set, or always
       in CI mode set via ECHOSYNC_CI=1 env variable).
"""

from __future__ import annotations

import ast
import os
import sys
import argparse
from pathlib import Path
from typing import List, NamedTuple


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

# Directories to scan (relative to the project root)
SCAN_DIRS: List[str] = ["core", "plugins", "services", "web"]

# Rogue libraries that must NOT be imported directly outside the whitelist
ROGUE_LIBS: frozenset[str] = frozenset({"mutagen", "tinytag", "taglib"})

# Files that are ALLOWED to import these libraries directly.
# Paths are relative to the project root (forward-slash notation).
WHITELIST: frozenset[str] = frozenset({
    "core/file_handling/tagging_io.py",       # owns mutagen for tag reads
    "core/file_handling/post_processor.py",   # owns mutagen for tag writes
    "core/matching_engine/fingerprinting.py", # needs mutagen for channel probing
    "core/file_handling/audio_inspector.py",  # new central inspector (read-only delegation)
    "web/routes/metadata.py",                 # cover-art binary extraction only (not tag reads)
})


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

class Violation(NamedTuple):
    file: str          # Relative path from project root
    line: int
    col: int
    statement: str     # The offending import statement text
    library: str       # Which rogue library


# ─────────────────────────────────────────────────────────────────────────────
# AST walker
# ─────────────────────────────────────────────────────────────────────────────

def _find_rogue_imports(source: str, rel_path: str) -> List[Violation]:
    """Parse *source* with AST and return all rogue import statements."""
    violations: List[Violation] = []

    try:
        tree = ast.parse(source, filename=rel_path)
    except SyntaxError as e:
        print(f"  [WARN] Could not parse {rel_path}: {e}", file=sys.stderr)
        return violations

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in ROGUE_LIBS:
                    stmt = f"import {alias.name}"
                    if alias.asname:
                        stmt += f" as {alias.asname}"
                    violations.append(
                        Violation(rel_path, node.lineno, node.col_offset, stmt, top)
                    )

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in ROGUE_LIBS:
                    names = ", ".join(
                        (f"{a.name} as {a.asname}" if a.asname else a.name)
                        for a in node.names
                    )
                    stmt = f"from {node.module} import {names}"
                    violations.append(
                        Violation(rel_path, node.lineno, node.col_offset, stmt, top)
                    )

    return violations


# ─────────────────────────────────────────────────────────────────────────────
# Scanner
# ─────────────────────────────────────────────────────────────────────────────

def scan(project_root: Path) -> List[Violation]:
    """Walk SCAN_DIRS and collect all violations."""
    all_violations: List[Violation] = []

    for scan_dir in SCAN_DIRS:
        target = project_root / scan_dir
        if not target.exists():
            continue

        for py_file in sorted(target.rglob("*.py")):
            # Compute relative path with forward slashes for cross-platform matching
            rel = py_file.relative_to(project_root).as_posix()

            if rel in WHITELIST:
                continue  # allowed

            try:
                source = py_file.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                print(f"  [WARN] Cannot read {rel}: {e}", file=sys.stderr)
                continue

            violations = _find_rogue_imports(source, rel)
            all_violations.extend(violations)

    return all_violations


# ─────────────────────────────────────────────────────────────────────────────
# Reporter
# ─────────────────────────────────────────────────────────────────────────────

_REFACTOR_HINT = """\
  Suggested fix  ->  Replace the direct {lib!r} import with:

      from core.file_handling.audio_inspector import inspect_audio_file

  Then replace any mutagen.File(...) / read-tag calls with:

      result = inspect_audio_file(Path(file_path))
      # result.title, result.artist, result.duration_ms, result.to_dict(), ...

  For cover-art / write operations (post_processor, metadata route):
      Continue using tagging_io.read_tags() or the cover-art helpers in
      tagging_io -- those are whitelisted write/cover-art paths.
"""


def report(violations: List[Violation], fix_hints: bool = False) -> None:
    if not violations:
        print(f"\n[OK]  No rogue tag-reader imports found. Codebase is clean.\n")
        return

    print(f"\n[FAIL]  Found {len(violations)} rogue import(s):\n")
    prev_file = None
    for v in violations:
        if v.file != prev_file:
            print(f"  [file]  {v.file}")
            prev_file = v.file
        print(f"      Line {v.line:>4}: {v.statement}")

    if fix_hints:
        seen_libs: set[str] = set()
        for v in violations:
            if v.library not in seen_libs:
                seen_libs.add(v.library)
                print(_REFACTOR_HINT.format(lib=v.library))

    print()


# ─────────────────────────────────────────────────────────────────────────────
# Entry-point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="AST linter: flag rogue mutagen/tinytag/taglib imports."
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit with code 1 if any violations are found."
    )
    parser.add_argument(
        "--fix", action="store_true",
        help="Print refactor hints alongside violations."
    )
    parser.add_argument(
        "--root", default=None,
        help="Project root directory (default: parent of this script's directory)."
    )
    args = parser.parse_args()

    # Resolve project root
    if args.root:
        root = Path(args.root).resolve()
    else:
        # tools/ lives one level below the project root
        root = Path(__file__).resolve().parent.parent

    print(f"[SCAN]  Scanning project at: {root}")
    print(f"    Dirs : {', '.join(SCAN_DIRS)}")
    print(f"    Libs : {', '.join(sorted(ROGUE_LIBS))}")
    print(f"    Whitelist ({len(WHITELIST)} file(s)):")
    for w in sorted(WHITELIST):
        print(f"      - {w}")

    violations = scan(root)
    report(violations, fix_hints=args.fix)

    ci_mode = os.environ.get("ECHOSYNC_CI") == "1"
    if violations and (args.strict or ci_mode):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
