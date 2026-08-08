from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json
import time
from core.scan_state import scan_state_manager
from web.services.library_service import LibraryAdapter
from services.media_manager import MediaManagerService
from core.settings import config_manager
from core.nexus_framework.plugin_loader import PluginRegistry, ServiceRegistry
from core.tiered_logger import get_logger
import threading

logger = get_logger("library")
router = APIRouter(prefix="/api/v1/core/library", tags=["Library"])

@router.get("/")
def library_overview():
    adapter = LibraryAdapter()
    data = adapter.overview()
    return data


@router.post("/scan")
def trigger_library_scan(request: Request):
    """
    Trigger a library scan/refresh on the active media server.
    
    Query params:
        - path: Optional library section path (Plex section ID, Jellyfin library name, etc.)
    """
    try:
        path = request.query_params.get("path")
        
        # Get active media server
        from core.nexus_framework.plugin_loader import PluginRegistry
        active_servers = PluginRegistry.get_active_services_by_type('media_server')
        active_server = active_servers[0] if active_servers else None

        if not active_server:
            raise HTTPException(status_code=400, detail={"error": "No active media server configured"})

        try:
            provider = PluginRegistry.create_instance(active_server)
        except Exception as e:
            logger.error(f"Failed to create provider instance for {active_server}: {e}")
            raise HTTPException(status_code=500, detail={"error": f"Media server '{active_server}' not available"})
        
        # Check if it has scan capability
        if not hasattr(provider, 'trigger_library_scan'):
            return jsonify({
                "error": f"Media server '{active_server}' does not support library scans"
            }), 400
        
        # Trigger scan
        success = provider.trigger_library_scan(path=path)
        
        if success:
            logger.info(f"Library scan initiated on {active_server} {f'(path: {path})' if path else ''}")
            return jsonify({
                "success": True,
                "server": active_server,
                "message": "Library scan initiated"
            }), 200
        else:
            return jsonify({
                "error": f"Failed to initiate library scan on {active_server}"
            }), 500
            
    except Exception as e:
        logger.error(f"Library scan error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/scan-status")
