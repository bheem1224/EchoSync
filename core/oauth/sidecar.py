import os
import sys
import threading
from typing import Optional
import urllib.parse
from flask import Flask, request, redirect
from werkzeug.serving import make_server

from core.tiered_logger import get_logger
from core.oauth.cert_manager import ensure_ssl_certs
from core.network_utils import get_lan_ip, get_main_app_port

logger = get_logger("oauth_sidecar")

app = Flask("oauth_sidecar")

@app.route("/api/oauth/callback/<provider_name>")
def oauth_callback(provider_name: str):
    """
    Universal callback route for OAuth. Acts as a dumb proxy,
    redirecting to the main application via 302 redirect.
    """
    lan_ip = get_lan_ip()
    main_port = get_main_app_port()

    # Construct redirect URL
    query_string = request.query_string.decode('utf-8')
    redirect_url = f"http://{lan_ip}:{main_port}/api/{provider_name}/callback"
    if query_string:
        redirect_url += f"?{query_string}"

    logger.info(f"OAuth sidecar proxying callback for {provider_name} to {redirect_url}")
    return redirect(redirect_url, code=302)


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
