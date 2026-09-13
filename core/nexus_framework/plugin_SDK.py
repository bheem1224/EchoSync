import inspect
import re
from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Protocol

from core.db.echo_sync_track import EchosyncTrack
from core.enums import Capability
from core.matching_engine import text_utils
from core.request_manager import RequestManager
from time_utils import utc_now


@dataclass
class PluginRef:
    """Reference to a track in a specific plugin"""

    plugin: str
    plugin_id: str  # Plugin's native ID
    plugin_url: str | None = None  # Direct URL if available
    metadata: dict[str, Any] = field(default_factory=dict)  # Plugin-specific extras
    last_updated: datetime = field(default_factory=utc_now)

    def validate(self) -> None:
        """Validate the plugin reference fields."""
        if not self.plugin_id:
            raise ValueError("Plugin ID cannot be empty.")
        if self.plugin_url and not re.match(r"^https?://", self.plugin_url):
            raise ValueError("Plugin URL must start with http:// or https://.")


class _ConfigFacade:
    def __init__(self, plugin_id: str):
        _verify_caller(plugin_id)
        self.plugin_id = plugin_id

    def get(self, key: str, default=None):
        from database.config_database import get_config_database

        db = get_config_database()
        svc_id = db.get_or_create_service_id(self.plugin_id)
        val = db.get_service_config(svc_id, key)
        return val if val is not None else default

    def set(self, key: str, value: str):
        from database.config_database import get_config_database

        db = get_config_database()
        svc_id = db.get_or_create_service_id(self.plugin_id)
        db.set_service_config(svc_id, key, value, is_sensitive=False)


class _SecretsFacade:
    def __init__(self, plugin_id: str):
        _verify_caller(plugin_id)
        self.plugin_id = plugin_id

    def get(self, key: str, default=None):
        from database.config_database import get_config_database

        db = get_config_database()
        svc_id = db.get_or_create_service_id(self.plugin_id)
        val = db.get_service_config(svc_id, key)
        return val if val is not None else default

    def set(self, key: str, value: str):
        from database.config_database import get_config_database

        db = get_config_database()
        svc_id = db.get_or_create_service_id(self.plugin_id)
        db.set_service_config(svc_id, key, value, is_sensitive=True)


class _JobsSDKFacade:
    def __init__(self, plugin_id: str):
        _verify_caller(plugin_id)
        self.plugin_id = plugin_id

    def register_job(
        self,
        name: str,
        func,
        interval_seconds=None,
        start_after=0.0,
        enabled=True,
        max_retries=0,
        backoff_base=5.0,
        backoff_factor=2.0,
        tags=None,
    ):
        from core.job_queue import job_queue

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
        from core.job_queue import job_queue

        prefixed_name = f"{self.plugin_id}.{name}" if not name.startswith(self.plugin_id) else name
        return job_queue.execute_job_now(prefixed_name)


class _AccountsSDKFacade:
    def get_token(self, account_id: int):
        from database.config_database import get_config_database

        token = get_config_database().get_account_token(account_id)
        if not token:
            return None

        # Find actual calling module from stack frames
        caller_mod = ""
        frame = inspect.currentframe()
        while frame:
            mod = frame.f_globals.get("__name__", "")
            if (
                mod
                and not mod.startswith("core.nexus_framework")
                and not mod.startswith("inspect")
                and not mod.startswith("spotipy")
            ):
                caller_mod = mod
                break
            frame = frame.f_back

        # Core system and routes have host access
        if (
            not caller_mod
            or caller_mod.startswith("core.")
            or caller_mod.startswith("web.")
            or caller_mod.startswith("services.")
        ):
            return token

        # Extract the plugin ID from the caller's module path, ignoring 'beta'
        parts = [p for p in caller_mod.split(".") if p.lower() != "beta"]
        if parts and parts[0] == "plugins" and len(parts) >= 3:
            caller_plugin_id = f"{parts[1]}.{parts[2]}"
        elif parts and parts[0] == "plugins" and len(parts) == 2:
            caller_plugin_id = parts[1]
        else:
            caller_plugin_id = parts[-1] if parts else caller_mod

        account_owner_plugin_id = token.get("provider", "")

        # Determine if caller has privileged mode
        from core.settings import config_manager

        privileged = False
        try:
            import json

            manifest_path = config_manager.get_plugins_dir() / caller_plugin_id / "manifest.json"
            if manifest_path.exists():
                manifest = json.loads(manifest_path.read_text())
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

        # Redact lateral tokens
        redacted = dict(token)
        redacted["access_token"] = "REDACTED"
        redacted["refresh_token"] = "REDACTED"
        return redacted

    def save_token(
        self,
        account_id: int,
        access_token: str,
        refresh_token: str,
        expires_at: int,
        token_type: str = "Bearer",
        scope: str = None,
    ):
        from database.config_database import get_config_database

        get_config_database().save_account_token(account_id, access_token, refresh_token, token_type, expires_at, scope)

    def get_all(self):
        """Return all accounts associated with the calling plugin."""
        from database.config_database import get_config_database

        db = get_config_database()

        # Get plugin_id from stack inspection
        import inspect

        frame = inspect.currentframe()
        caller_mod = ""
        while frame:
            mod = frame.f_globals.get("__name__", "")
            if mod and not mod.startswith("core.nexus_framework"):
                caller_mod = mod
                break
            frame = frame.f_back

        plugin_id_str = ""
        if caller_mod.startswith("plugins."):
            parts = caller_mod.split(".")
            if len(parts) >= 3:
                plugin_id_str = f"{parts[1]}.{parts[2]}"
            else:
                plugin_id_str = parts[1]
        elif caller_mod.startswith("core.providers."):
            plugin_id_str = caller_mod.split(".")[2]
        else:
            plugin_id_str = caller_mod

        service_id = db.get_or_create_service_id(plugin_id_str)
        return db.get_accounts(service_id=service_id)

    def ensure_account(
        self,
        account_id: int = None,
        account_name: str = None,
        display_name: str = None,
        user_id: str = None,
    ) -> int:
        from database.config_database import get_config_database

        db = get_config_database()

        import inspect

        frame = inspect.currentframe()
        caller_mod = ""
        while frame:
            mod = frame.f_globals.get("__name__", "")
            if mod and not mod.startswith("core.nexus_framework"):
                caller_mod = mod
                break
            frame = frame.f_back

        plugin_id_str = ""
        if caller_mod.startswith("plugins."):
            parts = caller_mod.split(".")
            plugin_id_str = f"{parts[1]}.{parts[2]}" if len(parts) >= 3 else parts[1]
        elif caller_mod.startswith("core.providers."):
            plugin_id_str = caller_mod.split(".")[2]
        else:
            plugin_id_str = caller_mod

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
        account_name: str = None,
        display_name: str = None,
        user_id: str = None,
        account_email: str = None,
        is_active: bool = None,
        is_authenticated: bool = None,
        account_id: int = None,
    ) -> int:
        from database.config_database import get_config_database

        db = get_config_database()

        import inspect

        frame = inspect.currentframe()
        caller_mod = ""
        while frame:
            mod = frame.f_globals.get("__name__", "")
            if mod and not mod.startswith("core.nexus_framework"):
                caller_mod = mod
                break
            frame = frame.f_back

        plugin_id_str = ""
        if caller_mod.startswith("plugins."):
            parts = caller_mod.split(".")
            plugin_id_str = f"{parts[1]}.{parts[2]}" if len(parts) >= 3 else parts[1]
        elif caller_mod.startswith("core.providers."):
            plugin_id_str = caller_mod.split(".")[2]
        else:
            plugin_id_str = caller_mod

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

    def mark_account_authenticated(self, account_id: int):
        from database.config_database import get_config_database

        get_config_database().mark_account_authenticated(account_id)

    def mark_authenticated(self, account_id: int):
        self.mark_account_authenticated(account_id)

    def toggle_account_active(self, account_id: int, is_active: bool):
        from database.config_database import get_config_database

        get_config_database().toggle_account_active(account_id, is_active)

    def delete_account(self, account_id: int) -> bool:
        from database.config_database import get_config_database

        return get_config_database().delete_account(account_id)

    def update_account_name(self, account_id: int, new_name: str):
        from database.config_database import get_config_database

        get_config_database().update_account_name(account_id, new_name)


