import json
from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from core.job_queue import job_queue
from core.job_queue import list_jobs as jq_list_jobs
from core.tiered_logger import get_logger
from web.auth import require_auth
from web.schemas.job import JobIntervalRequest, JobRunRequest

logger = get_logger("jobs_route")
router = APIRouter(prefix="/api/v1/system/jobs", tags=["Jobs"])


@router.get("")
@router.get("/")
def list_jobs(request: Request):
    """Return raw job queue listing (plain array for Svelte)."""
    try:
        items = jq_list_jobs()
        return JSONResponse(content={"total": len(items), "items": items}, status_code=200)
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

        from datetime import datetime

        upcoming_jobs = []
        for j in items:
            if not j.get("enabled"):
                continue
            interval = j.get("interval_seconds") or 0
            if interval <= 0:
                continue

            lr_float = j.get("last_started") or j.get("last_finished")
            nr_float = j.get("next_run")
            if not nr_float and lr_float:
                nr_float = lr_float + interval
            elif not nr_float:
                nr_float = datetime.now(UTC).timestamp() + interval

            lr_iso = datetime.fromtimestamp(lr_float, tz=UTC).isoformat() if lr_float else None
            nr_iso = datetime.fromtimestamp(nr_float, tz=UTC).isoformat() if nr_float else None

            upcoming_jobs.append(
                {
                    "job_name": j["name"],
                    "interval_seconds": int(interval),
                    "last_run": lr_iso,
                    "next_run": nr_iso,
                }
            )

        payload = {
            "running_jobs": running_jobs,
            "queued_jobs": queued_jobs,
            "errors": errors,
            "last_run": last_run,
            "upcoming_jobs": upcoming_jobs,
        }
        return payload
    except Exception as e:
        logger.error(f"Error building jobs summary: {e}")
        payload = {
            "running_jobs": 0,
            "queued_jobs": 0,
            "errors": ["Failed to build summary"],
            "last_run": None,
            "upcoming_jobs": [],
        }
        raise HTTPException(status_code=500, detail=payload)


@router.post("/run", dependencies=[Depends(require_auth)])
async def run_job(request: Request, payload: JobRunRequest = None):
    """Trigger immediate execution of a job."""
    if not payload:
        payload = JobRunRequest()
    job_name = (
        payload.job_name
        or payload.name
        or request.query_params.get("job_id")
        or request.query_params.get("name")
        or request.query_params.get("job_name")
    )
    params = dict(payload.params or {})
    if hasattr(payload, "__pydantic_extra__") and payload.__pydantic_extra__:
        params.update(payload.__pydantic_extra__)

    if payload.scan_mode:
        params["scan_mode"] = payload.scan_mode
    elif request.query_params.get("scan_mode"):
        params["scan_mode"] = request.query_params.get("scan_mode")

    # Extract and normalize force / force_refresh
    force_val = None
    if payload.force_refresh is not None:
        force_val = payload.force_refresh
    elif payload.force is not None:
        force_val = payload.force
    elif "force_refresh" in params:
        force_val = params["force_refresh"]
    elif "force" in params:
        force_val = params["force"]
    elif request.query_params.get("force_refresh") is not None:
        force_val = request.query_params.get("force_refresh")
    elif request.query_params.get("force") is not None:
        force_val = request.query_params.get("force")

    if force_val is not None:
        is_force = force_val if isinstance(force_val, bool) else (str(force_val).lower() in ("true", "1", "yes"))
        params["force_refresh"] = is_force
        params["force"] = is_force

    # Extract and normalize force_check
    force_check_val = None
    if payload.force_check is not None:
        force_check_val = payload.force_check
    elif "force_check" in params:
        force_check_val = params["force_check"]
    elif request.query_params.get("force_check") is not None:
        force_check_val = request.query_params.get("force_check")

    if force_check_val is not None:
        is_force_check = (
            force_check_val
            if isinstance(force_check_val, bool)
            else (str(force_check_val).lower() in ("true", "1", "yes"))
        )
        params["force_check"] = is_force_check

    # Extract and normalize check_all_files
    check_all_val = None
    if payload.check_all_files is not None:
        check_all_val = payload.check_all_files
    elif "check_all_files" in params:
        check_all_val = params["check_all_files"]
    elif request.query_params.get("check_all_files") is not None:
        check_all_val = request.query_params.get("check_all_files")

    if check_all_val is not None:
        is_check_all = (
            check_all_val if isinstance(check_all_val, bool) else (str(check_all_val).lower() in ("true", "1", "yes"))
        )
        params["check_all_files"] = is_check_all
        if is_check_all and force_val is None:
            params["force_refresh"] = True
            params["force"] = True

    # Extract batch_size
    if payload.batch_size is not None:
        params["batch_size"] = payload.batch_size
    elif "batch_size" not in params and request.query_params.get("batch_size") is not None:
        try:
            params["batch_size"] = int(request.query_params.get("batch_size"))
        except ValueError:
            pass

    # Extract limit
    if payload.limit is not None:
        params["limit"] = payload.limit
    elif "limit" not in params and request.query_params.get("limit") is not None:
        try:
            params["limit"] = int(request.query_params.get("limit"))
        except ValueError:
            pass

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
            return Response(
                json.dumps(
                    {
                        "error": f"job '{job_name}' is already running",
                        "reason": "Job is currently executing. Please wait for it to complete.",
                        "job": job_name,
                        "started_at": job.get("last_started"),
                    }
                ),
                status=409,
                mimetype="application/json",
            )

        if not job_queue.execute_job_now(job_name, params=params):
            return Response(
                json.dumps(
                    {
                        "error": f"job '{job_name}' could not be executed",
                        "reason": "Job may be disabled or already running.",
                    }
                ),
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
        raise HTTPException(
            status_code=400,
            detail={"error": "interval_seconds required and must be >= 60"},
        )

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
            raise HTTPException(
                status_code=404,
                detail={"error": "job not running or could not be killed"},
            )
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
                "message": f"Cancellation requested for {job_name}",
            }
        else:
            raise HTTPException(
                status_code=404,
                detail={
                    "status": "error",
                    "message": f"Job {job_name} not found or not cancellable",
                },
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in cancel_queue_job: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Internal server error during cancellation",
            },
        )


@router.get("/stream", dependencies=[Depends(require_auth)])
def stream_queue_progress():
    """SSE endpoint streaming the live status of the job queue with keepalive heartbeats."""

    def event_generator():
        try:
            import json
            import time

            from core.job_queue import job_queue

            last_state = None
            last_heartbeat = time.time()
            HEARTBEAT_INTERVAL = 15.0  # seconds between keepalive pings

            while True:
                now = time.time()
                state = job_queue.get_queue_state()
                state_str = json.dumps(state, sort_keys=True)

                if state_str != last_state:
                    yield f"data: {state_str}\n\n"
                    last_state = state_str
                    last_heartbeat = now
                elif now - last_heartbeat >= HEARTBEAT_INTERVAL:
                    # SSE comment ping — keeps the connection alive through proxies
                    yield ": keepalive\n\n"
                    last_heartbeat = now

                time.sleep(1.0)
        except GeneratorExit:
            logger.debug("SSE stream client disconnected cleanly (system queue).")
        except Exception as e:
            logger.error(f"SSE stream error (queue): {e}", exc_info=True)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx proxy buffering
            "Connection": "keep-alive",
        },
    )
