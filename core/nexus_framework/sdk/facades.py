"""Unified Nexus Framework Plugin SDK Facades with Principal Capability Scope Enforcement."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import Callable, Iterable, Iterator
import contextlib
import inspect
import logging
from pathlib import Path
import random
import re
import secrets
import sqlite3
import sys
import time
from typing import Any
import zlib

from core.event_bus import event_bus
from core.hook_manager import hook_manager
from core.request_manager import RequestManager
from core.security.rbac import Principal, get_current_principal
from core.tiered_logger import get_logger
from time_utils import utc_now

logger = logging.getLogger("core.nexus_framework.plugin_SDK")
webhook_logger = get_logger("plugin_sdk")

# Global in-memory cache for fast ingress lookup: (crc32_id, slug) -> endpoint_dict
_REGISTERED_WEBHOOKS: dict[tuple[int, str], dict[str, Any]] = {}
# Global registry for plugin hook listeners: crc32_id -> list of callbacks
_WEBHOOK_HANDLERS: dict[int, list[Callable[[str, dict[str, Any]], Any]]] = {}


def compute_plugin_crc32(namespace: str) -> int:
    """Compute deterministic CRC32 32-bit integer for a fully qualified namespace."""
    clean_ns = str(namespace).strip().lower()
    return zlib.crc32(clean_ns.encode("utf-8")) & 0xFFFFFFFF


def build_plugin_principal(plugin_id: str | int, scopes: Iterable[str] = ()) -> Principal:
    """Construct a frozen Principal for a plugin execution context."""
    int_id = int(plugin_id) if isinstance(plugin_id, int) or str(plugin_id).isdigit() else compute_plugin_crc32(str(plugin_id))
    return Principal(
        user_id=None,
        username=f"plugin:{plugin_id}",
        principal_type="plugin",
        roles=(),
        scopes=frozenset(str(s).strip() for s in scopes if str(s).strip()),
        plugin_id=int_id,
    )


def _enforce_facade_scope(principal: Principal | None, *accepted_scopes: str) -> None:
    """Enforce Principal capability scopes (`contract:<entity>:<action>[:own|:any]`) when a Principal is active."""
    effective = principal if principal is not None else get_current_principal()
    if effective is None or not accepted_scopes:
        return

    for scope in accepted_scopes:
        if scope.startswith("contract:accounts:secrets") and effective.principal_type == "plugin":
            raise PermissionError("Missing required capability scope: contract:accounts:secrets")

    for scope in accepted_scopes:
        if effective.has_scope(scope):
            return
        if scope.endswith(":own") and effective.has_scope(scope[:-4]):
            return
        if not scope.endswith((":own", ":any")) and (
            effective.has_scope(f"{scope}:own") or effective.has_scope(f"{scope}:any")
        ):
            return

    effective.require(accepted_scopes[0])


def _resolve_caller_module() -> str:
    """Resolve the calling module from the execution stack, preferring in-tree modules over 3rd-party frames."""
    frame = inspect.currentframe()
    first_external = ""
    while frame:
        mod = frame.f_globals.get("__name__", "")
        if (
            mod
            and not mod.startswith("core.nexus_framework")
            and not mod.startswith("core.plugins")
            and not mod.startswith("inspect")
            and not mod.startswith("importlib")
            and not mod.startswith("_frozen_importlib")
        ):
            if mod.startswith(("plugins.", "core.", "web.", "services.", "tests.", "test_")):
                return mod
            if not first_external:
                first_external = mod
        frame = frame.f_back
    return first_external


def get_base_url() -> str:
    """Dynamically resolve external base URL for webhooks."""
    try:
        from database.config_database import get_config_database

        db = get_config_database()
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT key, value FROM system_settings WHERE key IN ('server.base_url', 'system.base_url')")
            rows = dict(c.fetchall())
            if rows.get("server.base_url"):
                return str(rows["server.base_url"]).rstrip("/")
            if rows.get("system.base_url"):
                return str(rows["system.base_url"]).rstrip("/")
    except Exception:
        pass

    try:
        from core.settings import config_manager

        explicit_url = config_manager.get("server.base_url") or config_manager.get("base_url")
        if explicit_url:
            return str(explicit_url).rstrip("/")

        cert_file = config_manager.get("ssl_cert_file")
        key_file = config_manager.get("ssl_key_file")
        scheme = "https" if cert_file and key_file and Path(cert_file).exists() and Path(key_file).exists() else "http"

        host = config_manager.get("server.host") or config_manager.get("host") or "localhost"
        if host in ("0.0.0.0", "::"):
            host = "localhost"
        port = config_manager.get("server.port") or config_manager.get("port") or 5000
        return f"{scheme}://{host}:{port}"
    except Exception:
        return "http://localhost:5000"


def _verify_caller(expected_plugin_id: str) -> None:
    # 1. Core Exemption via Physical Path
    for frame_info in inspect.stack():
        filename = frame_info.filename.replace("\\", "/")
        if "/app/core/" in filename or "/app/web/" in filename or "/tests/" in filename or "tests/" in filename:
            return
        if "/plugins/" in filename and ("/data/plugins/" in filename or "/app/plugins/" in filename):
            break

    caller_mod = _resolve_caller_module()
    if not caller_mod:
        return
    if caller_mod.startswith("core.") or caller_mod.startswith("providers."):
        return

    clean_expected = expected_plugin_id.removeprefix("plugin.")
    if "@beta" in clean_expected:
        clean_expected = clean_expected.split("@")[0]
    norm_expected = clean_expected.lower()

    parts = [p for p in caller_mod.split(".") if p.lower() != "beta"]
    if parts and parts[0] == "plugins" and len(parts) >= 3:
        caller_plugin_id = f"{parts[1]}.{parts[2]}"
        if caller_plugin_id.lower() == norm_expected:
            return

    caller_id = parts[-1] if parts else ""
    base_expected = norm_expected.split(".")[-1]
    if caller_id.lower() != base_expected and caller_id.lower() != norm_expected:
        raise PermissionError(f"Namespace Isolation Violation: {caller_mod} attempted to access {expected_plugin_id}")


def check_plugin_permission(plugin_id: str, scope: str) -> bool:
    """Check whether a plugin has been granted a particular permission scope."""
    clean_scope = scope.strip()
    if clean_scope.startswith("contract:accounts:secrets"):
        return False

    if not plugin_id or str(plugin_id) in ("core", "system") or str(plugin_id).startswith("core."):
        return True

    import json

    from core.nexus_framework.permissions import SAFE_BASE_SCOPES
    from core.settings import config_manager
    from database.config_database import get_config_database

    is_base_scope = clean_scope in SAFE_BASE_SCOPES or clean_scope in (
        "read_library",
        "metadata",
        "database.read_library",
        "metadata.read",
    )
    canonical_scope = (
        "database.read_library"
        if clean_scope == "read_library"
        else ("metadata.read" if clean_scope == "metadata" else clean_scope)
    )

    def _is_explicitly_denied(perms_obj: Any) -> bool:
        if not isinstance(perms_obj, dict):
            return False
        if perms_obj.get(canonical_scope) is False or perms_obj.get(clean_scope) is False:
            return True
        if "." in canonical_scope:
            cat, sub = canonical_scope.split(".", 1)
            cat_obj = perms_obj.get(cat)
            if isinstance(cat_obj, dict) and cat_obj.get(sub) is False:
                return True
            if perms_obj.get(sub) is False:
                return True
        else:
            db_perms_map = perms_obj.get("database")
            if isinstance(db_perms_map, dict) and db_perms_map.get(canonical_scope) is False:
                return True
        return False

    db_perms = None
    manifest_perms = None

    # 1. Check services table in config.db first
    try:
        int_id = int(plugin_id) if isinstance(plugin_id, int) or (isinstance(plugin_id, str) and plugin_id.isdigit()) else compute_plugin_crc32(str(plugin_id))
        clean_name = str(plugin_id).strip().lower()
        short_name = clean_name.split(".")[-1]

        db = get_config_database()
        conn = db._open_connection()
        try:
            c = conn.cursor()
            c.execute(
                "SELECT permissions, privileged_mode FROM services WHERE plugin_id=? OR LOWER(name)=? OR LOWER(name)=?",
                (int_id, clean_name, short_name),
            )
            row = c.fetchone()
            if row:
                if row[1]:
                    return True
                if row[0]:
                    try:
                        db_perms = json.loads(row[0])
                        if _is_explicitly_denied(db_perms):
                            return False
                        if isinstance(db_perms, list):
                            if "privileged_mode" in db_perms or canonical_scope in db_perms or clean_scope in db_perms:
                                return True
                            if "." in canonical_scope:
                                _base_cat, sub_key = canonical_scope.split(".", 1)
                                if sub_key in db_perms:
                                    return True
                        elif isinstance(db_perms, dict):
                            if db_perms.get("privileged_mode"):
                                return True
                            if "." in canonical_scope:
                                base_cat, sub_key = canonical_scope.split(".", 1)
                                cat_perms = db_perms.get(base_cat, {})
                                if isinstance(cat_perms, dict) and cat_perms.get(sub_key):
                                    return True
                                if db_perms.get(canonical_scope) or db_perms.get(sub_key):
                                    return True
                            elif db_perms.get(clean_scope) or db_perms.get(canonical_scope):
                                return True
                    except Exception:
                        pass
        finally:
            conn.close()
    except Exception:
        pass

    # 2. Check physical manifest.json
    try:
        clean_name = str(plugin_id).replace("plugin.", "").replace(".", "/")
        manifest_path = config_manager.get_plugins_dir() / clean_name / "manifest.json"
        if not manifest_path.exists():
            clean_name = str(plugin_id).replace("plugin.", "")
            manifest_path = config_manager.get_plugins_dir() / clean_name / "manifest.json"

        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("privileged") is True or manifest.get("privileged_mode") is True:
                return True
            manifest_perms = manifest.get("permissions", {})
            if _is_explicitly_denied(manifest_perms):
                return False

            if isinstance(manifest_perms, list):
                if (
                    "privileged_mode" in manifest_perms
                    or canonical_scope in manifest_perms
                    or clean_scope in manifest_perms
                ):
                    return True
                if "." in canonical_scope:
                    _base_cat, sub_key = canonical_scope.split(".", 1)
                    if sub_key in manifest_perms:
                        return True
            elif isinstance(manifest_perms, dict):
                if manifest_perms.get("privileged_mode") is True:
                    return True
                if "." in canonical_scope:
                    base_cat, sub_key = canonical_scope.split(".", 1)
                    cat_perms = manifest_perms.get(base_cat, {})
                    if isinstance(cat_perms, dict) and cat_perms.get(sub_key) is True:
                        return True
                    if manifest_perms.get(canonical_scope) is True or manifest_perms.get(sub_key) is True:
                        return True
                elif manifest_perms.get(clean_scope) or manifest_perms.get(canonical_scope):
                    return True
    except Exception:
        pass

    # 3. Auto-grant default base read scopes if not explicitly denied
    if is_base_scope and not _is_explicitly_denied(db_perms) and not _is_explicitly_denied(manifest_perms):
        return True

    return False


def _call_check_plugin_permission(plugin_id: str, scope: str) -> bool:
    """Dispatch check_plugin_permission respecting monkeypatches on legacy plugin_SDK or sdk modules."""
    for mod_name in ("core.nexus_framework.plugin_SDK", "core.nexus_framework.sdk"):
        mod = sys.modules.get(mod_name)
        if mod is not None:
            fn = getattr(mod, "check_plugin_permission", None)
            if fn is not None and fn is not check_plugin_permission:
                return bool(fn(plugin_id, scope))
    return check_plugin_permission(plugin_id, scope)


class _ConfigFacade:
    def __init__(self, plugin_id: str):
        _verify_caller(plugin_id)
        self.plugin_id = plugin_id

    def get(self, key: str, default: Any = None, *, principal: Principal | None = None) -> Any:
        _enforce_facade_scope(principal, "contract:config:read:own", "contract:config:read:any")
        from database.config_database import get_config_database

        db = get_config_database()
        max_retries = 5
        base_delay = 0.05
        for attempt in range(max_retries):
            try:
                svc_id = db.get_or_create_service_id(self.plugin_id)
                val = db.get_service_config(svc_id, key)
                return val if val is not None else default
            except Exception as e:
                err_msg = str(e).lower()
                is_transient = isinstance(e, sqlite3.OperationalError) or any(
                    tok in err_msg for tok in ("disk i/o error", "locked", "busy")
                )
                if is_transient and attempt < max_retries - 1:
                    delay = min(1.0, base_delay * (2**attempt)) + random.uniform(0, 0.05)
                    logger.warning(
                        f"[PluginConfigSDK] Transient database error accessing config key '{key}' "
                        f"for plugin '{self.plugin_id}' (attempt {attempt + 1}/{max_retries}): {e}. Backing off for {delay:.3f}s..."
                    )
                    time.sleep(delay)
                    continue
                logger.warning(
                    f"[PluginConfigSDK] Error reading config key '{key}' for plugin '{self.plugin_id}': {e}. "
                    f"Falling back to default value."
                )
                return default
        return default

    def set(self, key: str, value: Any, *, principal: Principal | None = None) -> None:
        _enforce_facade_scope(principal, "contract:config:edit:own", "contract:config:edit:any")
        from database.config_database import get_config_database

        db = get_config_database()
        max_retries = 5
        base_delay = 0.05
        for attempt in range(max_retries):
            try:
                svc_id = db.get_or_create_service_id(self.plugin_id)
                db.set_service_config(svc_id, key, value, is_sensitive=False)
                return
            except Exception as e:
                err_msg = str(e).lower()
                is_transient = isinstance(e, sqlite3.OperationalError) or any(
                    tok in err_msg for tok in ("disk i/o error", "locked", "busy")
                )
                if is_transient and attempt < max_retries - 1:
                    delay = min(1.0, base_delay * (2**attempt)) + random.uniform(0, 0.05)
                    logger.warning(
                        f"[PluginConfigSDK] Transient database error setting config key '{key}' "
                        f"for plugin '{self.plugin_id}' (attempt {attempt + 1}/{max_retries}): {e}. Backing off for {delay:.3f}s..."
                    )
                    time.sleep(delay)
                    continue
                logger.warning(
                    f"[PluginConfigSDK] Failed to set config key '{key}' for plugin '{self.plugin_id}': {e}."
                )
                return

    def get_for_service(
        self,
        service_key: str | int,
        key: str,
        default: Any = None,
        *,
        principal: Principal | None = None,
    ) -> Any:
        _enforce_facade_scope(principal, "contract:config:read:own", "contract:config:read:any")
        try:
            from database.config_database import get_config_database

            db = get_config_database()
            svc_id = db.get_service_id(service_key)
            if svc_id:
                val = db.get_service_config(svc_id, key)
                if val is not None:
                    return val
        except Exception:
            pass
        return default

    def set_for_service(
        self,
        service_key: str | int,
        key: str,
        value: Any,
        *,
        is_sensitive: bool = False,
        principal: Principal | None = None,
    ) -> bool:
        _enforce_facade_scope(principal, "contract:config:edit:own", "contract:config:edit:any")
        try:
            from database.config_database import get_config_database

            db = get_config_database()
            svc_id = db.get_service_id(service_key)
            if svc_id:
                db.set_service_config(svc_id, key, value, is_sensitive=is_sensitive)
                return True
        except Exception:
            pass
        return False


PluginConfigSDK = _ConfigFacade


class _SecretsFacade:
    def __init__(self, plugin_id: str):
        _verify_caller(plugin_id)
        self.plugin_id = plugin_id

    def get(self, key: str, default: Any = None, *, principal: Principal | None = None) -> Any:
        _enforce_facade_scope(principal, "contract:secrets:read:own", "contract:config:read:own")
        from database.config_database import get_config_database

        db = get_config_database()
        max_retries = 5
        base_delay = 0.05
        for attempt in range(max_retries):
            try:
                svc_id = db.get_or_create_service_id(self.plugin_id)
                val = db.get_service_config(svc_id, key)
                return val if val is not None else default
            except Exception as e:
                err_msg = str(e).lower()
                is_transient = isinstance(e, sqlite3.OperationalError) or any(
                    tok in err_msg for tok in ("disk i/o error", "locked", "busy")
                )
                if is_transient and attempt < max_retries - 1:
                    delay = min(1.0, base_delay * (2**attempt)) + random.uniform(0, 0.05)
                    logger.warning(
                        f"[SecretsFacade] Transient database error accessing secret key '{key}' "
                        f"for plugin '{self.plugin_id}' (attempt {attempt + 1}/{max_retries}): {e}. Backing off for {delay:.3f}s..."
                    )
                    time.sleep(delay)
                    continue
                logger.warning(
                    f"[SecretsFacade] Error reading secret key '{key}' for plugin '{self.plugin_id}': {e}. "
                    f"Falling back to default value."
                )
                return default
        return default

    def set(self, key: str, value: str, *, principal: Principal | None = None) -> None:
        _enforce_facade_scope(principal, "contract:secrets:edit:own", "contract:config:edit:own")
        from database.config_database import get_config_database

        db = get_config_database()
        max_retries = 5
        base_delay = 0.05
        for attempt in range(max_retries):
            try:
                svc_id = db.get_or_create_service_id(self.plugin_id)
                db.set_service_config(svc_id, key, value, is_sensitive=True)
                return
            except Exception as e:
                err_msg = str(e).lower()
                is_transient = isinstance(e, sqlite3.OperationalError) or any(
                    tok in err_msg for tok in ("disk i/o error", "locked", "busy")
                )
                if is_transient and attempt < max_retries - 1:
                    delay = min(1.0, base_delay * (2**attempt)) + random.uniform(0, 0.05)
                    logger.warning(
                        f"[SecretsFacade] Transient database error setting secret key '{key}' "
                        f"for plugin '{self.plugin_id}' (attempt {attempt + 1}/{max_retries}): {e}. Backing off for {delay:.3f}s..."
                    )
                    time.sleep(delay)
                    continue
                logger.warning(f"[SecretsFacade] Failed to set secret key '{key}' for plugin '{self.plugin_id}': {e}.")
                return


class _JobsSDKFacade:
    def __init__(self, plugin_id: str):
        _verify_caller(plugin_id)
        self.plugin_id = plugin_id

    def register_job(
        self,
        name: str,
        func: Callable[..., Any],
        interval_seconds: float | None = None,
        start_after: float = 0.0,
        enabled: bool = True,
        max_retries: int = 0,
        backoff_base: float = 5.0,
        backoff_factor: float = 2.0,
        tags: list[str] | None = None,
    ) -> None:
        from core.task_manager.task_queue import job_queue

        prefixed_name = f"{self.plugin_id}.{name}" if not name.startswith(self.plugin_id) else name
        job_queue.register_job(
            name=prefixed_name,
            func=func,
            interval_seconds=interval_seconds,
            start_after=start_after,
            enabled=enabled,
            max_retries=max_retries,
            backoff_base=backoff_base,
            backoff_factor=backoff_factor,
            tags=tags,
            plugin=self.plugin_id,
        )

    def dispatch_job(self, name: str) -> bool:
        from core.task_manager.task_queue import job_queue

        prefixed_name = f"{self.plugin_id}.{name}" if not name.startswith(self.plugin_id) else name
        return job_queue.execute_job_now(prefixed_name)


class _AccountsSDKFacade:
    def _resolve_caller_plugin_id(self) -> str:
        caller_mod = _resolve_caller_module()
        if caller_mod.startswith("plugins."):
            parts = [p for p in caller_mod.split(".") if p.lower() != "beta"]
            return f"{parts[1]}.{parts[2]}" if len(parts) >= 3 else parts[1]
        if caller_mod.startswith("core.providers."):
            return caller_mod.split(".")[2]
        return caller_mod

    def get_token(self, account_id: int, *, principal: Principal | None = None) -> dict[str, Any] | None:
        from database.config_database import get_config_database

        active_principal = principal if principal is not None else get_current_principal()
        if active_principal is not None:
            if active_principal.principal_type == "plugin":
                raise PermissionError(
                    "Missing required capability scope: contract:accounts:secrets "
                    "(plugins must use the centralized OAuth Sidecar)."
                )
            active_principal.require("contract:accounts:secrets")

        caller_mod = _resolve_caller_module()
        is_host_or_bundled_core = (
            not caller_mod
            or caller_mod.startswith("core.")
            or caller_mod.startswith("web.")
            or caller_mod.startswith("services.")
            or caller_mod.startswith("tests.")
            or caller_mod.startswith("test_")
            or caller_mod.startswith("plugins.EchoSync.")
        )
        if not is_host_or_bundled_core:
            raise PermissionError(
                "Missing required capability scope: contract:accounts:secrets "
                "(plugins must use the centralized OAuth Sidecar)."
            )

        token = get_config_database().get_account_token(account_id)
        if not token:
            return None

        if (
            not caller_mod
            or caller_mod.startswith("core.")
            or caller_mod.startswith("web.")
            or caller_mod.startswith("services.")
            or caller_mod.startswith("tests.")
            or caller_mod.startswith("test_")
        ):
            return token

        parts = [p for p in caller_mod.split(".") if p.lower() != "beta"]
        if parts and parts[0] == "plugins" and len(parts) >= 3:
            caller_plugin_id = f"{parts[1]}.{parts[2]}"
        elif parts and parts[0] == "plugins" and len(parts) == 2:
            caller_plugin_id = parts[1]
        else:
            caller_plugin_id = parts[-1] if parts else caller_mod

        account_owner_plugin_id = token.get("provider", "")

        from core.settings import config_manager

        privileged = False
        try:
            import json

            manifest_path = config_manager.get_plugins_dir() / caller_plugin_id / "manifest.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                privileged = manifest.get("privileged", False)
        except Exception:
            pass

        owner_lower = account_owner_plugin_id.lower().replace("echosync.", "").replace("echosync/", "").strip()
        caller_lower = caller_plugin_id.lower().replace("echosync.", "").replace("echosync/", "").strip()

        if (
            caller_lower == owner_lower
            or caller_lower.endswith(f".{owner_lower}")
            or owner_lower.endswith(f".{caller_lower}")
            or privileged
        ):
            return token

        redacted = dict(token)
        redacted["access_token"] = "REDACTED"
        redacted["refresh_token"] = "REDACTED"
        return redacted

    def save_token(
        self,
        account_id: int,
        access_token: str,
        refresh_token: str | None,
        expires_at: int | None,
        token_type: str = "Bearer",
        scope: str | None = None,
        *,
        principal: Principal | None = None,
    ) -> bool:
        _enforce_facade_scope(principal, "contract:accounts:edit:own", "contract:accounts:edit:any")
        from database.config_database import get_config_database

        return bool(
            get_config_database().save_account_token(
                account_id, access_token, refresh_token, token_type, expires_at, scope
            )
        )

    def get_all(self, *, principal: Principal | None = None) -> list[dict[str, Any]]:
        """Return all accounts associated with the calling plugin."""
        _enforce_facade_scope(principal, "contract:accounts:read:own", "contract:accounts:read:any")
        from database.config_database import get_config_database

        db = get_config_database()
        plugin_id_str = self._resolve_caller_plugin_id()
        service_id = db.get_or_create_service_id(plugin_id_str)
        return db.get_accounts(service_id=service_id)

    def ensure_account(
        self,
        account_id: int | None = None,
        account_name: str | None = None,
        display_name: str | None = None,
        user_id: str | None = None,
        *,
        principal: Principal | None = None,
    ) -> int:
        _enforce_facade_scope(principal, "contract:accounts:edit:own", "contract:accounts:edit:any")
        from database.config_database import get_config_database

        db = get_config_database()
        plugin_id_str = self._resolve_caller_plugin_id()
        service_id = db.get_or_create_service_id(plugin_id_str)
        return db.ensure_account(
            service_id=service_id,
            account_id=account_id,
            account_name=account_name,
            display_name=display_name,
            user_id=user_id,
        )

    def upsert_account(
        self,
        account_name: str | None = None,
        display_name: str | None = None,
        user_id: str | None = None,
        account_email: str | None = None,
        is_active: bool | None = None,
        is_authenticated: bool | None = None,
        account_id: int | None = None,
        *,
        principal: Principal | None = None,
    ) -> int:
        _enforce_facade_scope(principal, "contract:accounts:edit:own", "contract:accounts:edit:any")
        from database.config_database import get_config_database

        db = get_config_database()
        plugin_id_str = self._resolve_caller_plugin_id()
        service_id = db.get_or_create_service_id(plugin_id_str)
        return db.upsert_account(
            service_id=service_id,
            account_name=account_name,
            display_name=display_name,
            user_id=user_id,
            account_email=account_email,
            is_active=is_active,
            is_authenticated=is_authenticated,
            account_id=account_id,
        )

    def mark_account_authenticated(self, account_id: int, *, principal: Principal | None = None) -> None:
        _enforce_facade_scope(principal, "contract:accounts:edit:own", "contract:accounts:edit:any")
        from database.config_database import get_config_database

        get_config_database().mark_account_authenticated(account_id)

    def mark_authenticated(self, account_id: int, *, principal: Principal | None = None) -> None:
        self.mark_account_authenticated(account_id, principal=principal)

    def toggle_account_active(
        self, account_id: int, is_active: bool, *, principal: Principal | None = None
    ) -> None:
        _enforce_facade_scope(principal, "contract:accounts:edit:own", "contract:accounts:edit:any")
        from database.config_database import get_config_database

        get_config_database().toggle_account_active(account_id, is_active)

    def delete_account(self, account_id: int, *, principal: Principal | None = None) -> bool:
        _enforce_facade_scope(principal, "contract:accounts:delete:own", "contract:accounts:delete:any")
        from database.config_database import get_config_database

        return get_config_database().delete_account(account_id)

    def update_account_name(
        self, account_id: int, new_name: str, *, principal: Principal | None = None
    ) -> None:
        _enforce_facade_scope(principal, "contract:accounts:edit:own", "contract:accounts:edit:any")
        from database.config_database import get_config_database

        get_config_database().update_account_name(account_id, new_name)


class _PluginsSDKFacade:
    def invoke(self, target_plugin_id: str, action: str, payload: dict[str, Any]) -> Any:
        from core.nexus_framework.plugin_loader import PluginRegistry

        if PluginRegistry.is_provider_disabled(target_plugin_id):
            raise Exception(f"Plugin {target_plugin_id} is disabled or not found")

        provider = PluginRegistry.get_provider_class(target_plugin_id)
        if not provider:
            raise Exception(f"Plugin {target_plugin_id} not found")

        instance = PluginRegistry.create_instance(target_plugin_id)
        if hasattr(instance, "handle_ipc"):
            return instance.handle_ipc(action, payload)
        return None


class _FileSDKFacade:
    def delete(self, file_path: str, *, principal: Principal | None = None) -> bool:
        _enforce_facade_scope(principal, "contract:files:delete", "contract:tracks:delete")
        from core.settings import config_manager

        if config_manager.get("system.dry_run", False):
            log = get_logger("plugin_SDK")
            log.info(f"DRY RUN: Intercepted deletion of {file_path}")
            return True

        try:
            p = Path(file_path).resolve()
            if not p.exists():
                return False

            music_dir_setting = config_manager.get("music_dir", "")
            if music_dir_setting:
                music_dir = Path(music_dir_setting).resolve()
                try:
                    if not p.is_relative_to(music_dir):
                        log = get_logger("plugin_SDK")
                        log.error(f"Security violation: Attempted soft delete outside music_dir: {p}")
                        return False
                except AttributeError:
                    if not str(p).startswith(str(music_dir)):
                        log = get_logger("plugin_SDK")
                        log.error(f"Security violation: Attempted soft delete outside music_dir: {p}")
                        return False
            else:
                music_dir = p.parent

            trash_dir = music_dir / ".trash"
            trash_dir.mkdir(exist_ok=True)

            dest = trash_dir / p.name
            from core.io_gatekeeper import Gatekeeper

            Gatekeeper.authorize_and_execute({"operation": "safe_move", "src": str(p), "dst": str(dest)})
            return True
        except Exception as e:
            log = get_logger("plugin_SDK")
            log.error(f"Failed to soft delete {file_path}: {e}")
            return False


class _QualitySDKFacade:
    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id

    def register_option(
        self,
        name: str,
        label: str,
        input_type: str,
        default_value: Any,
        choices: list[Any] | None = None,
    ) -> None:
        if input_type not in ["boolean", "dropdown"]:
            raise ValueError("input_type must be either 'boolean' or 'dropdown'")

        option = {
            "name": name,
            "label": label,
            "type": input_type,
            "default": default_value,
            "choices": choices,
        }

        from core.nexus_framework.plugin_loader import PluginRegistry

        PluginRegistry.register_quality_option(self.plugin_id, option)


class _NetworkSDKFacade:
    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id
        self._manager = RequestManager(provider=plugin_id)

    def _check_allowlist(self, url: str) -> None:
        import json
        from urllib.parse import urlparse

        from core.settings import config_manager

        try:
            if self.plugin_id == "core" or self.plugin_id.startswith("core."):
                return

            manifest_path = config_manager.get_plugins_dir() / self.plugin_id.replace("plugin.", "") / "manifest.json"
            if not manifest_path.exists():
                raise PermissionError(f"Plugin manifest not found for {self.plugin_id}")

            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("privileged") is True or manifest.get("privileged_mode") is True:
                return
            if (
                isinstance(manifest.get("permissions"), dict)
                and manifest.get("permissions", {}).get("privileged_mode") is True
            ):
                return

            allowlist = manifest.get("network_domains")
            if allowlist is None:
                perms = manifest.get("permissions")
                if isinstance(perms, dict):
                    allowlist = perms.get("network_domains", [])
                else:
                    allowlist = []

            if "*" in allowlist:
                return

            parsed = urlparse(url)
            domain = parsed.netloc.split(":")[0]

            for pattern in allowlist:
                if pattern.startswith("*."):
                    suffix = pattern[1:]
                    if domain.endswith(suffix) or domain == suffix[1:]:
                        return
                elif domain == pattern:
                    return

            raise PermissionError(f"Network access to '{domain}' blocked. Domain not in 'network_domains' allowlist.")
        except Exception as e:
            if isinstance(e, PermissionError):
                raise
            raise PermissionError(f"Security check failed for network request: {e}")

    def get(self, url: str, **kwargs: Any) -> Any:
        self._check_allowlist(url)
        return self._manager.get(url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Any:
        self._check_allowlist(url)
        return self._manager.post(url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> Any:
        self._check_allowlist(url)
        return self._manager.put(url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> Any:
        self._check_allowlist(url)
        return self._manager.delete(url, **kwargs)


class _HealthCheckSDKFacade:
    def __init__(self, plugin_id: str | None = None):
        self.plugin_id = plugin_id

    def register(self, url_or_func: Any, interval_seconds: float = 300.0) -> None:
        from core.task_manager.health import HealthCheckResult, health_check_registry

        plugin_id = self.plugin_id or sdk._get_plugin_id()
        service_name = plugin_id.split(".")[-1].split("@")[0]

        if isinstance(url_or_func, str):
            url = url_or_func

            def url_health_check() -> HealthCheckResult:
                try:
                    manager = RequestManager(provider=plugin_id)
                    response = manager.get(url, timeout=10.0)
                    if 200 <= response.status_code < 400:
                        return HealthCheckResult(
                            service_name=service_name,
                            status="healthy",
                            message=f"Ping to {url} succeeded (HTTP {response.status_code})",
                        )
                    return HealthCheckResult(
                        service_name=service_name,
                        status="unhealthy",
                        message=f"Ping to {url} failed (HTTP {response.status_code})",
                    )
                except Exception as e:
                    return HealthCheckResult(
                        service_name=service_name,
                        status="unhealthy",
                        message=f"Ping to {url} failed: {e!s}",
                    )

            check_func = url_health_check
        else:
            check_func = url_or_func

        def wrapped_check_func() -> HealthCheckResult:
            try:
                res = check_func()
                if isinstance(res, HealthCheckResult):
                    return res
                if isinstance(res, bool):
                    return HealthCheckResult(
                        service_name=service_name,
                        status="healthy" if res else "unhealthy",
                        message="Service check succeeded" if res else "Service check failed",
                    )
                return HealthCheckResult(
                    service_name=service_name,
                    status="healthy" if res else "unhealthy",
                    message=str(res),
                )
            except Exception as e:
                return HealthCheckResult(service_name=service_name, status="unhealthy", message=str(e))

        health_check_registry.register_check_with_job(
            service_name=service_name,
            check_func=wrapped_check_func,
            interval_seconds=interval_seconds,
            plugin=plugin_id,
        )


class _DatabaseFacade:
    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id

    def check_permission(self, scope: str) -> bool:
        return _call_check_plugin_permission(self.plugin_id, scope)

    def can_read_library(self) -> bool:
        return _call_check_plugin_permission(self.plugin_id, "database.read_library")

    def can_mutate_aliases(self) -> bool:
        return _call_check_plugin_permission(self.plugin_id, "database.mutate_aliases")

    def can_mutate_attributes(self) -> bool:
        return _call_check_plugin_permission(self.plugin_id, "database.mutate_attributes")

    def get_plugin_session(self):
        from database.working_database import get_working_database

        working_db = get_working_database()
        provider_storage = working_db.get_provider_storage(self.plugin_id)
        return provider_storage.session_scope()

    @staticmethod
    def get_object_session(entity: Any) -> Any:
        """Resolve the active ORM session bound to an entity without plugins importing sqlalchemy."""
        if entity is None:
            return None
        try:
            from sqlalchemy.orm import object_session

            return object_session(entity)
        except Exception:
            return None


class _LibrarySDKFacade:
    """Governed SDK facade for reading and maintaining the canonical music library database."""

    def __init__(self, plugin_id: str):
        self._plugin_id = plugin_id

    def get_database(self, *, principal: Principal | None = None) -> Any:
        _enforce_facade_scope(principal, "contract:tracks:read", "contract:library:read")
        from database.music_database import get_database

        return get_database()

    @staticmethod
    def get_object_session(entity: Any) -> Any:
        return _DatabaseFacade.get_object_session(entity)

    def search_fuzzy(
        self,
        title: str,
        artist: str | None = None,
        limit: int = 10,
        *,
        principal: Principal | None = None,
    ) -> list[Any]:
        _enforce_facade_scope(principal, "contract:tracks:read")
        if not _call_check_plugin_permission(self._plugin_id, "database.read_library"):
            raise PermissionError(f"Plugin '{self._plugin_id}' lacks 'permissions.database.read_library' permission.")
        from services.storage_service import get_storage_service

        db = get_storage_service().get_music_database()
        return db.search_canonical_fuzzy(title=title, artist=artist, limit=limit)

    def get_track_record_by_id(
        self,
        track_id: int | str,
        *,
        principal: Principal | None = None,
    ) -> dict[str, Any] | None:
        _enforce_facade_scope(principal, "contract:tracks:read")
        if not _call_check_plugin_permission(self._plugin_id, "database.read_library"):
            raise PermissionError(f"Plugin '{self._plugin_id}' lacks 'permissions.database.read_library' permission.")
        try:
            tid = int(track_id)
        except (TypeError, ValueError):
            return None

        from sqlalchemy.orm import joinedload

        from database.music_database import Track
        from services.storage_service import get_storage_service

        db = get_storage_service().get_music_database()
        with db.session_scope() as session:
            t = (
                session.query(Track)
                .options(joinedload(Track.artist), joinedload(Track.album))
                .filter(Track.id == tid)
                .first()
            )
            if not t:
                return None
            return {
                "id": t.id,
                "title": t.title,
                "artist": t.artist.name if t.artist else "Unknown Artist",
                "album": t.album.title if t.album else "",
                "duration_ms": getattr(t, "duration_ms", None) or getattr(t, "duration", None),
                "track_number": t.track_number,
                "disc_number": t.disc_number,
                "bitrate": getattr(t, "bitrate", None),
                "file_path": getattr(t, "file_path", None),
                "file_format": getattr(t, "file_format", None),
                "isrc": t.isrc,
                "musicbrainz_id": getattr(t, "musicbrainz_id", None),
            }

    @contextlib.contextmanager
    def signed_tracks_scope(self, *, principal: Principal | None = None) -> Iterator[tuple[Any, list[Any]]]:
        """Yield (session, signed_tracks) for tracks possessing a cryptographic echosync_signature."""
        _enforce_facade_scope(principal, "contract:tracks:read")
        if not _call_check_plugin_permission(self._plugin_id, "database.read_library"):
            raise PermissionError(f"Plugin '{self._plugin_id}' lacks 'permissions.database.read_library' permission.")
        from database.music_database import Track, get_database

        music_db = get_database()
        with music_db.get_session() as session:
            tracks = (
                session.query(Track)
                .filter(
                    Track.echosync_signature.isnot(None),
                    Track.echosync_signature != "",
                )
                .all()
            )
            yield session, tracks

    def cleanup_library_database(
        self,
        *,
        db: Any = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
        canonicalize_path: Callable[[str], str] | None = None,
        sanctioned_prefixes: tuple[str, ...] = ("/data/library/",),
        skip_rogue_sweep: bool = False,
        principal: Principal | None = None,
    ) -> dict[str, int]:
        """Execute library hygiene cleanup (ghost media, rogue paths, orphaned tracks/albums/artists)."""
        _enforce_facade_scope(principal, "contract:tracks:delete", "contract:library:edit")
        from sqlalchemy import delete, or_, update

        from database.music_database import (
            Album,
            Artist,
            AudioFingerprint,
            ExternalIdentifier,
            LocalMedia,
            Track,
            get_database,
        )

        target_db = db if db is not None else get_database()
        notify = progress_callback or (lambda _c, _t, _s="": None)
        canon_fn = canonicalize_path or (
            lambda fp: Path(fp).resolve().as_posix()
            if fp and not fp.startswith("virtual://")
            else fp
        )

        with target_db.session_scope() as session:
            notify(0, 100, "Phase 0: Evicting missing physical media...")
            missing_media = []
            all_media = session.query(LocalMedia).all()
            for media in all_media:
                exists = Path(media.file_path).exists() if media.file_path else False
                if not media.file_path or not exists:
                    missing_media.append(media)
                    session.delete(media)
            session.flush()

            notify(10, 100, "Phase 0.5: Evicting rogue mount entries...")
            rogue_count = 0
            if not skip_rogue_sweep:
                prefix_conditions = [LocalMedia.file_path.startswith(prefix) for prefix in sanctioned_prefixes]
                rogue_media = (
                    session.query(LocalMedia)
                    .filter(
                        ~LocalMedia.file_path.startswith("virtual://"),
                        ~or_(*prefix_conditions),
                    )
                    .all()
                )
                for media in rogue_media:
                    session.delete(media)
                rogue_count = len(rogue_media)
                session.flush()

            notify(20, 100, "Phase 1: Evicting tracks without media...")
            empty_tracks = session.query(Track).filter(~Track.media_files.any()).all()
            deleted_track_count = len(empty_tracks)
            for track in empty_tracks:
                session.delete(track)
            session.commit()

            notify(40, 100, "Phase 2: Flattening redundant file paths...")
            path_groups: dict[str, list[Any]] = defaultdict(list)
            all_media = (
                session.query(LocalMedia).filter(LocalMedia.file_path.isnot(None), LocalMedia.file_path != "").all()
            )
            for media in all_media:
                try:
                    canon = canon_fn(media.file_path)
                except Exception:
                    canon = media.file_path
                path_groups[canon].append(media)

            flattened_duplicate_count = 0
            for _file_path, group in path_groups.items():
                if len(group) > 1:
                    group.sort(key=lambda m: m.id)
                    keeper = group[0]
                    for duplicate in group[1:]:
                        session.execute(
                            update(ExternalIdentifier)
                            .where(ExternalIdentifier.media_id == duplicate.media_id)
                            .values(media_id=keeper.media_id)
                        )
                        session.execute(
                            update(AudioFingerprint)
                            .where(AudioFingerprint.media_id == duplicate.media_id)
                            .values(media_id=keeper.media_id)
                        )
                        session.execute(delete(LocalMedia).where(LocalMedia.id == duplicate.id))
                        flattened_duplicate_count += 1

            session.flush()
            session.expire_all()
            session.commit()

            notify(66, 100, "Phase 3: Purging structural orphans...")
            empty_albums = session.query(Album).filter(~Album.tracks.any()).all()
            empty_album_count = len(empty_albums)
            for album in empty_albums:
                session.delete(album)

            empty_artists = session.query(Artist).filter(~Artist.tracks.any(), ~Artist.albums.any()).all()
            empty_artist_count = len(empty_artists)
            for artist in empty_artists:
                session.delete(artist)

            session.commit()

        notify(100, 100, "Database cleanup complete.")
        return {
            "missing_media": len(missing_media),
            "rogue_media": rogue_count,
            "deleted_tracks": deleted_track_count,
            "flattened_duplicates": flattened_duplicate_count,
            "deleted_albums": empty_album_count,
            "deleted_artists": empty_artist_count,
        }


class _WorkingSDKFacade:
    """Governed SDK facade for interacting with working.db download queue & transient state."""

    def __init__(self, plugin_id: str):
        self._plugin_id = plugin_id

    def resolve_active_download_task_id(
        self,
        *,
        filename: str = "",
        username: str = "",
        principal: Principal | None = None,
    ) -> int | None:
        _enforce_facade_scope(principal, "contract:downloads:read")
        if not filename and not username:
            return None

        norm_filename = filename.replace("\\", "/").split("/")[-1].strip().lower()
        from core.database.models.working import DownloadQueue, DownloadStatus
        from database.working_database import get_working_database

        work_db = get_working_database()
        with work_db.session_scope() as session:
            active_items = (
                session.query(DownloadQueue)
                .filter(
                    DownloadQueue.status.in_(
                        [
                            DownloadStatus.DOWNLOADING.value,
                            DownloadStatus.VERIFYING.value,
                            DownloadStatus.QUEUED.value,
                            DownloadStatus.SEARCHING.value,
                            DownloadStatus.RETRYING.value,
                            "downloading",
                            "verifying",
                            "queued",
                            "searching",
                            "retrying",
                        ]
                    )
                )
                .order_by(DownloadQueue.id.desc())
                .all()
            )
            for item in active_items:
                cand_id = item.active_candidate_id or item.plugin_id or ""
                if cand_id:
                    c_lower = cand_id.lower()
                    if norm_filename and norm_filename in c_lower:
                        return item.id
                    if username and username.lower() in c_lower:
                        return item.id

                track = item.echo_sync_track or {}
                t_file = track.get("file_path") or track.get("title") or ""
                if norm_filename and norm_filename in str(t_file).lower():
                    return item.id
        return None

    def transition_download_to_verifying(
        self,
        task_id: int | str,
        *,
        file_path: str | None = None,
        principal: Principal | None = None,
    ) -> bool:
        _enforce_facade_scope(principal, "contract:downloads:edit")
        import datetime

        from core.database.models.working import DownloadQueue, DownloadStatus
        from database.working_database import get_working_database

        resolved_id = int(task_id) if str(task_id).isdigit() else task_id
        work_db = get_working_database()
        with work_db.session_scope() as session:
            task = session.get(DownloadQueue, resolved_id)
            if not task:
                return False
            task.status = DownloadStatus.VERIFYING.value
            if file_path and task.echo_sync_track is not None:
                track_dict = dict(task.echo_sync_track)
                track_dict["downloaded_file_path"] = file_path
                task.echo_sync_track = track_dict
            task.updated_at = datetime.datetime.now(datetime.UTC)
            session.commit()
            session.refresh(task)
            return True

    def get_download_candidate_identity(
        self,
        task_id: int | str,
        *,
        principal: Principal | None = None,
    ) -> tuple[str | None, str | None]:
        _enforce_facade_scope(principal, "contract:downloads:read")
        from core.database.models.working import DownloadQueue
        from database.working_database import get_working_database

        work_db = get_working_database()
        with work_db.session_scope() as session:
            item = session.get(DownloadQueue, int(task_id))
            if item:
                cand = item.active_candidate_id or item.plugin_id or ""
                if "|" in cand:
                    parts = cand.split("|", 1)
                    return parts[0], parts[1]
        return None, None


_ATTR_KEY_REGEX = re.compile(r"^[a-zA-Z0-9_.-]{1,100}$")


def _validate_attribute_payload(key: str, value: Any) -> None:
    """Validate attribute key format, JSON-serializability, recursion depth, and byte size."""
    if not isinstance(key, str) or not _ATTR_KEY_REGEX.match(key):
        raise ValueError(f"Invalid attribute key '{key}'. Must match pattern ^[a-zA-Z0-9_.-]{{1,100}}$.")

    def _check_depth(v: Any, current_depth: int = 1) -> None:
        if current_depth > 5:
            raise ValueError("Attribute value exceeds maximum allowed recursion depth of 5.")
        if isinstance(v, dict):
            for sub_v in v.values():
                _check_depth(sub_v, current_depth + 1)
        elif isinstance(v, list):
            for item in v:
                _check_depth(item, current_depth + 1)

    _check_depth(value)

    try:
        import json

        serialized = json.dumps(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Attribute value is not JSON-serializable: {e}") from e

    if len(serialized.encode("utf-8")) > 65536:
        raise ValueError("Attribute value payload exceeds 64 KB limit.")


def _resolve_plugin_id_int(plugin_name: str) -> int:
    """Resolve a plugin name to its deterministic CRC32 plugin_id."""
    import binascii

    clean_name = str(plugin_name).strip().lower()

    try:
        from database.config_database import get_config_database

        db = get_config_database()
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT plugin_id FROM services WHERE LOWER(name)=?",
                (clean_name,),
            )
            row = c.fetchone()
            if row and row[0]:
                return int(row[0])

            bare = clean_name.replace("echosync.", "").replace("echosync/", "").strip()
            for variant in (
                f"echosync.{bare}",
                f"echosync/{bare}",
                bare,
            ):
                c.execute(
                    "SELECT plugin_id FROM services WHERE LOWER(name)=?",
                    (variant,),
                )
                row = c.fetchone()
                if row and row[0]:
                    return int(row[0])
    except Exception:
        pass

    return binascii.crc32(clean_name.encode("utf-8")) & 0xFFFFFFFF


class _AliasBroker:
    """Governed SDK broker for mutating track and artist aliases."""

    def __init__(self, plugin_id_str: str):
        self._plugin_id_str = plugin_id_str

    @property
    def _plugin_id_int(self) -> int:
        return _resolve_plugin_id_int(self._plugin_id_str)

    def upsert(
        self,
        entity_type: str,
        entity_id: int | str | None,
        proposals: list[dict[str, Any] | Any],
        sync_id: str | None = None,
        session: Any = None,
        *,
        principal: Principal | None = None,
    ) -> int:
        _enforce_facade_scope(principal, f"contract:{entity_type}s:edit", "contract:aliases:edit")
        if not _call_check_plugin_permission(self._plugin_id_str, "database.mutate_aliases"):
            raise PermissionError(
                f"Plugin '{self._plugin_id_str}' lacks 'permissions.database.mutate_aliases' permission."
            )
        from core.database.repositories.track_repo import TrackRepository
        from core.metadata.schemas import EntityAliasProposal
        from database.music_database import get_database

        norm_proposals: list[EntityAliasProposal] = []
        for p in proposals:
            if isinstance(p, EntityAliasProposal):
                norm_proposals.append(p)
            elif isinstance(p, dict):
                norm_proposals.append(
                    EntityAliasProposal(
                        entity_type=p.get("entity_type", entity_type),
                        entity_id=p.get("entity_id", entity_id),
                        value=p.get("value") or p.get("name") or "",
                        language=p.get("language") or p.get("locale"),
                        script=p.get("script"),
                        alias_type=p.get("alias_type"),
                    )
                )

        if session:
            return TrackRepository.upsert_entity_aliases(
                session=session,
                proposals=norm_proposals,
                sync_id=sync_id,
                plugin_id=self._plugin_id_int,
                commit=False,
            )
        music_db = get_database()
        with music_db.get_session() as sess:
            return TrackRepository.upsert_entity_aliases(
                session=sess,
                proposals=norm_proposals,
                sync_id=sync_id,
                plugin_id=self._plugin_id_int,
                commit=True,
            )


class _AttributeBroker:
    """Governed SDK broker for reading and mutating namespaced entity KVS attributes."""

    def __init__(self, plugin_id_str: str):
        self._plugin_id_str = plugin_id_str

    @property
    def _plugin_id_int(self) -> int:
        return _resolve_plugin_id_int(self._plugin_id_str)

    def set(
        self,
        entity_type: str,
        entity_id: int,
        key: str,
        value: Any,
        session: Any = None,
        *,
        principal: Principal | None = None,
    ) -> bool:
        _enforce_facade_scope(principal, f"contract:{entity_type}s:edit", "contract:attributes:edit")
        if not _call_check_plugin_permission(self._plugin_id_str, "database.mutate_attributes"):
            raise PermissionError(
                f"Plugin '{self._plugin_id_str}' lacks 'permissions.database.mutate_attributes' permission."
            )
        _validate_attribute_payload(key, value)
        from core.database.repositories.track_repo import TrackRepository
        from database.music_database import get_database

        if session:
            return TrackRepository.set_entity_attributes(
                session=session,
                entity_type=entity_type,
                entity_id=entity_id,
                plugin_id=self._plugin_id_int,
                key=key,
                value=value,
                commit=False,
            )
        music_db = get_database()
        with music_db.get_session() as sess:
            return TrackRepository.set_entity_attributes(
                session=sess,
                entity_type=entity_type,
                entity_id=entity_id,
                plugin_id=self._plugin_id_int,
                key=key,
                value=value,
                commit=True,
            )

    def get(
        self,
        entity_type: str,
        entity_id: int,
        key: str | None = None,
        session: Any = None,
        *,
        principal: Principal | None = None,
    ) -> Any:
        _enforce_facade_scope(principal, f"contract:{entity_type}s:read", "contract:attributes:read")
        if not (
            _call_check_plugin_permission(self._plugin_id_str, "database.read_library")
            or _call_check_plugin_permission(self._plugin_id_str, "database.mutate_attributes")
        ):
            raise PermissionError(
                f"Plugin '{self._plugin_id_str}' lacks 'permissions.database.read_library' or 'permissions.database.mutate_attributes' permission."
            )
        from core.database.repositories.track_repo import TrackRepository
        from database.music_database import get_database

        if session:
            attrs = TrackRepository.get_entity_attributes(
                session=session,
                entity_type=entity_type,
                entity_id=entity_id,
                plugin_id=self._plugin_id_int,
            )
        else:
            music_db = get_database()
            with music_db.get_session() as sess:
                attrs = TrackRepository.get_entity_attributes(
                    session=sess,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    plugin_id=self._plugin_id_int,
                )

        if key is not None:
            return attrs.get(key)
        return attrs

    def delete(
        self,
        entity_type: str,
        entity_id: int,
        key: str,
        session: Any = None,
        *,
        principal: Principal | None = None,
    ) -> bool:
        _enforce_facade_scope(principal, f"contract:{entity_type}s:delete", "contract:attributes:delete")
        if not _call_check_plugin_permission(self._plugin_id_str, "database.mutate_attributes"):
            raise PermissionError(
                f"Plugin '{self._plugin_id_str}' lacks 'permissions.database.mutate_attributes' permission."
            )
        from core.database.repositories.track_repo import TrackRepository
        from database.music_database import get_database

        if session:
            return TrackRepository.delete_entity_attribute(
                session=session,
                entity_type=entity_type,
                entity_id=entity_id,
                plugin_id=self._plugin_id_int,
                key=key,
                commit=False,
            )
        music_db = get_database()
        with music_db.get_session() as sess:
            return TrackRepository.delete_entity_attribute(
                session=sess,
                entity_type=entity_type,
                entity_id=entity_id,
                plugin_id=self._plugin_id_int,
                key=key,
                commit=True,
            )


class _OAuthSDKFacade:
    """Governed SDK facade for Centralized HTTPS OAuth Token Broker integration."""

    def __init__(self, plugin_id_str: str):
        self._plugin_id_str = plugin_id_str

    @property
    def _plugin_id_int(self) -> int:
        return _resolve_plugin_id_int(self._plugin_id_str)

    def get_redirect_uri(self, provider_or_slug: str | None = None) -> str:
        """Derive the canonical centralized HTTPS redirect URI on port 5001."""
        from core.network_utils import get_lan_ip

        slug = provider_or_slug or self._plugin_id_str.split(".")[-1]
        lan_ip = get_lan_ip()
        return f"https://{lan_ip}:5001/api/oauth/callback/plugins/{slug}"

    def create_session(
        self,
        provider: str,
        auth_url: str,
        token_url: str,
        client_id: str,
        client_secret: str | None = None,
        scopes: str | list[str] | None = None,
        use_pkce: bool = True,
        account_id: int | None = None,
        on_token: Any = None,
        on_error: Any = None,
        extra_auth_params: dict[str, Any] | None = None,
        ttl_seconds: int = 600,
    ) -> Any:
        """Register an OAuth flow with the centralized token broker on port 5001."""
        from core.oauth.sidecar import register_oauth_session

        return register_oauth_session(
            plugin_id=self._plugin_id_int,
            provider=provider,
            auth_url=auth_url,
            token_url=token_url,
            client_id=client_id,
            client_secret=client_secret,
            scopes=scopes,
            use_pkce=use_pkce,
            account_id=account_id,
            on_token=on_token,
            on_error=on_error,
            extra_auth_params=extra_auth_params,
            ttl_seconds=ttl_seconds,
        )


class _WebhooksSDKFacade:
    """SDK Facade for registering and managing plugin webhooks."""

    def __init__(self, caller_namespace: str | None = None):
        self._explicit_namespace = caller_namespace

    def _resolve_namespace_and_id(self) -> tuple[str, int]:
        if self._explicit_namespace and "." in self._explicit_namespace:
            ns = self._explicit_namespace
            return ns, compute_plugin_crc32(ns)

        frame = inspect.currentframe()
        caller_mod = ""
        while frame:
            mod = frame.f_globals.get("__name__", "")
            if (
                mod
                and not mod.startswith("core.plugins")
                and not mod.startswith("core.nexus_framework")
                and mod.startswith("plugins.")
            ):
                caller_mod = mod
                break
            frame = frame.f_back

        if caller_mod.startswith("plugins."):
            parts = [p for p in caller_mod.split(".") if p.lower() != "beta"]
            if len(parts) >= 3:
                ns = f"{parts[1]}.{parts[2]}"
                return ns, compute_plugin_crc32(ns)
            if len(parts) == 2:
                ns = parts[1]
                return ns, compute_plugin_crc32(ns)

        fallback = self._explicit_namespace or "EchoSync.generic"
        return fallback, compute_plugin_crc32(fallback)

    def register_endpoint(
        self,
        slug: str,
        secret: str | None = None,
        allow_unauthenticated: bool = False,
        allowed_subnets: list[str] | None = None,
        namespace: str | None = None,
        *,
        principal: Principal | None = None,
    ) -> dict[str, Any]:
        _enforce_facade_scope(principal, "contract:webhooks:edit:own", "contract:config:edit:own")
        if namespace:
            ns = namespace.strip()
            crc32_id = compute_plugin_crc32(ns)
        else:
            ns, crc32_id = self._resolve_namespace_and_id()

        if not allow_unauthenticated and not secret:
            secret = f"sk_live_{secrets.token_hex(16)}"

        base_url = get_base_url()
        canonical_url = f"{base_url}/api/v1/webhooks/{ns}/{slug}"

        headers_yaml = ""
        if secret:
            headers_yaml = f'        headers:\n          - name: "X-EchoSync-Secret"\n            value: "{secret}"\n'

        yaml_template = (
            f"integrations:\n"
            f"  webhooks:\n"
            f"    echosync_downloads:\n"
            f"      on:\n"
            f"        - DownloadFileComplete\n"
            f"        - DownloadFileFailed\n"
            f"        - SoulseekClientConnected\n"
            f"        - SoulseekClientDisconnected\n"
            f"      call:\n"
            f'        url: "{canonical_url}"\n'
            f"{headers_yaml}"
            f"        timeout: 10000\n"
            f"        retry:\n"
            f"          attempts: 3\n"
        )

        registration_data = {
            "slug": slug,
            "plugin_id": crc32_id,
            "namespace": ns,
            "secret": secret,
            "allow_unauthenticated": bool(allow_unauthenticated),
            "allowed_subnets": allowed_subnets or [],
            "url": canonical_url,
            "yaml_template": yaml_template,
            "registered_at": utc_now().isoformat(),
        }

        _REGISTERED_WEBHOOKS[(crc32_id, slug)] = registration_data

        try:
            from database.config_database import get_config_database

            db = get_config_database()
            service_id = db.get_service_id(crc32_id) or db.get_service_id(ns)
            if not service_id:
                db.register_service(
                    name=ns,
                    service_type="downloader",
                    description=f"Plugin {ns}",
                    plugin_id=crc32_id,
                )
                service_id = db.get_service_id(crc32_id) or db.get_service_id(ns)

            if service_id:
                config_key = f"webhook:{slug}"
                db.set_service_config(service_id, config_key, registration_data, is_sensitive=True)
                webhook_logger.info(
                    "Registered webhook endpoint '%s' for %s (CRC32: %d)",
                    slug,
                    ns,
                    crc32_id,
                )
        except Exception as e:
            webhook_logger.warning("Could not persist webhook endpoint in config.db: %s", e)

        return registration_data

    def get_endpoint(
        self,
        slug: str,
        namespace: str | None = None,
        *,
        principal: Principal | None = None,
    ) -> dict[str, Any] | None:
        _enforce_facade_scope(principal, "contract:webhooks:read:own", "contract:config:read:own")
        if namespace:
            ns = namespace.strip()
            crc32_id = compute_plugin_crc32(ns)
        else:
            ns, crc32_id = self._resolve_namespace_and_id()
        if (crc32_id, slug) in _REGISTERED_WEBHOOKS:
            return _REGISTERED_WEBHOOKS[(crc32_id, slug)]

        try:
            from database.config_database import get_config_database

            db = get_config_database()
            service_id = db.get_service_id(crc32_id)
            if service_id:
                val = db.get_service_config(service_id, f"webhook:{slug}")
                if isinstance(val, dict):
                    _REGISTERED_WEBHOOKS[(crc32_id, slug)] = val
                    return val
        except Exception:
            pass
        return None

    def list_endpoints(self, *, principal: Principal | None = None) -> list[dict[str, Any]]:
        _enforce_facade_scope(principal, "contract:webhooks:read:own", "contract:config:read:own")
        _namespace, crc32_id = self._resolve_namespace_and_id()
        results = [ep for (p_id, _), ep in _REGISTERED_WEBHOOKS.items() if p_id == crc32_id]
        if not results:
            try:
                from database.config_database import get_config_database

                db = get_config_database()
                service_id = db.get_service_id(crc32_id)
                if service_id:
                    all_cfg = db.get_all_service_config(service_id)
                    for k, v in all_cfg.items():
                        if k.startswith("webhook:") and isinstance(v, dict):
                            results.append(v)
            except Exception:
                pass
        return results


def lookup_registered_endpoint(plugin_id: int, slug: str) -> dict[str, Any] | None:
    """Lookup registered webhook endpoint metadata by CRC32 integer plugin_id and slug."""
    if (plugin_id, slug) in _REGISTERED_WEBHOOKS:
        return _REGISTERED_WEBHOOKS[(plugin_id, slug)]

    try:
        from database.config_database import get_config_database

        db = get_config_database()
        service_id = db.get_service_id(plugin_id)
        if service_id:
            val = db.get_service_config(service_id, f"webhook:{slug}")
            if isinstance(val, dict):
                _REGISTERED_WEBHOOKS[(plugin_id, slug)] = val
                return val
    except Exception as e:
        webhook_logger.warning("Error looking up endpoint for plugin %d, slug '%s': %s", plugin_id, slug, e)
    return None


def register_webhook_handler(plugin_id: int, handler: Callable[[str, dict[str, Any]], Any]) -> None:
    """Register a callable hook handler for webhooks dispatched to a plugin_id."""
    if plugin_id not in _WEBHOOK_HANDLERS:
        _WEBHOOK_HANDLERS[plugin_id] = []
    _WEBHOOK_HANDLERS[plugin_id].append(handler)


async def dispatch_webhook(plugin_id: int, slug: str, payload: dict[str, Any]) -> None:
    """Dispatch an inbound webhook payload to the target plugin's @hookimpl on_webhook_received."""
    from core.nexus_framework.plugin_loader import PluginRegistry

    if plugin_id in _WEBHOOK_HANDLERS:
        for handler in _WEBHOOK_HANDLERS[plugin_id]:
            try:
                res = handler(slug, payload)
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                webhook_logger.exception("Error in webhook handler for plugin %d", plugin_id)

    try:
        provider_cls = PluginRegistry.get_plugin_class(plugin_id)
        if provider_cls:
            instance = None
            try:
                instance = PluginRegistry.create_instance(plugin_id)
            except Exception:
                pass

            target = instance or provider_cls
            if hasattr(target, "on_webhook_received"):
                hook_method = target.on_webhook_received
                res = hook_method(slug, payload)
                if asyncio.iscoroutine(res):
                    await res
    except Exception:
        webhook_logger.exception("Error invoking on_webhook_received on plugin %d", plugin_id)

    try:
        event_bus.publish(
            {
                "event": "WEBHOOK_RECEIVED",
                "plugin_id": plugin_id,
                "slug": slug,
                "payload": payload,
            }
        )
    except Exception as e:
        webhook_logger.warning("Failed to publish WEBHOOK_RECEIVED to event_bus: %s", e)

    try:
        hook_manager.trigger("ON_WEBHOOK_RECEIVED", plugin_id=plugin_id, slug=slug, payload=payload)
    except Exception as e:
        webhook_logger.warning("Failed to trigger ON_WEBHOOK_RECEIVED hook: %s", e)