class _PluginsSDKFacade:
    def invoke(self, target_plugin_id: str, action: str, payload: dict):
        # Determine if target is enabled/exists
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
    def delete(self, file_path: str):
        from pathlib import Path

        from core.settings import config_manager

        # Check dry run mode
        if config_manager.get("system.dry_run", False):
            from core.tiered_logger import get_logger

            logger = get_logger("plugin_SDK")
            logger.info(f"DRY RUN: Intercepted deletion of {file_path}")
            return True

        # Physical soft delete
        try:
            p = Path(file_path).resolve()
            if not p.exists():
                return False

            # Find root mount. For simplicity, we assume music_dir
            music_dir_setting = config_manager.get("music_dir", "")
            if music_dir_setting:
                music_dir = Path(music_dir_setting).resolve()
                try:
                    if not p.is_relative_to(music_dir):
                        from core.tiered_logger import get_logger

                        logger = get_logger("plugin_SDK")
                        logger.error(f"Security violation: Attempted soft delete outside music_dir: {p}")
                        return False
                except AttributeError:
                    if not str(p).startswith(str(music_dir)):
                        from core.tiered_logger import get_logger

                        logger = get_logger("plugin_SDK")
                        logger.error(f"Security violation: Attempted soft delete outside music_dir: {p}")
                        return False
            else:
                music_dir = p.parent

            # Create hidden trash if needed
            trash_dir = music_dir / ".trash"
            trash_dir.mkdir(exist_ok=True)

            # Move instead of unlink
            dest = trash_dir / p.name
            from core.io_gatekeeper import Gatekeeper

            Gatekeeper.authorize_and_execute({"operation": "safe_move", "src": str(p), "dst": str(dest)})
            return True
        except Exception as e:
            from core.tiered_logger import get_logger

            logger = get_logger("plugin_SDK")
            logger.error(f"Failed to soft delete {file_path}: {e}")
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
        choices: list | None = None,
    ):
        """
        Register a custom quality profile configuration field.

        Args:
            name: Machine-readable name for the setting (key)
            label: Human-readable label for the UI
            input_type: Control type, must be 'boolean' or 'dropdown'
            default_value: Initial value for the setting
            choices: List of options for 'dropdown' type. Can be list of strings or list of {'label': str, 'value': Any}
        """
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

    def _check_allowlist(self, url: str):
        import json
        from urllib.parse import urlparse

        from core.settings import config_manager

        try:
            # Core always allowed
            if self.plugin_id == "core" or self.plugin_id.startswith("core."):
                return

            manifest_path = config_manager.get_plugins_dir() / self.plugin_id.replace("plugin.", "") / "manifest.json"
            if not manifest_path.exists():
                raise PermissionError(f"Plugin manifest not found for {self.plugin_id}")

            manifest = json.loads(manifest_path.read_text())
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
            domain = parsed.netloc.split(":")[0]  # Remove port

            for pattern in allowlist:
                if pattern.startswith("*."):
                    suffix = pattern[1:]  # ".example.com"
                    if domain.endswith(suffix) or domain == suffix[1:]:
                        return
                elif domain == pattern:
                    return

            raise PermissionError(f"Network access to '{domain}' blocked. Domain not in 'network_domains' allowlist.")
        except Exception as e:
            if isinstance(e, PermissionError):
                raise
            # Fail closed on manifest errors for security
            raise PermissionError(f"Security check failed for network request: {e}")

    def get(self, url: str, **kwargs):
        self._check_allowlist(url)
        return self._manager.get(url, **kwargs)

    def post(self, url: str, **kwargs):
        self._check_allowlist(url)
        return self._manager.post(url, **kwargs)

    def put(self, url: str, **kwargs):
        self._check_allowlist(url)
        return self._manager.put(url, **kwargs)

    def delete(self, url: str, **kwargs):
        self._check_allowlist(url)
        return self._manager.delete(url, **kwargs)


