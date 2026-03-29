#!/usr/bin/env python
"""
Simple launcher for the SoulSync Flask API backend.

Usage:
    python run_api.py                    # Run in standard HTTP mode (Production)
    DEV_MODE=true python run_api.py      # Run in Development mode (Debug logs, CORS, Debugger)
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

# Phase 0: Safe Mode Circuit Breaker
import sys
from core.tiered_logger import get_logger

logger = get_logger("boot")
lock_file = config_manager.config_dir / "booting.lock"
safe_mode = False

if lock_file.exists():
    logger.critical("FATAL LOOP DETECTED: 'booting.lock' found from a previous crashed startup.")
    logger.critical("Booting into SAFE MODE. All community plugins will be disabled.")
    safe_mode = True
else:
    logger.info("Writing boot lock file...")
    try:
        lock_file.touch()
    except Exception as e:
        logger.warning(f"Could not create boot lock file: {e}")

# Inject safe mode into the app configuration dynamically so other components (like PluginLoader) can see it
# Alternatively, we could set an environment variable or directly configure the PluginLoader.
# Setting it in environment is reliable.
if safe_mode:
    os.environ['SOULSYNC_SAFE_MODE'] = '1'


# Run Phase 1 Database Migrations securely
from core.migrations import run_migrations
run_migrations()

# Pillar 1: The Auto-Migrator
from core.migrations import run_auto_migrations
run_auto_migrations()

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

    # Initialization successful — clear the boot lock unconditionally so the next
    # boot starts clean.  Critically, this must also run when we booted into Safe
    # Mode: Safe Mode is meant to survive *one* bad boot cycle, not permanently
    # brick the server.  If this boot itself crashes before reaching here, the
    # lock survives and the next restart will enter Safe Mode again as designed.
    if lock_file.exists():
        try:
            lock_file.unlink()
            if safe_mode:
                logger.info("Safe Mode boot complete. Removed boot lock file — next boot will be normal.")
            else:
                logger.info("Boot successful. Removed boot lock file.")
        except Exception as e:
            logger.error(f"Failed to remove boot lock file: {e}")

    # Run in standard HTTP mode
    # debug=True enables the reloader and debugger, which is only desired in DEV_MODE
    app.run(host="0.0.0.0", port=5000, debug=dev_mode)
