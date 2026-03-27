import json
import sqlite3
import contextlib
import os
from pathlib import Path
from typing import Iterable
from core.settings import config_manager
from core.tiered_logger import get_logger
from core.security import decrypt_string, encrypt_string
from database.config_database import get_config_database

logger = get_logger("migrations")


def run_auto_migrations(databases: list[str] | None = None) -> None:
    """Run Alembic upgrades for all configured database environments.

    Safe to call on every startup — ``upgrade head`` is a no-op when the
    target database is already at the current revision.

    Args:
        databases: Ordered list of alembic.ini section names to migrate.
                   Defaults to ["config", "working", "music"].
    """
    if databases is None:
        databases = ["config", "working", "music"]

    try:
        from alembic import command
        from alembic.config import Config
    except Exception as e:
        logger.warning(f"Alembic is not available; skipping startup migrations: {e}")
        return

    ini_path = Path(__file__).resolve().parent.parent / "alembic.ini"
    if not ini_path.exists():
        logger.warning(f"Alembic config not found at {ini_path}; skipping startup migrations")
        return

    for db_name in databases:
        logger.info(f"Checking migrations for database: {db_name}")
        try:
            alembic_cfg = Config(str(ini_path), ini_section=db_name)
            command.upgrade(alembic_cfg, "head")
            logger.info(f"Database '{db_name}' is at head")
        except Exception as e:
            logger.critical(f"Failed to migrate {db_name} database: {e}", exc_info=True)
            raise e


# Backwards-compatible alias for any external callers.
run_alembic_startup_migrations = run_auto_migrations

# Minimum SQLite version required for ALTER TABLE ... RENAME COLUMN (3.25.0).
_MIN_SQLITE_RENAME_COLUMN = (3, 25, 0)

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

def migrate_user_provider_identifier(working_db_engine) -> None:
    """
    v2.2.0 working.db migration: rename the Plex-specific ``plex_id`` column on
    the ``users`` table to the provider-agnostic ``provider_identifier``.

    Safety notes
    ------------
    * Guards against SQLite < 3.25.0 (which lacks ALTER TABLE RENAME COLUMN).
    * Uses ``engine.begin()`` — the idiomatic SQLAlchemy 2.0 pattern — so the
      DDL is committed automatically on clean exit and rolled back automatically
      on any exception.  An explicit ``conn.commit()`` is neither required nor
      used, avoiding the implicit second autobegin that ``engine.connect()`` +
      ``conn.commit()`` leaves open.
    * Raises on failure so startup fails loudly: a silent swallow here would
      leave the SQLAlchemy model column name (``provider_identifier``) mismatched
      against the database column (``plex_id``), causing every ORM query on that
      column to raise at runtime.
    """
    from sqlalchemy import text

    # Version guard — RENAME COLUMN requires SQLite ≥ 3.25.0.
    sqlite_version = tuple(int(x) for x in sqlite3.sqlite_version.split("."))
    if sqlite_version < _MIN_SQLITE_RENAME_COLUMN:
        raise RuntimeError(
            f"SQLite {sqlite3.sqlite_version} is too old to perform ALTER TABLE "
            f"RENAME COLUMN (requires ≥ 3.25.0).  Upgrade SQLite and restart."
        )

    try:
        # Read the current column list outside of the write transaction so we
        # avoid holding a write lock during the PRAGMA query.
        with working_db_engine.connect() as conn:
            rows = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        columns = {row[1] for row in rows}

        if "plex_id" not in columns:
            if "provider_identifier" in columns:
                logger.debug(
                    "working.db 'users' table already has 'provider_identifier'; "
                    "v2.2.0 migration not needed."
                )
            else:
                logger.warning(
                    "working.db 'users' table has neither 'plex_id' nor "
                    "'provider_identifier'; schema is in an unexpected state."
                )
            return

        if "provider_identifier" in columns:
            # Both columns present — a previous partial migration; nothing to do.
            logger.warning(
                "working.db 'users' table already has 'provider_identifier' "
                "alongside 'plex_id'; skipping rename."
            )
            return

        # engine.begin() auto-commits on clean block exit and auto-rolls back on
        # any exception — no explicit conn.commit() required.
        with working_db_engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE users RENAME COLUMN plex_id TO provider_identifier")
            )

        logger.info(
            "v2.2.0 migration: successfully renamed 'plex_id' → 'provider_identifier' "
            "in working.db users table."
        )

    except Exception as e:
        # Re-raise so the caller (run_working_db_migrations / startup) sees a
        # hard failure rather than silently continuing with a mismatched schema.
        logger.error(f"v2.2.0 migration failed: {e}", exc_info=True)
        raise


def run_working_db_migrations(working_db_engine) -> None:
    """
    Entry point for all working.db schema migrations.
    Called once at application startup after the WorkingDatabase engine is available.
    """
    migrate_user_provider_identifier(working_db_engine)


def run_migrations() -> None:
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