class _HealthCheckSDKFacade:
    def __init__(self, plugin_id: str | None = None):
        self.plugin_id = plugin_id

    def register(self, url_or_func, interval_seconds: float = 300.0):
        """
        Register a health check for the calling plugin.

        Args:
            url_or_func: Either a string URL to GET or a function returning HealthCheckResult.
            interval_seconds: How often to run the check (default: 300 seconds).
        """
        from core.health_check import HealthCheckResult, health_check_registry

        plugin_id = self.plugin_id or sdk._get_plugin_id()
        service_name = plugin_id.split(".")[-1].split("@")[0]

        if isinstance(url_or_func, str):
            url = url_or_func

            def url_health_check() -> HealthCheckResult:
                try:
                    from core.request_manager import RequestManager

                    manager = RequestManager(provider=plugin_id)
                    response = manager.get(url, timeout=10.0)
                    if 200 <= response.status_code < 400:
                        return HealthCheckResult(
                            service_name=service_name,
                            status="healthy",
                            message=f"Ping to {url} succeeded (HTTP {response.status_code})",
                        )
                    else:
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
                elif isinstance(res, bool):
                    return HealthCheckResult(
                        service_name=service_name,
                        status="healthy" if res else "unhealthy",
                        message="Service check succeeded" if res else "Service check failed",
                    )
                else:
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


def check_plugin_permission(plugin_id: str, scope: str) -> bool:
    """Check whether a plugin has been granted a particular permission scope.

    Supported scopes:
      - "privileged_mode"
      - "network_domains"
      - "database.read_library"
      - "database.mutate_aliases"
      - "database.mutate_attributes"
      - "wasm_fs_access"
    """
    if not plugin_id or plugin_id in ("core", "system") or plugin_id.startswith("core."):
        return True

    import json
    from core.settings import config_manager
    from database.config_database import get_config_database

    # 1. Check services table in config.db first
    try:
        db = get_config_database()
        conn = db._open_connection()
        try:
            c = conn.cursor()
            c.execute(
                "SELECT permissions, privileged_mode FROM services WHERE name=? OR plugin_id=?",
                (plugin_id, plugin_id),
            )
            row = c.fetchone()
            if row:
                if row[1]:  # privileged_mode flag enabled
                    return True
                if row[0]:
                    try:
                        perms = json.loads(row[0])
                        if isinstance(perms, dict):
                            if perms.get("privileged_mode"):
                                return True
                            if scope.startswith("database."):
                                db_key = scope.split(".", 1)[1]
                                db_perms = perms.get("database", {})
                                if isinstance(db_perms, dict) and db_perms.get(db_key):
                                    return True
                                if perms.get(scope) or perms.get(db_key):
                                    return True
                            elif scope in perms and perms[scope]:
                                return True
                    except Exception:
                        pass
        finally:
            conn.close()
    except Exception:
        pass

    # 2. Check physical manifest.json
    try:
        clean_name = plugin_id.replace("plugin.", "").replace(".", "/")
        manifest_path = config_manager.get_plugins_dir() / clean_name / "manifest.json"
        if not manifest_path.exists():
            clean_name = plugin_id.replace("plugin.", "")
            manifest_path = config_manager.get_plugins_dir() / clean_name / "manifest.json"

        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest.get("privileged") is True or manifest.get("privileged_mode") is True:
                return True
            perms = manifest.get("permissions", {})
            if isinstance(perms, dict):
                if perms.get("privileged_mode") is True:
                    return True
                if scope.startswith("database."):
                    db_key = scope.split(".", 1)[1]
                    db_perms = perms.get("database", {})
                    if isinstance(db_perms, dict) and db_perms.get(db_key) is True:
                        return True
                    if perms.get(scope) is True or perms.get(db_key) is True:
                        return True
                elif perms.get(scope):
                    return True
    except Exception:
        pass

    return False


class _DatabaseFacade:
    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id

    def check_permission(self, scope: str) -> bool:
        return check_plugin_permission(self.plugin_id, scope)

    def can_read_library(self) -> bool:
        return check_plugin_permission(self.plugin_id, "database.read_library")

    def can_mutate_aliases(self) -> bool:
        return check_plugin_permission(self.plugin_id, "database.mutate_aliases")

    def can_mutate_attributes(self) -> bool:
        return check_plugin_permission(self.plugin_id, "database.mutate_attributes")

    def get_plugin_session(self):
        from database.working_database import get_working_database

        working_db = get_working_database()
        provider_storage = working_db.get_provider_storage(self.plugin_id)
        return provider_storage.session_scope()


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
    import binascii

    try:
        from database.config_database import get_config_database

        db = get_config_database()
        int_id = db.get_service_id(plugin_name)
        if int_id:
            return int(int_id)
    except Exception:
        pass
    return binascii.crc32(plugin_name.lower().encode("utf-8")) & 0xFFFFFFFF


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
        proposals: list[dict | Any],
        sync_id: str | None = None,
        session: Any = None,
    ) -> int:
        if not check_plugin_permission(self._plugin_id_str, "database.mutate_aliases"):
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
        else:
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
    ) -> bool:
        if not check_plugin_permission(self._plugin_id_str, "database.mutate_attributes"):
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
        else:
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
    ) -> Any:
        if not (
            check_plugin_permission(self._plugin_id_str, "database.read_library")
            or check_plugin_permission(self._plugin_id_str, "database.mutate_attributes")
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
    ) -> bool:
        if not check_plugin_permission(self._plugin_id_str, "database.mutate_attributes"):
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
        else:
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
    ):
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


