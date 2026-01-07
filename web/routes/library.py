from flask import Blueprint, jsonify, request
from web.services.library_service import LibraryAdapter
from config.settings import config_manager
from core.provider_registry import ProviderRegistry
from utils.logging_config import get_logger
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
        
        # Try to get provider instance (prefer AdapterRegistry for instances)
        provider = None
        try:
            # Try AdapterRegistry first (instance-based)
            provider = AdapterRegistry.create_instance(active_server)
        except Exception as e:
            logger.debug(f"AdapterRegistry lookup failed for {active_server}: {e}")
            # Fall back to ProviderRegistry (class-based instantiation)
            try:
                provider = ProviderRegistry.create_instance(active_server)
            except Exception as e2:
                logger.error(f"Failed to create provider instance for {active_server}: {e2}")
                return jsonify({"error": f"Media server '{active_server}' not available"}), 500
        
        if not provider:
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
        
        # Try to get provider instance (prefer AdapterRegistry for instances)
        provider = None
        try:
            # Try AdapterRegistry first (instance-based)
            provider = AdapterRegistry.create_instance(active_server)
        except Exception as e:
            logger.debug(f"AdapterRegistry lookup failed for {active_server}: {e}")
            # Fall back to ProviderRegistry (class-based instantiation)
            try:
                provider = ProviderRegistry.create_instance(active_server)
            except Exception as e2:
                logger.error(f"Failed to create provider instance for {active_server}: {e2}")
                return jsonify({"error": f"Media server '{active_server}' not available"}), 500
        
        if not provider:
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
        active_server = config_manager.get_active_media_server()
        if not active_server:
            return jsonify({"error": "No active media server configured"}), 400
        
        # Check if update is already running
        with _db_update_lock:
            if _db_update_worker is not None:
                # Check if thread is alive (handle both Qt and headless modes)
                thread_obj = getattr(_db_update_worker, 'thread', None)
                if thread_obj is not None and callable(getattr(thread_obj, 'is_alive', None)) and thread_obj.is_alive():
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
            provider = ProviderRegistry.create_instance(active_server)
        except Exception as e:
            logger.error(f"Failed to create provider instance for {active_server}: {e}")
            return jsonify({"error": f"Media server '{active_server}' not available"}), 500
        
        if not provider:
            return jsonify({"error": f"Media server '{active_server}' not available"}), 500
        
        # Ensure connection
        if not provider.ensure_connection():
            return jsonify({"error": f"Could not connect to {active_server}"}), 500
        
        # Import DatabaseUpdateWorker
        from core.database_update_worker import DatabaseUpdateWorker
        
        # Create and start worker
        with _db_update_lock:
            _db_update_worker = DatabaseUpdateWorker(
                media_client=provider,
                database_path=None,  # Use default path
                full_refresh=full_refresh,
                server_type=active_server,
                force_sequential=True  # Force sequential for web server to avoid threading issues
            )
            
            # Start worker thread
            _db_update_worker.start()
        
        logger.info(f"Database update started ({mode} mode) for {active_server}")
        
        return jsonify({
            "success": True,
            "server": active_server,
            "mode": mode,
            "message": f"Database update started in {mode} mode"
        }), 200
        
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
            
            # Check if thread is alive (handle both Qt and headless modes)
            is_running = False
            thread_obj = getattr(_db_update_worker, 'thread', None)
            if thread_obj is not None and callable(getattr(thread_obj, 'is_alive', None)):
                is_running = thread_obj.is_alive()
            
            return jsonify({
                "running": is_running,
                "progress": {
                    "artists": _db_update_worker.processed_artists,
                    "albums": _db_update_worker.processed_albums,
                    "tracks": _db_update_worker.processed_tracks,
                    "successful": _db_update_worker.successful_operations,
                    "failed": _db_update_worker.failed_operations
                },
                "server": active_server
            }), 200
            
    except Exception as e:
        logger.error(f"Database update status error: {e}", exc_info=True)
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
