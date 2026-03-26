"""
core/file_handling/base_io.py — Safe file-system operations

Implements safe_move and safe_delete.  Both operations:
  1. Resolve and jail-check their paths via the shared FileJail.
  2. Acquire per-file locks from the shared LockManager before touching disk.

Import the module-level convenience functions rather than instantiating
BaseIO directly:

    from core.file_handling.base_io import safe_move, safe_delete
"""

import shutil
from pathlib import Path
from typing import Union

from core.tiered_logger import get_logger
from .jail import file_jail, lock_manager, SecurityError  # noqa: F401 re-export

logger = get_logger("core.file_handling.base_io")


def _map_to_local(path: Union[str, Path]) -> Path:
    """
    Apply configured path mappings (remote → local / container → host).
    Shared helper used by base_io and tagging_io to avoid duplicating the
    PathMapper logic.
    """
    from core.settings import config_manager

    path_str = str(path).replace("\\", "/")
    mappings = config_manager.get("path_mappings", []) or []
    if isinstance(mappings, dict):
        mappings = [m for m in mappings.values() if isinstance(m, dict)]

    for mapping in mappings:
        if not isinstance(mapping, dict):
            continue
        remote = (mapping.get("remote") or "").replace("\\", "/").rstrip("/")
        local = (mapping.get("local") or "").replace("\\", "/")
        if not remote:
            continue
        if path_str == remote or path_str.startswith(remote + "/"):
            suffix = path_str[len(remote):]
            if local.endswith("/") and suffix.startswith("/"):
                result = local + suffix[1:]
            elif not local.endswith("/") and not suffix.startswith("/") and suffix:
                result = local + "/" + suffix
            else:
                result = local + suffix
            return Path(result)

    return Path(path_str)


def resolve_path(path: Union[str, Path]) -> Path:
    """Translate via mappings then resolve to an absolute, normalised path."""
    return _map_to_local(path).resolve()


# ─────────────────────────────────────────────────────────────────────────────

def safe_move(src: Union[str, Path], dest: Union[str, Path]) -> Path:
    """
    Securely move a file from *src* to *dest*.

    - Both paths are jail-checked.
    - Locks are acquired in lexicographic order to prevent deadlock when two
      threads move files in opposite directions.
    - Parent directories of *dest* are created automatically.
    - Returns the resolved destination path.

    Raises:
        SecurityError: If either path escapes its allowed root.
    """
    resolved_src = resolve_path(src)
    resolved_dest = _map_to_local(dest).resolve()   # dest may not exist yet
    file_jail.validate(resolved_src)
    file_jail.validate(resolved_dest)

    # Acquire locks in deterministic order to prevent ABBA deadlock
    pair = sorted([resolved_src, resolved_dest], key=str)
    lock_a = lock_manager.lock_for(pair[0])
    lock_b = lock_manager.lock_for(pair[1])
    with lock_a:
        with lock_b:
            resolved_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(resolved_src), str(resolved_dest))
            logger.debug("safe_move: %s → %s", resolved_src, resolved_dest)
            return resolved_dest


def safe_delete(path: Union[str, Path]) -> None:
    """
    Securely delete the file at *path*.

    - Path is jail-checked.
    - File lock is held during deletion.
    - A missing file is logged as a warning rather than raised.

    Raises:
        SecurityError: If the path escapes its allowed root.
    """
    resolved = resolve_path(path)
    file_jail.validate(resolved)
    with lock_manager.lock_for(resolved):
        if resolved.exists():
            resolved.unlink()
            logger.debug("safe_delete: %s", resolved)
        else:
            logger.warning("safe_delete: file not found, skipping: %s", resolved)
