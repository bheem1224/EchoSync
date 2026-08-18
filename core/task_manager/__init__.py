"""
Centralized Task Manager & Supervision Subsystem for EchoSync.
Provides task queue management, health checks, background service orchestration, process tracking, and plugin lifecycle state management.
"""

from core.task_manager.task_queue import (
    TaskCategory,
    TaskState,
    ScheduledJob,
    JobQueue,
    job_queue,
    list_jobs,
    update_job_interval,
    start_job_queue,
    stop_job_queue,
    register_job,
    unregister_job,
)
from core.task_manager.health import (
    HealthCheckResult,
    HealthCheckRegistry,
    health_check_registry,
    register_health_check,
    register_health_check_job,
    run_health_check,
    run_all_health_checks,
)
from core.task_manager.health_service import get_system_health
from core.task_manager.binary_runner import CoreBinaryRunner
from core.task_manager.backend_services import start_services, backend_main
from core.task_manager.system_jobs import register_all_system_jobs, register_auto_import_scan_job
from core.task_manager.models import (
    OwnerType,
    PluginLifecycleState,
    ProcessOwner,
    PluginStatus,
)
from core.task_manager.supervisor import ProcessSupervisor, supervisor
from core.task_manager.plugin_state import PluginStateManager, plugin_state_manager

__all__ = [
    "TaskCategory",
    "TaskState",
    "ScheduledJob",
    "JobQueue",
    "job_queue",
    "list_jobs",
    "update_job_interval",
    "start_job_queue",
    "stop_job_queue",
    "register_job",
    "unregister_job",
    "HealthCheckResult",
    "HealthCheckRegistry",
    "health_check_registry",
    "register_health_check",
    "register_health_check_job",
    "run_health_check",
    "run_all_health_checks",
    "get_system_health",
    "CoreBinaryRunner",
    "start_services",
    "backend_main",
    "register_all_system_jobs",
    "register_auto_import_scan_job",
    "OwnerType",
    "PluginLifecycleState",
    "ProcessOwner",
    "PluginStatus",
    "ProcessSupervisor",
    "supervisor",
    "PluginStateManager",
    "plugin_state_manager",
]
