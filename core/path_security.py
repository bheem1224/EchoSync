"""
Path Security and Jail Sanitizer Utility.

Centralizes path normalization, traversal checks, and Zip Slip prevention.
Provides a CodeQL-recognized path sanitization node for all file and directory operations.
"""

import os
from pathlib import Path
from typing import Union


class PathTraversalError(ValueError):
    """Raised when a user-controlled path attempts to escape its allowed base directory."""
    pass


def resolve_safe_path(base_dir: Union[str, Path], user_input: Union[str, Path]) -> Path:
    """
    Resolve and validate a user-supplied path strictly within a base directory.

    Args:
        base_dir: Configured root directory (allowed sandbox).
        user_input: Relative or absolute path provided by untrusted input/ZIP entry.

    Returns:
        Path: Absolute, resolved Path guaranteed to be inside base_dir.

    Raises:
        PathTraversalError: If the resolved path escapes base_dir.
    """
    if not base_dir:
        raise ValueError("base_dir must be specified")

    # 1. Convert base_dir to an absolute resolved Path
    base_path = Path(base_dir).resolve()

    # 2. Sanitize user input string/path (strip absolute root markers if passed as string)
    input_str = str(user_input).strip()
    
    # Neutralize leading slashes/drive letters to prevent Path('/') ignoring base_path
    if os.path.isabs(input_str) or input_str.startswith('/') or input_str.startswith('\\'):
        input_str = input_str.lstrip('/\\')
        # On Windows, strip drive letters like C:
        if len(input_str) >= 2 and input_str[1] == ':':
            input_str = input_str[2:].lstrip('/\\')

    # 3. Combine and resolve the target path
    target_path = (base_path / input_str).resolve()

    # 4. Enforce strict containment check
    try:
        # Python 3.9+ containment check
        is_safe = target_path.is_relative_to(base_path)
    except AttributeError:
        # Fallback for Python < 3.9 using commonpath
        try:
            is_safe = os.path.commonpath([str(target_path), str(base_path)]) == str(base_path)
        except ValueError:
            is_safe = False

    if not is_safe:
        raise PathTraversalError(
            f"Security Violation: Path traversal attempt detected. "
            f"Input '{user_input}' escapes root directory '{base_path}'"
        )

    return target_path


def validate_zip_entry(base_dir: Union[str, Path], zip_filename: str) -> Path:
    """
    Validate a ZipArchive entry filename against Zip Slip path traversal attacks.

    Args:
        base_dir: Target extraction directory.
        zip_filename: Entry filename inside the zip archive.

    Returns:
        Path: Validated extraction path.

    Raises:
        PathTraversalError: If the entry attempts Zip Slip traversal.
    """
    # Reject explicit double-dot path elements up front
    normalized = zip_filename.replace('\\', '/')
    parts = normalized.split('/')
    if '..' in parts:
        raise PathTraversalError(
            f"Security Violation: Zip Slip attack blocked for entry '{zip_filename}'"
        )

    return resolve_safe_path(base_dir, zip_filename)
