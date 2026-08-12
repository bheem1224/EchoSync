from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

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
    GET /api/v1/system/tasks/queue
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


@router.get("/processes")
def get_active_processes():
    """
    GET /api/v1/system/tasks/processes
    Returns running process/thread owners registered with the ProcessSupervisor,
    each enriched with its registration_id so the frontend can issue kill requests.
    """
    try:
        processes = supervisor.get_active_processes_with_ids()
        return {"total": len(processes), "processes": processes}
    except Exception as e:
        logger.error(f"Error listing active processes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve active processes: {str(e)}")


@router.get("/processes/stream")
async def stream_processes():
    """
    GET /api/v1/system/tasks/processes/stream
    SSE stream that pushes live process list updates every 2 seconds with
    keepalive heartbeats every 15 seconds.
    """
    async def event_generator():
        import asyncio
        import json

        last_state = None
        last_heartbeat = asyncio.get_event_loop().time()
        HEARTBEAT_INTERVAL = 15.0

        try:
            while True:
                now = asyncio.get_event_loop().time()
                processes = supervisor.get_active_processes_with_ids()
                payload = {"total": len(processes), "processes": processes}
                state_str = json.dumps(payload, sort_keys=True, default=str)

                if state_str != last_state:
                    yield f"data: {state_str}\n\n"
                    last_state = state_str
                    last_heartbeat = now
                elif now - last_heartbeat >= HEARTBEAT_INTERVAL:
                    yield ": keepalive\n\n"
                    last_heartbeat = now

                await asyncio.sleep(2.0)
        except GeneratorExit:
            logger.debug("SSE processes stream client disconnected cleanly.")
        except Exception as e:
            logger.error(f"SSE processes stream error: {e}", exc_info=True)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/processes/{registration_id}/terminate", response_model=ProcessTerminateResponse)
def terminate_process(registration_id: str):
    """
    POST /api/v1/system/tasks/processes/{registration_id}/terminate
    Terminates a specific registered process or thread owner (legacy, no DB cleanup).
    Prefer /kill for running jobs that may hold database connections.
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


@router.post("/processes/{registration_id}/kill")
def kill_process_with_cleanup(registration_id: str):
    """
    POST /api/v1/system/tasks/processes/{registration_id}/kill
    Safely terminates a process and flushes any SQLAlchemy DB sessions it holds,
    preventing database corruption (locked WAL / uncommitted transactions).
    """
    try:
        success, message = supervisor.kill_with_cleanup(registration_id)
        if not success:
            raise HTTPException(status_code=404, detail=message)
        return {"status": "killed", "registration_id": registration_id, "message": message}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error killing process '{registration_id}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to kill process: {str(e)}")


@router.get("/health", response_model=SystemHealthResponse)
def get_unified_system_health():
    """
    GET /api/v1/system/tasks/health
    Aggregates health checks and plugin lifecycle states into a unified SystemHealthResponse.
    """
    try:
        health_data = get_system_health()
        
        with plugin_state_manager._lock:
            plugin_states = {
                p_id: status.model_dump()
                for p_id, status in plugin_state_manager._states.items()
                if status.state != PluginLifecycleState.UNCONFIGURED
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
