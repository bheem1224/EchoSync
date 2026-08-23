"""
Utilities package for EchoSync.
"""
import os
import re
from typing import List, Dict, Union, Optional
import logging

from core.path_security import resolve_safe_path, validate_zip_entry, PathTraversalError
from core.utils.file_utils import (
    prune_empty_parent_directories,
    prune_empty_directories_tree,
    _IGNORE_FILES,
)

logger = logging.getLogger("utils")


class PathMapper:
    """
    Utility to map remote paths (e.g., from Docker containers) to local paths.
    """
    def __init__(self, mappings: Union[List[Dict[str, str]], Dict[str, Dict[str, str]]]):
        if isinstance(mappings, dict):
            self.mappings = [m for m in mappings.values() if isinstance(m, dict)]
        else:
            self.mappings = mappings or []

    def _normalize(self, path: str) -> str:
        if not path:
            return ""
        return path.replace('\\', '/')

    @classmethod
    def to_local(cls, remote_path: str) -> str:
        from core.settings import config_manager
        mappings = config_manager.get('path_mappings', [])
        return cls(mappings).map_to_local(remote_path)

    def map_to_local(self, remote_path: str) -> str:
        if not remote_path:
            return ""

        try:
            from core.hook_manager import hook_manager
            plugin_path = hook_manager.apply_filters('RESOLVE_STORAGE_PATH', None, remote_path=remote_path)
            if plugin_path and isinstance(plugin_path, str):
                return plugin_path
        except Exception as e:
            logger.error(f"Error in RESOLVE_STORAGE_PATH hook: {e}")

        normalized_remote = self._normalize(remote_path)

        for mapping in self.mappings:
            if not isinstance(mapping, dict):
                continue

            remote_prefix = self._normalize(mapping.get('remote', ''))
            local_prefix = self._normalize(mapping.get('local', ''))

            if not remote_prefix:
                continue

            search_prefix = remote_prefix.rstrip('/') if len(remote_prefix) > 1 else remote_prefix

            is_match = False
            if search_prefix == '/':
                is_match = True
            elif normalized_remote == search_prefix or normalized_remote.startswith(search_prefix + '/'):
                is_match = True

            if is_match:
                suffix = normalized_remote[len(search_prefix):].lstrip('/')
                if not suffix:
                    return local_prefix.rstrip('/') if local_prefix != '/' else '/'
                return os.path.join(local_prefix, suffix).replace('\\', '/')

        return normalized_remote


def docker_resolve_path(path_str: str) -> str:
    """
    Resolve absolute paths for Docker container access.
    In Docker, Windows drive paths (E:/) need to be mapped to WSL mount points (/mnt/e/).
    """
    if os.path.exists('/.dockerenv') and len(path_str) >= 3 and path_str[1] == ':' and path_str[0].isalpha():
        drive_letter = path_str[0].lower()
        rest_of_path = path_str[2:].replace('\\', '/')
        return f"/host/mnt/{drive_letter}{rest_of_path}"
    return path_str


def extract_filename(full_path: str) -> str:
    """
    Extract filename by working backwards from the end until we hit a separator.
    Handles both Windows and Unix path separators.
    """
    if not full_path:
        return ""
    last_slash = max(full_path.rfind('/'), full_path.rfind('\\'))
    if last_slash != -1:
        return full_path[last_slash + 1:]
    else:
        return full_path


def extract_primary_artist(artist_string: str) -> str:
    """
    Extract the primary artist from a collaboration string.
    e.g., "ATEEZ feat. LA POEM" -> "ATEEZ"
    """
    if not artist_string:
        return ""

    delimiters = [
        r'\bfeat\.', r'\bft\.', r'\bfeaturing\b',
        r'\bwith\b', r'\bx\b', r'&', r','
    ]
    pattern = re.compile('|'.join(delimiters), re.IGNORECASE)
    match = pattern.search(artist_string)
    if match:
        return artist_string[:match.start()].strip()
    return artist_string.strip()


__all__ = [
    "PathMapper",
    "docker_resolve_path",
    "extract_filename",
    "extract_primary_artist",
    "resolve_safe_path",
    "validate_zip_entry",
    "PathTraversalError",
    "prune_empty_parent_directories",
    "prune_empty_directories_tree",
]
