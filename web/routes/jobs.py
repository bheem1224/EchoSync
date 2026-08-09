from web.auth import require_auth
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from web.auth import require_auth
import json
from core.tiered_logger import get_logger
from core.job_queue import list_jobs as jq_list_jobs, job_queue
from web.schemas.job import JobRunRequest, JobIntervalRequest

logger = get_logger("jobs_route")
router = APIRouter(prefix="/api/v1/system/jobs", tags=["Jobs"])

@router.get("")
@router.get("/")
def list_jobs(request: Request):
    """Return raw job queue listing (plain array for Svelte)."""
    try:
        items = jq_list_jobs()
        return JSONResponse(content={
            "total": len(items),
            "items": items
        }, status_code=200)
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        payload = {"total": 0, "items": []}
        raise HTTPException(status_code=500, detail=payload)


@router.get("/active")
def list_active_jobs(request: Request):
    """Return running/queued jobs expected by web UI."""
    try:
        items = jq_list_jobs()
        active = [j for j in items if j.get("running") or j.get("enabled")]
        return active
    except Exception as e:
        logger.error(f"Error listing active jobs: {e}")
        raise HTTPException(status_code=500, detail=[])


@router.get("/summary")
def jobs_summary(request: Request):
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
        return payload
    except Exception as e:
        logger.error(f"Error building jobs summary: {e}")
        payload = {
            "running_jobs": 0,
            "queued_jobs": 0,
            "errors": ["Failed to build summary"],
            "last_run": None,
        }
        raise HTTPException(status_code=500, detail=payload)


@router.post("/run", dependencies=[Depends(require_auth)])
async def run_job(request: Request, payload: JobRunRequest = None):
    """Trigger immediate execution of a job."""
    if not payload:
        payload = JobRunRequest()
    job_name = payload.job_name or payload.name or request.query_params.get("job_id") or request.query_params.get("name") or request.query_params.get("job_name")
    params = payload.params or {}
    
    if not job_name:
        raise HTTPException(status_code=400, detail={"error": "job name required"})

    if job_name == "download_manager_status":
        job_name = "download_manager"
    
    try:
        # Get current job status
        items = jq_list_jobs()
        job = next((j for j in items if j.get("name") == job_name), None)
        
        if not job:
            raise HTTPException(status_code=404, detail={"error": f"job '{job_name}' not found"})
        
        # Check if job is already running
        if job.get("running"):
            return Response(json.dumps({
                "error": f"job '{job_name}' is already running",
                "reason": "Job is currently executing. Please wait for it to complete.",
                "job": job_name,
                "started_at": job.get("last_started"),
            }), status=409, mimetype="application/json")
        
        if not job_queue.execute_job_now(job_name, params=params):
            return Response(
                json.dumps({
                    "error": f"job '{job_name}' could not be executed",
                    "reason": "Job may be disabled or already running.",
                }),
                status=409,
                mimetype="application/json",
            )
        logger.info(f"Job triggered: {job_name} with params={params}")
        return {"accepted": True, "job": job_name}
    except Exception as e:
        logger.error(f"Error triggering job {job_name}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/{job_name}")
@router.get("/{job_name}")
def get_job(job_name: str):
    """Return status of a specific job by name/id."""
    try:
        items = jq_list_jobs()
        job = next((j for j in items if j.get("name") == job_name), None)
        if not job:
            raise HTTPException(status_code=404, detail={"error": f"job '{job_name}' not found"})
        return job
    except Exception as e:
        logger.error(f"Error fetching job {job_name}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post("/{job_name}/interval", dependencies=[Depends(require_auth)])
async def update_job_interval_route(job_name: str, payload: JobIntervalRequest):
    """Update interval for any job and persist to config."""
    new_interval = payload.interval_seconds
    
    if new_interval is None or new_interval < 60:
        raise HTTPException(status_code=400, detail={"error": "interval_seconds required and must be >= 60"})
    
    try:
        from core.job_queue import update_job_interval

        success = update_job_interval(job_name, float(new_interval))

        if not success:
             raise HTTPException(status_code=404, detail={"error": "job not found or update failed"})
        
        return {"accepted": True, "job": job_name, "interval": new_interval}
    except Exception as e:
        logger.error(f"Error updating job {job_name} interval: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/{job_name}/kill", dependencies=[Depends(require_auth)])
def kill_job_route(job_name):
    """OS-Level Escape Hatch to kill a hung worker process."""
    try:
        from core.job_queue import job_queue
        success = job_queue.kill_job(job_name)
        if not success:
            raise HTTPException(status_code=404, detail={"error": "job not running or could not be killed"})
        return {"accepted": True, "job": job_name, "status": "killed"}
    except Exception as e:
        logger.error(f"Error killing job {job_name}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/{job_name}/cancel", dependencies=[Depends(require_auth)])
async def cancel_queue_job(job_name: str, request: Request):
    """Cancel a running or scheduled job in the task manager using the new CancellationToken API."""
    try:
        from core.job_queue import job_queue
        
        success = job_queue.cancel_job(job_name)
        if success:
            return {
                "status": "success",
                "message": f"Cancellation requested for {job_name}"
            }
        else:
            raise HTTPException(status_code=404, detail={
                "status": "error", 
                "message": f"Job {job_name} not found or not cancellable"
            })
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in cancel_queue_job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"status": "error", "message": "Internal server error during cancellation"})


@router.get("/stream", dependencies=[Depends(require_auth)])
def stream_queue_progress():
    """SSE endpoint streaming the live status of the job queue."""
    def event_generator():
        try:
            from core.job_queue import job_queue
            import time
            import json
            
            last_state = None
            while True:
                state = job_queue.get_queue_state()
                state_str = json.dumps(state, sort_keys=True)
                if state_str != last_state:
                    yield f"event: queue_update\ndata: {state_str}\n\n"
                    last_state = state_str
                time.sleep(1.0)
        except GeneratorExit:
            logger.debug("SSE stream client disconnected cleanly (system queue).")
        except Exception as e:
            logger.error(f"SSE stream error (queue): {e}", exc_info=True)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
