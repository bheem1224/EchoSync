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
