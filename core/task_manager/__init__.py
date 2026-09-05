"""
Centralized Task Manager & Supervision Subsystem for EchoSync.
Provides task queue management, health checks, background service orchestration, process tracking, and plugin lifecycle state management.
"""

from core.task_manager.backend_services import backend_main, start_services
from core.task_manager.binary_runner import CoreBinaryRunner
from core.task_manager.health import (
    HealthCheckRegistry,
    HealthCheckResult,
    health_check_registry,
    register_health_check,
    register_health_check_job,
    run_all_health_checks,
    run_health_check,
)
from core.task_manager.health_service import get_system_health
from core.task_manager.models import (
    OwnerType,
    PluginLifecycleState,
    PluginStatus,
    ProcessOwner,
)
from core.task_manager.plugin_state import PluginStateManager, plugin_state_manager
from core.task_manager.supervisor import ProcessSupervisor, supervisor
from core.task_manager.system_jobs import (
    register_all_system_jobs,
    register_auto_import_scan_job,
)
from core.task_manager.task_queue import (
    JobQueue,
    ScheduledJob,
    TaskCategory,
    TaskState,
    job_queue,
    list_jobs,
    register_job,
    start_job_queue,
    stop_job_queue,
    unregister_job,
    update_job_interval,
)

__all__ = [
    "CoreBinaryRunner",
    "HealthCheckRegistry",
    "HealthCheckResult",
    "JobQueue",
    "OwnerType",
    "PluginLifecycleState",
    "PluginStateManager",
    "PluginStatus",
    "ProcessOwner",
    "ProcessSupervisor",
    "ScheduledJob",
    "TaskCategory",
    "TaskState",
    "backend_main",
    "get_system_health",
    "health_check_registry",
    "job_queue",
    "list_jobs",
    "plugin_state_manager",
    "register_all_system_jobs",
    "register_auto_import_scan_job",
    "register_health_check",
    "register_health_check_job",
    "register_job",
    "run_all_health_checks",
    "run_health_check",
    "start_job_queue",
    "start_services",
    "stop_job_queue",
    "supervisor",
    "unregister_job",
    "update_job_interval",
]
