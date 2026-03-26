"""
core/file_handling/local_io.py — Facade (v2.2.0+)

LocalFileHandler is now a thin facade over the three single-responsibility
modules introduced in v2.2.0:

  • jail.py       — SecurityError, FileJail, LockManager singletons
  • base_io.py    — safe_move, safe_delete
  • tagging_io.py — read_tags, write_tags (full Mutagen stack)

All consumers should obtain the singleton via LocalFileHandler.get_instance().
Direct use of the underlying modules is also acceptable for new code.
"""

import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from core.tiered_logger import get_logger
from .jail import SecurityError, file_jail, lock_manager  # noqa: F401
from .base_io import safe_move, safe_delete, resolve_path  # noqa: F401
from .tagging_io import read_tags as _read_tags, write_tags as _write_tags

logger = get_logger("core.file_handling.local_io")


# SecurityError is re-exported from jail.py above.


# ─────────────────────────────────────────────────────────────────────────────
class LocalFileHandler:
    """
    Singleton secure gateway for all physical file-system operations.

    Every public method:
      1. Translates remote/container paths via configured path mappings
         (logic absorbed from core/path_mapper.py).
      2. Resolves the final absolute path and confirms it falls within an
         allowed root (Path Jail).  Path-traversal via '../' is neutralised
         by Path.resolve() before the jail check is applied.
      3. Acquires a per-file threading.Lock before touching the file system
         to prevent concurrent read/write races.
    """

    _instance: Optional["LocalFileHandler"] = None
    _instance_lock: threading.Lock = threading.Lock()

    # ── Singleton ─────────────────────────────────────────────────────────
    @classmethod
    def get_instance(cls) -> "LocalFileHandler":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = LocalFileHandler()
        return cls._instance

    def __init__(self) -> None:
        # Lock state is now owned by the shared jail.lock_manager singleton;
        # the dicts below are kept only for backward-compatibility inspection.
        pass

    # ── Path translation (PathMapper logic absorbed) ───────────────────────
    def _map_to_local(self, path: Union[str, Path]) -> Path:
        """Delegate to base_io.  Kept for backward compatibility."""
        from .base_io import _map_to_local as _impl
        return _impl(path)

    def _resolve_path(self, path: Union[str, Path]) -> Path:
        """Delegate to base_io.resolve_path."""
        return resolve_path(path)

    # ── Security — Path Jail ───────────────────────────────────────────────
    def _allowed_roots(self) -> List[Path]:
        return file_jail.allowed_roots()

    def _validate_safe_path(self, resolved: Path) -> None:
        """Delegate to the shared FileJail singleton."""
        file_jail.validate(resolved)

    # ── Lock Manager ──────────────────────────────────────────────────────
    def _get_lock(self, resolved: Path) -> threading.Lock:
        """Delegate to the shared LockManager singleton."""
        return lock_manager.lock_for(resolved)

    # ── Public gateway methods ─────────────────────────────────────────────
    def read_tags(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Delegate to tagging_io.read_tags (jail + lock included)."""
        return _read_tags(path)

    def write_tags(self, path: Union[str, Path], metadata: Dict[str, Any]) -> None:
        """Delegate to tagging_io.write_tags (jail + lock included)."""
        _write_tags(path, metadata)

    def safe_move(self, src: Union[str, Path], dest: Union[str, Path]) -> Path:
        """Delegate to base_io.safe_move (jail + lock included)."""
        return safe_move(src, dest)

    def safe_delete(self, path: Union[str, Path]) -> None:
        """Delegate to base_io.safe_delete (jail + lock included)."""
        safe_delete(path)

