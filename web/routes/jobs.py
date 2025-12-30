from flask import Blueprint, Response
import json
from utils.logging_config import get_logger
from core.job_queue import list_jobs as jq_list_jobs

logger = get_logger("jobs_route")
bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")

@bp.get("")
@bp.get("/")
def list_jobs():
    """Return raw job queue listing (plain array for Svelte)."""
    try:
        items = jq_list_jobs()
        return Response(json.dumps({
            "total": len(items),
            "items": items
        }), status=200, mimetype="application/json")
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        payload = {"total": 0, "items": []}
        return Response(json.dumps(payload), status=500, mimetype="application/json")


@bp.get("/active")
def list_active_jobs():
    """Return running/queued jobs expected by web UI."""
    try:
        items = jq_list_jobs()
        active = [j for j in items if j.get("running") or j.get("enabled")]
        return Response(json.dumps(active), status=200, mimetype="application/json")
    except Exception as e:
        logger.error(f"Error listing active jobs: {e}")
        return Response("[]", status=500, mimetype="application/json")


@bp.get("/summary")
def jobs_summary():
    """Return summarized job queue status for dashboard."""
    try:
        items = jq_list_jobs()
        running_jobs = sum(1 for j in items if j.get("running"))
        queued_jobs = sum(1 for j in items if j.get("enabled") and not j.get("running"))
        errors = [j["name"] for j in items if j.get("last_error")]
        # Compute last_run from last_finished or last_success
        timestamps = [t for j in items for t in (j.get("last_finished"), j.get("last_success")) if t]
        last_run = max(timestamps) if timestamps else None
        payload = {
            "running_jobs": running_jobs,
            "queued_jobs": queued_jobs,
            "errors": errors,
            "last_run": last_run,
        }
        return Response(json.dumps(payload), status=200, mimetype="application/json")
    except Exception as e:
        logger.error(f"Error building jobs summary: {e}")
        payload = {
            "running_jobs": 0,
            "queued_jobs": 0,
            "errors": ["Failed to build summary"],
            "last_run": None,
        }
        return Response(json.dumps(payload), status=500, mimetype="application/json")
