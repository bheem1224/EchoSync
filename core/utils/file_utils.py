"""
File and Directory Utilities for EchoSync.

Provides safe, root-bounded directory pruning and bottom-up cleanup
for library and downloads directory trees.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger("file_utils")

_IGNORE_FILES = {".ds_store", "thumbs.db", ".directory", "desktop.ini"}


def prune_empty_parent_directories(
    start_path: Path | str, stop_at_roots: set[Path] | None = None
) -> int:
    """
    Ascend upwards from start_path (or its parent if start_path is a file)
    and remove empty directories, ignoring and unlinking junk metadata artifacts
    (.DS_Store, Thumbs.db, .directory, desktop.ini).

    Halts immediately if:
    - current directory is in stop_at_roots
    - current directory is the filesystem root (curr == curr.parent)
    - current directory contains valid non-junk files or subdirectories
    - rmdir fails with OSError

    Args:
        start_path: Path to start ascending from (file or directory).
        stop_at_roots: Set of Path objects where deletion must halt.

    Returns:
        Total count of pruned directories.
    """
    path = Path(start_path)
    if path.is_file() or not path.exists():
        curr = path.parent
    else:
        curr = path

    stop_roots = {p.resolve() for p in (stop_at_roots or set()) if p}
    pruned_count = 0

    while curr.exists() and curr.is_dir():
        resolved = curr.resolve()
        if resolved in stop_roots or resolved == resolved.parent:
            break

        try:
            entries = list(curr.iterdir())
            valid_entries = [e for e in entries if e.name.lower() not in _IGNORE_FILES]
            if not valid_entries:
                # Remove ignored junk files first
                for junk in entries:
                    try:
                        junk.unlink()
                    except OSError:
                        pass
                curr.rmdir()
                pruned_count += 1
                logger.debug("Pruned empty directory: %s", curr)
                curr = curr.parent
            else:
                break
        except OSError:
            break

    return pruned_count


def prune_empty_directories_tree(root_path: Path | str) -> int:
    """
    Execute a bottom-up directory traversal across root_path to clean
    orphaned empty directories and junk metadata files (.DS_Store, Thumbs.db, etc.).

    Never removes the root directory itself.

    Args:
        root_path: Root folder path to clean up.

    Returns:
        Total count of pruned directories.
    """
    root = Path(root_path)
    if not root.exists() or not root.is_dir():
        return 0

    resolved_root = root.resolve()
    pruned_count = 0

    for dirpath, dirnames, filenames in os.walk(str(root), topdown=False):
        curr = Path(dirpath)
        resolved_curr = curr.resolve()
        if resolved_curr == resolved_root:
            continue

        try:
            entries = list(curr.iterdir())
            valid_entries = [e for e in entries if e.name.lower() not in _IGNORE_FILES]
            if not valid_entries:
                for junk in entries:
                    try:
                        junk.unlink()
                    except OSError:
                        pass
                curr.rmdir()
                pruned_count += 1
                logger.debug("Pruned empty tree directory: %s", curr)
        except OSError:
            pass

    return pruned_count
