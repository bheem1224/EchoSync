"""Backward-compatible re-export shim for core.nexus_framework.sdk."""

from __future__ import annotations

from core.nexus_framework.sdk import (
    _REGISTERED_WEBHOOKS,
    _SDK,
    _WEBHOOK_HANDLERS,
    _WebhooksSDKFacade,
    compute_plugin_crc32,
    dispatch_webhook,
    get_base_url,
    hookimpl,
    lookup_registered_endpoint,
    register_webhook_handler,
    sdk,
    verify_file_signature,
)
from core.nexus_framework.sdk import *  # noqa: F403

__all__ = [
    "_REGISTERED_WEBHOOKS",
    "_SDK",
    "_WEBHOOK_HANDLERS",
    "_WebhooksSDKFacade",
    "compute_plugin_crc32",
    "dispatch_webhook",
    "get_base_url",
    "hookimpl",
    "lookup_registered_endpoint",
    "register_webhook_handler",
    "sdk",
    "verify_file_signature",
]
