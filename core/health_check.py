"""Compatibility shim for legacy `core.health_check` imports.

New code should import directly from `core.task_manager.health`.
"""

from core.task_manager.health import (  # noqa: F401
    HealthCheckRegistry,
    HealthCheckResult,
    health_check_registry,
    register_health_check,
    register_health_check_job,
    run_all_health_checks,
    run_health_check,
)
