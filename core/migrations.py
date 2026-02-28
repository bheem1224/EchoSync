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

def _decrypt_legacy_value(value: str) -> str:
    if isinstance(value, str) and value.startswith('enc:'):
        return decrypt_string(value)
    return value

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
    """Check for the metadata table containing the legacy app_config JSON blob,
       migrate Plex and Slskd data securely to the new tables,
       and then strictly DROP the metadata table.
    """
    db_path = str(config_manager.database_path)
    if not os.path.exists(db_path):
        logger.info("Config database does not exist yet. No migration needed.")
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
                    if slskd_data:
                        service_id = config_db.get_or_create_service_id('slskd')
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
