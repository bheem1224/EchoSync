from flask import Blueprint, jsonify, request, send_file
from web.services.library_service import LibraryAdapter
from services.media_manager import MediaManagerService
from core.settings import config_manager
from core.provider import ProviderRegistry
from core.tiered_logger import get_logger
import threading

logger = get_logger("library")
bp = Blueprint("library", __name__, url_prefix="/api/library")

@bp.get("/")
def library_overview():
    adapter = LibraryAdapter()
    data = adapter.overview()
    return jsonify(data), 200


@bp.post("/scan")
def trigger_library_scan():
    """
    Trigger a library scan/refresh on the active media server.
    
    Query params:
        - path: Optional library section path (Plex section ID, Jellyfin library name, etc.)
    """
    try:
        path = request.args.get("path")
        
        # Get active media server
        active_server = config_manager.get_active_media_server()
        if not active_server:
            return jsonify({"error": "No active media server configured"}), 400

        try:
            provider = ProviderRegistry.create_instance(active_server)
        except Exception as e:
            logger.error(f"Failed to create provider instance for {active_server}: {e}")
            return jsonify({"error": f"Media server '{active_server}' not available"}), 500
        
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
        return jsonify({"error": str(e)}), 500


@bp.get("/scan-status")
def get_library_scan_status():
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
        active_server = config_manager.get_active_media_server()
        if not active_server:
            return jsonify({"error": "No active media server configured"}), 400

        try:
            provider = ProviderRegistry.create_instance(active_server)
        except Exception as e:
            logger.error(f"Failed to create provider instance for {active_server}: {e}")
            return jsonify({"error": f"Media server '{active_server}' not available"}), 500
        
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
        return jsonify({"error": str(e)}), 500


# Global worker instance to track database update progress
_db_update_worker = None
_db_update_lock = threading.Lock()