class StateKVS:
    def __init__(self, plugin_id: str):
        frame = inspect.currentframe()
        try:
            caller_module = inspect.getmodule(frame.f_back) if frame else None
            if (
                caller_module
                and not caller_module.__name__.startswith("core.")
                and not caller_module.__name__.startswith("tests.")
            ):
                caller_name = caller_module.__name__
                parts = [p for p in caller_name.split(".") if p.lower() != "beta"]
                norm_caller = ".".join(parts).lower()
                clean_plugin_id = plugin_id.removeprefix("plugin.")
                if "@beta" in clean_plugin_id:
                    clean_plugin_id = clean_plugin_id.split("@")[0]
                norm_expected = f"plugins.{clean_plugin_id}".lower()
                if not norm_caller.startswith(norm_expected):
                    raise PermissionError(
                        f"Cross-namespace data access forbidden. Caller '{caller_name}' cannot access StateKVS for '{plugin_id}'."
                    )
        finally:
            del frame
        self.plugin_id = plugin_id

    def get(self, key: str, default: Any = None, *, principal: Principal | None = None) -> str | Any:
        _enforce_facade_scope(principal, "contract:kvs:read:own", "contract:config:read:own")
        from database.working_database import get_working_database

        db = get_working_database()
        val = None
        with db.session_scope() as session:
            from sqlalchemy.sql import text

            res = session.execute(
                text("SELECT value FROM plugin_state_kvs WHERE plugin_id=:ns AND key=:k"),
                {"ns": self.plugin_id, "k": key},
            ).fetchone()
            if res:
                val = res[0]
        return val if val is not None else default

    def set(self, key: str, value: str, *, principal: Principal | None = None) -> None:
        _enforce_facade_scope(principal, "contract:kvs:edit:own", "contract:config:edit:own")
        from database.working_database import get_working_database

        db = get_working_database()
        with db.session_scope() as session:
            from sqlalchemy.sql import text

            session.execute(
                text("INSERT OR REPLACE INTO plugin_state_kvs (plugin_id, key, value) VALUES (:ns, :k, :v)"),
                {"ns": self.plugin_id, "k": key, "v": value},
            )


