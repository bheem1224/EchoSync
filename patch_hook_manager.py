import re

with open('core/hook_manager.py', 'r') as f:
    content = f.read()

# Add to __init__
init_patch = """    def __init__(self):
        # hook_name -> list of callback functions
        self._filters: Dict[str, List[Callable]] = {}
        import threading
        self._local = threading.local()
        self.MAX_DEPTH = 10"""

content = content.replace("    def __init__(self):\n        # hook_name -> list of callback functions\n        self._filters: Dict[str, List[Callable]] = {}", init_patch)

# Add to apply_filters
apply_filters_orig = """    def apply_filters(self, hook_name: str, default_value: Any, *args, **kwargs) -> Any:
        \"\"\"
        Pass a value through all registered filters for a hook.
        Each callback must accept the value (and optionally args) and return the modified value.
        \"\"\"
        value = default_value
        if hook_name in self._filters:
            for callback in self._filters[hook_name]:
                import logging"""

apply_filters_patch = """    def apply_filters(self, hook_name: str, default_value: Any, *args, **kwargs) -> Any:
        \"\"\"
        Pass a value through all registered filters for a hook.
        Each callback must accept the value (and optionally args) and return the modified value.
        \"\"\"
        if not hasattr(self._local, 'depths'):
            self._local.depths = {}

        current_depth = self._local.depths.get(hook_name, 0)
        if current_depth >= self.MAX_DEPTH:
            return default_value

        self._local.depths[hook_name] = current_depth + 1

        try:
            value = default_value
            if hook_name in self._filters:
                for callback in self._filters[hook_name]:
                    import logging"""

content = content.replace(apply_filters_orig, apply_filters_patch)

# Now fix the finally block
# The original has:
#                 except Exception as e:
#                     value = prev_value
#                     logging.getLogger("hook_manager").error(
#                         f"Error applying filter for hook '{hook_name}': {e}", exc_info=True
#                     )
#         return value

content = content.replace("                    )\n        return value", "                    )\n        finally:\n            self._local.depths[hook_name] -= 1\n        return value")

with open('core/hook_manager.py', 'w') as f:
    f.write(content)
