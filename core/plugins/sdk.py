"""
EchoSync Core Plugin SDK.

Provides standardized Plugin SDK interfaces, webhook gateway registration,
deterministic CRC32 / namespace resolution, and @hookimpl decorators.
"""

from __future__ import annotations

import asyncio
import inspect
import secrets
import zlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

from core.event_bus import event_bus
from core.hook_manager import hook_manager
from core.nexus_framework.plugin_SDK import _SDK
from core.nexus_framework.plugin_SDK import sdk as _base_sdk
from core.tiered_logger import get_logger
from time_utils import utc_now

logger = get_logger("plugin_sdk")

# Global in-memory cache for fast ingress lookup: (crc32_id, slug) -> endpoint_dict
_REGISTERED_WEBHOOKS: dict[tuple[int, str], dict[str, Any]] = {}
# Global registry for plugin hook listeners: crc32_id -> list of callbacks
_WEBHOOK_HANDLERS: dict[int, list[Callable[[str, dict[str, Any]], Any]]] = {}


def hookimpl(func: Callable | None = None, **kwargs: Any) -> Callable:
    """Decorator marking a method or function as a plugin hook implementation."""

    def decorator(fn: Callable) -> Callable:
        fn._is_hookimpl = True
        fn._hookimpl_opts = kwargs
        return fn

    if func is not None:
        return decorator(func)
    return decorator


def compute_plugin_crc32(namespace: str) -> int:
    """Compute deterministic CRC32 32-bit integer for a fully qualified namespace."""
    clean_ns = namespace.strip()
    return zlib.crc32(clean_ns.encode("utf-8")) & 0xFFFFFFFF


def get_base_url() -> str:
    """
    Dynamically resolve external base URL for webhooks.
    Priority:
    1. config.db system_settings: 'server.base_url' or 'system.base_url'
    2. config_manager: 'server.base_url' or 'base_url'
    3. Scheme detection: 'https' if ssl_cert_file and ssl_key_file are configured and exist, else 'http'
    4. Fallback host/port: http://localhost:5000
    """
    try:
        from database.config_database import get_config_database

        db = get_config_database()
        with db._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                "SELECT key, value FROM system_settings WHERE key IN ('server.base_url', 'system.base_url')"
            )
            rows = dict(c.fetchall())
            if rows.get("server.base_url"):
                return str(rows["server.base_url"]).rstrip("/")
            if rows.get("system.base_url"):
                return str(rows["system.base_url"]).rstrip("/")
    except Exception:
        pass

    try:
        from core.settings import config_manager

        explicit_url = config_manager.get("server.base_url") or config_manager.get(
            "base_url"
        )
        if explicit_url:
            return str(explicit_url).rstrip("/")

        cert_file = config_manager.get("ssl_cert_file")
        key_file = config_manager.get("ssl_key_file")
        scheme = (
            "https"
            if cert_file
            and key_file
            and Path(cert_file).exists()
            and Path(key_file).exists()
            else "http"
        )

        host = (
            config_manager.get("server.host")
            or config_manager.get("host")
            or "localhost"
        )
        if host in ("0.0.0.0", "::"):
            host = "localhost"
        port = config_manager.get("server.port") or config_manager.get("port") or 5000
        return f"{scheme}://{host}:{port}"
    except Exception:
        return "http://localhost:5000"


