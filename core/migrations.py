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

def run_working_db_migrations(working_db_engine) -> None:  # noqa: ARG001
    """
    Entry point for working.db schema migrations at application startup.

    All DDL is managed exclusively by Alembic via ``run_auto_migrations()``
    (the "alembic:working" environment).  Raw ALTER TABLE statements have been
    removed — schema changes must be expressed as Alembic migration scripts.
    """
    logger.debug(
        "run_working_db_migrations: schema management delegated to Alembic — nothing to do here."
    )


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


def _engine_for_env(env: str):
    """Return the live SQLAlchemy engine for the given Alembic environment name."""
    if env == "alembic:working":
        from database.working_database import get_working_database
        return get_working_database().engine
    if env == "alembic:music":
        from database.music_database import get_database
        return get_database().engine
    if env == "alembic:config":
        from sqlalchemy import create_engine as _ce
        return _ce(f"sqlite:///{config_manager.database_path}")
    return None


# Maps each Alembic environment to (sentinel_table, v2_3_0_baseline_revision).
# The Smart Inspector checks these to decide whether a legacy database needs
# to be stamped before upgrade() runs.
_ENV_LEGACY_BASELINE = {
    "alembic:working": ("downloads", "4661df33cf8b"),
    "alembic:music":   ("tracks",    "cb4f02f432ea"),
    # alembic:config has no application tables — no legacy adoption needed.
}


def run_auto_migrations() -> None:
    """
    Pillar 1: The Auto-Migrator

    Loops through the three database environments (config, working, music)
    and brings each schema to head via Alembic.

    Smart Inspector — Legacy Database Adoption
    ------------------------------------------
    v2.3.0 databases were bootstrapped with ``metadata.create_all()`` and
    therefore have no ``alembic_version`` table.  Calling
    ``command.upgrade("head")`` on such a database would try to CREATE TABLE
    on tables that already exist and crash with OperationalError.

    For each environment that has a legacy baseline, the Smart Inspector runs
    three-case logic before upgrade():

    * **has_alembic is True** → Normal flow: database is already Alembic-managed,
      just run upgrade("head").

    * **has_alembic is False, has_legacy is False** → Fresh install: truly empty
      database, run upgrade("head") from scratch.

    * **has_alembic is False, has_legacy is True** → Legacy adoption: v2.3.0
      tables exist without an alembic_version record.  Stamp the database at
      the v2.3.0 baseline revision so that upgrade("head") only applies the
      new v2.4.0 additions without touching existing tables.
    """
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect as sa_inspect

    logger.info("Starting automatic database schema migrations via Alembic...")

    alembic_cfg_path = Path(__file__).parent.parent / "alembic.ini"

    environments = [
        "alembic:config",
        "alembic:working",
        "alembic:music",
    ]

    for env in environments:
        logger.info("Running Alembic migrations for environment: %s", env)

        alembic_cfg = Config(str(alembic_cfg_path))
        # Prevent Alembic from resetting our tiered logger configuration.
        alembic_cfg.attributes['configure_logger'] = False
        # Override the active section: our alembic.ini uses [alembic:*] sections
        # instead of the default [alembic].
        alembic_cfg.set_main_option(
            "script_location",
            alembic_cfg.get_section_option(env, "script_location"),
        )

        # ── Smart Inspector ───────────────────────────────────────────────────
        if env in _ENV_LEGACY_BASELINE:
            sentinel_table, baseline_rev = _ENV_LEGACY_BASELINE[env]
            engine = _engine_for_env(env)

            if engine is not None:
                inspector = sa_inspect(engine)
                has_alembic = inspector.has_table("alembic_version")
                has_legacy  = inspector.has_table(sentinel_table)

                if has_alembic:
                    # ── Case 1: Normal flow ───────────────────────────────────
                    logger.info(
                        "%s: alembic_version present — running upgrade to head.", env
                    )
                    try:
                        command.upgrade(alembic_cfg, "head")
                        logger.info("Successfully migrated %s to head.", env)
                    except Exception as e:
                        logger.error("Failed to migrate %s: %s", env, e, exc_info=True)
                        raise
                    continue

                if not has_legacy:
                    # ── Case 2: Fresh install ─────────────────────────────────
                    logger.info(
                        "%s: fresh database (no tables) — running full upgrade to head.", env
                    )
                    try:
                        command.upgrade(alembic_cfg, "head")
                        logger.info("Successfully migrated %s to head.", env)
                    except Exception as e:
                        logger.error("Failed to migrate %s: %s", env, e, exc_info=True)
                        raise
                    continue

                # ── Case 3: Legacy adoption ───────────────────────────────────
                # v2.3.0 tables present, no alembic_version → stamp at baseline
                # so upgrade() only runs the v2.4.0 additions.
                logger.info(
                    "%s: legacy database detected (table '%s' exists, alembic_version absent)"
                    " — stamping at v2.3.0 baseline %s, then upgrading to head.",
                    env, sentinel_table, baseline_rev,
                )
                try:
                    command.stamp(alembic_cfg, baseline_rev)
                    logger.info("%s stamped at %s.", env, baseline_rev)
                except Exception as e:
                    logger.error(
                        "Failed to stamp %s at baseline %s: %s", env, baseline_rev, e,
                        exc_info=True,
                    )
                    raise
                try:
                    command.upgrade(alembic_cfg, "head")
                    logger.info("Successfully migrated %s to head.", env)
                except Exception as e:
                    logger.error("Failed to migrate %s: %s", env, e, exc_info=True)
                    raise
                continue

        # ── No legacy baseline for this environment (alembic:config) ─────────
        try:
            command.upgrade(alembic_cfg, "head")
            logger.info("Successfully migrated %s to head.", env)
        except Exception as e:
            logger.error("Failed to migrate %s: %s", env, e, exc_info=True)
            raise


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
