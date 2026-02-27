#!/usr/bin/env python
"""
Simple launcher for the SoulSync Flask API backend.

Usage:
    python run_api.py                    # Run in standard HTTP mode (Production)
    DEV_MODE=true python run_api.py      # Run in Development mode (Verbose logs, CORS, Debugger)
"""

from dotenv import load_dotenv
from pathlib import Path
import os

# Load .env file from project root explicitly so SOULSYNC_* vars are available before config_manager
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)

# Determine development mode
dev_mode = os.getenv('DEV_MODE', 'false').lower() in ('true', '1', 'yes')

from core.settings import config_manager

# Setup logging from config.json settings (loaded via config_manager)
# DEV_MODE determines the log level override
from core.tiered_logger import setup_logging
logging_config = config_manager.get_logging_config()

# Task 2: DEV_MODE=true -> Level DEBUG. DEV_MODE=false -> Level INFO (Production).
log_level = "DEBUG" if dev_mode else logging_config.get("level", "INFO")

setup_logging(level=log_level, log_file=logging_config.get("path"))

from web.api_app import create_app

if __name__ == "__main__":
    if dev_mode:
        print("[DEV] Development mode enabled - Log Level: DEBUG, CORS: *")
    else:
        print("[PROD] Production mode - Log Level: INFO")

    print(f"[API] Starting HTTP backend on http://0.0.0.0:5000/api")

    app = create_app()

    # Generate SSL certs for the sidecar
    from core.cert_manager import generate_ssl_certs
    cert_path, key_path = generate_ssl_certs()

    # Start the OAuth Sidecar App in a background thread if certs exist
    if cert_path and key_path:
        print(f"[API] Starting HTTPS OAuth Sidecar on https://0.0.0.0:5001")
        from web.oauth_sidecar import sidecar_app
        import threading

        def run_sidecar():
            # Use Werkzeug's SSL context
            ssl_context = (cert_path, key_path)
            # Disable Werkzeug's own logging for the sidecar so we don't get duplicate request logs
            import logging
            log = logging.getLogger('werkzeug')
            log.setLevel(logging.ERROR)

            sidecar_app.run(host="0.0.0.0", port=5001, ssl_context=ssl_context, debug=False, use_reloader=False)

        sidecar_thread = threading.Thread(target=run_sidecar, daemon=True, name="OAuthSidecar")
        sidecar_thread.start()
    else:
        print("[WARN] Failed to generate or locate SSL certs. OAuth Sidecar will not start.")

    # Run in standard HTTP mode
    # debug=True enables the reloader and debugger, which is only desired in DEV_MODE
    app.run(host="0.0.0.0", port=5000, debug=dev_mode)
