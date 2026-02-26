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
import asyncio
import threading

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
from core.service_bootstrap import start_services

def run_backend_services_thread():
    """Run async background services in a separate thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(start_services())
        # Ideally, start_services() should return or loop forever?
        # If start_services() just initializes and returns, we might not need a loop.run_forever()
        # unless services rely on it.
        # DownloadManager usually spins up its own thread or task.
        # Let's assume start_services() handles the lifecycle.
    except Exception as e:
        print(f"[ERROR] Backend services failed: {e}")
    finally:
        loop.close()

if __name__ == "__main__":
    if dev_mode:
        print("[DEV] Development mode enabled - Log Level: DEBUG, CORS: *")
    else:
        print("[PROD] Production mode - Log Level: INFO")

    # Start background services
    # In Flask dev mode with reloader, this might run twice.
    # WERKZEUG_RUN_MAIN check prevents double execution in reloader child process.
    if not dev_mode or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        print("[API] Starting background services...")
        backend_thread = threading.Thread(target=run_backend_services_thread, daemon=True, name="BackendServices")
        backend_thread.start()

    print(f"[API] Starting HTTP backend on http://0.0.0.0:5000/api")

    app = create_app()
    # Run in standard HTTP mode
    # debug=True enables the reloader and debugger, which is only desired in DEV_MODE
    app.run(host="0.0.0.0", port=5000, debug=dev_mode)