class _SDK:
    def __init__(self):
        # We don't know the plugin_id here yet as it's a global singleton,
        # but facade methods will verify caller.
        self._accounts = _AccountsSDKFacade()
        self.plugins = _PluginsSDKFacade()
        self.file = _FileSDKFacade()

    @property
    def health(self):
        return _HealthCheckSDKFacade(self._get_plugin_id())

    @property
    def config(self):
        return _ConfigFacade(self._get_plugin_id())

    @property
    def secrets(self):
        return _SecretsFacade(self._get_plugin_id())

    @property
    def storage(self):
        from services.storage_service import get_storage_service

        return get_storage_service()

    @property
    def db(self):
        return _DatabaseFacade(self._get_plugin_id())

    @property
    def aliases(self):
        return _AliasBroker(self._get_plugin_id())

    @property
    def attributes(self):
        return _AttributeBroker(self._get_plugin_id())

    @property
    def accounts(self):
        return self._accounts

    @property
    def quality(self):
        return _QualitySDKFacade(self._get_plugin_id())

    @property
    def models(self):
        return _PluginModelFacade()

    @property
    def webhooks(self):
        from core.plugins.sdk import _WebhooksSDKFacade

        return _WebhooksSDKFacade(self._get_plugin_id())

    @property
    def oauth(self):
        return _OAuthSDKFacade(self._get_plugin_id())

    def _get_plugin_id(self):
        import inspect

        frame = inspect.currentframe()
        caller_mod = ""
        fallback_mod = ""
        while frame:
            mod = frame.f_globals.get("__name__", "")
            if mod and not mod.startswith("core.nexus_framework"):
                if not mod.startswith("importlib") and not mod.startswith("_frozen_importlib"):
                    if mod.startswith("plugins."):
                        caller_mod = mod
                        break
                    if not fallback_mod:
                        fallback_mod = mod
            frame = frame.f_back

        if not caller_mod:
            caller_mod = fallback_mod or ""

        # Handle plugins.{author}.{plugin_name}
        if caller_mod.startswith("plugins."):
            parts = [p for p in caller_mod.split(".") if p.lower() != "beta"]
            # parts[0] is 'plugins', parts[1] is author, parts[2] is plugin_name
            if len(parts) >= 3:
                return f"{parts[1]}.{parts[2]}"
            return parts[1] if len(parts) > 1 else caller_mod  # fallback for single-part names

        # Handle core.providers.{name}
        if caller_mod.startswith("core.providers."):
            return caller_mod.split(".")[2]

        return caller_mod.replace("plugins.", "").replace("core.", "").split(".")[0]

    def get_database_connection(self, write_access: bool = False, require_library: bool = True):
        """
        Returns an SQLAlchemy engine connected to the calling plugin's isolated SQLite database.
        It also securely mounts the core databases (music_library.db, working.db) as attached databases.
        """
        import os

        from sqlalchemy import create_engine, event

        from core.settings import config_manager
        from database.config_database import get_config_database

        plugin_name = self._get_plugin_id()
        if require_library and not check_plugin_permission(plugin_name, "database.read_library"):
            raise PermissionError(f"Plugin '{plugin_name}' lacks 'permissions.database.read_library' permission.")
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
        def set_sqlite_pragma(dbapi_connection, connection_record):
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
    def network(self):
        return _NetworkSDKFacade(self._get_plugin_id())

    @property
    def dry_run(self) -> bool:
        from core.settings import config_manager

        return config_manager.get("system.dry_run", False)

    @property
    def jobs(self):
        return _JobsSDKFacade(self._get_plugin_id())

    def schedule(self, interval_minutes: int):
        def decorator(func):
            func._schedule_interval = interval_minutes
            return func

        return decorator


sdk = _SDK()


class WasmPluginWrapper:
    """Wrapper to safely execute .wasm plugins via wasmtime-py"""

    def __init__(self, wasm_path: str):
        self.wasm_path = wasm_path

        try:
            import wasmtime

            # Initialize rigid sandbox configuration
            config = wasmtime.Config()

            # Prevent malicious compilation or infinite loops
            config.consume_fuel = True
            config.epoch_interruption = True
            # Max memory usage for WASM is natively constrained by the module's memory limits,
            # but we disable unsafe features.
            config.wasm_simd = False
            config.wasm_multi_memory = False

            self.engine = wasmtime.Engine(config)

            # The WASI config acts as our syscall interceptor.
            # By providing a blank WasiConfig (no preopened directories, no network capabilities),
            # any WASI syscall attempting I/O will instantly trap and fail.
            self.wasi_config = wasmtime.WasiConfig()

            self.store = wasmtime.Store(self.engine)
            self.store.set_wasi(self.wasi_config)

            # Limit execution cycles (fuel) to prevent CPU DoS
            self.store.add_fuel(10_000_000)

            # Compile and validate the WASM binary
            self.module = wasmtime.Module.from_file(self.engine, self.wasm_path)

        except ImportError:
            # Non-fatal if wasmtime is not installed on the system
            pass
        except Exception as e:
            from core.tiered_logger import get_logger

            get_logger("wasm_sandbox").error(f"Failed to instantiate WASM runtime sandbox for {self.wasm_path}: {e}")


def _verify_caller(expected_plugin_id: str):
    import inspect

    # 1. Core Exemption via Physical Path
    for frame_info in inspect.stack():
        filename = frame_info.filename.replace("\\", "/")

        # If the execution frame originates from the trusted system directories or tests, grant absolute authority
        if "/app/core/" in filename or "/app/web/" in filename or "/tests/" in filename or "tests/" in filename:
            return  # The Core and tests are omnipotent; allow bypass

        # Once we hit a plugin boundary in the stack, we stop looking for a core bypass
        # and proceed to the standard plugin-to-plugin isolation checks below.
        if "/plugins/" in filename and ("/data/plugins/" in filename or "/app/plugins/" in filename):
            break

    frame = inspect.currentframe()
    caller_mod = ""
    while frame:
        mod = frame.f_globals.get("__name__", "")
        if mod and not mod.startswith("core.nexus_framework"):
            caller_mod = mod
            break
        frame = frame.f_back

    if not caller_mod:
        return
    # Bypass for core
    if caller_mod.startswith("core.") or caller_mod.startswith("providers."):
        return

    clean_expected = expected_plugin_id
    clean_expected = clean_expected.removeprefix("plugin.")
    if "@beta" in clean_expected:
        clean_expected = clean_expected.split("@")[0]
    norm_expected = clean_expected.lower()

    # Normalize caller_mod: split by '.' and filter out 'beta' (case-insensitive)
    parts = [p for p in caller_mod.split(".") if p.lower() != "beta"]

    # Check if this is a standard community plugin format (starts with plugins)
    if parts and parts[0] == "plugins" and len(parts) >= 3:
        caller_plugin_id = f"{parts[1]}.{parts[2]}"
        if caller_plugin_id.lower() == norm_expected:
            return

    # Validate community plugin format (fallback/compatibility)
    caller_id = parts[-1] if parts else ""
    base_expected = norm_expected.split(".")[-1]

    if caller_id.lower() != base_expected and caller_id.lower() != norm_expected:
        raise PermissionError(f"Namespace Isolation Violation: {caller_mod} attempted to access {expected_plugin_id}")


