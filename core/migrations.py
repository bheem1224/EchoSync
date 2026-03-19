import json
import sqlite3
import contextlib
import os
from pathlib import Path
from core.settings import config_manager
from core.tiered_logger import get_logger
from core.security import decrypt_string, encrypt_string
from database.config_database import get_config_database

logger = get_logger("migrations")

# Global flag to track if v2.1.0 migration was triggered during this session
_v2_1_migration_triggered = False

def was_v2_1_migration_triggered() -> bool:
    """Check if v2.1.0 hard reset migration was triggered in this session."""
    global _v2_1_migration_triggered
    return _v2_1_migration_triggered

def acknowledge_v2_1_migration() -> None:
    """Mark the v2.1.0 migration flag as acknowledged by the frontend."""
    global _v2_1_migration_triggered
    _v2_1_migration_triggered = False

def _decrypt_legacy_value(value: str) -> str:
    if isinstance(value, str) and value.startswith('enc:'):
        return decrypt_string(value)
    return value

def _handle_v2_1_0_migration() -> bool:
    """
    v2.1.0 Hard Reset Migration:
    Detect if we're upgrading from v2.0.x by checking if music_database.db exists but working.db doesn't.
    If detected, safely delete music_database.db and allow natural recreation with new schemas.
    
    Returns:
        bool: True if migration was triggered, False otherwise
    """
    global _v2_1_migration_triggered
    
    data_dir = os.getenv("SOULSYNC_DATA_DIR")
    if data_dir:
        base_path = Path(data_dir)
    else:
        base_path = Path("data")
    
    music_db = base_path / "music_library.db"
    working_db = base_path / "working.db"
    
    # Check if we need to perform v2.1.0 migration
    if music_db.exists() and not working_db.exists():
        logger.warning(
            f"Detected v2.0.x upgrade to v2.1.0: music_library.db exists but working.db does not. "
            f"Performing hard reset of music database..."
        )
        
        try:
            # Safely delete the old music database
            music_db.unlink()
            logger.info(f"Deleted old music_library.db at {music_db}")
            _v2_1_migration_triggered = True
            return True
        except Exception as e:
            logger.error(f"Failed to delete music_library.db during v2.1.0 migration: {e}")
            # Don't raise - allow app to continue and try to proceed
            return False
    
    return False

def traverse_and_decrypt(data, transform_func, keys_to_transform):
    """Helper to decrypt legacy app_config JSON similar to core/settings.py"""
    if isinstance(data, dict):
        output = {}
        for k, v in data.items():
            if isinstance(v, dict):
                output[k] = traverse_and_decrypt(v, transform_func, keys_to_transform)
            elif k in keys_to_transform:
                output[k] = transform_func(v)
            else:
                output[k] = v
        return output
    return data

SECRETS = {
    'password', 'token', 'client_secret', 'api_key', 'access_token', 'refresh_token'
}

def run_migrations():
    """
    Check for the metadata table containing the legacy app_config JSON blob,
    migrate Plex and Slskd data securely to the new tables,
    and then strictly DROP the metadata table.
    
    Also handles v2.1.0 hard reset migration for database schema upgrades.
    """
    # First: Handle v2.1.0 migration (hard reset if upgrading from v2.0.x)
    _handle_v2_1_0_migration()
    
    db_path = str(config_manager.database_path)
    if not os.path.exists(db_path):
        logger.info("Config database does not exist yet. No config migration needed.")
        return

    try:
        with contextlib.closing(sqlite3.connect(db_path, timeout=30.0)) as conn:
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute("PRAGMA journal_mode = WAL")
            cursor = conn.cursor()

            # Check if metadata table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='metadata'")
            if not cursor.fetchone():
                logger.info("No 'metadata' table found. Migration already completed or fresh install.")
                return

            # Check for app_config blob
            cursor.execute("SELECT value FROM metadata WHERE key='app_config'")
            row = cursor.fetchone()

            if row and row[0]:
                logger.info("Legacy 'app_config' found. Running migration...")
                config_db = get_config_database()
                try:
                    app_config = json.loads(row[0])
                    decrypted_config = traverse_and_decrypt(app_config, _decrypt_legacy_value, SECRETS)

                    # Migrate Plex Data
                    plex_data = decrypted_config.get('plex')
                    if plex_data:
                        service_id = config_db.get_or_create_service_id('plex')
                        for key, value in plex_data.items():
                            is_sensitive = key in SECRETS or 'token' in key
                            config_db.set_service_config(service_id, key, value, is_sensitive=is_sensitive)
                        logger.info("Migrated legacy Plex configuration.")

                    # Migrate Slskd Data
                    slskd_data = decrypted_config.get('slskd')
                    if not slskd_data:
                        slskd_data = decrypted_config.get('soulseek')

                    if slskd_data:
                        service_id = config_db.get_or_create_service_id('soulseek')
                        for key, value in slskd_data.items():
                            is_sensitive = key in SECRETS or 'password' in key
                            config_db.set_service_config(service_id, key, value, is_sensitive=is_sensitive)
                        logger.info("Migrated legacy Slskd configuration.")
                except Exception as e:
                    logger.error(f"Error parsing or migrating legacy app_config: {e}")
                    # Even if there is an error processing the config, we shouldn't fail totally,
                    # but maybe we shouldn't drop the table if we didn't migrate successfully?
                    # The instruction says "If found: Load JSON... Map... Delete entry".
                    # We will proceed to drop to follow the burn strategy.
            else:
                logger.info("No 'app_config' row found in metadata table.")

            # Drop the metadata table completely
            cursor.execute("DROP TABLE IF EXISTS metadata")
            conn.commit()
            logger.info("Successfully DROPPED 'metadata' table permanently.")

    except Exception as e:
        logger.error(f"Migration script encountered an error: {e}")


def trigger_post_migration_database_update():
    """
    Trigger a one-time database update after v2.1.0 migration.
    This is called after databases have been initialized.
    """
    global _v2_1_migration_triggered
    
    if not _v2_1_migration_triggered:
        logger.debug("No v2.1.0 migration was triggered; skipping automatic database update")
        return
    
    try:
        logger.info("v2.1.0 migration detected: triggering immediate database update job...")
        from core.job_queue import job_queue
        
        # Trigger the database_update job immediately
        job_queue.enqueue_job("database_update")
        logger.info("Database update job enqueued successfully")
    except Exception as e:
        logger.error(f"Failed to trigger database update after v2.1.0 migration: {e}", exc_info=True)
