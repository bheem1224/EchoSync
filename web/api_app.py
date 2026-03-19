"""Flask API app for the Svelte web UI.

Registers all route blueprints under /api. This supersedes the legacy
web_server.py UI and should be used as the backend for the Svelte frontend.
"""

import os
import logging
from pathlib import Path
from flask import Flask, send_from_directory
from core.settings import config_manager

try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False
    print("[WARN] flask-cors not installed. Install with: pip install flask-cors")

class SensitiveRequestFilter(logging.Filter):
    """Filter to downgrade sensitive request logs to DEBUG level."""
    def filter(self, record):
        msg = record.getMessage()
        # Check for sensitive endpoints/params
        if "/api/spotify/callback" in msg or "code=" in msg or "token=" in msg:
            # Downgrade to DEBUG level so it doesn't show in standard INFO logs
            record.levelno = logging.DEBUG
            record.levelname = "DEBUG"
        return True

# Standard core blueprints
from web.routes.providers import bp as providers_bp
from web.routes.jobs import bp as jobs_bp
from web.routes.tracks import bp as tracks_bp
from web.routes.search import bp as search_bp
from web.routes.system import bp as system_bp
from web.routes.sync import bp as sync_bp
from web.routes.playlists import bp as playlists_bp
from web.routes.accounts import bp as accounts_bp
from web.routes.media_server import bp as media_server_bp
from web.routes.library import bp as library_bp
from web.routes.metadata import bp as metadata_bp
from web.routes.manager import bp as manager_bp
from web.routes.downloads import bp as downloads_bp
from web.routes.suggestions import bp as suggestions_bp

from core.plugin_loader import PluginLoader
from core.settings import config_manager
from core.job_queue import start_job_queue
from core.backend_services import start_services
import threading
import asyncio

_backend_started = False