# KVS class removed


class StateKVS:
    def __init__(self, plugin_id: str):
        import inspect

        frame = inspect.currentframe()
        try:
            caller_module = inspect.getmodule(frame.f_back)
            if caller_module and not caller_module.__name__.startswith("core."):
                caller_name = caller_module.__name__
                parts = [p for p in caller_name.split(".") if p.lower() != "beta"]
                norm_caller = ".".join(parts).lower()
                clean_plugin_id = plugin_id
                clean_plugin_id = clean_plugin_id.removeprefix("plugin.")
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

    def get(self, key: str, default=None) -> str:
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

    def set(self, key: str, value: str) -> None:
        from database.working_database import get_working_database

        db = get_working_database()
        with db.session_scope() as session:
            from sqlalchemy.sql import text

            session.execute(
                text("INSERT OR REPLACE INTO plugin_state_kvs (plugin_id, key, value) VALUES (:ns, :k, :v)"),
                {"ns": self.plugin_id, "k": key, "v": value},
            )


class _PluginModelFacade:
    def __init__(self):
        # Lazy imports to avoid circular dependencies
        pass

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


class PluginBase(ABC):
    """
    Abstract base class for all music providers (Spotify, Tidal, Plex, Jellyfin, etc.).

    KEY PRINCIPLE: Providers are DUMB - they only convert their native format to EchosyncTrack.
    Core/Database/MatchingEngine are SMART - they process EchosyncTrack objects.

    All providers must implement these methods.

    Attributes:
        http: RequestManager instance for making HTTP requests with rate limiting and retries.
              MANDATORY: All HTTP requests must use this, not requests.get() directly.
    """

    name: str  # Unique provider name (e.g., 'spotify', 'tidal', 'plex')
    category: str = "provider"  # 'provider' (bundled, stable) or 'plugin' (community, unstable)
    supports_downloads: bool = False  # Indicates if provider supports downloads
    enabled: bool = True  # Flag to enable/disable provider without deleting files
    version: str = "Unknown"  # Version string for the provider/plugin
    metadata_quality_score: int = 50  # Quality score of metadata from this provider (0-100)

    # Set to True in providers that can resolve metadata by ISRC code.
    # Providers that set this to True MUST implement search_by_isrc().
    supports_isrc_lookup: bool = False

    # Typed capability class for registry detection
    capabilities: "ProviderCapabilities" = None

    # Default rate limit (requests per second). Can be overridden by subclasses.
    # None = unlimited/config driven.
    rate_limit: float = None

    # State key-value store facade explicitly mapped for the plugin
    kvs: StateKVS

    def __init__(self):
        """Initialize provider with HTTP client."""
        from core.request_manager import RateLimitConfig

        # Configure rate limiting if specified by subclass
        rate_config = None
        if self.rate_limit:
            rate_config = RateLimitConfig(requests_per_second=self.rate_limit)

        self.http = RequestManager(self.name, rate=rate_config)

        # Sandbox API facades for Plugin Architecture
        self._name = self.name
        self.sdk = sdk
        self.config = _ConfigFacade(self.name)
        self.secrets = _SecretsFacade(self.name)
        self.accounts = _AccountsSDKFacade()
        self.plugins = _PluginsSDKFacade()
        self.file = _FileSDKFacade()
        self.kvs = StateKVS(self.name)

        self.aliases = _AliasBroker(self.name)
        self.attributes = _AttributeBroker(self.name)
        self.db = _DatabaseFacade(self.name)
        self.models = _PluginModelFacade()

    async def _async_cancel_download(self, provider_id: str) -> bool:
        """Cancel an active or queued download transfer on the provider. Returns True if cancelled."""
        return False

    def get_database_connection(self, write_access: bool = False, require_library: bool = True):
        """
        Returns an SQLAlchemy engine connected to the plugin's isolated SQLite database.
        It also securely mounts the core databases (music_library.db, working.db) as attached databases.
        If write_access is explicitly granted, working.db will be attached in mode=rw.
        """
        import os

        from sqlalchemy import create_engine, event

        from core.settings import config_manager
        from database.config_database import get_config_database

        if require_library and not check_plugin_permission(self.name, "database.read_library"):
            raise PermissionError(f"Plugin '{self.name}' lacks 'permissions.database.read_library' permission.")

        # Resolve the strict plugin_id integer
        db = get_config_database()
        plugin_id_int = db.get_service_id(self.name)
        if not plugin_id_int:
            # Fallback to crc32 of name if not yet registered during boot
            import binascii

            plugin_id_int = binascii.crc32(self.name.lower().encode("utf-8")) & 0xFFFFFFFF

        channel = config_manager.get_plugin_channel(self.name) or "stable"
        db_file_name = f"{plugin_id_int}@beta.db" if channel == "beta" else f"{plugin_id_int}.db"

        # Ensure directory exists
        plugin_data_dir = "/data/plugins/data/"
        os.makedirs(plugin_data_dir, exist_ok=True)

        db_path = os.path.join(plugin_data_dir, db_file_name)
        engine = create_engine(f"sqlite:///{db_path}")

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()

            # Attach core databases
            try:
                cursor.execute("ATTACH DATABASE 'file:/data/music.db?mode=ro' AS music_lib")

                working_mode = "rw" if write_access else "ro"
                if working_mode not in ("ro", "rw", "rwc"):
                    raise ValueError(f"Invalid attach database mode: {working_mode}")
                cursor.execute(f"ATTACH DATABASE 'file:/data/working.db?mode={working_mode}' AS working")
            except Exception:
                pass
            cursor.close()

        return engine

    @property
    def logger(self):
        from core.tiered_logger import get_logger

        return get_logger(f"plugin.{self._name}")

    def get_oauth_redirect_uri(self) -> str:
        """
        Calculates the standardized redirect URI for this provider using the OAuth sidecar.
        Falls back to detecting primary local IP if not explicitly set in config.
        """
        from core.settings import config_manager

        # Determine the base host to use. Try server_url, then base_ip.
        host = config_manager.get("server_url")
        if not host:
            host = config_manager.get("base_ip")

        # If we still don't have a valid host, attempt dynamic IP detection
        if not host:
            import socket

            try:
                # Create a dummy socket connection to a public DNS to determine the primary interface IP
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                # Doesn't have to be reachable, just needs to route correctly
                s.connect(("8.8.8.8", 80))
                host = s.getsockname()[0]
                s.close()
            except Exception:
                host = "localhost"  # Last resort fallback

        # Ensure scheme is present (strip if mistakenly entered)
        if host.startswith("http://") or host.startswith("https://"):
            host = host.split("://")[-1]

        # Ensure no trailing slashes or paths
        host = host.split("/")[0]

        # Strip existing port if present
        host = host.split(":")[0]

        # The OAuth path for plugin providers uses the short plugin name segment.
        provider_name = self.name.split(".")[-1]

        # The OAuth sidecar runs securely on port 5001
        return f"https://{host}:5001/api/oauth/callback/plugins/{provider_name}"

    def handle_oauth_callback(self, args: dict[str, str]) -> Any:
        """
        Handle an OAuth callback from the sidecar.
        Providers must override this if they support OAuth.

        Args:
            args: The query parameters from the callback request.

        Returns:
            A Flask response (string, tuple, or redirect)
        """
        raise NotImplementedError("This provider does not implement handle_oauth_callback")

    def authenticate(self, **kwargs) -> bool:
        """Authenticate the provider (OAuth, API key, etc.)."""

    def search(
        self,
        query: str,
        type: str = "track",
        limit: int = 10,
        quality_profile: dict[str, Any] | None = None,
        includes: list[str] | None = None,
        excludes: list[str] | None = None,
        **kwargs,
    ) -> list[EchosyncTrack]:
        """Search for tracks. Must return EchosyncTrack objects.

        Args:
            quality_profile: Optional active quality profile for provider-side pre-filtering.
            includes: Optional list of terms that must all appear in a result's filename
                      (client-side text filter, AND semantics).
            excludes: Optional list of terms where any match causes the result to be dropped
                      (client-side text filter, OR semantics).
        """

    def get_track(self, track_id: str) -> EchosyncTrack | None:
        """Fetch a single track by ID. Must return EchosyncTrack object."""

    def get_metadata(self, mbid: str) -> dict[str, Any] | None:
        """Fetch full metadata for a recording/track."""
        return None

    def get_metadata_batch(self, mbids: list[str]) -> dict[str, dict[str, Any]]:
        """Fetch metadata for multiple recordings/tracks at once."""
        return {}

    def get_album(self, album_id: str) -> dict[str, Any] | None:
        """Fetch a single album by ID."""

    def get_artist(self, artist_id: str) -> dict[str, Any] | None:
        """Fetch a single artist by ID."""

    def get_user_playlists(self, user_id: str | None = None) -> list[dict[str, Any]]:
        """Fetch playlists for a user (if supported)."""

    def get_playlist_tracks(self, playlist_id: str) -> list[EchosyncTrack]:
        """Fetch tracks for a playlist. Must return List[EchosyncTrack]."""

    def add_tracks_to_playlist(self, playlist_id: str, provider_track_ids: list[str]) -> bool:
        """Add tracks to a playlist using provider-specific IDs (e.g., Plex ratingKeys, Spotify URIs).

        This is the RECOMMENDED method for adding tracks to playlists.
        Providers should override this to accept a list of string IDs instead of track objects.

        Args:
            playlist_id: The playlist ID in this provider's system
            provider_track_ids: List of provider-specific track IDs (e.g., ['1', '2', '3'] for Plex)

        Returns:
            True if successful, False otherwise
        """
        # Default implementation: not supported by this provider
        raise NotImplementedError(f"add_tracks_to_playlist not implemented for {self.name} provider")

    def remove_tracks_from_playlist(self, playlist_id: str, provider_track_ids: list[str]) -> bool:
        """Remove tracks from a playlist using provider-specific IDs.

        Args:
            playlist_id: The playlist ID in this provider's system
            provider_track_ids: List of provider-specific track IDs to remove

        Returns:
            True if successful, False otherwise
        """
        raise NotImplementedError(f"remove_tracks_from_playlist not implemented for {self.name} provider")

    def is_configured(self) -> bool:
        """Return True if provider is configured and ready to use."""

    def get_logo_url(self) -> str:
        """Return a URL or path to the provider's logo/icon."""

    def search_by_isrc(self, isrc: str) -> EchosyncTrack | None:
        """Look up a single track by its ISRC code.

        Providers that support ISRC lookup MUST set ``supports_isrc_lookup = True``
        and override this method.  The default implementation returns ``None`` so
        that existing providers that do not support this capability are unaffected.

        Args:
            isrc: A canonical 12-character ISRC (no hyphens, already validated).

        Returns:
            A ``EchosyncTrack`` populated with as much metadata as the provider
            can supply, or ``None`` if the ISRC was not found.
        """
        return None

    # ===== HELPER METHODS (Reusable by all providers) =====

    @staticmethod
    def create_echo_sync_track(
        title: str,
        artist: str,
        album_artist: str | None = None,
        album: str | None = None,
        duration_ms: int | None = None,
        isrc: str | None = None,
        musicbrainz_id: str | None = None,
        musicbrainz_album_id: str | None = None,
        year: int | None = None,
        track_number: int | None = None,
        disc_number: int | None = None,
        bitrate: int | None = None,
        sample_rate: int | None = None,
        bit_depth: int | None = None,
        file_size_bytes: int | None = None,
        added_at: datetime | None = None,
        file_format: str | None = None,
        file_path: str | None = None,
        fingerprint: str | None = None,
        quality_tags: list | None = None,
        provider_id: str | None = None,
        source: str | None = None,
        **extra_fields,
    ) -> EchosyncTrack:
        """
        Factory method to create EchosyncTrack with normalized metadata.

        This centralizes normalization logic used by all providers.
        Providers call this after extracting their native data.

        Args:
            title: Track title
            artist: Primary artist
            album: Album name
            duration_ms: Duration in milliseconds
            isrc: International Standard Recording Code
            musicbrainz_id: MusicBrainz Recording ID
            musicbrainz_album_id: MusicBrainz Album ID
            musicbrainz_artist_id: MusicBrainz Artist ID
            year: Release year
            track_number: Track position
            disc_number: Disc number
            bitrate: Bitrate in kbps
            file_format: File format (mp3, flac, etc.)
            source: Provider name (spotify, plex, etc.)
            **extra_fields: Additional EchosyncTrack fields

        Returns:
            EchosyncTrack with normalized metadata
        """

        # Defensive coercion helpers for provider-provided values
        def _coerce_to_str(val):
            if val is None:
                return None
            # If it's callable (some provider libs expose methods), call it
            if callable(val):
                try:
                    val = val()
                except Exception:
                    # Fallback to string representation
                    return str(val)
            # If it's a list (e.g., artist objects), try to join names
            if isinstance(val, (list, tuple)):
                parts = []
                for it in val:
                    if isinstance(it, str):
                        parts.append(it)
                    else:
                        # Try common attributes
                        parts.append(str(getattr(it, "name", getattr(it, "title", it))))
                return " ".join([p for p in parts if p])
            # If object has name/title attribute, prefer that
            if not isinstance(val, str):
                for attr in ("name", "title", "tag", "artist"):
                    if hasattr(val, attr):
                        try:
                            return str(getattr(val, attr))
                        except Exception:
                            continue
                return str(val)
            return val  # Already a string

        # Coerce inputs to strings where appropriate
        title_str = _coerce_to_str(title)
        artist_str = _coerce_to_str(artist)
        album_str = _coerce_to_str(album)

        # Extract edition info from title (remaster, live, remix, etc.)
        clean_title, edition = text_utils.extract_edition(title_str) if title_str else (None, None)

        # Normalize text fields (handle None inputs)
        normalized_title = text_utils.normalize_title(clean_title) if clean_title else None
        normalized_artist = text_utils.normalize_artist(artist_str) if artist_str else None
        normalized_album = text_utils.normalize_album(album_str) if album_str else None

        # Validate required fields after normalization
        if not normalized_title or not normalized_title.strip():
            from core.tiered_logger import get_logger

            get_logger("provider_base").debug(
                f"Skipping track creation - normalized title is empty (original: '{title_str}')"
            )
            return None

        if not normalized_artist or not normalized_artist.strip():
            artist_str = "Unknown Artist"
            normalized_artist = "unknown artist"

        # Parse duration
        parsed_duration = text_utils.parse_duration_to_ms(duration_ms)
        parsed_track_number = text_utils.parse_int_safe(track_number)
        parsed_disc_number = text_utils.parse_int_safe(disc_number)

        # Build identifiers list for ExternalIdentifiers table
        identifiers = []
        if provider_id and source:
            identifiers.append(
                {
                    "plugin_source": source,
                    "plugin_item_id": str(provider_id),
                    "raw_data": extra_fields or None,
                }
            )

        # Create EchosyncTrack
        track_kwargs = dict(
            raw_title=title_str,
            artist_name=artist_str,
            album_artist=album_artist,
            album_title=album_str,
            edition=edition,
            duration=parsed_duration,
            track_number=parsed_track_number,
            disc_number=parsed_disc_number,
            release_year=year,
            musicbrainz_id=musicbrainz_id,
            isrc=isrc,
            fingerprint=fingerprint,
            quality_tags=quality_tags,
            identifiers=identifiers,
        )

        media_list = extra_fields.pop("media", [])
        # Route ALL physical file telemetry through EchosyncMedia — never flat on EchosyncTrack.
        # If any physical file params were supplied, build an EchosyncMedia and append it.
        has_media_params = any(
            [
                file_path,
                file_format,
                bitrate,
                sample_rate,
                bit_depth,
                file_size_bytes,
                added_at,
            ]
        )
        if has_media_params:
            from core.db.echo_sync_track import EchosyncMedia

            media = EchosyncMedia(
                file_path=file_path,
                file_format=file_format,
                bitrate=bitrate,
                sample_rate=sample_rate,
                bit_depth=bit_depth,
                file_size_bytes=file_size_bytes,
                added_at=added_at,
            )
            media_list.append(media)

        if media_list:
            track_kwargs["media"] = media_list

        # Add any valid EchosyncTrack fields from extra_fields
        import dataclasses

        valid_fields = {f.name for f in dataclasses.fields(EchosyncTrack)}
        for k, v in extra_fields.items():
            if k in valid_fields:
                track_kwargs[k] = v

        return EchosyncTrack(**track_kwargs)

    @staticmethod
    def extract_guid_identifier(guid_id: str, identifier_type: str) -> str | None:
        """
        Extract specific identifier from Plex guid format.

        Args:
            guid_id: Full guid ID string
            identifier_type: Type to extract ('isrc', 'musicbrainz', 'acoustid')

        Returns:
            Clean identifier or None if not found
        """
        if not guid_id:
            return None

        target_prefix = identifier_type.lower()

        # Check if this guid contains our target type
        if target_prefix not in guid_id.lower():
            return None

        # Extract the ID part after ://
        clean_id = text_utils.clean_guid_id(guid_id)
        return clean_id


