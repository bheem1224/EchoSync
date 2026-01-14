#!/usr/bin/env python
"""
Simple launcher for the SoulSync Flask API backend.

Usage:
    python run_api.py                    # Run with HTTPS (self-signed cert)
    DISABLE_INTERNAL_HTTPS=true python run_api.py  # Run with HTTP (dev only)
"""

from dotenv import load_dotenv
from pathlib import Path
import os

# Load .env file from project root explicitly so SOULSYNC_* vars are available before config_manager
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env", override=True)
print("SOULSYNC_CONFIG_DIR env:", os.environ.get("SOULSYNC_CONFIG_DIR"))
print("SOULSYNC_DATA_DIR env:", os.environ.get("SOULSYNC_DATA_DIR"))

from core.settings import config_manager

# Setup logging from config.json settings (loaded via config_manager, which now honors .env)
from core.tiered_logger import setup_logging
logging_config = config_manager.get_logging_config()
setup_logging(level=logging_config.get("level", "INFO"), log_file=logging_config.get("path"))

from web.api_app import run_with_ssl, create_app

if __name__ == "__main__":
    # Check if development mode is enabled (skips HTTPS)
    dev_mode = os.getenv('DEV_MODE', 'false').lower() in ('true', '1', 'yes')
    
    if dev_mode:
        print("[DEV] Development mode enabled - skipping HTTPS")
        app = create_app()
        app.run(host="0.0.0.0", port=8000, debug=True)
    else:
        # Default: Run with ephemeral self-signed cert, fallback to HTTP on error
        run_with_ssl(debug=True)
