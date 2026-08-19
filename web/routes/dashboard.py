import os
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from web.auth import require_auth
from core.tiered_logger import get_logger
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

logger = get_logger("dashboard_route")
dashboard_bp = APIRouter(prefix="/api/v1/system/dashboard", tags=["Dashboard"])
dashboards_bp = APIRouter(prefix="/api/v1/dashboards", tags=["Dashboards"])

@dashboards_bp.get("/{filename}", dependencies=[Depends(require_auth)])
def get_custom_dashboard_yaml(filename: str):
    from fastapi.responses import PlainTextResponse
    import re
    from core.path_security import resolve_safe_path, PathTraversalError

    safe_name = os.path.basename(filename.strip())
    if not re.match(r'^[a-zA-Z0-9_\-]+\.(yaml|yml|json)$', safe_name):
        raise HTTPException(status_code=400, detail="Invalid dashboard filename")

    try:
        base_dir = Path("config/webui").resolve()
        target_path = resolve_safe_path(base_dir, safe_name)
    except (PathTraversalError, ValueError):
        raise HTTPException(status_code=403, detail="Access denied")

    if not target_path.exists() or not target_path.is_file():
        raise HTTPException(status_code=404, detail="Dashboard not found")

    try:
        with open(target_path, "r", encoding="utf-8") as f:
            return PlainTextResponse(f.read(), media_type="text/yaml")
    except Exception as e:
        logger.error(f"Error reading {safe_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to read dashboard")

DASHBOARD_FILE = os.path.join("config", "webui", "dashboard.yaml")
DEFAULT_DASHBOARD_CONTENT = """# EchoSync Dashboard Configuration
# You can manually edit this file or use the UI editor.
views:
  - title: Home
    icon: mdi:home
    sections:
      - cards:
          - type: echosync-system-overview
"""

def _ensure_file():
    if not os.path.exists(DASHBOARD_FILE):
        os.makedirs(os.path.dirname(DASHBOARD_FILE), exist_ok=True)
        with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
            f.write(DEFAULT_DASHBOARD_CONTENT)

@dashboard_bp.get("/command-center", dependencies=[Depends(require_auth)])
def command_center():
    """Aggregated command center dashboard data."""
    try:
        from services.health_check import get_system_health
        health_data = get_system_health()
    except Exception as e:
        logger.error(f"Error getting health data: {e}")
        health_data = {"status": "error", "message": "Failed to get health data"}

    try:
        from web.services.library_service import LibraryAdapter
        from database.music_database import get_database
        adapter = LibraryAdapter()
        lib_overview = adapter.overview()
        stats = lib_overview.get("stats", {})
        
        db = get_database()
        total_tracks = stats.get("total_tracks", 0)
        lossless_count = db.count_lossless_files()
        lossless_ratio = round(lossless_count / total_tracks, 2) if total_tracks > 0 else 0.0
        
        library_stats = {
            "total_tracks": total_tracks,
            "total_albums": stats.get("total_albums", 0),
            "total_artists": stats.get("total_artists", 0),
            "database_size_mb": stats.get("database_size_mb", 0.0),
            "lossless_ratio": lossless_ratio
        }
    except Exception as e:
        logger.error(f"Error getting library stats: {e}")
        library_stats = {
            "total_tracks": 0, "total_albums": 0, "total_artists": 0,
            "database_size_mb": 0.0, "lossless_ratio": 0.0
        }

    try:
        from core.job_queue import list_jobs as jq_list_jobs
        items = jq_list_jobs()
        
        from datetime import datetime, timezone
        upcoming_jobs = []
        active_pipeline = []
        for j in items:
            if j.get("running"):
                active_pipeline.append(j)
                
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
                nr_float = datetime.now(timezone.utc).timestamp() + interval
                
            lr_iso = datetime.fromtimestamp(lr_float, tz=timezone.utc).isoformat() if lr_float else None
            nr_iso = datetime.fromtimestamp(nr_float, tz=timezone.utc).isoformat() if nr_float else None
            
            upcoming_jobs.append({
                "job_name": j["name"],
                "interval_seconds": int(interval),
                "last_run": lr_iso,
                "next_run": nr_iso
            })
    except Exception as e:
        logger.error(f"Error getting jobs info: {e}")
        active_pipeline = []
        upcoming_jobs = []

    try:
        from database.working_database import get_working_database
        wdb = get_working_database()
        pending_reviews = wdb.count_pending_reviews()
    except Exception as e:
        logger.error(f"Error getting pending reviews: {e}")
        pending_reviews = 0

    return {
        "health": health_data,
        "library_stats": library_stats,
        "active_pipeline": active_pipeline,
        "upcoming_jobs": upcoming_jobs,
        "pending_reviews": pending_reviews
    }

@dashboard_bp.get("", dependencies=[Depends(require_auth)])
def get_dashboard():
    """Reads dashboard.yaml and returns the parsed structure as standard JSON."""
    _ensure_file()

    yaml = YAML()
    try:
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            data = yaml.load(f)

        if data is None:
            data = {}

    except YAMLError as e:
        raise HTTPException(status_code=400, detail={"error": "YAML Syntax Error", "details": str(e)})
    except Exception as e:
        logger.error(f"Error reading dashboard.yaml: {e}")
        raise HTTPException(status_code=500, detail="Failed to read dashboard configuration")

    return data

@dashboard_bp.post("", dependencies=[Depends(require_auth)])
async def update_dashboard(request: Request):
    """Accepts a JSON payload, converts it, and writes it back to dashboard.yaml preserving comments."""
    try:
        payload = await request.json()
    except Exception:
        payload = None
        
    if payload is None:
        raise HTTPException(status_code=400, detail="Invalid or missing JSON payload")

    _ensure_file()

    yaml = YAML()
    yaml.preserve_quotes = True

    try:
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            data = yaml.load(f)

        if data is None:
            data = payload
        elif isinstance(data, dict) and isinstance(payload, dict):
            for key in list(data.keys()):
                if key not in payload:
                    del data[key]
            for key, value in payload.items():
                data[key] = value
        else:
            data = payload

        with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

        return {"success": True}
    except YAMLError as e:
        raise HTTPException(status_code=400, detail={"error": "YAML Syntax Error while writing", "details": str(e)})
    except Exception as e:
        logger.error(f"Error writing dashboard.yaml: {e}")
        raise HTTPException(status_code=500, detail="Failed to write dashboard configuration")

@dashboard_bp.get("/layout", dependencies=[Depends(require_auth)])
def get_dashboard_layout():
    """Reads the Lovelace dashboard layout from config/dashboard.yaml."""
    layout_file = os.path.join("config", "dashboard.yaml")
    yaml = YAML()
    
    fallback = {
        "dashboard": {
            "views": [
                {
                    "id": "manager",
                    "title": "Manager",
                    "sidebar": {
                        "enabled": True,
                        "cards": [{"type": "echosync-download-queue"}]
                    },
                    "sections": [
                        {
                            "title": "Accounts",
                            "cards": [{"type": "echosync-plex-card"}]
                        },
                        {
                            "title": "System",
                            "cards": [{"type": "echosync-system-metrics"}]
                        }
                    ]
                }
            ]
        }
    }

    if not os.path.exists(layout_file):
        return fallback

    try:
        with open(layout_file, "r", encoding="utf-8") as f:
            data = yaml.load(f)
        if data is None:
            data = fallback
    except YAMLError as e:
        logger.error(f"YAML Syntax Error reading config/dashboard.yaml: {e}")
        data = fallback
    except Exception as e:
        logger.error(f"Error reading config/dashboard.yaml: {e}")
        data = fallback

    return data
