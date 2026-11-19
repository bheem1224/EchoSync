"""Capability-gated HookManager with explicit PipelineContext stage tracking."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
import logging
import threading
from typing import Any

from core.nexus_framework.sdk.context import (
    ACTIVE_PIPELINE_HOOK_CAPABILITIES,
    RETIRED_UNSUBSCRIBED_HOOK_STAGES,
    PipelineContext,
    PipelineStage,
    get_current_pipeline_context,
)
from core.security.rbac import Principal, get_current_principal


class HookManager:
    """
    Capability-gated middleware filter registry for plugins, paired with
    explicit PipelineContext stage tracking for the 16 retired lifecycle hooks.
    """

    def __init__(self, pipeline_context: PipelineContext | None = None):
        # hook_name -> list of callback functions (kept as plain list[Callable] for unit test contract)
        self._filters: dict[str, list[Callable[..., Any]]] = {}
        self._filter_capabilities: dict[tuple[str, int], str] = {}
        self._local = threading.local()
        self.MAX_DEPTH = 10
        self.active_hook_capabilities: dict[str, str] = dict(ACTIVE_PIPELINE_HOOK_CAPABILITIES)
        self.retired_hook_stages: dict[str, str] = dict(RETIRED_UNSUBSCRIBED_HOOK_STAGES)
        self.pipeline_context: PipelineContext = pipeline_context or PipelineContext(pipeline_name="hook_manager")

    def required_capability_for(self, hook_name: str, explicit_capability: str | None = None) -> str | None:
        """Return the required capability (`pipeline:enrich` or `pipeline:intercept`) for a hook, if any."""
        if explicit_capability:
            return explicit_capability.strip()
        return self.active_hook_capabilities.get(hook_name)

    def _resolve_context(self, explicit_ctx: PipelineContext | None = None) -> PipelineContext:
        if isinstance(explicit_ctx, PipelineContext):
            return explicit_ctx
        ambient = get_current_pipeline_context()
        if ambient is not None:
            return ambient
        return self.pipeline_context

    def record_stage(
        self,
        stage_or_hook: str | PipelineStage,
        *,
        status: str = "completed",
        pipeline_context: PipelineContext | None = None,
        **metadata: Any,
    ) -> None:
        """Record a pipeline stage transition on the active PipelineContext."""
        ctx = self._resolve_context(pipeline_context)
        raw_name = stage_or_hook.value if isinstance(stage_or_hook, PipelineStage) else str(stage_or_hook)
        stage_name = self.retired_hook_stages.get(raw_name, raw_name)
        ctx.record_stage(stage_name, status=status, **metadata)

    def add_filter(
        self,
        hook_name: str,
        callback: Callable[..., Any],
        *,
        capability: str | None = None,
        principal: Principal | None = None,
    ) -> None:
        """Register a callback for a specific hook, enforcing pipeline capability scope when a Principal is bound."""
        req_cap = self.required_capability_for(hook_name, capability)
        active_principal = principal if principal is not None else get_current_principal()
        if active_principal is not None and req_cap:
            active_principal.require(req_cap)

        if hook_name not in self._filters:
            self._filters[hook_name] = []
        self._filters[hook_name].append(callback)
        if req_cap:
            self._filter_capabilities[(hook_name, id(callback))] = req_cap

    def apply_filters(self, hook_name: str, default_value: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Pass a value through all registered filters for a hook.
        If the hook is one of the 16 retired unsubscribed hooks, records its explicit PipelineContext stage.
        """
        pipeline_ctx = kwargs.pop("pipeline_context", None) if "pipeline_context" in kwargs else None
        if hook_name in self.retired_hook_stages or pipeline_ctx is not None or get_current_pipeline_context() is not None:
            self.record_stage(
                hook_name,
                pipeline_context=pipeline_ctx,
                hook_name=hook_name,
                has_subscribers=bool(self._filters.get(hook_name)),
            )

        if hook_name not in self._filters or not self._filters[hook_name]:
            return default_value

        active_principal = get_current_principal()
        req_cap = self.required_capability_for(hook_name)
        if active_principal is not None and req_cap and not active_principal.has_scope(req_cap):
            active_principal.require(req_cap)

        if not hasattr(self._local, "depths"):
            self._local.depths = {}

        current_depth = self._local.depths.get(hook_name, 0)
        if current_depth >= self.MAX_DEPTH:
            return default_value

        self._local.depths[hook_name] = current_depth + 1

        try:
            value = default_value
            for callback in self._filters.get(hook_name, []):
                prev_value = value
                try:
                    value = callback(value, *args, **kwargs)
                    if asyncio.iscoroutine(value):
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

    def register_hook(
        self,
        hook_name: str,
        callback: Callable[..., Any],
        *,
        capability: str | None = None,
        principal: Principal | None = None,
    ) -> None:
        """Register a callback for a specific hook (alias for add_filter)."""
        self.add_filter(hook_name, callback, capability=capability, principal=principal)

    def trigger(self, hook_name: str, *args: Any, **kwargs: Any) -> list[Any]:
        """Trigger a hook (alias for execute_hook)."""
        return self.execute_hook(hook_name, *args, **kwargs)

    def execute_hook(self, hook_name: str, *args: Any, **kwargs: Any) -> list[Any]:
        """
        Execute all callbacks registered for a hook and collect results into a flat list.
        """
        pipeline_ctx = kwargs.pop("pipeline_context", None) if "pipeline_context" in kwargs else None
        if hook_name in self.retired_hook_stages or pipeline_ctx is not None or get_current_pipeline_context() is not None:
            self.record_stage(
                hook_name,
                pipeline_context=pipeline_ctx,
                hook_name=hook_name,
                has_subscribers=bool(self._filters.get(hook_name)),
            )

        results: list[Any] = []
        if hook_name in self._filters:
            active_principal = get_current_principal()
            req_cap = self.required_capability_for(hook_name)
            if active_principal is not None and req_cap and not active_principal.has_scope(req_cap):
                active_principal.require(req_cap)

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
                    logging.getLogger("hook_manager").exception(
                        f"Error executing hook '{hook_name}' in callback '{getattr(callback, '__name__', str(callback))}'"
                    )
        return results


# Global singleton
hook_manager = HookManager()
