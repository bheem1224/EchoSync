from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from core.tiered_logger import get_logger
from core.task_manager import job_queue, supervisor, plugin_state_manager, get_system_health, PluginLifecycleState
from api.schemas.system_tasks import (
    TaskQueueSummaryResponse,
    ProcessListResponse,
    ProcessTerminateResponse,
    SystemHealthResponse,
)

logger = get_logger("system_tasks_api")

router = APIRouter(prefix="/api/v1/system/tasks", tags=["System Tasks"])


@router.get("/queue", response_model=TaskQueueSummaryResponse)
def get_task_queue_status():
    """
    GET /api/v1/tasks/queue
    Returns summary counts and serialized lists of queued, active, and PENDING_BLOCKED jobs.
    """
    try:
        raw_state = job_queue.get_queue_state()
        return TaskQueueSummaryResponse(
            stats=raw_state.get("stats", {}),
            running_jobs=raw_state.get("running_jobs", []),
            pending_jobs=raw_state.get("pending_jobs", []),
            blocked_jobs=raw_state.get("blocked_jobs", [])
        )
    except Exception as e:
        logger.error(f"Error fetching task queue status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve task queue status: {str(e)}")


@router.get("/processes", response_model=ProcessListResponse)
def get_active_processes():
    """
    GET /api/v1/tasks/processes
    Returns running process/thread owners registered with the ProcessSupervisor.
    """
    try:
        active_processes = supervisor.get_active_processes()
        return ProcessListResponse(
            total=len(active_processes),
            processes=active_processes
        )
    except Exception as e:
        logger.error(f"Error listing active processes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve active processes: {str(e)}")


@router.post("/processes/{registration_id}/terminate", response_model=ProcessTerminateResponse)
def terminate_process(registration_id: str):
    """
    POST /api/v1/tasks/processes/{registration_id}/terminate
    Terminates a specific registered process or thread owner.
    """
    try:
        with supervisor._lock:
            owner = supervisor._processes.get(registration_id)

        if not owner:
            raise HTTPException(status_code=404, detail="Process registration not found")

        # Unregister from supervisor
        supervisor.unregister_process(registration_id)

        # Terminate PID if attached
        if owner.pid:
            supervisor._kill_process(owner.pid, owner.task_name)

        return ProcessTerminateResponse(
            status="terminated",
            registration_id=registration_id,
            message=f"Successfully terminated process '{registration_id}' (Task: {owner.task_name})"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error terminating process '{registration_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to terminate process: {str(e)}")


@router.get("/health", response_model=SystemHealthResponse)
def get_unified_system_health():
    """
    GET /api/v1/system/health
    Aggregates health checks and plugin lifecycle states into a unified SystemHealthResponse.
    """
    try:
        health_data = get_system_health()
        
        with plugin_state_manager._lock:
            plugin_states = {
                p_id: status.model_dump()
                for p_id, status in plugin_state_manager._states.items()
            }

        # Calculate overall unified health status
        raw_status = health_data.get("status", "healthy").lower()
        if raw_status == "error" or any(s.get("state") == PluginLifecycleState.ERROR for s in plugin_states.values()):
            overall_status = "error"
        elif raw_status == "degraded" or any(s.get("state") == PluginLifecycleState.DEGRADED for s in plugin_states.values()):
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return SystemHealthResponse(
            status=overall_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            health_checks=health_data,
            plugin_states=plugin_states
        )
    except Exception as e:
        logger.error(f"Error fetching unified system health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve system health: {str(e)}")
