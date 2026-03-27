"""core.plugins — SoulSync plugin platform sub-package.

Exposes the two main platform objects so callers can write::

    from core.plugins import hook_manager, PluginScanner
    from core.plugins import SecurityViolationError
"""

from core.plugins.hook_manager import HookManager, hook_manager
from core.plugins.security import PluginScanner, SecurityViolationError, BANNED_IMPORTS

__all__ = [
    "HookManager",
    "hook_manager",
    "PluginScanner",
    "SecurityViolationError",
    "BANNED_IMPORTS",
]