class _PluginModelFacade:
    @property
    def Track(self):
        from database.music_database import Track

        return Track

    @property
    def Album(self):
        from database.music_database import Album

        return Album

    @property
    def Artist(self):
        from database.music_database import Artist

        return Artist

    @property
    def ExternalIdentifier(self):
        from database.music_database import ExternalIdentifier

        return ExternalIdentifier

    @property
    def Download(self):
        from database.working_database import Download

        return Download

    @property
    def UserRating(self):
        from database.working_database import UserRating

        return UserRating

    @property
    def PlaybackHistory(self):
        from database.working_database import PlaybackHistory

        return PlaybackHistory


class _SDK:
    def __init__(self):
        self._accounts = _AccountsSDKFacade()
        self.plugins = _PluginsSDKFacade()
        self.file = _FileSDKFacade()

    @property
    def health(self) -> _HealthCheckSDKFacade:
        return _HealthCheckSDKFacade(self._get_plugin_id())

    @property
    def config(self) -> _ConfigFacade:
        return _ConfigFacade(self._get_plugin_id())

    @property
    def secrets(self) -> _SecretsFacade:
        return _SecretsFacade(self._get_plugin_id())

    @property
    def storage(self) -> Any:
        from services.storage_service import get_storage_service

        return get_storage_service()

    @property
    def db(self) -> _DatabaseFacade:
        return _DatabaseFacade(self._get_plugin_id())

    @property
    def library(self) -> _LibrarySDKFacade:
        return _LibrarySDKFacade(self._get_plugin_id())

    @property
    def working(self) -> _WorkingSDKFacade:
        return _WorkingSDKFacade(self._get_plugin_id())

    @property
    def aliases(self) -> _AliasBroker:
        return _AliasBroker(self._get_plugin_id())

    @property
    def attributes(self) -> _AttributeBroker:
        return _AttributeBroker(self._get_plugin_id())

    @property
    def accounts(self) -> _AccountsSDKFacade:
        return self._accounts

    @property
    def quality(self) -> _QualitySDKFacade:
        return _QualitySDKFacade(self._get_plugin_id())

    @property
    def models(self) -> _PluginModelFacade:
        return _PluginModelFacade()

    @property
    def webhooks(self) -> _WebhooksSDKFacade:
        return _WebhooksSDKFacade(self._get_plugin_id())

    @property
    def oauth(self) -> _OAuthSDKFacade:
        return _OAuthSDKFacade(self._get_plugin_id())

    def _get_plugin_id(self) -> str:
        frame = inspect.currentframe()
        caller_mod = ""
        fallback_mod = ""
        while frame:
            mod = frame.f_globals.get("__name__", "")
            if mod and not mod.startswith("core.nexus_framework") and not mod.startswith("core.plugins"):
                if not mod.startswith("importlib") and not mod.startswith("_frozen_importlib"):
                    if mod.startswith("plugins."):
                        caller_mod = mod
                        break
                    if not fallback_mod:
                        fallback_mod = mod
            frame = frame.f_back

        if not caller_mod:
            caller_mod = fallback_mod or ""

        if caller_mod.startswith("plugins."):
            parts = [p for p in caller_mod.split(".") if p.lower() != "beta"]
            if len(parts) >= 3:
                return f"{parts[1]}.{parts[2]}"
            return parts[1] if len(parts) > 1 else caller_mod

        if caller_mod.startswith("core.providers."):
            return caller_mod.split(".")[2]

        return caller_mod.replace("plugins.", "").replace("core.", "").split(".")[0]

    def get_plugin_data_dir(self) -> str:
        """Return private persistent storage for the calling plugin."""
        import os

        plugin_name = self._get_plugin_id()
        return os.path.join("/data/plugins_data", plugin_name)

    def get_database_connection(self, write_access: bool = False, require_library: bool = True):
        """Return an SQLAlchemy engine connected to the calling plugin's isolated SQLite database."""
        import os

        from sqlalchemy import create_engine, event

        from core.settings import config_manager
        from database.config_database import get_config_database

        plugin_name = self._get_plugin_id()
        if require_library and not _call_check_plugin_permission(plugin_name, "database.read_library"):
            raise PermissionError(f"Plugin '{plugin_name}' lacks 'permissions.database.read_library' permission.")
        if write_access and not (
            _call_check_plugin_permission(plugin_name, "database.mutate_working")
            or _call_check_plugin_permission(plugin_name, "privileged_mode")
        ):
            raise PermissionError(
                f"Plugin '{plugin_name}' lacks 'permissions.database.mutate_working' or 'privileged_mode' permission for write access."
            )
        db = get_config_database()
        plugin_id_int = db.get_service_id(plugin_name)
        if not plugin_id_int:
            import binascii

            plugin_id_int = binascii.crc32(plugin_name.lower().encode("utf-8")) & 0xFFFFFFFF

        channel = config_manager.get_plugin_channel(plugin_name) or "stable"
        db_file_name = f"{plugin_id_int}@beta.db" if channel == "beta" else f"{plugin_id_int}.db"

        plugin_data_dir = "/data/plugins/data/"
        os.makedirs(plugin_data_dir, exist_ok=True)

        db_path = os.path.join(plugin_data_dir, db_file_name)
        engine = create_engine(f"sqlite:///{db_path}")

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            try:
                if os.path.exists("/data/music.db"):
                    cursor.execute("ATTACH DATABASE 'file:/data/music.db?mode=ro' AS music_lib")
                working_mode = "rw" if write_access else "ro"
                if os.path.exists("/data/working.db"):
                    cursor.execute(f"ATTACH DATABASE 'file:/data/working.db?mode={working_mode}' AS working")
            except Exception:
                pass
            finally:
                cursor.close()

        return engine

    @property
    def network(self) -> _NetworkSDKFacade:
        return _NetworkSDKFacade(self._get_plugin_id())

    @property
    def dry_run(self) -> bool:
        from core.settings import config_manager

        return config_manager.get("system.dry_run", False)

    @property
    def jobs(self) -> _JobsSDKFacade:
        return _JobsSDKFacade(self._get_plugin_id())

    def schedule(self, interval_minutes: int):
        def decorator(func):
            func._schedule_interval = interval_minutes
            return func

        return decorator


sdk = _SDK()
