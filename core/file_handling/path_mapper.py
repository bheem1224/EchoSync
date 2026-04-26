import os
from typing import List, Dict, Union

class PathMapper:
    """
    Utility to map remote paths (e.g., from Docker containers) to local paths.
    """
    def __init__(self, mappings: Union[List[Dict[str, str]], Dict[str, Dict[str, str]]]):
        """
        Initialize with a list of path mappings.

        Args:
            mappings: List of dicts, e.g., [{"remote": "/data/media", "local": "/mnt/user/media"}]
                      OR Dict of dicts (keys ignored), e.g., {"1": {"remote": "...", "local": "..."}}
        """
        if isinstance(mappings, dict):
            # If mappings is a dict (e.g. from config file where keys are IDs), extract values
            # Ensure values are dicts before adding
            self.mappings = [m for m in mappings.values() if isinstance(m, dict)]
        else:
            self.mappings = mappings or []

    def _normalize(self, path: str) -> str:
        """
        Normalize path separators to forward slashes.
        """
        if not path:
            return ""
        return path.replace('\\', '/')

    @classmethod
    def to_local(cls, remote_path: str) -> str:
        """
        Convenience method to map a remote path to a local path using current config.
        """
        from core.settings import config_manager
        mappings = config_manager.get('path_mappings', [])
        return cls(mappings).map_to_local(remote_path)

    def map_to_local(self, remote_path: str) -> str:
        """
        Map a remote path to a local path based on configured mappings.
        """
        if not remote_path:
            return ""

        try:
            from core.hook_manager import hook_manager
            plugin_path = hook_manager.apply_filters('RESOLVE_STORAGE_PATH', None, remote_path=remote_path)
            if plugin_path and isinstance(plugin_path, str):
                return plugin_path
        except Exception as e:
            import logging
            logging.getLogger("path_mapper").error(f"Error in RESOLVE_STORAGE_PATH hook: {e}")

        normalized_remote = self._normalize(remote_path)

        # OPTIMIZATION: Use os.path or pathlib for filesystem operations
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
                # OPTIMIZATION: Use standard lib path joining instead of slow string concatenation
                suffix = normalized_remote[len(search_prefix):].lstrip('/')
                if not suffix:
                    # if suffix is empty, just return the local prefix without appending a trailing slash
                    # unless the local_prefix inherently had one we want to keep
                    return local_prefix.rstrip('/') if local_prefix != '/' else '/'
                return os.path.join(local_prefix, suffix).replace('\\', '/')

        return normalized_remote


def docker_resolve_path(path_str):
    """
    Resolve absolute paths for Docker container access
    In Docker, Windows drive paths (E:/) need to be mapped to WSL mount points (/mnt/e/)
    """
    import os
    if os.path.exists('/.dockerenv') and len(path_str) >= 3 and path_str[1] == ':' and path_str[0].isalpha():
        # Convert Windows path (E:/path) to WSL mount path (/mnt/e/path)
        drive_letter = path_str[0].lower()
        rest_of_path = path_str[2:].replace('\\', '/')  # Remove E: and convert backslashes
        return f"/host/mnt/{drive_letter}{rest_of_path}"
    return path_str


def extract_filename(full_path):
    """
    Extract filename by working backwards from the end until we hit a separator.
    This is cross-platform compatible and handles both Windows and Unix path separators.
    """
    if not full_path:
        return ""
    last_slash = max(full_path.rfind('/'), full_path.rfind('\\'))
    if last_slash != -1:
        return full_path[last_slash + 1:]
    else:
        return full_path
