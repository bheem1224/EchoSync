from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, Response
import json

from core.tiered_logger import get_logger
from core.task_manager import job_queue, supervisor, plugin_state_manager, get_system_health, PluginLifecycleState
from api.schemas.system_tasks import (
    TaskQueueSummaryResponse,
    ProcessListResponse,
    ProcessTerminateResponse,
    SystemHealthResponse,
)

logger = get_logger("system_tasks_api")

bp = Blueprint("system_tasks", __name__, url_prefix="/api/v1")


@bp.get("/tasks/queue")
def get_task_queue_status():
    """
    GET /api/v1/tasks/queue
    Returns summary counts and serialized lists of queued, active, and PENDING_BLOCKED jobs.
    """
    try:
        raw_state = job_queue.get_queue_state()
        response_model = TaskQueueSummaryResponse(
            stats=raw_state.get("stats", {}),
            running_jobs=raw_state.get("running_jobs", []),
            pending_jobs=raw_state.get("pending_jobs", []),
            blocked_jobs=raw_state.get("blocked_jobs", [])
        )
        return Response(response_model.model_dump_json(), status=200, mimetype="application/json")
    except Exception as e:
        logger.error(f"Error fetching task queue status: {e}", exc_info=True)
        return jsonify({"error": f"Failed to retrieve task queue status: {str(e)}"}), 500


@bp.get("/tasks/processes")
def get_active_processes():
    """
    GET /api/v1/tasks/processes
    Returns running process/thread owners registered with the ProcessSupervisor.
    """
    try:
        active_processes = supervisor.get_active_processes()
        response_model = ProcessListResponse(
            total=len(active_processes),
            processes=active_processes
        )
        return Response(response_model.model_dump_json(), status=200, mimetype="application/json")
    except Exception as e:
        logger.error(f"Error listing active processes: {e}", exc_info=True)
        return jsonify({"error": f"Failed to retrieve active processes: {str(e)}"}), 500


@bp.post("/tasks/processes/<registration_id>/terminate")
def terminate_process(registration_id: str):
    """
    POST /api/v1/tasks/processes/<registration_id>/terminate
    Terminates a specific registered process or thread owner.
    """
    try:
        with supervisor._lock:
            owner = supervisor._processes.get(registration_id)

        if not owner:
            return jsonify({
                "error": "Process registration not found",
                "registration_id": registration_id
            }), 404

        # Unregister from supervisor
        supervisor.unregister_process(registration_id)

        # Terminate PID if attached
        if owner.pid:
            supervisor._kill_process(owner.pid, owner.task_name)

        response_model = ProcessTerminateResponse(
            status="terminated",
            registration_id=registration_id,
            message=f"Successfully terminated process '{registration_id}' (Task: {owner.task_name})"
        )
        return Response(response_model.model_dump_json(), status=200, mimetype="application/json")
    except Exception as e:
        logger.error(f"Error terminating process '{registration_id}': {e}", exc_info=True)
        return jsonify({"error": f"Failed to terminate process: {str(e)}"}), 500


@bp.get("/system/health")
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

        response_model = SystemHealthResponse(
            status=overall_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            health_checks=health_data,
            plugin_states=plugin_states
        )
        return Response(response_model.model_dump_json(), status=200, mimetype="application/json")
    except Exception as e:
        logger.error(f"Error fetching unified system health: {e}", exc_info=True)
        return jsonify({"error": f"Failed to retrieve system health: {str(e)}"}), 500
