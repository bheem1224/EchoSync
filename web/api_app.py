"""Flask API app for the Svelte web UI.

Registers all route blueprints under /api. This supersedes the legacy
web_server.py UI and should be used as the backend for the Svelte frontend.
"""

import os
import ssl
import tempfile
import subprocess
import logging
from pathlib import Path
from flask import Flask

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

from core.plugin_loader import PluginLoader
from core.settings import config_manager
from core.job_queue import start_job_queue
from backend_entry import start_services
import threading
import asyncio

_backend_started = False

def create_app() -> Flask:
    app = Flask(__name__)
    
    # Configure sensitive logging filter for Werkzeug
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.addFilter(SensitiveRequestFilter())
    
    # Suppress verbose urllib3 debug logs (from PlexAPI/requests)
    logging.getLogger('urllib3.connectionpool').setLevel(logging.INFO)

    # Enable CORS for frontend (if flask-cors is installed)
    if CORS_AVAILABLE:
        CORS(app, origins=['http://localhost:5173', 'https://localhost:5173'])

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

    # Start Backend Services (Download Manager, Monitors) in a separate thread
    # We use WERKZEUG_RUN_MAIN to ensure we only run in the reloader child process
    # to avoid double execution (one in watcher, one in worker).
    # Since run_api.py defaults to debug=True (reloader enabled), this is the safest check.
    global _backend_started
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" and not _backend_started:
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

    return app


def generate_ephemeral_cert():
    """Generate a temporary self-signed certificate for internal backend↔frontend encryption.
    
    This cert is ONLY for encrypting traffic between the Svelte frontend and Flask backend.
    User-facing HTTPS should be handled by a reverse proxy (NPM, Traefik, Caddy, etc.).
    
    The certificate is ephemeral (regenerated on each backend restart) to:
    - Avoid config file clutter
    - Support rolling certs in production
    - Eliminate user confusion about cert purpose
    - Simplify deployment (no cert mounting needed)
    
    Returns:
        tuple: (cert_path, key_path) - Paths to temporary cert/key files
    """
    print("[SECURITY] Generating ephemeral self-signed certificate for internal API encryption...")
    print("[INFO] This cert is for backend↔frontend traffic only. Use reverse proxy for public HTTPS.")
    
    # Use temp directory - cert auto-cleaned on process exit
    temp_dir = tempfile.mkdtemp(prefix='soulsync_ssl_')
    cert_file = Path(temp_dir) / 'backend.crt'
    key_file = Path(temp_dir) / 'backend.key'
    
    try:
        # Generate self-signed cert (valid 1 day - regenerates on restart)
        subprocess.run([
            'openssl', 'req', '-x509', '-newkey', 'rsa:2048',
            '-keyout', str(key_file),
            '-out', str(cert_file),
            '-days', '1',  # Short-lived, regenerates on restart
            '-nodes',  # No passphrase
            '-subj', '/CN=soulsync-internal-api/O=SoulSync/C=US'
        ], check=True, capture_output=True, text=True)
        
        print(f"[SECURITY] Ephemeral cert generated (valid 24h, auto-regenerates)")
        print(f"[INFO] Frontend must accept self-signed certs for internal API calls")
        
        return str(cert_file), str(key_file)
        
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[ERROR] Failed to generate certificate: {e}")
        print("[ERROR] OpenSSL not found or failed. Install OpenSSL to enable internal HTTPS.")
        raise


def run_with_ssl(host='0.0.0.0', port=8000, debug=False):
    """Run Flask app with optional auto-generated ephemeral self-signed SSL cert.
    
    The certificate is regenerated on each startup (ephemeral) for simplicity.
    Frontend must accept self-signed certs for internal API calls.
    
    Can be skipped by setting DEV_MODE=true environment variable.
    """
    import os
    
    app = create_app()
    
    # Check if development mode is enabled (skip HTTPS)
    dev_mode = os.getenv('DEV_MODE', 'false').lower() in ('true', '1', 'yes')
    if dev_mode:
        print("[DEV] Development mode enabled - skipping HTTPS certificate")
        print("[WARNING] This is only safe for development. Use HTTPS in production!")
        print(f"[API] Starting HTTP backend on http://{host}:{port}/api")
        app.run(host=host, port=port, debug=debug)
        return
    
    try:
        cert_file, key_file = generate_ephemeral_cert()
        
        # Create SSL context
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
        
        print(f"[API] Starting HTTPS backend on https://{host}:{port}/api")
        print("[SECURITY] Internal traffic encrypted via ephemeral self-signed cert")
        print("[SECURITY] Use reverse proxy (NPM, Caddy, etc.) for public HTTPS")
        
        app.run(host=host, port=port, ssl_context=context, debug=debug)
        
    except Exception as e:
        print(f"[ERROR] Could not start with HTTPS: {e}")
        print("[FALLBACK] Starting HTTP backend (credentials UNENCRYPTED on wire)")
        print("[WARNING] This is only safe for development. Use HTTPS in production!")
        app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    # Check if HTTPS is explicitly disabled (for dev/testing)
    if os.getenv('DISABLE_INTERNAL_HTTPS') == 'true':
        print("[DEV MODE] Internal HTTPS disabled via DISABLE_INTERNAL_HTTPS env var")
        app = create_app()
        app.run(host="0.0.0.0", port=8000, debug=True)
    else:
        # Default: Run with ephemeral self-signed cert
        run_with_ssl(debug=True)