def get_library_scan_status(request: Request):
    """
    Get current library scan status from the active media server.
    
    Returns:
        {
            'server': str,
            'scanning': bool,
            'progress': float (0-100 or -1 if unknown),
            'eta_seconds': int or None,
            'error': str or None
        }
    """
    try:
        # Get active media server
        from core.nexus_framework.plugin_loader import PluginRegistry
        active_servers = PluginRegistry.get_active_services_by_type('media_server')
        active_server = active_servers[0] if active_servers else None

        if not active_server:
            raise HTTPException(status_code=400, detail={"error": "No active media server configured"})

        try:
            provider = PluginRegistry.create_instance(active_server)
        except Exception as e:
            logger.error(f"Failed to create provider instance for {active_server}: {e}")
            raise HTTPException(status_code=500, detail={"error": f"Media server '{active_server}' not available"})
        
        # Check if it has scan capability
        if not hasattr(provider, 'get_scan_status'):
            return jsonify({
                "error": f"Media server '{active_server}' does not support scan status"
            }), 400
        
        # Get status
        status = provider.get_scan_status()
        
        return jsonify({
            "server": active_server,
            **status  # Merge in the status dict (scanning, progress, eta_seconds, error)
        }), 200
            
    except Exception as e:
        logger.error(f"Library scan status error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})


# Global worker instance to track database update progress
_db_update_worker = None
_db_update_lock = threading.Lock()


@router.post("/update-database")
def update_database(request: Request):
    """
    Update Echosync database from active media server library.
    
    Query params:
        - mode: 'full' or 'incremental' (default: 'incremental')
    """
    global _db_update_worker
    
    try:
        mode = request.query_params.get("mode", "incremental").lower()
        full_refresh = (mode == "full")
        
        # Get active media server
        try:
            from core.nexus_framework.plugin_loader import PluginRegistry
            active_servers = PluginRegistry.get_active_services_by_type('media_server')
            active_server = active_servers[0] if active_servers else None
        except Exception as e:
            logger.error(f"Failed to get active media server: {e}")
            raise HTTPException(status_code=500, detail={"error": f"Failed to get active media server: {str(e)}"})
        
        if not active_server:
            raise HTTPException(status_code=400, detail={"error": "No active media server configured"})
        
        # Check if update is already running
        with _db_update_lock:
            if _db_update_worker is not None:
                # Query the job queue's authoritative _is_running flag.
                # self.thread is never set (start() dispatches via job_queue),
                # so the old thread.is_alive() guard always evaluated False.
                _already_running = False
                _job_name = getattr(_db_update_worker, '_job_name', None)
                if _job_name:
                    try:
                        from core.job_queue import job_queue
                        _already_running = job_queue._is_running.get(_job_name, False)
                    except Exception:
                        pass
                if _already_running:
                    return jsonify({
                        "error": "Database update already in progress",
                        "current_progress": {
                            "artists": _db_update_worker.processed_artists,
                            "albums": _db_update_worker.processed_albums,
                            "tracks": _db_update_worker.processed_tracks
                        }
                    }), 409
        
        # Get provider instance
        provider = None
        try:
            from core.nexus_framework.plugin_loader import PluginRegistry
            active_servers = PluginRegistry.get_active_services_by_type('media_server')
            active_server = active_servers[0] if active_servers else None
            if active_server:
                provider = PluginRegistry.create_instance(active_server)
        except Exception as e:
            logger.error(f"Failed to create provider instance for {active_server}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail={"error": f"Media server '{active_server}' not available: {str(e)}"})
        
        if not provider:
            raise HTTPException(status_code=500, detail={"error": f"Media server '{active_server}' not available"})
        
        # Ensure connection
        try:
            if not provider.ensure_connection():
                msg = (
                    f"Could not connect to {active_server}. "
                    "Check your credentials in the provider settings."
                )
                logger.error(
                    "update-database: ensure_connection() returned False for %s — "
                    "likely expired or missing credentials.",
                    active_server,
                )
                raise HTTPException(status_code=500, detail={"error": msg})
        except Exception as e:
            logger.error(
                "update-database: connection to %s raised an exception: %s",
                active_server, e, exc_info=True,
            )
            raise HTTPException(status_code=500, detail={"error": f"Could not connect to {active_server}: {str(e)}"})
        
        # Import LibrarySyncService
        try:
            from services.library_sync_service import LibrarySyncService
        except ImportError as e:
            logger.error(f"Failed to import LibrarySyncService: {e}")
            raise HTTPException(status_code=500, detail={"error": "Database update module not available"})
        
        # Create and start worker
        try:
            with _db_update_lock:
                import threading
                _db_update_worker = threading.Thread(target=LibrarySyncService().sync_library)
                # Start worker thread
                _db_update_worker.start()
            
            return jsonify({
                "success": True,
                "server": active_server,
                "mode": mode,
                "message": f"Database update started in {mode} mode"
            }), 200
        except Exception as e:
            logger.error(f"Failed to start database update worker: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail={"error": f"Failed to start database update: {str(e)}"})
        
    except Exception as e:
        logger.error(f"Database update error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/update-status")
def get_database_update_status(request: Request):
    """
    Get current database update progress.
    
    Returns:
        {
            'running': bool,
            'progress': {
                'artists': int,
                'albums': int,
                'tracks': int,
                'successful': int,
                'failed': int
            },
            'server': str
        }
    """
    global _db_update_worker
    try:
        from core.nexus_framework.plugin_loader import PluginRegistry
        active_servers = PluginRegistry.get_active_services_by_type('media_server')
        active_server = active_servers[0] if active_servers else None
    except Exception as e:
        logger.error(f"Database update status error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})

    is_running = False
    stats = {
        "artists": 0, "albums": 0, "tracks": 0,
        "successful": 0, "failed": 0
    }
    
    with _db_update_lock:
        if _db_update_worker is not None:
            # Check if job is still in progress via job_queue
            _job_name = getattr(_db_update_worker, '_job_name', None)
            if _job_name:
                try:
                    from core.job_queue import job_queue
                    is_running = job_queue._is_running.get(_job_name, False)
                except Exception:
                    # Fallback to thread check if job_queue fails
                    is_running = False
            
            stats = {
                "artists": _db_update_worker.processed_artists,
                "albums": _db_update_worker.processed_albums,
                "tracks": _db_update_worker.processed_tracks,
                "successful": _db_update_worker.successful_operations,
                "failed": _db_update_worker.failed_operations,
                "warnings": getattr(_db_update_worker, "warnings", [])
            }

    return jsonify({
        "running": is_running,
        "progress": stats,
        "server": active_server
    }), 200


@router.post("/backfill-identifiers")
def backfill_identifiers():
    """
    Repair tracks that are missing their media-server external identifier (e.g. Plex
    ratingKey) due to the historical duplicate-row bug.

    Scans all tracks in the database that share a ``file_path`` with a track that
    already has an identifier for the active media server, then writes the missing
    ``ExternalIdentifier`` row so playlist sync can include them.

    Returns the number of new identifier rows written.
    """
    try:
        from core.nexus_framework.plugin_loader import PluginRegistry
        active_servers = PluginRegistry.get_active_services_by_type('media_server')
        active_server = active_servers[0] if active_servers else None
        
        if not active_server:
            raise HTTPException(status_code=400, detail={"error": "No active media server configured"})

        from database.music_database import get_database
        from database import LibraryManager
        
        db = get_database()
        library_manager = LibraryManager(db.session_factory)
        
        count = library_manager.backfill_provider_identifiers(active_server)
        
        return jsonify({
            "success": True,
            "count": count,
            "message": f"Successfully backfilled {count} identifiers for {active_server}"
        }), 200
    except Exception as e:
        logger.error(f"Backfill error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post("/update-cancel")
def cancel_database_update():
    """Cancel the running database update."""
    global _db_update_worker
    
    try:
        with _db_update_lock:
            if _db_update_worker is None:
                raise HTTPException(status_code=400, detail={"error": "No database update in progress"})
            
            # Check if running
            is_running = False
            _job_name = getattr(_db_update_worker, '_job_name', None)
            if _job_name:
                try:
                    from core.task_manager import job_queue
                    is_running = job_queue._is_running.get(_job_name, False)
                except Exception:
                    pass
            
            if not is_running:
                raise HTTPException(status_code=400, detail={"error": "No database update in progress"})
            
            # Stop the worker and kill job
            _db_update_worker.stop()
            if _job_name:
                from core.task_manager import job_queue
                job_queue.kill_job(_job_name)
            
            logger.info("Database update cancelled by user")
            
            return jsonify({
                "success": True,
                "message": "Database update cancelled"
            }), 200
            
    except Exception as e:
        logger.error(f"Database update cancel error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": str(e)})


# New Media Manager Routes

media_manager = MediaManagerService()

@router.get("/index")
def get_library_index(request: Request):
    """Get the full library hierarchy.
    DEPRECATED: Emits legacy nested payload. Use /api/v1/core/tracks?detail=true instead.
    """
    try:
        index = media_manager.get_library_index()
        response = jsonify(index)
        response.headers['Deprecation'] = 'true'
        response.headers['X-EchoSync-Warning'] = 'Legacy nested tracks payload'
        return response
    except Exception as e:
        logger.error(f"Error fetching library index: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.get("/stream/{track_id}")
def stream_track(track_id):
    """Stream a track file."""
    try:
        file_path = media_manager.get_track_stream(track_id)
        if not file_path:
            raise HTTPException(status_code=404, detail={"error": "Track not found or file missing"})

        return send_file(file_path)
    except Exception as e:
        logger.error(f"Error streaming track {track_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.delete("/{track_id}")
def delete_track_endpoint(track_id):
    """Delete a track."""
    try:
        success = media_manager.delete_track(track_id)
        if success:
            return {"success": True, "message": f"Track {track_id} deleted"}
        else:
            raise HTTPException(status_code=500, detail={"error": "Failed to delete track"})
    except Exception as e:
        logger.error(f"Error deleting track {track_id}: {e}")
        raise HTTPException(status_code=500, detail={"error": str(e)})




# FastAPI Router for SSE (as requested by user directives)

@router.get("/scan/stream")
async def stream_scan_progress():
    """
    SSE endpoint streaming the live progress of the Rust local ingestion scanner.
    """
    async def event_generator():
        try:
            last_status = None
            last_processed = -1

            while True:
                payload = scan_state_manager.get_state_payload()
                status = payload.get("status")
                processed = payload.get("tracks_processed", 0)

                # Yield only if status changed or processed tracks changed
                if status != last_status or processed != last_processed:
                    # Determine event type based on schemas
                    if status == "scanning":
                        event_type = "scan_progress"
                    elif status == "complete":
                        event_type = "scan_complete"
                    elif status == "failed":
                        event_type = "scan_error"
                    else:
                        event_type = "scan_idle"

                    # Format as SSE
                    yield f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"

                    last_status = status
                    last_processed = processed

                    if status in ("complete", "failed", "idle"):
                        break

                await asyncio.sleep(0.5)
        except (asyncio.CancelledError, GeneratorExit):
            logger.debug("SSE stream client disconnected cleanly (library scan).")
        except Exception as e:
            logger.error(f"SSE stream error: {e}", exc_info=True)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
