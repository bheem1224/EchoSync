"""
Zero-Trust I/O Gatekeeper (core/io_gatekeeper.py).
Validates URI paths, enforces path traversal security boundaries, and dispatches sanitized POSIX paths to echosync_core.
"""

import hashlib
import logging
import os
import uuid
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
        self_or_manifest: Any = None,
        manifest: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Parse, validate, and execute an I/O manifest via echosync_core.
        Supports both Gatekeeper().authorize_and_execute(manifest) and
        Gatekeeper.authorize_and_execute(manifest), as well as keyword arguments:
        Gatekeeper.authorize_and_execute(operation="move", source=..., destination=...).
        """
        if isinstance(self_or_manifest, Gatekeeper):
            instance = self_or_manifest
            m = dict(manifest or {})
            m.update(kwargs)
        elif isinstance(self_or_manifest, type) and issubclass(
            self_or_manifest, Gatekeeper
        ):
            instance = self_or_manifest()
            m = dict(manifest or {})
            m.update(kwargs)
        elif isinstance(self_or_manifest, dict):
            instance = Gatekeeper()
            m = dict(self_or_manifest)
            if manifest:
                m.update(manifest)
            m.update(kwargs)
        elif isinstance(self_or_manifest, str):
            instance = Gatekeeper()
            m = {"operation": self_or_manifest}
            if manifest:
                m.update(manifest)
            m.update(kwargs)
        else:
            instance = Gatekeeper()
            m = dict(manifest or {})
            m.update(kwargs)

        return instance._authorize_and_execute(m)

    def _authorize_and_execute(self, manifest: dict[str, Any]) -> dict[str, Any]:
        operation = manifest.get("operation")
        if not operation:
            raise ValueError("Manifest missing required 'operation' key")

        uris = manifest.get("target_uris") or []
        if not uris:
            for k in ("target_uri", "src", "target", "source"):
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

            elif operation in ("safe_move", "move"):
                dst_uri = (
                    manifest.get("destination_uri")
                    or manifest.get("dst_uri")
                    or manifest.get("dst")
                    or manifest.get("destination")
                    or manifest.get("dest")
                )
                if not dst_uri:
                    raise ValueError(
                        f"Operation '{operation}' requires 'destination_uri' or 'destination'"
                    )
                resolved_dst = self.resolve_uri(str(dst_uri))
                validated_dst = self.validate_path(resolved_dst).as_posix()

                # Ensure destination parent directory exists and is writable
                try:
                    dst_parent = Path(validated_dst).parent
                    dst_parent.mkdir(parents=True, exist_ok=True)
                    p_mode = dst_parent.stat().st_mode
                    if not (p_mode & 0o200):
                        dst_parent.chmod(p_mode | 0o775)
                except OSError as err:
                    logger.debug("Could not adjust destination parent permissions: %s", err)

                # Attempt to ensure source parent directory is writable (needed for file deletion)
                try:
                    src_parent = Path(posix_path).parent
                    if src_parent.exists():
                        sp_mode = src_parent.stat().st_mode
                        if not (sp_mode & 0o200):
                            src_parent.chmod(sp_mode | 0o775)
                except OSError as err:
                    logger.debug("Could not adjust source parent permissions: %s", err)

                try:
                    echosync_core.safe_move_file(posix_path, validated_dst)
                except (OSError, RuntimeError) as move_err:
                    self._cross_volume_safe_move(
                        echosync_core, posix_path, validated_dst, move_err
                    )

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

    @staticmethod
    def _compute_file_digest(file_path: Path) -> str:
        """Compute SHA-256 hex digest of a file using bounded streaming chunks."""
        hasher = hashlib.sha256()
        with file_path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _cross_volume_safe_move(
        self,
        echosync_core_mod: Any,
        src_posix: str,
        dst_posix: str,
        move_err: Exception,
    ) -> None:
        """Cross-volume fallback: atomic temp copy, size/hash verify, promote, then delete source."""
        src_path = Path(src_posix)
        dst_path = Path(dst_posix)
        if not src_path.exists():
            raise move_err from None

        src_size = src_path.stat().st_size
        src_digest = self._compute_file_digest(src_path)
        tmp_path = dst_path.with_name(f".{dst_path.name}.{uuid.uuid4().hex[:8]}.tmp")

        try:
            bytes_copied = echosync_core_mod.copy_file(src_posix, tmp_path.as_posix())
            if not tmp_path.exists():
                raise OSError(f"Cross-volume copy did not create staging file '{tmp_path}'")

            tmp_size = tmp_path.stat().st_size
            if tmp_size != src_size or (
                isinstance(bytes_copied, int) and bytes_copied != src_size
            ):
                raise OSError(
                    f"Cross-volume size mismatch for '{src_posix}': "
                    f"expected {src_size}, got {tmp_size} (copied={bytes_copied})"
                )

            if self._compute_file_digest(tmp_path) != src_digest:
                raise OSError(
                    f"Cross-volume integrity verification failed for '{src_posix}'"
                )

            try:
                echosync_core_mod.safe_move_file(tmp_path.as_posix(), dst_posix)
            except (OSError, RuntimeError):
                os.replace(tmp_path, dst_path)

            if not dst_path.exists() or dst_path.stat().st_size != src_size:
                raise OSError(
                    f"Cross-volume promotion verification failed for '{dst_posix}'"
                )

            try:
                echosync_core_mod.delete_file(src_posix)
            except (OSError, RuntimeError) as del_err:
                logger.warning(
                    "File copied to library (%s) but source could not be deleted (%s): %s",
                    dst_posix,
                    src_posix,
                    del_err,
                )
        except Exception as fallback_err:
            if tmp_path.exists():
                try:
                    echosync_core_mod.delete_file(tmp_path.as_posix())
                except Exception:
                    try:
                        tmp_path.unlink(missing_ok=True)
                    except OSError:
                        pass
            if isinstance(fallback_err, (OSError, RuntimeError)):
                raise fallback_err from move_err
            raise move_err from fallback_err