def create_app() -> Flask:
    # configure static folder for the compiled Svelte frontend build
    # path is relative to this file; container working dir is /app
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), '../webui/build'),
        static_url_path='/static_assets_placeholder' # Avoid conflict with catch-all route at /
    )
    
    # Configure sensitive logging filter for Werkzeug
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addFilter(SensitiveRequestFilter())
    
    # Suppress verbose urllib3 debug logs (from PlexAPI/requests)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.INFO)

    # Enable CORS for frontend (if flask-cors is installed)
    if CORS_AVAILABLE:
        dev_mode = os.getenv('DEV_MODE', 'false').lower() in ('true', '1', 'yes')

        if dev_mode:
            # Allow all origins in DEV_MODE
            CORS(app, resources={r"/*": {"origins": "*"}})
            print("[DEV] CORS enabled for ALL origins")
        else:
            # Production: Allow origins defined in config or default to same-origin
            # If no cors_origins config is present, we don't enable global CORS,
            # effectively enforcing same-origin policy (unless handled by proxy).
            allowed_origins = config_manager.get('cors_origins', [])
            if allowed_origins:
                 CORS(app, origins=allowed_origins)
            else:
                 # Minimal fallback for typical local setups if needed,
                 # or simply do nothing to enforce same-origin.
                 # User requested "default to same-origin".
                 pass

    # Register Core API blueprints
    app.register_blueprint(providers_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(tracks_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(sync_bp)
    app.register_blueprint(playlists_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(media_server_bp)
    app.register_blueprint(library_bp)
    app.register_blueprint(metadata_bp)
    app.register_blueprint(manager_bp)
    app.register_blueprint(downloads_bp)
    app.register_blueprint(suggestions_bp)
    
    # Initialize databases (triggers v2.1.0 migration if needed)
    try:
        from database.music_database import get_database
        from database.working_database import get_working_database
        get_database()  # Initialize and create music_database
        get_working_database()  # Initialize and create working_database
    except Exception as e:
        print(f"[ERROR] Failed to initialize databases: {e}")
        raise
    
    # Trigger post-migration tasks (e.g., database_update job if v2.1.0 was migrated)
    try:
        from core.migrations import trigger_post_migration_database_update
        trigger_post_migration_database_update()
    except Exception as e:
        print(f"[WARN] Failed to trigger post-migration tasks: {e}")
    
    # Initialize Plugin Loader
    # Determine app root (parent of 'web/')
    app_root = Path(__file__).parent.parent
    loader = PluginLoader(app_root)
    
    # Load Disabled List first
    from core.provider import ProviderRegistry
    disabled_providers = config_manager.get_disabled_providers()
    ProviderRegistry.set_disabled_providers(disabled_providers)
    
    # Scan and Load Providers/Plugins
    loader.load_all()
    
    # Register Dynamic Blueprints from Providers/Plugins
    for bp in loader.get_all_blueprints():
        try:
            app.register_blueprint(bp)
        except Exception as e:
            print(f"[ERROR] Failed to register blueprint {bp.name}: {e}")

    # Load scheduled sync jobs on startup
    from web.routes.playlists import load_scheduled_syncs_on_startup
    try:
        load_scheduled_syncs_on_startup()
    except Exception as e:
        print(f"[WARN] Failed to load scheduled syncs: {e}")

    # Start the job queue for async task execution
    start_job_queue()
    
    # Register system jobs with job_queue
    try:
        from core.system_jobs import register_all_system_jobs
        register_all_system_jobs()
    except Exception as e:
        print(f"[WARN] Failed to register system jobs: {e}")
    
    try:
        from services.download_manager import register_download_manager_job
        register_download_manager_job()
    except Exception as e:
        print(f"[WARN] Failed to register download manager job: {e}")
    
    # Register metadata enhancer service
    try:
        from services.metadata_enhancer import register_metadata_enhancer_service
        register_metadata_enhancer_service()
    except Exception as e:
        print(f"[WARN] Failed to register metadata enhancer service: {e}")

    # Register Auto Import Service
    try:
        from services.auto_importer import register_auto_import_service
        register_auto_import_service()
    except Exception as e:
        print(f"[WARN] Failed to register auto import service: {e}")

    # Start Backend Services (Download Manager, Monitors) in a separate thread
    # In debug mode (reloader enabled), WERKZEUG_RUN_MAIN is set in the child process.
    # In production mode (no reloader), WERKZEUG_RUN_MAIN is not set.
    # We want to run services in:
    # 1. Production mode (DEV_MODE=false)
    # 2. Debug mode's child process (DEV_MODE=true AND WERKZEUG_RUN_MAIN="true")
    global _backend_started

    dev_mode = os.getenv('DEV_MODE', 'false').lower() in ('true', '1', 'yes')
    is_reloader_child = os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    should_start = (not dev_mode) or is_reloader_child

    if should_start and not _backend_started:
        def run_backend_services():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(start_services())
            except Exception as e:
                print(f"[ERROR] Backend services failed: {e}")
            finally:
                loop.close()

        backend_thread = threading.Thread(target=run_backend_services, daemon=True, name="BackendServices")
        backend_thread.start()
        _backend_started = True
        print("[INFO] Backend services thread started")


    # ------------------------------------------------------------
    # SPA support: Serve static files for any non-API route
    # ------------------------------------------------------------
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve_frontend(path):
        # If the path starts with "api/", let Flask return its own 404
        if path.startswith('api/'):
            return {"error": "API route not found"}, 404

        # Explicitly handle app assets to prevent fallback to index.html
        # SvelteKit with adapter-static uses _app/immutable/...
        if path.startswith('_app/') or path.startswith('assets/'):
             if path and os.path.exists(os.path.join(app.static_folder, path)):
                 return send_from_directory(app.static_folder, path)
             else:
                 return "Asset not found", 404

        # serve the requested file if it exists under static_folder
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)

        # otherwise fall back to index.html (for client-side routing)
        # This handles nested routes like /settings/servers by serving the main SPA entry point
        index_file = os.path.join(app.static_folder, 'index.html')
        if os.path.exists(index_file):
            return send_from_directory(app.static_folder, 'index.html')

        return "Frontend build not found", 404

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