class SyncServiceProvider(PluginBase):
    """
    Interface for sync service providers (Spotify, Tidal).
    """

    def get_user_playlists(self, user_id: str | None = None) -> list[Any]:
        pass

    def get_playlist_tracks(self, playlist_id: str) -> list[Any]:
        pass


@dataclass(frozen=True)
class SearchCapabilities:
    tracks: bool = False
    artists: bool = False
    albums: bool = False
    playlists: bool = False


@dataclass(frozen=True)
class ProviderCapabilities:
    name: str
    supports_playlists: "PlaylistSupport"
    search: SearchCapabilities
    metadata: "MetadataRichness"
    supports_cover_art: bool = False
    supports_lyrics: bool = False
    supports_user_auth: bool = False
    supports_library_scan: bool = False
    supports_streaming: bool = False
    supports_downloads: bool = False
    supports_pre_filtering: bool = False
    max_concurrency: int = 3
    max_concurrent_searches: int = 3
    pre_filters: list = None
    playlist_algorithms: list = None  # List of algorithm IDs (e.g., ['spotify_mood'])
    supports_fingerprinting: bool = False  # Audio fingerprinting (AcoustID)
    fingerprint_algorithms: list = None
    supports_metadata_fetch: bool = False  # Metadata fetching (MusicBrainz)
    supports_isrc_lookup: bool = False
    supports_batching: bool = False  # Batch requests support
    supports_metrics: bool = False  # Supports ratings, listen counts, listening metrics

    def to_enum_list(self) -> list["Capability"]:
        """Adapter pattern to translate ProviderCapabilities dataclass back to legacy Enums."""
        from core.enums import Capability

        caps = []
        if getattr(self, "supports_fingerprinting", False):
            caps.append(Capability.RESOLVE_FINGERPRINT)
        if getattr(self, "supports_metadata_fetch", False):
            caps.append(Capability.FETCH_METADATA)
        if getattr(self, "supports_isrc_lookup", False):
            caps.append(Capability.FETCH_BY_ISRC)
        if getattr(self, "supports_pre_filtering", False):
            caps.append(Capability.CLIENT_PREFILTER)
        return caps


