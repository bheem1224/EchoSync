"""
HookManager — filter pipeline and service override registry for the plugin platform.

Two mechanisms are provided:

Filter Hooks (WordPress/WooCommerce style)
------------------------------------------
Plugins register callables against a named hook.  When core code calls
``apply_filters(hook_name, value)``, *value* passes through every registered
callable (in priority order) and each callable may transform it.  This lets
plugins intercept and modify data anywhere in the pipeline without forking
core code.

Example — a plugin that uppercases every track title::

    from core.plugins import hook_manager

    def my_title_filter(value, **kwargs):
        return value.upper()

    hook_manager.add_filter("normalize_title", my_title_filter, priority=20)

Core code then calls::

    title = hook_manager.apply_filters("normalize_title", raw_title)

Service Overrides
-----------------
A plugin may replace an entire core engine object by registering a
fully-initialised replacement instance under a well-known service name::

    hook_manager.register_override("SuggestionEngine", my_custom_engine)

Core code resolves the engine at use-time::

    engine = hook_manager.get_override("SuggestionEngine") or DefaultSuggestionEngine()

Only ONE override per service name is allowed; attempting to register a
second raises ``RuntimeError`` so plugin conflicts surface immediately.

Thread Safety
-------------
All public methods are safe to call from multiple threads.  Internal state
is protected by per-collection ``threading.Lock`` objects so add_filter and
apply_filters can run concurrently with each other.
"""

import threading
from typing import Any, Callable, Optional

from core.tiered_logger import get_logger

logger = get_logger("hook_manager")


