"""
Centralized File System Operations — v2.2.0+

Module layout
-------------
  jail.py       — SecurityError, FileJail, LockManager (shared singletons)
  base_io.py    — safe_move, safe_delete
  tagging_io.py — read_tags, write_tags (full Mutagen stack + RIFF/WAV)
  local_io.py   — LocalFileHandler singleton facade (backward-compat)
"""

from .jail import SecurityError, file_jail, lock_manager
from .base_io import safe_move, safe_delete, resolve_path
from .tagging_io import read_tags, write_tags
from .local_io import LocalFileHandler

__all__ = [
    # Singleton facade (primary consumer API)
    'LocalFileHandler',
    # Fine-grained sub-module API
    'SecurityError',
    'file_jail',
    'lock_manager',
    'safe_move',
    'safe_delete',
    'resolve_path',
    'read_tags',
    'write_tags',
]
