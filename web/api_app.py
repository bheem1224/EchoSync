"""Flask API app for the Svelte web UI.

Registers all route blueprints under /api. This supersedes the legacy
web_server.py UI and should be used as the backend for the Svelte frontend.
"""

import os
import ssl
import tempfile
import subprocess
from pathlib import Path
from flask import Flask

try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False
    print("[WARN] flask-cors not installed. Install with: pip install flask-cors")

from web.routes.providers import bp as providers_bp
from web.routes.jobs import bp as jobs_bp
from web.routes.tracks import bp as tracks_bp
from web.routes.search import bp as search_bp
from web.routes.system import bp as system_bp
from web.routes.sync import bp as sync_bp
from web.routes.playlists import bp as playlists_bp
from web.routes.accounts import bp as accounts_bp
from web.routes.tidal_accounts import bp as tidal_accounts_bp
from web.routes.plex_settings import bp as plex_settings_bp
from web.routes.navidrome_settings import bp as navidrome_settings_bp
from web.routes.jellyfin_settings import bp as jellyfin_settings_bp
from web.routes.media_server import bp as media_server_bp
import importlib
import providers as providers_pkg


def create_app() -> Flask:
    app = Flask(__name__)
    
    # Enable CORS for frontend (if flask-cors is installed)
    if CORS_AVAILABLE:
        CORS(app, origins=['http://localhost:5173', 'https://localhost:5173'])

    # Register API blueprints
    app.register_blueprint(providers_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(tracks_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(system_bp)
    app.register_blueprint(sync_bp)
    app.register_blueprint(playlists_bp)
    app.register_blueprint(accounts_bp)
    app.register_blueprint(tidal_accounts_bp)
    app.register_blueprint(plex_settings_bp)
    app.register_blueprint(navidrome_settings_bp)
    app.register_blueprint(jellyfin_settings_bp)
    app.register_blueprint(media_server_bp)
    
    # Dynamically register provider-specific blueprints (e.g., OAuth endpoints)
    for prov_name in getattr(providers_pkg, '__all__', []):
        try:
            mod = importlib.import_module(f'providers.{prov_name}')
            # If provider package exposes an oauth_bp or oauth_routes.bp, register it
            bp = getattr(mod, 'oauth_bp', None)
            if bp:
                app.register_blueprint(bp)
        except Exception:
            # Ignore providers that don't expose additional routes
            continue
    
    # Instantiate provider clients so they self-register in plugin_registry
    _init_provider_clients()

    return app


def _init_provider_clients():
    """Instantiate provider clients to trigger self-registration in plugin_registry."""
    from providers.spotify.client import SpotifyClient
    from providers.plex.client import PlexClient
    from providers.jellyfin.client import JellyfinClient
    from providers.navidrome.client import NavidromeClient
    from providers.soulseek.client import SoulseekClient
    try:
        from providers.tidal.client import TidalClient
        TidalClient()  # Instantiate to trigger self-registration
    except Exception:
        pass  # Tidal may not be configured
    
    SpotifyClient()
    PlexClient()
    JellyfinClient()
    NavidromeClient()
    SoulseekClient()


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
    """Run Flask app with auto-generated ephemeral self-signed SSL cert.
    
    The certificate is regenerated on each startup (ephemeral) for simplicity.
    Frontend must accept self-signed certs for internal API calls.
    """
    app = create_app()
    
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
