import asyncio
from typing import Callable, Dict, List, Any

class HookManager:
    """
    Middleware filter registry for plugins.
    Allows plugins to register hooks that intercept and modify data.
    """
    def __init__(self):
        # hook_name -> list of callback functions
        self._filters: Dict[str, List[Callable]] = {}

    def add_filter(self, hook_name: str, callback: Callable) -> None:
        """Register a callback for a specific hook."""
        if hook_name not in self._filters:
            self._filters[hook_name] = []
        self._filters[hook_name].append(callback)

    def apply_filters(self, hook_name: str, default_value: Any, *args, **kwargs) -> Any:
        """
        Pass a value through all registered filters for a hook.
        Each callback must accept the value (and optionally args) and return the modified value.
        """
        value = default_value
        if hook_name in self._filters:
            for callback in self._filters[hook_name]:
                try:
                    value = callback(value, *args, **kwargs)
                    if asyncio.iscoroutine(value):
                        raise TypeError('Async hooks are not supported in apply_filters')
                except Exception as e:
                    import logging
                    logging.getLogger("hook_manager").error(
                        f"Error applying filter for hook '{hook_name}': {e}", exc_info=True
                    )
        return value

# Global singleton
hook_manager = HookManager()