@bp.post("/update-database")
def update_database():
    """
    Update SoulSync database from active media server library.
    
    Query params:
        - mode: 'full' or 'incremental' (default: 'incremental')
    """
    global _db_update_worker
    
    try:
        mode = request.args.get("mode", "incremental").lower()
        full_refresh = (mode == "full")
        
        # Get active media server
        try:
            active_server = config_manager.get_active_media_server()
        except Exception as e:
            logger.error(f"Failed to get active media server: {e}")
            return jsonify({"error": f"Failed to get active media server: {str(e)}"}), 500
        
        if not active_server:
            return jsonify({"error": "No active media server configured"}), 400
        
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
            from core.provider import ProviderRegistry
            provider = ProviderRegistry.create_instance(active_server)
        except Exception as e:
            logger.error(f"Failed to create provider instance for {active_server}: {e}", exc_info=True)
            return jsonify({"error": f"Media server '{active_server}' not available: {str(e)}"}), 500
        
        if not provider:
            return jsonify({"error": f"Media server '{active_server}' not available"}), 500
        
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
                return jsonify({"error": msg}), 500
        except Exception as e:
            logger.error(
                "update-database: connection to %s raised an exception: %s",
                active_server, e, exc_info=True,
            )
            return jsonify({"error": f"Could not connect to {active_server}: {str(e)}"}), 500
        
        # Import DatabaseUpdateWorker
        try:
            from core.database_update_worker import DatabaseUpdateWorker
        except ImportError as e:
            logger.error(f"Failed to import DatabaseUpdateWorker: {e}")
            return jsonify({"error": "Database update module not available"}), 500
        
        # Create and start worker
        try:
            with _db_update_lock:
                _db_update_worker = DatabaseUpdateWorker(
                    media_client=provider,
                    database_path=None,  # Use default path
                    full_refresh=full_refresh,
                    server_type=active_server,
                    force_sequential=False
                )
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
            return jsonify({"error": f"Failed to start database update: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Database update error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.get("/update-status")
def get_database_update_status():
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
        active_server = config_manager.get_active_media_server()
        
        with _db_update_lock:
            if _db_update_worker is None:
                return jsonify({
                    "running": False,
                    "progress": {
                        "artists": 0,
                        "albums": 0,
                        "tracks": 0,
                        "successful": 0,
                        "failed": 0
                    },
                    "server": active_server
                }), 200
            
            # Ask the job queue directly — it sets _is_running[job_name] before
            # spawning the thread and clears it in the finally block, so this is
            # accurate from the moment start() returns until the job finishes.
            is_running = False
            job_name = getattr(_db_update_worker, '_job_name', None)
            if job_name:
                try:
                    from core.job_queue import job_queue
                    is_running = job_queue._is_running.get(job_name, False)
                except Exception:
                    is_running = False
            if not is_running:
                # Fallback for any worker that didn't go through start() (e.g. tests):
                # infer from progress counters once the track list is fetched.
                try:
                    total = getattr(_db_update_worker, 'total_tracks', 0)
                    processed = getattr(_db_update_worker, 'processed_tracks', 0)
                    is_running = total > 0 and processed < total
                except Exception:
                    is_running = False
            
            return jsonify({
                "running": is_running,
                "progress": {
                    "artists": _db_update_worker.processed_artists,
                    "albums": _db_update_worker.processed_albums,
                    "tracks": _db_update_worker.processed_tracks,
                    "total": getattr(_db_update_worker, 'total_tracks', 0),
                    "successful": _db_update_worker.successful_operations,
                    "failed": _db_update_worker.failed_operations
                },
                "server": active_server
            }), 200
            
    except Exception as e:
        logger.error(f"Database update status error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.post("/backfill-identifiers")
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
        active_server = config_manager.get_active_media_server()
        if not active_server:
            return jsonify({"error": "No active media server configured"}), 400

        from database import MusicDatabase, LibraryManager
        db = MusicDatabase()
        library_manager = LibraryManager(db.session_factory)

        added = library_manager.backfill_provider_identifiers(active_server)
        return jsonify({
            "success": True,
            "provider": active_server,
            "identifiers_added": added,
            "message": f"Linked {added} missing '{active_server}' identifier(s) to existing tracks.",
        }), 200

    except Exception as e:
        logger.error("backfill_identifiers error: %s", e, exc_info=True)
        return jsonify({"error": str(e)}), 500


@bp.post("/update-cancel")
def cancel_database_update():
    """Cancel the running database update."""
    global _db_update_worker
    
    try:
        with _db_update_lock:
            if _db_update_worker is None:
                return jsonify({"error": "No database update in progress"}), 400
            
            # Check if running
            thread_obj = getattr(_db_update_worker, 'thread', None)
            if thread_obj is None or not (callable(getattr(thread_obj, 'is_alive', None)) and thread_obj.is_alive()):
                return jsonify({"error": "No database update in progress"}), 400
            
            # Stop the worker
            _db_update_worker.stop()
            _db_update_worker.wait()  # Wait for thread to finish
            
            logger.info("Database update cancelled by user")
            
            return jsonify({
                "success": True,
                "message": "Database update cancelled"
            }), 200
            
    except Exception as e:
        logger.error(f"Database update cancel error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# New Media Manager Routes

media_manager = MediaManagerService()

@bp.get("/index")
def get_library_index():
    """Get the full library hierarchy."""
    try:
        index = media_manager.get_library_index()
        return jsonify(index)
    except Exception as e:
        logger.error(f"Error fetching library index: {e}")
        return jsonify({"error": str(e)}), 500


@bp.get("/stream/<int:track_id>")
def stream_track(track_id):
    """Stream a track file."""
    try:
        file_path = media_manager.get_track_stream(track_id)
        if not file_path:
            return jsonify({"error": "Track not found or file missing"}), 404

        return send_file(file_path)
    except Exception as e:
        logger.error(f"Error streaming track {track_id}: {e}")
        return jsonify({"error": str(e)}), 500


@bp.delete("/<int:track_id>")
def delete_track_endpoint(track_id):
    """Delete a track."""
    try:
        success = media_manager.delete_track(track_id)
        if success:
            return jsonify({"success": True, "message": f"Track {track_id} deleted"}), 200
        else:
            return jsonify({"error": "Failed to delete track"}), 500
    except Exception as e:
        logger.error(f"Error deleting track {track_id}: {e}")
        return jsonify({"error": str(e)}), 500
