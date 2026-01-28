from flask import Blueprint, Response, request
import json
from core.tiered_logger import get_logger
from core.job_queue import list_jobs as jq_list_jobs, job_queue, run_job_now

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


@bp.post("/run")
def run_job():
    """Trigger immediate execution of a job."""
    payload = request.get_json(silent=True) or {}
    job_name = payload.get("name")
    
    if not job_name:
        return Response(json.dumps({"error": "job name required"}), status=400, mimetype="application/json")
    
    try:
        run_job_now(job_name)
        logger.info(f"Job triggered: {job_name}")
        return Response(json.dumps({"accepted": True, "job": job_name}), status=200, mimetype="application/json")
    except Exception as e:
        logger.error(f"Error triggering job {job_name}: {e}")
        return Response(json.dumps({"error": str(e)}), status=500, mimetype="application/json")


@bp.post("/<job_name>/interval")
def update_job_interval(job_name):
    """Update interval for a user-configurable job."""
    payload = request.get_json(silent=True) or {}
    new_interval = payload.get("interval_seconds")
    
    if new_interval is None or new_interval < 60:
        return Response(json.dumps({"error": "interval_seconds required and must be >= 60"}), status=400, mimetype="application/json")
    
    try:
        with job_queue._lock:
            job = job_queue._jobs.get(job_name)
            if not job:
                return Response(json.dumps({"error": "job not found"}), status=404, mimetype="application/json")
            
            # Only allow updating user-configurable jobs (not system/SoulSync)
            if job.tags and any(t in ["system", "soulsync"] for t in job.tags):
                return Response(json.dumps({"error": "cannot modify system or SoulSync jobs"}), status=403, mimetype="application/json")
            
            job.interval_seconds = new_interval
        
        logger.info(f"Updated job {job_name} interval to {new_interval}s")
        return Response(json.dumps({"accepted": True, "job": job_name, "interval": new_interval}), status=200, mimetype="application/json")
    except Exception as e:
        logger.error(f"Error updating job {job_name} interval: {e}")
        return Response(json.dumps({"error": str(e)}), status=500, mimetype="application/json")
