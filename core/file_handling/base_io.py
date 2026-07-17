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
    """
    resolved_src = resolve_path(src)
    resolved_dest = _map_to_local(dest).resolve()   # dest may not exist yet

    try:
        from core.hook_manager import hook_manager
        plugin_dest = hook_manager.apply_filters('BEFORE_FILE_RENAME', str(resolved_dest), src_path=str(resolved_src))
        if plugin_dest and plugin_dest != str(resolved_dest):
            resolved_dest = Path(plugin_dest).resolve()
            logger.info(f"Plugin altered destination path to: {resolved_dest}")
    except Exception as e:
        logger.error(f"Error in BEFORE_FILE_RENAME hook: {e}")

    file_jail.validate(resolved_src)
    file_jail.validate(resolved_dest)

    # Acquire locks in deterministic order to prevent ABBA deadlock
    pair = sorted([resolved_src, resolved_dest], key=str)
    lock_a = lock_manager.lock_for(pair[0])
    lock_b = lock_manager.lock_for(pair[1])
    with lock_a:
        with lock_b:
            try:
                from core.hook_manager import hook_manager
                plugin_io = hook_manager.apply_filters('CUSTOM_FILE_IO', None, src_path=str(resolved_src), dest_path=str(resolved_dest))
                if plugin_io == "SKIP":
                    logger.info(f"Plugin intercepted CUSTOM_FILE_IO for {resolved_dest}, skipping local move")
                    return resolved_dest
            except Exception as e:
                logger.error(f"Error in CUSTOM_FILE_IO hook: {e}")

            resolved_dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(resolved_src), str(resolved_dest))
            except Exception as e:
                # If shutil.move fails mid-copy (e.g. out of space across partitions), clean up corrupted destination
                resolved_dest.unlink(missing_ok=True)
                raise
            logger.debug("safe_move: %s → %s", resolved_src, resolved_dest)
            return resolved_dest


def safe_delete(path: Union[str, Path]) -> None:
    """
    Securely delete the file at *path*. (Soft Delete enforced)

    - Instead of unlink/rmtree, moves file to .trash/ at the library root.
    - Path is jail-checked.
    - File lock is held during deletion.

    Raises:
        SecurityError: If the path escapes its allowed root.
    """
    from core.settings import config_manager
    resolved = resolve_path(path)
    file_jail.validate(resolved)

    with lock_manager.lock_for(resolved):
        if resolved.exists():
            try:
                # Resolve the user's library mount
                library_dir = config_manager.get('storage', {}).get('library_dir')
                if not library_dir:
                    logger.warning("No library_dir configured. Soft delete defaulting to current directory .trash")
                    library_dir = "."

                trash_dir = Path(library_dir) / ".trash"
                trash_dir.mkdir(parents=True, exist_ok=True)

                # Move to trash instead of permanent deletion
                dest = trash_dir / resolved.name
                # Ensure unique name in trash
                counter = 1
                while dest.exists():
                    dest = trash_dir / f"{resolved.stem}_{counter}{resolved.suffix}"
                    counter += 1

                shutil.move(str(resolved), str(dest))
                logger.debug("safe_delete (Soft Delete): %s -> %s", resolved, dest)
            except Exception as e:
                logger.error(f"Soft delete failed for {resolved}: {e}")
        else:
            logger.warning("safe_delete: file not found, skipping: %s", resolved)


def safe_write_text(path: Union[str, Path], content: str, encoding: str = 'utf-8') -> None:
    """
    Securely write text content to a file at *path*.

    - Path is jail-checked.
    - File lock is held during writing.
    - Parent directories are created if missing.

    Raises:
        SecurityError: If the path escapes its allowed root.
    """
    resolved = _map_to_local(path).resolve()
    file_jail.validate(resolved)
    
    with lock_manager.lock_for(resolved):
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding=encoding)
        logger.debug("safe_write_text: %s (%d chars)", resolved, len(content))


def check_file_exists(path: Union[str, Path]) -> bool:
    """
    Check if a file exists and is a file under the jail directory.
    - Resolves path mappings
    - Checks jail constraints
    """
    try:
        resolved = resolve_path(path)
        file_jail.validate(resolved)
        return resolved.exists() and resolved.is_file()
    except Exception as e:
        logger.warning(f"check_file_exists validation failed or file not found for {path}: {e}")
        return False