class _WebhooksSDKFacade:
    """SDK Facade for registering and managing plugin webhooks."""

    def __init__(self, caller_namespace: str | None = None):
        self._explicit_namespace = caller_namespace

    def _resolve_namespace_and_id(self) -> tuple[str, int]:
        """
        Inspect call stack to resolve calling plugin's fully qualified namespace
        and calculate its authoritative CRC32 integer ID.
        """
        if self._explicit_namespace and "." in self._explicit_namespace:
            ns = self._explicit_namespace
            return ns, compute_plugin_crc32(ns)

        # Inspect call stack frames
        frame = inspect.currentframe()
        caller_mod = ""
        while frame:
            mod = frame.f_globals.get("__name__", "")
            if (
                mod
                and not mod.startswith("core.plugins")
                and not mod.startswith("core.nexus_framework")
            ):
                if mod.startswith("plugins."):
                    caller_mod = mod
                    break
            frame = frame.f_back

        if caller_mod.startswith("plugins."):
            parts = [p for p in caller_mod.split(".") if p.lower() != "beta"]
            # parts: ['plugins', 'EchoSync', 'slskd', ...]
            if len(parts) >= 3:
                ns = f"{parts[1]}.{parts[2]}"
                return ns, compute_plugin_crc32(ns)
            elif len(parts) == 2:
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
    ) -> dict[str, Any]:
        """
        Register a webhook endpoint for the calling plugin.

        Args:
            slug: Subpath slug (e.g. 'download_status').
            secret: Optional secret token. If omitted and auth enabled, generates 'sk_live_...'.
            allow_unauthenticated: If True, allows unauthenticated calls.
            allowed_subnets: Optional CIDR subnets allowed to access the endpoint.
            namespace: Optional fully qualified namespace override.

        Returns:
            Dict containing registration metadata, full callback URL, and sample YAML.
        """
        if namespace:
            ns = namespace.strip()
            crc32_id = compute_plugin_crc32(ns)
        else:
            ns, crc32_id = self._resolve_namespace_and_id()

        if not allow_unauthenticated and not secret:
            secret = f"sk_live_{secrets.token_hex(16)}"

        base_url = get_base_url()
        canonical_url = f"{base_url}/api/v1/webhooks/{ns}/{slug}"
        call_url_with_secret = (
            f"{canonical_url}?secret={secret}" if secret else canonical_url
        )

        yaml_template = (
            f"integration:\n"
            f"  webhooks:\n"
            f"    echosync_downloads:\n"
            f"      on:\n"
            f"        - DownloadFileComplete\n"
            f"        - DownloadFileFailed\n"
            f"      call:\n"
            f'        url: "{call_url_with_secret}"\n'
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

        # 1. Update in-memory registry
        _REGISTERED_WEBHOOKS[(crc32_id, slug)] = registration_data

        # 2. Persist in config.db under service_config
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
                db.set_service_config(
                    service_id, config_key, registration_data, is_sensitive=True
                )
                logger.info(
                    "Registered webhook endpoint '%s' for %s (CRC32: %d)",
                    slug,
                    ns,
                    crc32_id,
                )
        except Exception as e:
            logger.warning("Could not persist webhook endpoint in config.db: %s", e)

        return registration_data

    def get_endpoint(
        self, slug: str, namespace: str | None = None
    ) -> dict[str, Any] | None:
        """Retrieve registered endpoint metadata by slug."""
        if namespace:
            ns = namespace.strip()
            crc32_id = compute_plugin_crc32(ns)
        else:
            ns, crc32_id = self._resolve_namespace_and_id()
        # Check in-memory first
        if (crc32_id, slug) in _REGISTERED_WEBHOOKS:
            return _REGISTERED_WEBHOOKS[(crc32_id, slug)]

        # Check config.db
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

    def list_endpoints(self) -> list[dict[str, Any]]:
        """List all endpoints registered for this plugin."""
        namespace, crc32_id = self._resolve_namespace_and_id()
        results = [
            ep for (p_id, _), ep in _REGISTERED_WEBHOOKS.items() if p_id == crc32_id
        ]
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
    # 1. Check in-memory registry
    if (plugin_id, slug) in _REGISTERED_WEBHOOKS:
        return _REGISTERED_WEBHOOKS[(plugin_id, slug)]

    # 2. Check config.db
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
        logger.warning(
            "Error looking up endpoint for plugin %d, slug '%s': %s", plugin_id, slug, e
        )
    return None


def register_webhook_handler(
    plugin_id: int, handler: Callable[[str, dict[str, Any]], Any]
) -> None:
    """Register a callable hook handler for webhooks dispatched to a plugin_id."""
    if plugin_id not in _WEBHOOK_HANDLERS:
        _WEBHOOK_HANDLERS[plugin_id] = []
    _WEBHOOK_HANDLERS[plugin_id].append(handler)


async def dispatch_webhook(plugin_id: int, slug: str, payload: dict[str, Any]) -> None:
    """
    Dispatch an inbound webhook payload to the target plugin's @hookimpl on_webhook_received.
    """
    from core.nexus_framework.plugin_loader import PluginRegistry

    # 1. Dispatch to registered functional handlers
    if plugin_id in _WEBHOOK_HANDLERS:
        for handler in _WEBHOOK_HANDLERS[plugin_id]:
            try:
                res = handler(slug, payload)
                if asyncio.iscoroutine(res):
                    await res
            except Exception as e:
                logger.error(
                    "Error in webhook handler for plugin %d: %s",
                    plugin_id,
                    e,
                    exc_info=True,
                )

    # 2. Dispatch to PluginRegistry provider class / instance
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
    except Exception as e:
        logger.error(
            "Error invoking on_webhook_received on plugin %d: %s",
            plugin_id,
            e,
            exc_info=True,
        )

    # 3. Publish to EventBus
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
        logger.warning("Failed to publish WEBHOOK_RECEIVED to event_bus: %s", e)

    # 4. Trigger hook_manager
    try:
        hook_manager.trigger(
            "ON_WEBHOOK_RECEIVED", plugin_id=plugin_id, slug=slug, payload=payload
        )
    except Exception as e:
        logger.warning("Failed to trigger ON_WEBHOOK_RECEIVED hook: %s", e)


# Attach webhooks property dynamically to _SDK if not present
if not hasattr(_SDK, "webhooks"):

    @property
    def _webhooks_prop(self: _SDK) -> _WebhooksSDKFacade:
        return _WebhooksSDKFacade(self._get_plugin_id())

    _SDK.webhooks = _webhooks_prop  # type: ignore[attr-defined]

sdk = _base_sdk
