import os
import sys
import threading
from typing import Optional
from flask import Flask, request
from werkzeug.serving import make_server

from core.tiered_logger import get_logger
from core.oauth.cert_manager import ensure_ssl_certs

logger = get_logger("oauth_sidecar")

app = Flask("oauth_sidecar")

@app.route("/api/oauth/callback/<provider_id>")
def oauth_callback(provider_id: str):
    """
    Universal callback route for OAuth. Looks up the provider instance from ProviderRegistry
    and invokes its `handle_oauth_callback` method with request arguments.
    """
    from core.provider import ProviderRegistry

    # Try to get an existing instance or create one if it doesn't exist
    provider = ProviderRegistry.create_instance(provider_id)
    if not provider:
         logger.error(f"Received OAuth callback for unknown or uninitialized provider: {provider_id}")
         return "Provider not found or not initialized", 404

    try:
         # Pass request.args (dict-like) down to the provider
         return provider.handle_oauth_callback(request.args)
    except NotImplementedError:
         logger.error(f"Provider '{provider_id}' does not implement handle_oauth_callback")
         return "Callback handling not implemented for this provider", 501
    except Exception as e:
         logger.error(f"Error handling OAuth callback for '{provider_id}': {e}", exc_info=True)
         return f"Error processing callback: {e}", 500


class SidecarServerThread(threading.Thread):
    def __init__(self, host: str, port: int, cert_path: str, key_path: str):
        super().__init__(daemon=True, name="OAuthSidecar")
        self.host = host
        self.port = port
        self.cert_path = cert_path
        self.key_path = key_path
        self.server = None

    def run(self):
        try:
             # use_reloader=False and threaded=True to prevent issues with main app
             self.server = make_server(
                 self.host,
                 self.port,
                 app,
                 threaded=True,
                 ssl_context=(self.cert_path, self.key_path)
             )
             logger.info(f"OAuth sidecar listening securely on https://{self.host}:{self.port}")
             self.server.serve_forever()
        except OSError as e:
             if e.errno == 98: # Address already in use
                  logger.error(f"CRITICAL: OAuth sidecar port {self.port} is already in use. OAuth redirects will fail. Please kill any lingering processes.")
             else:
                  logger.error(f"Failed to start OAuth sidecar on port {self.port}: {e}")
        except Exception as e:
             logger.error(f"Unexpected error starting OAuth sidecar: {e}", exc_info=True)

def start_oauth_sidecar(host: str = "0.0.0.0", port: int = 5001, data_dir: str = "data"):
    """
    Initializes SSL certificates and starts the sidecar Flask app in a daemonized thread.
    """
    try:
         cert_path, key_path = ensure_ssl_certs(data_dir)
         sidecar_thread = SidecarServerThread(host, port, cert_path, key_path)
         sidecar_thread.start()
    except Exception as e:
         logger.error(f"Could not start OAuth sidecar: {e}", exc_info=True)
