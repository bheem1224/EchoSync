import asyncio
from collections.abc import Callable
from typing import Any


class HookManager:
    """
    Middleware filter registry for plugins.
    Allows plugins to register hooks that intercept and modify data.
    """

    def __init__(self):
        # hook_name -> list of callback functions
        self._filters: dict[str, list[Callable]] = {}
        import threading

        self._local = threading.local()
        self.MAX_DEPTH = 10

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
        if not hasattr(self._local, "depths"):
            self._local.depths = {}

        current_depth = self._local.depths.get(hook_name, 0)
        if current_depth >= self.MAX_DEPTH:
            return default_value

        self._local.depths[hook_name] = current_depth + 1

        try:
            value = default_value
            if hook_name in self._filters:
                for callback in self._filters[hook_name]:
                    import logging

                    prev_value = value
                    try:
                        value = callback(value, *args, **kwargs)
                        if asyncio.iscoroutine(value):
                            # H1: close the coroutine to silence ResourceWarning, restore
                            # the last known-good value, and log so the plugin author is
                            # immediately informed.  The chain continues uninterrupted.
                            value.close()
                            value = prev_value
                            logging.getLogger("hook_manager").error(
                                f"Async hook rejected for '{hook_name}': "
                                f"callback '{callback.__name__}' returned a coroutine. "
                                "Hooks must be synchronous plain functions."
                            )
                    except Exception:
                        value = prev_value
                        logging.getLogger("hook_manager").exception(
                            f"Error applying filter for hook '{hook_name}'"
                        )
        finally:
            self._local.depths[hook_name] -= 1
        return value

    def register_hook(self, hook_name: str, callback: Callable) -> None:
        """Register a callback for a specific hook (alias for add_filter)."""
        self.add_filter(hook_name, callback)

    def trigger(self, hook_name: str, *args: Any, **kwargs: Any) -> list[Any]:
        """Trigger a hook (alias for execute_hook)."""
        return self.execute_hook(hook_name, *args, **kwargs)

    def execute_hook(self, hook_name: str, *args: Any, **kwargs: Any) -> list[Any]:
        """
        Execute all callbacks registered for a hook and collect results into a flat list.
        Each callback may return an item, a list of items, or None.
        Exceptions raised by individual callbacks are caught, logged, and dropped to prevent
        pipeline abort.
        """
        results: list[Any] = []
        if hook_name in self._filters:
            import logging

            for callback in self._filters[hook_name]:
                try:
                    res = callback(*args, **kwargs)
                    if asyncio.iscoroutine(res):
                        res.close()
                        logging.getLogger("hook_manager").error(
                            f"Async hook rejected for '{hook_name}': "
                            f"callback '{getattr(callback, '__name__', str(callback))}' returned a coroutine. "
                            "Hooks must be synchronous plain functions."
                        )
                        continue
                    if res is None:
                        continue
                    if isinstance(res, list):
                        results.extend(res)
                    else:
                        results.append(res)
                except Exception:
                    import logging

                    logging.getLogger("hook_manager").exception(
                        f"Error executing hook '{hook_name}' in callback '{getattr(callback, '__name__', str(callback))}'"
                    )
        return results


# Global singleton
hook_manager = HookManager()
