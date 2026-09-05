"""
Path Security and Jail Sanitizer Utility.

Centralizes path normalization, traversal checks, and Zip Slip prevention.
Provides a CodeQL-recognized path sanitization node for all file and directory operations.
"""

import os
from pathlib import Path


class PathTraversalError(ValueError):
    """Raised when a user-controlled path attempts to escape its allowed base directory."""


def is_safe_path(
    target_path: str | Path, allowed_roots: str | Path | list[str | Path]
) -> bool:
    """
    Check whether target_path resides strictly within one of the allowed_roots.

    Args:
        target_path: Path to validate.
        allowed_roots: One or more allowed root directory sandboxes.

    Returns:
        bool: True if target_path is strictly inside an allowed root, False otherwise.
    """
    try:
        target_abs = os.path.abspath(
            os.path.realpath(os.path.normpath(str(target_path)))
        )
    except Exception:
        return False

    if isinstance(allowed_roots, (str, Path)):
        roots = [allowed_roots]
    else:
        roots = list(allowed_roots)

    for root in roots:
        try:
            root_abs = os.path.abspath(os.path.realpath(os.path.normpath(str(root))))
            if os.path.commonpath([target_abs, root_abs]) == root_abs:
                return True
        except (ValueError, Exception):
            continue

    return False


def resolve_safe_path(
    base_dir: str | Path | list[str | Path], user_input: str | Path
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
        raw_roots = [base_dir]
    else:
        raw_roots = list(base_dir)

    allowed_roots = [
        os.path.abspath(os.path.realpath(os.path.normpath(str(r))))
        for r in raw_roots
        if r
    ]
    if not allowed_roots:
        raise ValueError("At least one valid base_dir must be provided")

    # 1. Sanitize user input string/path
    input_str = str(user_input).strip()
    if "\0" in input_str:
        raise PathTraversalError("Null byte in path")

    # Reject explicit double-dot path traversal elements
    parts = input_str.replace("\\", "/").split("/")
    if ".." in parts or any(p == ".." for p in parts):
        raise PathTraversalError(
            f"Security Violation: Path traversal attempt detected. "
            f"Input '{user_input}' escapes root directory."
        )

    # If input is already an absolute path
    if os.path.isabs(input_str) or (len(input_str) >= 2 and input_str[1] == ":"):
        target_abs = os.path.abspath(os.path.realpath(os.path.normpath(input_str)))
    else:
        cleaned = os.path.normpath(input_str).lstrip("/\\")
        target_abs = os.path.abspath(
            os.path.realpath(os.path.normpath(os.path.join(allowed_roots[0], cleaned)))
        )

    if not is_safe_path(target_abs, allowed_roots):
        raise PathTraversalError(
            f"Security Violation: Path traversal attempt detected. "
            f"Input '{user_input}' escapes allowed root directories."
        )

    return Path(target_abs)


def validate_zip_entry(base_dir: str | Path, zip_filename: str) -> Path:
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
    normalized = zip_filename.replace("\\", "/")
    parts = normalized.split("/")
    if ".." in parts:
        raise PathTraversalError(
            f"Security Violation: Zip Slip attack blocked for entry '{zip_filename}'"
        )

    return resolve_safe_path(base_dir, zip_filename)
