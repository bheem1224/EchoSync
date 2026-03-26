"""
core/file_handling/jail.py — Path Jail + Lock Manager

Central single-responsibility module that owns:
  • SecurityError           — raised on any path-traversal attempt
  • FileJail.validate()     — confirms a resolved Path is inside an allowed root
  • LockManager.lock_for()  — returns a per-file threading.Lock (globally shared)

Both are exposed as module-level singletons so the same lock registry is shared
across jail, base_io, and tagging_io regardless of import order.
"""

import threading
from pathlib import Path
from typing import Dict, List, Union

from core.tiered_logger import get_logger

logger = get_logger("core.file_handling.jail")


# ─────────────────────────────────────────────────────────────────────────────
class SecurityError(Exception):
    """Raised when a path escapes its designated root (path-traversal blocked)."""


# ─────────────────────────────────────────────────────────────────────────────
class FileJail:
    """
    Validates that a fully-resolved Path falls within one of the configured
    allowed roots (downloads dir *or* library dir).

    All path-traversal neutralisation is handled upstream by Path.resolve()
    before validate() is called; is_relative_to() is therefore a safe check.
    """

    def allowed_roots(self) -> List[Path]:
        from core.settings import config_manager
        return [
            config_manager.get_download_dir().resolve(),
            config_manager.get_library_dir().resolve(),
        ]

    def validate(self, resolved: Path) -> None:
        """
        Raise SecurityError if *resolved* does not fall within any allowed root.

        Args:
            resolved: An already-resolved (absolute, normalised) Path.

        Raises:
            SecurityError: If the path escapes all allowed roots.
        """
        for root in self.allowed_roots():
            if resolved == root or resolved.is_relative_to(root):
                return
        roots_str = ", ".join(str(r) for r in self.allowed_roots())
        raise SecurityError(
            f"Path '{resolved}' is outside all allowed roots ({roots_str}). "
            "Possible path-traversal attempt blocked."
        )


class LockManager:
    """
    Maintains a global dictionary of per-file threading.Locks.

    The same LockManager instance must be shared by *all* I/O modules so that
    a lock acquired in base_io is visible to tagging_io operating on the same
    file.  Use the module-level singleton ``lock_manager`` for this purpose.
    """

    def __init__(self) -> None:
        self._locks: Dict[str, threading.Lock] = {}
        self._mutex = threading.Lock()

    def lock_for(self, resolved: Path) -> threading.Lock:
        """Return (creating if absent) the Lock for the given resolved path."""
        key = str(resolved)
        with self._mutex:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]


# ── Module-level singletons ───────────────────────────────────────────────────
file_jail = FileJail()
lock_manager = LockManager()
