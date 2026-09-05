"""
Core Plugins SDK package.
"""

from core.plugins.sdk import _WebhooksSDKFacade, dispatch_webhook, hookimpl, sdk

__all__ = ["_WebhooksSDKFacade", "dispatch_webhook", "hookimpl", "sdk"]