class PlaylistSupport(Enum):
    NONE = auto()
    READ = auto()
    READ_WRITE = auto()


class MetadataRichness(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


class DisabledProvider(PluginBase):
    """
    Placeholder class for disabled providers.
    Used to keep metadata in the registry without loading the actual module.
    """

    def __init__(self, name: str, version: str = "Unknown", category: str = "provider"):
        self.name = name
        self.version = version
        self.category = category
        self.is_disabled = True

    def is_configured(self) -> bool:
        return False


class Provider(Protocol):
    """
    Strict Contract that all future providers (Python or Rust) must adhere to.
    """

    def search_tracks(self, query: str) -> list[EchosyncTrack]:
        """
        Search for tracks based on a query string.
        """
        ...

    def get_track_by_id(self, item_id: str) -> EchosyncTrack | None:
        """
        Retrieve a specific track by its ID.
        """
        ...

    def get_artist_details(self, artist_id: str) -> dict[str, Any]:
        """
        Retrieve details about an artist.
        """
        ...


class DownloaderProvider(PluginBase):
    """
    Interface for downloader-style providers (Soulseek/slskd).
    """

    def search(self, query: str, limit: int = 10) -> list[Any]:
        pass

    def download(self, username: str, filename: str, file_size: int = 0) -> str | None:
        pass

    def get_download_status(self, download_id: str) -> dict[str, Any] | None:
        pass

    def cancel_download(self, download_id: str) -> bool:
        pass


class MediaServerProvider(PluginBase):
    """
    Base interface for media server providers (Plex, Jellyfin, Navidrome).
    Provides shared library scan polling logic; subclasses implement server-specific API calls.
    """

    def __init__(self):
        super().__init__()
        self._scan_state = {
            "scanning": False,
            "progress": 0.0,
            "eta_seconds": None,
            "error": None,
        }

    def get_library_stats(self) -> dict[str, int]:
        pass

    def get_all_artists(self) -> list[Any]:
        pass

    def get_all_albums(self) -> list[Any]:
        pass

    def get_all_tracks(self) -> list[Any]:
        pass

    def trigger_library_scan(self, path: str | None = None) -> bool:
        """
        Public method: Trigger a library refresh/scan on the media server.
        Calls server-specific _trigger_scan_api() implementation.
        """
        from core.tiered_logger import get_logger

        logger = get_logger("MediaServerProvider")
        try:
            success = self._trigger_scan_api(path)
            if success:
                self._scan_state["scanning"] = True
                self._scan_state["error"] = None
                logger.info(f"{self.name} library scan initiated")
            return success
        except Exception as e:
            logger.error(f"Error triggering {self.name} scan: {e}", exc_info=True)
            self._scan_state["error"] = str(e)
            return False

    def _trigger_scan_api(self, path: str | None = None) -> bool:
        """
        Server-specific: Trigger scan on the media server API.
        Returns: True if API call succeeded.
        """

    def get_scan_status(self) -> dict[str, Any]:
        """
        Public method: Get current scan status. Calls server-specific _get_scan_status_api().
        """
        from core.tiered_logger import get_logger

        logger = get_logger("MediaServerProvider")
        try:
            api_status = self._get_scan_status_api()
            # Merge API status into cached state
            self._scan_state.update(api_status)
            return self._scan_state.copy()
        except Exception as e:
            logger.error(f"Error getting {self.name} scan status: {e}", exc_info=True)
            self._scan_state["error"] = str(e)
            return self._scan_state.copy()

    def _get_scan_status_api(self) -> dict[str, Any]:
        """
        Server-specific: Poll scan status from the media server API.
        Returns: partial dict with 'scanning', 'progress', 'eta_seconds', 'error' keys.
        """

    def get_content_changes_since(self, last_update: Any | None = None) -> Any:
        """
        Get content changes since the last update timestamp.
        Enables incremental syncs by detecting only new/modified content.
        """


def provision_plugin_table(plugin_id: int, table_schema: str) -> None:
    """Deprecated: Plugins must provision their own isolated SQLite databases."""
    raise NotImplementedError(
        "provision_plugin_table is deprecated. Use raw sqlite3/sqlalchemy to a local plugin .db file instead."
    )
