"""
Core Plugins SDK package.
"""

from core.plugins.sdk import sdk, hookimpl, _WebhooksSDKFacade, dispatch_webhook

__all__ = ["sdk", "hookimpl", "_WebhooksSDKFacade", "dispatch_webhook"]

