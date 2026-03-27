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
# Priority: LOG_LEVEL env var > DEV_MODE=true > config.json level > INFO
from core.tiered_logger import setup_logging
logging_config = config_manager.get_logging_config()

_env_log_level = os.getenv('LOG_LEVEL', '').upper()
if _env_log_level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
    log_level = _env_log_level
elif dev_mode:
    log_level = 'DEBUG'
else:
    log_level = logging_config.get('level', 'INFO')

setup_logging(level=log_level, log_file=logging_config.get("path"))

# Run Phase 1 Database Migrations securely
from core.migrations import run_migrations, run_auto_migrations
run_migrations()

# Run Alembic migrations unconditionally — no-op if already at head.
run_auto_migrations()

# Re-apply SoulSync's logging config after Alembic migrations, as a safety net.
# Alembic's fileConfig() may adjust logger levels even with disable_existing_loggers=False.
setup_logging(level=log_level, log_file=logging_config.get("path"))

# Run Phase 2: working.db column migrations (must run after working DB engine is initialised)
from database.working_database import get_working_database
from core.migrations import run_working_db_migrations
run_working_db_migrations(get_working_database().engine)

from web.api_app import create_app

# Ensure SSL certs exist and start OAuth sidecar
from core.oauth.sidecar import start_oauth_sidecar
start_oauth_sidecar()

if __name__ == "__main__":
    if dev_mode:
        print("[DEV] Development mode enabled - Log Level: DEBUG, CORS: *")
    else:
        print("[PROD] Production mode - Log Level: INFO")

    print(f"[API] Starting HTTP backend on http://0.0.0.0:5000/api")

    app = create_app()
    # Run in standard HTTP mode
    # debug=True enables the reloader and debugger, which is only desired in DEV_MODE
    app.run(host="0.0.0.0", port=5000, debug=dev_mode)
