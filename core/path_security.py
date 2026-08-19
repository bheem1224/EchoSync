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


def is_safe_path(target_path: Union[str, Path], allowed_roots: Union[str, Path, list[Union[str, Path]]]) -> bool:
    """
    Check whether target_path resides strictly within one of the allowed_roots.

    Args:
        target_path: Path to validate.
        allowed_roots: One or more allowed root directory sandboxes.

    Returns:
        bool: True if target_path is strictly inside an allowed root, False otherwise.
    """
    try:
        target = Path(target_path).resolve()
    except Exception:
        return False

    if isinstance(allowed_roots, (str, Path)):
        roots = [allowed_roots]
    else:
        roots = list(allowed_roots)

    for root in roots:
        try:
            r = Path(root).resolve()
            try:
                if target.is_relative_to(r):
                    return True
            except AttributeError:
                target_str = str(target)
                root_str = str(r)
                if os.path.commonpath([target_str, root_str]) == root_str:
                    return True
        except Exception:
            continue

    return False


def resolve_safe_path(
    base_dir: Union[str, Path, list[Union[str, Path]]],
    user_input: Union[str, Path]
) -> Path:
    """
    Resolve and validate a user-supplied path strictly within base directory/directories.

    Args:
        base_dir: Configured root directory or list of allowed roots (allowed sandboxes).
        user_input: Relative or absolute path provided by untrusted input/ZIP entry.

    Returns:
        Path: Absolute, resolved Path guaranteed to be inside an allowed base root.

    Raises:
        PathTraversalError: If the resolved path escapes all allowed base directories.
    """
    if not base_dir:
        raise ValueError("base_dir must be specified")

    if isinstance(base_dir, (str, Path)):
        allowed_roots = [Path(base_dir).resolve()]
    else:
        allowed_roots = [Path(r).resolve() for r in base_dir if r]

    if not allowed_roots:
        raise ValueError("At least one valid base_dir must be provided")

    # 1. Sanitize user input string/path
    input_str = str(user_input).strip()
    if "\0" in input_str:
        raise PathTraversalError("Null byte in path")

    # If input is already an absolute path
    input_p = Path(input_str)
    if input_p.is_absolute() or (len(input_str) >= 2 and input_str[1] == ':'):
        target_path = input_p.resolve()
        if not is_safe_path(target_path, allowed_roots):
            raise PathTraversalError(
                f"Security Violation: Path traversal attempt detected. "
                f"Input '{user_input}' escapes allowed root directories."
            )
        return target_path

    # Relative path: check for '..' traversal tokens
    cleaned = os.path.normpath(input_str).lstrip('/\\')
    parts = cleaned.replace('\\', '/').split('/')
    if '..' in parts or any(p == '..' for p in parts):
        raise PathTraversalError(
            f"Security Violation: Path traversal attempt detected. "
            f"Input '{user_input}' escapes root directory."
        )

    # Try resolving relative to first root
    target_path = (allowed_roots[0] / cleaned).resolve()
    if not is_safe_path(target_path, allowed_roots):
        raise PathTraversalError(
            f"Security Violation: Path traversal attempt detected. "
            f"Input '{user_input}' escapes root directory."
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
