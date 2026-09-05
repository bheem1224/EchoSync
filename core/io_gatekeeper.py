"""
Zero-Trust I/O Gatekeeper (core/io_gatekeeper.py).
Validates URI paths, enforces path traversal security boundaries, and dispatches sanitized POSIX paths to echosync_core.
"""

import logging
import os
from pathlib import Path
from typing import Any

from core.settings import config_manager

logger = logging.getLogger("io_gatekeeper")


class SecurityViolationError(PermissionError):
    """Raised when an operation attempts path traversal or accesses unauthorized storage locations."""


class Gatekeeper:
    """
    Zero-Trust I/O Gatekeeper enforcing root boundary validation and secure dispatching to echosync_core.
    """

    def __init__(self, allowed_roots: list[str | Path] | None = None):
        if allowed_roots:
            self.allowed_roots = [Path(r).resolve() for r in allowed_roots]
        else:
            self.allowed_roots = self._get_default_allowed_roots()

    def _get_default_allowed_roots(self) -> list[Path]:
        """Fetch allowed storage roots from ConfigManager / StorageService."""
        library_dir = (
            config_manager.get("storage.library_dir")
            or config_manager.get("library_dir")
            or "./library"
        )
        download_dir = (
            config_manager.get("storage.download_dir")
            or config_manager.get("download_dir")
            or "./downloads"
        )
        config_dir = (
            config_manager.get("storage.config_dir")
            or config_manager.get("config_dir")
            or "./config"
        )
        temp_dir = "./tmp"

        # Resolve all allowed root directories
        roots = [
            Path(library_dir).resolve(),
            Path(download_dir).resolve(),
            Path(config_dir).resolve(),
            Path(temp_dir).resolve(),
            Path(os.getcwd()).resolve(),
        ]
        return roots

    def resolve_uri(self, uri_or_path: str) -> Path:
        """
        Resolve echosync:// URI schemes or raw paths into physical Path objects.

        Schemes:
            echosync://library/...   -> <library_dir>/...
            echosync://downloads/... -> <download_dir>/...
            echosync://config/...    -> <config_dir>/...
            echosync://temp/...      -> <temp_dir>/...
        """
        if not uri_or_path:
            raise SecurityViolationError("Empty URI or path provided")

        if uri_or_path.startswith("echosync://"):
            scheme_part = uri_or_path[len("echosync://") :]
            parts = scheme_part.split("/", 1)
            root_name = parts[0].lower()
            rel_subpath = parts[1] if len(parts) > 1 else ""

            if root_name == "library":
                base = Path(
                    config_manager.get("storage.library_dir")
                    or config_manager.get("library_dir")
                    or "./library"
                )
            elif root_name in ("downloads", "download"):
                base = Path(
                    config_manager.get("storage.download_dir")
                    or config_manager.get("download_dir")
                    or "./downloads"
                )
            elif root_name == "config":
                base = Path(
                    config_manager.get("storage.config_dir")
                    or config_manager.get("config_dir")
                    or "./config"
                )
            elif root_name in ("temp", "tmp"):
                base = Path("./tmp")
            else:
                raise SecurityViolationError(
                    f"Unknown echosync URI scheme root: '{root_name}'"
                )

            target_path = (base / rel_subpath).resolve()
        else:
            target_path = Path(uri_or_path).resolve()

        return target_path

    def validate_path(self, target_path: Path) -> Path:
        """
        Ensure resolved target_path sits strictly within at least one authorized storage root.
        Raises SecurityViolationError if path traversal or unauthorized directory access is detected.
        """
        resolved_target = Path(target_path).resolve()

        is_allowed = False
        for root in self.allowed_roots:
            try:
                if resolved_target == root or resolved_target.is_relative_to(root):
                    is_allowed = True
                    break
            except ValueError:
                continue

        if not is_allowed:
            logger.error(
                f"SecurityViolationError: Path '{resolved_target}' traverses outside authorized roots {self.allowed_roots}"
            )
            raise SecurityViolationError(
                f"Access denied. Target path '{resolved_target}' traverses outside authorized storage roots."
            )

        return resolved_target

    def authorize_and_execute(
        self_or_manifest, manifest: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Parse, validate, and execute an I/O manifest via echosync_core.
        Supports both Gatekeeper().authorize_and_execute(manifest) and
        Gatekeeper.authorize_and_execute(manifest).
        """
        if manifest is None and isinstance(self_or_manifest, dict):
            manifest = self_or_manifest
            self = Gatekeeper()
        else:
            self = self_or_manifest

        return self._authorize_and_execute(manifest)

    def _authorize_and_execute(self, manifest: dict[str, Any]) -> dict[str, Any]:
        operation = manifest.get("operation")
        if not operation:
            raise ValueError("Manifest missing required 'operation' key")

        uris = manifest.get("target_uris") or []
        if not uris:
            for k in ("target_uri", "src", "target"):
                if manifest.get(k):
                    uris = [manifest[k]]
                    break

        if not uris:
            raise ValueError("Manifest missing required 'target_uris' or 'target_uri'")

        validated_posix_paths = []
        for uri in uris:
            resolved_path = self.resolve_uri(str(uri))
            validated_path = self.validate_path(resolved_path)
            validated_posix_paths.append(validated_path.as_posix())

        import echosync_core

        callback = manifest.get("callback")
        batch_interval_ms = manifest.get("batch_interval_ms", 50)
        batch_size = manifest.get("batch_size", 100)

        execution_results = []

        for posix_path in validated_posix_paths:
            if operation in ("batch_process", "batch_process_directory"):
                echosync_core.batch_process_directory(
                    posix_path, callback=callback, batch_interval_ms=batch_interval_ms
                )
                execution_results.append({"path": posix_path, "status": "dispatched"})

            elif operation == "scan_directory":
                echosync_core.scan_directory(
                    posix_path, callback=callback, batch_size=batch_size
                )
                execution_results.append({"path": posix_path, "status": "scanned"})

            elif operation == "extract_metadata":
                meta = echosync_core.extract_metadata(posix_path)
                execution_results.append(
                    {"path": posix_path, "metadata": meta, "status": "extracted"}
                )

            elif operation == "safe_move":
                dst_uri = (
                    manifest.get("destination_uri")
                    or manifest.get("dst_uri")
                    or manifest.get("dst")
                )
                if not dst_uri:
                    raise ValueError("Operation 'safe_move' requires 'destination_uri'")
                resolved_dst = self.resolve_uri(str(dst_uri))
                validated_dst = self.validate_path(resolved_dst).as_posix()

                # Ensure destination parent directory exists and is writable
                try:
                    dst_parent = Path(validated_dst).parent
                    dst_parent.mkdir(parents=True, exist_ok=True)
                    p_mode = dst_parent.stat().st_mode
                    if not (p_mode & 0o200):
                        dst_parent.chmod(p_mode | 0o775)
                except Exception:
                    pass

                # Attempt to ensure source parent directory is writable (needed for file deletion)
                try:
                    src_parent = Path(posix_path).parent
                    if src_parent.exists():
                        sp_mode = src_parent.stat().st_mode
                        if not (sp_mode & 0o200):
                            src_parent.chmod(sp_mode | 0o775)
                except Exception:
                    pass

                try:
                    echosync_core.safe_move_file(posix_path, validated_dst)
                except Exception as move_err:
                    # Fallback in Python if cross-device / container volume permissions block atomic move
                    import shutil

                    try:
                        shutil.copy2(posix_path, validated_dst)
                        try:
                            Path(posix_path).unlink()
                        except Exception as del_err:
                            logger.warning(
                                f"File copied to library ({validated_dst}) but source could not be deleted ({posix_path}): {del_err}"
                            )
                    except Exception:
                        raise move_err

                execution_results.append(
                    {"src": posix_path, "dst": validated_dst, "status": "moved"}
                )

            elif operation == "copy_file":
                dst_uri = (
                    manifest.get("destination_uri")
                    or manifest.get("dst_uri")
                    or manifest.get("dst")
                )
                if not dst_uri:
                    raise ValueError("Operation 'copy_file' requires 'destination_uri'")
                resolved_dst = self.resolve_uri(str(dst_uri))
                validated_dst = self.validate_path(resolved_dst).as_posix()
                bytes_copied = echosync_core.copy_file(posix_path, validated_dst)
                execution_results.append(
                    {
                        "src": posix_path,
                        "dst": validated_dst,
                        "bytes_copied": bytes_copied,
                        "status": "copied",
                    }
                )

            elif operation == "delete_file":
                echosync_core.delete_file(posix_path)
                execution_results.append({"path": posix_path, "status": "deleted"})

            elif operation == "validate_only":
                execution_results.append({"path": posix_path, "status": "authorized"})

            else:
                raise ValueError(
                    f"Unsupported operation '{operation}' in Gatekeeper manifest"
                )

        return {
            "success": True,
            "operation": operation,
            "validated_paths": validated_posix_paths,
            "execution_results": execution_results,
        }
