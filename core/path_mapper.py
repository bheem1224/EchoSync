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

    def map_to_local(self, remote_path: str) -> str:
        """
        Map a remote path to a local path based on configured mappings.

        Args:
            remote_path: The path received from a remote service (e.g., Plex).

        Returns:
            The mapped local path, or the original path if no mapping matches.
            The returned path is always normalized to use forward slashes.
        """
        if not remote_path:
            return ""

        normalized_remote = self._normalize(remote_path)

        for mapping in self.mappings:
            # Ensure mapping is a dict
            if not isinstance(mapping, dict):
                continue

            remote_prefix = self._normalize(mapping.get('remote', ''))
            local_prefix = self._normalize(mapping.get('local', ''))

            if not remote_prefix:
                continue

            # Remove trailing slash from remote_prefix for consistent matching, unless it's root
            search_prefix = remote_prefix.rstrip('/') if len(remote_prefix) > 1 else remote_prefix

            # Check if the path starts with the remote prefix
            is_match = False
            if search_prefix == '/':
                # Special case for root mapping: matches everything
                is_match = True
            elif normalized_remote == search_prefix or normalized_remote.startswith(search_prefix + '/'):
                is_match = True

            if is_match:
                # Replace the prefix
                # We simply use the length of the matched prefix to slice the path
                suffix = normalized_remote[len(search_prefix):]

                # Ensure local_prefix doesn't have a double slash when joining
                # If local_prefix is /mnt/user/media and suffix is /movie.mkv, result is /mnt/user/media/movie.mkv

                if local_prefix.endswith('/') and suffix.startswith('/'):
                    return local_prefix + suffix[1:]
                elif not local_prefix.endswith('/') and not suffix.startswith('/') and suffix:
                     return local_prefix + '/' + suffix
                else:
                    return local_prefix + suffix

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