class HookManager:
    """
    Process-wide singleton that manages plugin filter hooks and service overrides.

    Obtain the singleton via :func:`get_instance` or use the module-level
    :data:`hook_manager` alias.
    """

    _instance: Optional["HookManager"] = None
    _class_lock: threading.Lock = threading.Lock()

    def __init__(self) -> None:
        # {hook_name: [(priority, callable), ...]}  — kept sorted by priority
        self._filters: dict[str, list[tuple[int, Callable[..., Any]]]] = {}
        self._filters_lock = threading.Lock()

        # {service_name: instance}
        self._overrides: dict[str, Any] = {}
        self._overrides_lock = threading.Lock()

    # ── Singleton factory ──────────────────────────────────────────────────

    @classmethod
    def get_instance(cls) -> "HookManager":
        """Return the process-wide HookManager (double-checked locking)."""
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Filter hooks ───────────────────────────────────────────────────────

    def add_filter(
        self,
        hook_name: str,
        fn: Callable[..., Any],
        priority: int = 10,
    ) -> None:
        """
        Register *fn* as a filter for *hook_name*.

        Filters are executed from **lowest** priority value to highest (priority 1
        runs before priority 10, which runs before priority 100).  Multiple
        callables at the same priority are executed in registration order
        (stable sort).

        Args:
            hook_name:  Logical name of the filter pipeline, e.g.
                        ``"normalize_title"`` or ``"rewrite_artwork_url"``.
            fn:         Callable with signature ``(value: Any, **kwargs) -> Any``
                        that receives the current value and must return the
                        (possibly modified) value.
            priority:   Execution order; lower numbers run first (default: 10).

        Raises:
            TypeError: If *fn* is not callable.
        """
        if not callable(fn):
            raise TypeError(f"add_filter: {fn!r} is not callable")

        with self._filters_lock:
            bucket = self._filters.setdefault(hook_name, [])
            bucket.append((priority, fn))
            # Stable sort preserves registration order for ties.
            bucket.sort(key=lambda t: t[0])

        logger.debug(
            "add_filter: registered '%s' on hook '%s' (priority %d)",
            getattr(fn, "__qualname__", repr(fn)),
            hook_name,
            priority,
        )

    def remove_filter(
        self,
        hook_name: str,
        fn: Callable[..., Any],
        priority: int = 10,
    ) -> bool:
        """
        Remove a previously registered filter.

        Matches by both *fn* identity and *priority*.  Returns ``True`` if the
        filter was found and removed.
        """
        with self._filters_lock:
            bucket = self._filters.get(hook_name, [])
            target = (priority, fn)
            if target in bucket:
                bucket.remove(target)
                if not bucket:
                    del self._filters[hook_name]
                logger.debug(
                    "remove_filter: removed '%s' from hook '%s'",
                    getattr(fn, "__qualname__", repr(fn)),
                    hook_name,
                )
                return True
        return False

    def apply_filters(self, hook_name: str, value: Any, **kwargs: Any) -> Any:
        """
        Pass *value* through every filter registered under *hook_name*.

        Each callable receives the **current** value plus any **kwargs and
        must return the (possibly transformed) value.

        If a filter raises an exception it is logged and **skipped** — the
        pipeline continues with the unmodified value from that step so one
        misbehaving plugin cannot prevent the rest of the pipeline from
        running.

        If no filters are registered for *hook_name* the original *value* is
        returned unchanged.

        Args:
            hook_name:  The filter pipeline to invoke.
            value:      The initial value to pass through the pipeline.
            **kwargs:   Extra context forwarded verbatim to every filter
                        callable (e.g. ``provider="spotify"``).

        Returns:
            The value after all filters have been applied.
        """
        # Copy the bucket under the lock so callers can safely call
        # add_filter() from within a filter callback without deadlocking.
        with self._filters_lock:
            pipeline = list(self._filters.get(hook_name, []))

        for _priority, fn in pipeline:
            try:
                value = fn(value, **kwargs)
            except Exception as exc:
                logger.error(
                    "apply_filters: filter '%s' on hook '%s' raised %s — skipping",
                    getattr(fn, "__qualname__", repr(fn)),
                    hook_name,
                    exc,
                    exc_info=True,
                )

        return value

    # ── Service overrides ──────────────────────────────────────────────────

    def register_override(self, service_name: str, instance: Any) -> None:
        """
        Register *instance* as the canonical implementation of *service_name*.

        Only the **first** call for a given service name succeeds.  A second
        call (from a different plugin) raises ``RuntimeError`` to surface the
        conflict immediately rather than silently clobbering an existing
        override.

        Core systems resolve overrides at use-time::

            engine = hook_manager.get_override("SuggestionEngine") or Default()

        Args:
            service_name:  Well-known service identifier, e.g.
                           ``"SuggestionEngine"`` or ``"MatchingEngine"``.
            instance:      Fully-initialised replacement object.

        Raises:
            RuntimeError:  If *service_name* is already overridden.
        """
        with self._overrides_lock:
            if service_name in self._overrides:
                existing = self._overrides[service_name]
                raise RuntimeError(
                    f"register_override: '{service_name}' is already overridden by "
                    f"'{type(existing).__qualname__}'. "
                    "Only one plugin may override a service at a time."
                )
            self._overrides[service_name] = instance

        logger.info(
            "register_override: '%s' is now handled by '%s'",
            service_name,
            type(instance).__qualname__,
        )

    def get_override(self, service_name: str) -> Optional[Any]:
        """
        Return the registered override for *service_name*, or ``None``.

        Core systems call this at each resolution point::

            engine = hook_manager.get_override("SuggestionEngine") or default

        Returns ``None`` when no plugin has claimed *service_name*, which
        signals the caller to instantiate its own default implementation.
        """
        with self._overrides_lock:
            return self._overrides.get(service_name)

    # ── Introspection (useful for admin API / testing) ─────────────────────

    def registered_hooks(self) -> list[str]:
        """Return a sorted list of hook names that have at least one filter."""
        with self._filters_lock:
            return sorted(self._filters)

    def registered_overrides(self) -> list[str]:
        """Return a sorted list of service names that currently have an override."""
        with self._overrides_lock:
            return sorted(self._overrides)

    def filter_count(self, hook_name: str) -> int:
        """Return the number of filters registered for *hook_name*."""
        with self._filters_lock:
            return len(self._filters.get(hook_name, []))


# ---------------------------------------------------------------------------
# Module-level singleton — preferred accessor for all core and plugin code
# ---------------------------------------------------------------------------

#: The process-wide HookManager instance.
#:
#: Import and use directly::
#:
#:     from core.plugins.hook_manager import hook_manager
#:
#:     hook_manager.add_filter("normalize_title", my_fn)
#:     title = hook_manager.apply_filters("normalize_title", raw_title)
hook_manager: HookManager = HookManager.get_instance()
