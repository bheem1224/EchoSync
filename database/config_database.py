from __future__ import annotations

import contextlib
import functools
import os
import random
import re
import sqlite3
import threading
import time
from collections.abc import Generator
from pathlib import Path
from typing import Any

from core.tiered_logger import get_logger

logger = get_logger("config_database")

# Import write helpers after logger to avoid circular issues
from . import ensure_writer, execute_write, execute_write_sql


def retry_sqlite_io(max_retries: int = 5, base_delay: float = 0.05, max_delay: float = 1.0):
    """Decorator to retry SQLite queries encountering transient disk I/O errors or lock contention.

    Catches sqlite3.OperationalError with messages matching 'disk i/o error', 'locked', or 'busy',
    and applies exponential backoff with random jitter.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    err_msg = str(e).lower()
                    if any(token in err_msg for token in ("disk i/o error", "locked", "busy")):
                        last_exc = e
                        delay = min(max_delay, base_delay * (2**attempt)) + random.uniform(0, 0.05)
                        logger.warning(
                            f"[SQLite Retry] Transient '{e}' in {func.__name__} (attempt {attempt + 1}/{max_retries}). "
                            f"Backing off for {delay:.3f}s..."
                        )
                        time.sleep(delay)
                        continue
                    raise
            raise last_exc

        return wrapper

    return decorator


class ConfigDatabase:
    _schema_lock = threading.Lock()
    _schema_initialized: bool = False
    _schema_verified: bool = False
    _initialized_paths: set[str] = set()

    def __init__(self, db_path: str | None = None):
        if db_path:
            self.database_path = Path(db_path)
        else:
            from core.settings import config_manager

            uri = config_manager.get("database.config_uri")
            if uri:
                # We assume the config_database.py wrapper is heavily SQLite-dependent right now,
                # but we still support passing the URI. For SQLite it should extract the path.
                if uri.startswith("sqlite:///"):
                    self.database_path = Path(uri.replace("sqlite:///", ""))
                else:
                    self.database_path = Path(uri)
            else:
                self.database_path = Path(config_manager.database_path)

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        # Ensure writer queue is running for this DB
        try:
            ensure_writer(str(self.database_path))
        except Exception:
            # best-effort; don't fail startup if writer can't be created
            pass

        try:
            self._ensure_schema_once()
        except sqlite3.DatabaseError as de:
            if "malformed database schema" in str(de) or "orphan index" in str(de):
                logger.warning(
                    f"Database schema malformed: {de}. Attempting automatic recovery via VACUUM and REINDEX..."
                )
                try:
                    conn = sqlite3.connect(str(self.database_path), timeout=30.0)
                    conn.execute("PRAGMA busy_timeout = 30000")
                    conn.execute("PRAGMA journal_mode = WAL")
                    conn.execute("PRAGMA synchronous = NORMAL")
                    conn.execute("VACUUM")
                    conn.execute("REINDEX")
                    conn.close()
                    logger.info("Automatic database recovery completed successfully. Retrying schema initialization...")
                    self._ensure_schema_once(force=True)
                except Exception as ree:
                    logger.error(f"Automatic database recovery failed: {ree}")
                    raise de
            else:
                raise

    def _ensure_schema_once(self, force: bool = False) -> None:
        try:
            path_key = str(self.database_path.resolve())
        except Exception:
            path_key = str(self.database_path)

        if not force and ConfigDatabase._schema_initialized and path_key in ConfigDatabase._initialized_paths:
            return

        with ConfigDatabase._schema_lock:
            if not force and ConfigDatabase._schema_initialized and path_key in ConfigDatabase._initialized_paths:
                return
            self._run_schema_migrations()
            ConfigDatabase._initialized_paths.add(path_key)
            ConfigDatabase._schema_initialized = True
            ConfigDatabase._schema_verified = True

    def _run_schema_migrations(self) -> None:
        self._initialize_schema()

    @contextlib.contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager that opens a SQLite connection and guarantees it is
        closed when the ``with`` block exits — even on exceptions.

        Using ``with db._get_connection() as conn:`` previously relied on
        SQLite's built-in context manager which only manages transactions
        (commit/rollback) and does NOT close the connection, leaking handles
        across every health-check and install cycle.
        """
        conn = self._open_connection()
        try:
            yield conn
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _open_connection(self) -> sqlite3.Connection:
        """Open and return a raw SQLite connection with hardened PRAGMAs.

        Callers MUST close this connection themselves (prefer a try/finally).
        Prefer ``_get_connection()`` as a context manager where possible.
        """
        conn = sqlite3.connect(str(self.database_path), timeout=60.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = -2000")
        conn.execute("PRAGMA wal_autocheckpoint = 100")
        return conn

    def _initialize_schema(self):
        try:

            def _schema(cursor):
                def heal_table_schemas(cursor):
                    cursor.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE '%accounts_temp_migration_swap%'"
                    )
                    broken_tables = [r[0] for r in cursor.fetchall()]

                    if "account_tokens" in broken_tables:
                        logger.warning("Healing corrupted account_tokens schema...")
                        cursor.execute("CREATE TABLE account_tokens_backup AS SELECT * FROM account_tokens")
                        cursor.execute("DROP TABLE account_tokens")
                        cursor.execute("""
                            CREATE TABLE account_tokens (
                                id INTEGER PRIMARY KEY,
                                account_id INTEGER NOT NULL UNIQUE,
                                access_token TEXT NOT NULL,
                                refresh_token TEXT,
                                token_type TEXT DEFAULT 'Bearer',
                                expires_at INTEGER,
                                scope TEXT,
                                created_at INTEGER DEFAULT (strftime('%s','now')),
                                updated_at INTEGER DEFAULT (strftime('%s','now')),
                                FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
                            )
                        """)
                        cursor.execute("INSERT INTO account_tokens SELECT * FROM account_tokens_backup")
                        cursor.execute("DROP TABLE account_tokens_backup")
                        logger.info("Successfully healed account_tokens schema.")

                    if "account_mappings" in broken_tables:
                        logger.warning("Healing corrupted account_mappings schema...")
                        cursor.execute("CREATE TABLE account_mappings_backup AS SELECT * FROM account_mappings")
                        cursor.execute("DROP TABLE account_mappings")
                        cursor.execute("""
                            CREATE TABLE account_mappings (
                                id INTEGER PRIMARY KEY,
                                source_account_id INTEGER NOT NULL,
                                mapped_account_id INTEGER NOT NULL,
                                created_at INTEGER DEFAULT (strftime('%s','now')),
                                updated_at INTEGER DEFAULT (strftime('%s','now')),
                                UNIQUE(source_account_id, mapped_account_id),
                                FOREIGN KEY(source_account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                                FOREIGN KEY(mapped_account_id) REFERENCES accounts(id) ON DELETE CASCADE
                            )
                        """)
                        cursor.execute("INSERT INTO account_mappings SELECT * FROM account_mappings_backup")
                        cursor.execute("DROP TABLE account_mappings_backup")
                        logger.info("Successfully healed account_mappings schema.")

                    if "pkce_sessions" in broken_tables:
                        logger.warning("Healing corrupted pkce_sessions schema...")
                        cursor.execute("DROP TABLE IF EXISTS pkce_sessions")
                        cursor.execute("""
                            CREATE TABLE pkce_sessions (
                                pkce_id TEXT PRIMARY KEY,
                                service TEXT NOT NULL,
                                account_id INTEGER NOT NULL,
                                code_verifier TEXT NOT NULL,
                                code_challenge TEXT NOT NULL,
                                redirect_uri TEXT NOT NULL,
                                client_id TEXT NOT NULL,
                                created_at INTEGER NOT NULL,
                                expires_at INTEGER NOT NULL
                            )
                        """)
                        logger.info("Successfully healed pkce_sessions schema.")

                # 0. Self-healing: Repair any tables whose foreign keys were rewritten to _old or _temp tables
                heal_table_schemas(cursor)

                # Cleanup orphaned triggers/views from DB Browser migrations
                cursor.execute(
                    "SELECT type, name FROM sqlite_master WHERE sql LIKE '%accounts_temp_migration_swap%' AND type IN ('trigger', 'view')"
                )
                for t_row in cursor.fetchall():
                    cursor.execute(f"DROP {t_row[0].upper()} IF EXISTS {t_row[1]}")

                # Check if services table exists and has UNIQUE name constraint
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='services'")
                row = cursor.fetchone()
                has_unique_name = False
                if row:
                    sql_str = row[0]
                    col_unique = re.search(r"\bname\b[^,]*\bunique\b", sql_str, re.IGNORECASE) is not None
                    table_unique = re.search(r"\bunique\s*\(\s*name\s*\)", sql_str, re.IGNORECASE) is not None
                    has_unique_name = col_unique or table_unique
                if has_unique_name:
                    logger.info("Migrating services table to remove UNIQUE constraint from name column...")
                    try:
                        cursor.connection.commit()
                        cursor.execute("PRAGMA foreign_keys = OFF")
                        cursor.execute("ALTER TABLE services RENAME TO services_old")
                        cursor.execute("""
                            CREATE TABLE services (
                                id INTEGER PRIMARY KEY,
                                name TEXT NOT NULL,
                                plugin_id INTEGER UNIQUE,
                                absolute_install_path TEXT,
                                loaded_modules TEXT,
                                version TEXT,
                                service_type TEXT,
                                description TEXT,
                                is_active INTEGER DEFAULT 1,
                                beta_opt_in INTEGER,
                                channel_preference TEXT DEFAULT 'inherit',
                                previous_version_path TEXT,
                                verified_source INTEGER DEFAULT 0,
                                privileged_mode INTEGER DEFAULT 0,
                                permissions TEXT DEFAULT '[]',
                                capabilities TEXT DEFAULT '{}',
                                created_at INTEGER DEFAULT (strftime('%s','now')),
                                updated_at INTEGER DEFAULT (strftime('%s','now'))
                            )
                        """)
                        cursor.execute("""
                            INSERT INTO services (
                                id, name, plugin_id, absolute_install_path, loaded_modules, 
                                version, service_type, description, is_active, beta_opt_in, channel_preference,
                                previous_version_path, verified_source, privileged_mode, permissions, 
                                capabilities, created_at, updated_at
                            )
                            SELECT 
                                id, name, plugin_id, absolute_install_path, loaded_modules, 
                                version, service_type, description, is_active, beta_opt_in, 
                                CASE WHEN beta_opt_in = 1 THEN 'beta' WHEN beta_opt_in = 0 THEN 'stable' ELSE 'inherit' END,
                                previous_version_path, verified_source, privileged_mode, permissions, 
                                '{}', created_at, updated_at
                            FROM services_old
                        """)
                        cursor.execute("DROP TABLE services_old")
                        logger.info("Successfully migrated services table (removed UNIQUE constraint on name)")
                    except Exception as me:
                        logger.error(f"Failed to migrate services table (UNIQUE removal): {me}")
                        # Safe fallback recovery
                        try:
                            cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='services_old'")
                            has_old = cursor.fetchone() is not None
                            cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='services'")
                            has_new = cursor.fetchone() is not None
                            if has_old and not has_new:
                                cursor.execute("ALTER TABLE services_old RENAME TO services")
                            elif has_old and has_new:
                                cursor.execute("DROP TABLE services_old")
                        except Exception as fe:
                            logger.error(f"Failed fallback services recovery: {fe}")
                    finally:
                        cursor.execute("PRAGMA foreign_keys = ON")

                # Services
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS services (
                        id INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        plugin_id INTEGER UNIQUE,
                        absolute_install_path TEXT,
                        loaded_modules TEXT,
                        version TEXT,
                        service_type TEXT,
                        description TEXT,
                        is_active INTEGER DEFAULT 1,
                        beta_opt_in INTEGER,
                        channel_preference TEXT DEFAULT 'inherit',
                        previous_version_path TEXT,
                        verified_source INTEGER DEFAULT 0,
                        privileged_mode INTEGER DEFAULT 0,
                        permissions TEXT DEFAULT '[]',
                        capabilities TEXT DEFAULT '{}',
                        created_at INTEGER DEFAULT (strftime('%s','now')),
                        updated_at INTEGER DEFAULT (strftime('%s','now'))
                    )
                """)
                # Service config (sensitive values allowed)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS service_config (
                        id INTEGER PRIMARY KEY,
                        service_id INTEGER NOT NULL,
                        config_key TEXT NOT NULL,
                        config_value TEXT,
                        is_sensitive INTEGER DEFAULT 0,
                        created_at INTEGER DEFAULT (strftime('%s','now')),
                        updated_at INTEGER DEFAULT (strftime('%s','now')),
                        UNIQUE(service_id, config_key),
                        FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE CASCADE
                    )
                """)
                # Accounts
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS accounts (
                        id INTEGER PRIMARY KEY,
                        service_id INTEGER NOT NULL,
                        account_name TEXT,
                        display_name TEXT,
                        user_id TEXT,
                        account_email TEXT,
                        is_active INTEGER DEFAULT 0,
                        is_authenticated INTEGER DEFAULT 0,
                        last_authenticated_at INTEGER,
                        created_at INTEGER DEFAULT (strftime('%s','now')),
                        updated_at INTEGER DEFAULT (strftime('%s','now')),
                        FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE CASCADE
                    )
                """)
                # Account tokens
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS account_tokens (
                        id INTEGER PRIMARY KEY,
                        account_id INTEGER NOT NULL UNIQUE,
                        access_token TEXT NOT NULL,
                        refresh_token TEXT,
                        token_type TEXT DEFAULT 'Bearer',
                        expires_at INTEGER,
                        scope TEXT,
                        created_at INTEGER DEFAULT (strftime('%s','now')),
                        updated_at INTEGER DEFAULT (strftime('%s','now')),
                        FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
                    )
                """)
                # Drop deprecated Account metadata
                cursor.execute("DROP TABLE IF EXISTS account_metadata")
                # PKCE sessions
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS pkce_sessions (
                        pkce_id TEXT PRIMARY KEY,
                        service TEXT NOT NULL,
                        account_id INTEGER NOT NULL,
                        code_verifier TEXT NOT NULL,
                        code_challenge TEXT NOT NULL,
                        redirect_uri TEXT NOT NULL,

                        client_id TEXT NOT NULL,
                        created_at INTEGER NOT NULL,
                        expires_at INTEGER NOT NULL,
                        FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
                    )
                """)
                # Account Mappings (Agnostic Node Mapping)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS account_mappings (
                        id INTEGER PRIMARY KEY,
                        source_account_id INTEGER NOT NULL,
                        mapped_account_id INTEGER NOT NULL,
                        created_at INTEGER DEFAULT (strftime('%s','now')),
                        updated_at INTEGER DEFAULT (strftime('%s','now')),
                        UNIQUE(source_account_id, mapped_account_id),
                        FOREIGN KEY(source_account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                        FOREIGN KEY(mapped_account_id) REFERENCES accounts(id) ON DELETE CASCADE
                    )
                """)

                # Plugin Snapshots (24h Grace Period)
                cursor.execute("PRAGMA table_info(plugin_snapshots)")
                ps_columns = [row[1] for row in cursor.fetchall()]
                if ps_columns and "plugin_id" not in ps_columns:
                    cursor.execute("DROP TABLE IF EXISTS plugin_snapshots")

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS plugin_snapshots (
                        id INTEGER PRIMARY KEY,
                        plugin_id INTEGER NOT NULL UNIQUE,
                        snapshot_data TEXT NOT NULL,
                        expires_at INTEGER NOT NULL,
                        created_at INTEGER DEFAULT (strftime('%s','now'))
                    )
                """)

                # UI Component Registry (Sprint 6 — replaces live ui_manifest.json disk parsing)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ui_components (
                        id INTEGER PRIMARY KEY,
                        plugin_id INTEGER,
                        tag_name TEXT NOT NULL UNIQUE,
                        component_type TEXT NOT NULL,
                        entry_path TEXT NOT NULL,
                        is_core INTEGER DEFAULT 0,
                        created_at INTEGER DEFAULT (strftime('%s','now')),
                        updated_at INTEGER DEFAULT (strftime('%s','now'))
                    )
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_settings (
                        key VARCHAR NOT NULL PRIMARY KEY,
                        value TEXT,
                        updated_at DATETIME
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS quality_profiles (
                        id VARCHAR NOT NULL PRIMARY KEY,
                        name VARCHAR,
                        prefer_max_quality BOOLEAN
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS quality_profile_steps (
                        id INTEGER NOT NULL PRIMARY KEY,
                        profile_id VARCHAR NOT NULL,
                        priority INTEGER NOT NULL,
                        rules JSON,
                        FOREIGN KEY(profile_id) REFERENCES quality_profiles (id) ON DELETE CASCADE
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password_hash TEXT,
                        auth_provider TEXT NOT NULL DEFAULT 'local',
                        oidc_subject TEXT UNIQUE,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        created_at INTEGER DEFAULT (strftime('%s','now'))
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS roles (
                        id INTEGER PRIMARY KEY,
                        name TEXT UNIQUE NOT NULL,
                        is_system INTEGER NOT NULL DEFAULT 0,
                        permissions_json TEXT NOT NULL
                    )
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_role_assignments (
                        user_id TEXT NOT NULL,
                        role_id INTEGER NOT NULL,
                        PRIMARY KEY (user_id, role_id),
                        FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
                        FOREIGN KEY(role_id) REFERENCES roles (id) ON DELETE CASCADE
                    ) WITHOUT ROWID
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_managed_accounts (
                        user_id TEXT NOT NULL,
                        server_plugin_id INTEGER NOT NULL,
                        managed_account_id TEXT NOT NULL,
                        PRIMARY KEY (user_id, server_plugin_id, managed_account_id),
                        FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
                    ) WITHOUT ROWID
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_external_accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        provider TEXT NOT NULL,
                        category TEXT NOT NULL DEFAULT 'streaming',
                        external_account_id TEXT NOT NULL,
                        display_name TEXT,
                        plugin_id INTEGER,
                        created_at INTEGER DEFAULT (strftime('%s','now')),
                        UNIQUE(user_id, provider, external_account_id),
                        FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                """)
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS ix_user_external_accounts_user ON user_external_accounts(user_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS ix_user_external_accounts_provider ON user_external_accounts(provider)"
                )

                # Backfill user_external_accounts from legacy user_managed_accounts without deleting legacy rows
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO user_external_accounts
                        (user_id, provider, category, external_account_id, display_name, plugin_id)
                    SELECT
                        uma.user_id,
                        CASE uma.server_plugin_id
                            WHEN 3021005569 THEN 'plex'
                            WHEN 2305548545 THEN 'jellyfin'
                            WHEN 4010168341 THEN 'navidrome'
                            ELSE COALESCE(LOWER(REPLACE(s.name, 'EchoSync.', '')), CAST(uma.server_plugin_id AS TEXT))
                        END,
                        'media_server',
                        uma.managed_account_id,
                        uma.managed_account_id,
                        uma.server_plugin_id
                    FROM user_managed_accounts uma
                    LEFT JOIN services s ON s.plugin_id = uma.server_plugin_id
                    """
                )

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS api_keys (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        key_prefix TEXT NOT NULL,
                        key_hash TEXT NOT NULL,
                        scopes_json TEXT NOT NULL,
                        expires_at INTEGER,
                        revoked_at INTEGER,
                        created_at INTEGER DEFAULT (strftime('%s','now')),
                        FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
                    )
                """)

                cursor.execute("CREATE INDEX IF NOT EXISTS ix_api_keys_user_id ON api_keys(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS ix_api_keys_key_prefix ON api_keys(key_prefix)")

                # Seed built-in system roles
                import json as _json
                from core.security.rbac import SYSTEM_ROLE_PERMISSIONS

                for role_name, role_perms in SYSTEM_ROLE_PERMISSIONS.items():
                    cursor.execute(
                        """
                        INSERT INTO roles (name, is_system, permissions_json) VALUES (?, 1, ?)
                        ON CONFLICT(name) DO UPDATE SET permissions_json = excluded.permissions_json
                        WHERE roles.is_system = 1
                        """,
                        (role_name, _json.dumps(list(role_perms))),
                    )

                # Migration: Add missing columns to services table if they don't exist
                cursor.execute("PRAGMA table_info(services)")
                columns = [row[1] for row in cursor.fetchall()]
                if "absolute_install_path" not in columns:
                    cursor.execute("ALTER TABLE services ADD COLUMN absolute_install_path TEXT")
                if "loaded_modules" not in columns:
                    cursor.execute("ALTER TABLE services ADD COLUMN loaded_modules TEXT")
                if "plugin_id" not in columns:
                    cursor.execute("ALTER TABLE services ADD COLUMN plugin_id INTEGER")
                if "version" not in columns:
                    cursor.execute("ALTER TABLE services ADD COLUMN version TEXT")
                if "capabilities" not in columns:
                    cursor.execute("ALTER TABLE services ADD COLUMN capabilities TEXT DEFAULT '{}'")
                if "channel_preference" not in columns:
                    cursor.execute("ALTER TABLE services ADD COLUMN channel_preference TEXT DEFAULT 'inherit'")
                if "granted_scopes" not in columns:
                    cursor.execute("ALTER TABLE services ADD COLUMN granted_scopes TEXT DEFAULT '[]'")
                    cursor.execute(
                        "UPDATE services SET granted_scopes = COALESCE(permissions, '[]') WHERE granted_scopes IS NULL"
                    )

                # Cleanup: Drop deprecated tables
                cursor.execute("DROP TABLE IF EXISTS accounts_metadata")
                cursor.execute("DROP TABLE IF EXISTS config_kvs")

                # Indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_services_name ON services(name)")

                cursor.execute("CREATE INDEX IF NOT EXISTS idx_services_plugin_id ON services(plugin_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_service ON accounts(service_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tokens_account ON account_tokens(account_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pkce_expires ON pkce_sessions(expires_at)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_account_mappings_source ON account_mappings(source_account_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_account_mappings_mapped ON account_mappings(mapped_account_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_plugin_snapshots_plugin_id ON plugin_snapshots(plugin_id)"
                )
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_plugin_snapshots_expires ON plugin_snapshots(expires_at)"
                )
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_ui_components_plugin_id ON ui_components(plugin_id)")
                cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_ui_components_component_type ON ui_components(component_type)"
                )

                # Inline legacy services migration to avoid schema cache latency on separate connection
                cursor.execute("PRAGMA table_info(services)")
                current_columns = [row[1] for row in cursor.fetchall()]
                if "plugin_id" in current_columns:
                    import binascii

                    cursor.execute(
                        "SELECT id, name FROM services WHERE plugin_id IS NULL OR typeof(plugin_id) = 'text'"
                    )
                    rows = cursor.fetchall()
                    if rows:
                        try:
                            from core.nexus_framework.plugin_loader import (
                                get_all_plugins,
                            )

                            all_plugins = get_all_plugins()
                            for r in rows:
                                s_id, s_name = r[0], r[1]
                                resolved_plugin_id_str = s_name
                                resolved_version = "1.0.0"
                                for p in all_plugins:
                                    p_id = p.get("id", "")
                                    p_name = p.get("name", "")
                                    p_folder = p.get("folder_name", "")
                                    norm_s_name = s_name.replace(".", "/")
                                    if (
                                        s_name.lower() in p_folder.lower()
                                        or norm_s_name.lower() in p_folder.lower()
                                        or s_name.lower() == p_name.lower()
                                        or s_name.lower() in p_id.lower()
                                    ):
                                        resolved_plugin_id_str = p_folder.split("/")[-1]
                                        resolved_version = p.get("version", "1.0.0")
                                        break
                                plugin_id_int = binascii.crc32(resolved_plugin_id_str.encode("utf-8")) & 0xFFFFFFFF
                                cursor.execute(
                                    "UPDATE services SET plugin_id = ? WHERE id = ?",
                                    (plugin_id_int, s_id),
                                )
                        except Exception:
                            pass

                # Final Self-healing: Double check that no table references services_old or accounts_temp
                heal_table_schemas(cursor)

            # Run schema creation and inline migrations on writer thread to avoid concurrent-writes
            execute_write(str(self.database_path), _schema)
            logger.debug("[system] - Config database schema ensured and legacy services migrated")
            self.seed_default_system_settings()
        except Exception as e:
            logger.error(f"Failed to initialize config schema: {e}", exc_info=True)

    # Service helpers
    @retry_sqlite_io(max_retries=5, base_delay=0.05, max_delay=1.0)
    def get_or_create_service_id(self, name) -> int:
        # Strip channel-suffix (@beta / @stable) produced by SDK._get_plugin_id()
        # so all lookups operate on the canonical plugin name regardless of active channel.
        if isinstance(name, str) and "@" in name:
            name = name.split("@")[0]

        # 1. Try to find existing using the extremely robust get_service_id
        existing_id = self.get_service_id(name)
        if existing_id:
            return existing_id

        # 2. Register if missing (ONLY if it is core service 'system' OR matches a physically installed plugin)
        import binascii

        resolved_plugin_id_str = name
        resolved_version = "1.0.0"
        resolved_path = None
        is_matched = False
        try:
            from core.nexus_framework.plugin_loader import get_all_plugins

            for p in get_all_plugins():
                p_id = p.get("id", "")
                p_name = p.get("name", "")
                if (
                    name.lower() == p_id.lower()
                    or p_id.lower().endswith("." + name.lower())
                    or name.lower() == p_name.lower()
                    or p_name.lower().endswith("." + name.lower())
                ):
                    resolved_plugin_id_str = p_id
                    resolved_version = p.get("version", "1.0.0")
                    resolved_path = p.get("abs_path")
                    is_matched = True
                    break
        except Exception as e:
            logger.error(f"Failed to resolve plugin details for {name}: {e}")

        if not is_matched:
            import re

            from core.settings import config_manager

            plugin_name = name.split(".")[-1]
            if re.match(r"^[a-zA-Z0-9_\-]+$", plugin_name):
                candidate_roots = [
                    Path(config_manager.get_plugins_dir()) / "EchoSync",
                    Path(__file__).resolve().parent.parent / "plugins" / "EchoSync",
                    Path(config_manager.get_plugins_dir()),
                    Path(__file__).resolve().parent.parent / "plugins",
                ]
                for root in candidate_roots:
                    plugins_root = os.path.abspath(os.path.realpath(str(root)))
                    bundle_path = os.path.abspath(os.path.realpath(os.path.join(plugins_root, plugin_name)))
                    if os.path.isdir(bundle_path):
                        resolved_plugin_id_str = (
                            name if name.lower().startswith("echosync.") else f"EchoSync.{plugin_name}"
                        )
                        resolved_version = "1.0.0"
                        resolved_path = bundle_path
                        is_matched = True
                        break

        if name.lower() == "system" or is_matched:
            plugin_id_int = binascii.crc32(resolved_plugin_id_str.lower().encode("utf-8")) & 0xFFFFFFFF
            self.register_service(
                resolved_plugin_id_str,
                "streaming",
                f"{resolved_plugin_id_str.capitalize()} service",
                absolute_install_path=resolved_path,
                plugin_id=plugin_id_int,
                version=resolved_version,
            )

            # 3. Try to find again after registration
            existing_id = self.get_service_id(name)
            if existing_id:
                return existing_id
        else:
            logger.debug(f"Service '{name}' is not physically installed or core. Not registering.")

        return 0

    def register_service(
        self,
        name: str,
        service_type: str,
        description: str,
        absolute_install_path: str | None = None,
        plugin_id: int | None = None,
        version: str | None = None,
        loaded_modules: str | None = None,
        beta_opt_in: int | None = None,
        verified_source: int | None = None,
        privileged_mode: int | None = None,
        permissions: str | None = None,
        capabilities: str | None = None,
        granted_scopes: str | None = None,
    ) -> int:
        import binascii

        if plugin_id is None:
            # Fallback CRC32 generation if not provided (ALWAYS use full lowercase namespace for consistency)
            plugin_id = binascii.crc32(name.lower().encode("utf-8")) & 0xFFFFFFFF

        from pathlib import Path

        from core.settings import config_manager

        core_services = {"system"}
        if absolute_install_path is None:
            # Check if name is a core streaming/built-in service
            if name.lower() in core_services:
                app_root = Path(__file__).parent.parent
                absolute_install_path = str((app_root / "core").resolve())
        else:
            # If path provided but not inside plugins dir and not a core service, invalidate path
            if name.lower() not in core_services:
                try:
                    plugins_dir_resolved = Path(config_manager.get_plugins_dir()).resolve()
                    repo_plugins_dir = (Path(__file__).resolve().parent.parent / "plugins").resolve()
                    path_resolved = Path(absolute_install_path).resolve()
                    if not (
                        path_resolved.is_relative_to(plugins_dir_resolved)
                        or path_resolved.is_relative_to(repo_plugins_dir)
                    ):
                        logger.warning(
                            f"Rejecting out-of-boundary plugin path {absolute_install_path} for service {name}; setting to None"
                        )
                        absolute_install_path = None
                except Exception as e:
                    logger.warning(f"Error checking plugin install path boundary: {e}")
                    absolute_install_path = None

        try:
            from core.task_manager import db_write_lease

            with db_write_lease(task_name="register_service"):
                execute_write_sql(
                    str(self.database_path),
                    """
                    INSERT INTO services(name, service_type, description, absolute_install_path, loaded_modules, plugin_id, version, is_active, beta_opt_in, verified_source, privileged_mode, permissions, capabilities, granted_scopes)
                    VALUES(?,?,?,?,?,?,?,1,COALESCE(?, 0),COALESCE(?, 0),COALESCE(?, 0),COALESCE(?, '[]'),COALESCE(?, '{}'),COALESCE(?, ?, '[]'))
                    ON CONFLICT(plugin_id) DO UPDATE SET 
                        name=excluded.name,
                        absolute_install_path=excluded.absolute_install_path,
                        loaded_modules=excluded.loaded_modules,
                        version=excluded.version,
                        is_active=1,
                        beta_opt_in=COALESCE(?, services.beta_opt_in),
                        verified_source=COALESCE(excluded.verified_source, services.verified_source, 0),
                        privileged_mode=COALESCE(excluded.privileged_mode, services.privileged_mode, 0),
                        permissions=COALESCE(excluded.permissions, services.permissions, '[]'),
                        capabilities=COALESCE(excluded.capabilities, services.capabilities, '{}'),
                        granted_scopes=COALESCE(?, services.granted_scopes, '[]'),
                        updated_at=strftime('%s','now')
                    """,
                    (
                        name,
                        service_type,
                        description,
                        absolute_install_path,
                        loaded_modules,
                        plugin_id,
                        version,
                        beta_opt_in,
                        verified_source,
                        privileged_mode,
                        permissions,
                        capabilities,
                        granted_scopes,
                        permissions,
                        beta_opt_in,
                        granted_scopes,
                    ),
                )
        except Exception as e:
            logger.error(f"Error registering service '{name}': {e}")

        return 0

    @retry_sqlite_io(max_retries=5, base_delay=0.05, max_delay=1.0)
    def set_service_config(self, service_id: int, key: str, value: Any, is_sensitive: bool = False) -> bool:
        try:
            import json

            from core.security import encrypt_string

            # Resolve to primary key services.id if a plugin_id/name was passed
            resolved_id = self.get_service_id(service_id)
            if resolved_id:
                service_id = resolved_id

            if not service_id:
                logger.warning(f"Cannot set service config for unknown service: {service_id}")
                return False

            if isinstance(value, (list, dict)):
                value = json.dumps(value)

            if is_sensitive and value is not None:
                value = encrypt_string(str(value))

            execute_write_sql(
                str(self.database_path),
                """
                    INSERT INTO service_config(service_id, config_key, config_value, is_sensitive)
                    VALUES(?,?,?,?)
                    ON CONFLICT(service_id, config_key)
                    DO UPDATE SET config_value=excluded.config_value, is_sensitive=excluded.is_sensitive, updated_at=strftime('%s','now')
                """,
                (service_id, key, value, 1 if is_sensitive else 0),
            )
            return True
        except sqlite3.OperationalError as oe:
            err_msg = str(oe).lower()
            if any(token in err_msg for token in ("disk i/o error", "locked", "busy")):
                raise
            logger.error(f"Error setting service config: {oe}")
            return False
        except Exception as e:
            logger.error(f"Error setting service config: {e}")
            return False

    @retry_sqlite_io(max_retries=5, base_delay=0.05, max_delay=1.0)
    def get_service_config(self, service_id: int, key: str) -> Any | None:
        try:
            import json

            resolved_id = self.get_service_id(service_id)
            if resolved_id:
                service_id = resolved_id

            if not service_id:
                return None

            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT config_value, is_sensitive FROM service_config WHERE service_id=? AND config_key=?",
                    (service_id, key),
                )
                row = c.fetchone()

                if not row:
                    return None

                value, is_sensitive = row[0], row[1]
                if is_sensitive and value is not None:
                    from core.security import decrypt_string

                    value = decrypt_string(value)

                if isinstance(value, str) and (value.startswith("[") or value.startswith("{")):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        pass

                return value
        except sqlite3.OperationalError as oe:
            err_msg = str(oe).lower()
            if any(token in err_msg for token in ("disk i/o error", "locked", "busy")):
                raise
            logger.error(f"Error getting service config: {oe}")
            return None
        except Exception as e:
            logger.error(f"Error getting service config: {e}")
            return None

    @retry_sqlite_io(max_retries=5, base_delay=0.05, max_delay=1.0)
    def get_all_service_config(self, service_id: int) -> dict[str, Any]:
        try:
            import json

            resolved_id = self.get_service_id(service_id)
            if resolved_id:
                service_id = resolved_id

            if not service_id:
                return {}

            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT config_key, config_value, is_sensitive FROM service_config WHERE service_id=?",
                    (service_id,),
                )
                rows = c.fetchall()

                config = {}
                from core.security import decrypt_string

                for key, value, is_sensitive in rows:
                    if is_sensitive and value is not None:
                        try:
                            value = decrypt_string(value)
                        except Exception:
                            pass

                    if isinstance(value, str) and (value.startswith("[") or value.startswith("{")):
                        try:
                            value = json.loads(value)
                        except json.JSONDecodeError:
                            pass

                    config[key] = value

                return config
        except sqlite3.OperationalError as oe:
            err_msg = str(oe).lower()
            if any(token in err_msg for token in ("disk i/o error", "locked", "busy")):
                raise
            logger.error(f"Error reading all service config: {oe}")
            return {}
        except Exception as e:
            logger.error(f"Error reading all service config: {e}")
            return {}

    @retry_sqlite_io(max_retries=5, base_delay=0.05, max_delay=1.0)
    def get_service_credentials(self, service_name: str) -> dict[str, Any]:
        """Get all credentials/config for a service from the database with transient retry."""
        service_id = self.get_or_create_service_id(service_name)
        if not service_id:
            return {}
        return self.get_all_service_config(service_id)

    # Accounts
    @retry_sqlite_io(max_retries=5, base_delay=0.05, max_delay=1.0)
    def get_service_name(self, service_id: int) -> str | None:
        """Resolve a service ID (PK or plugin_id) to its canonical name."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM services WHERE id=?", (service_id,))
            row = c.fetchone()
            if not row:
                return None
            return row["name"]

    @retry_sqlite_io(max_retries=5, base_delay=0.05, max_delay=1.0)
    def get_service_id(self, identifier: Any) -> int | None:
        """Resolve a name or plugin_id to the primary integer ID."""
        if identifier is None:
            return None
        with self._get_connection() as conn:
            c = conn.cursor()
            id_str = str(identifier).strip()
            if id_str.isdigit():
                c.execute(
                    "SELECT id FROM services WHERE id=? OR plugin_id=?",
                    (int(id_str), int(id_str)),
                )
                row = c.fetchone()
                if row:
                    return int(row[0])

            # 1. Check exact name (case-insensitive)
            c.execute("SELECT id FROM services WHERE LOWER(name)=LOWER(?)", (id_str,))
            row = c.fetchone()
            if row:
                return int(row[0])

            # 2. Check canonical variations & CRC32
            import binascii

            clean_name = id_str.lower().replace("echosync.", "").replace("echosync/", "").strip()
            variations = {
                id_str.lower(),
                clean_name,
                f"echosync.{clean_name}",
                f"echosync/{clean_name}",
            }
            crc_list = [binascii.crc32(v.encode("utf-8")) & 0xFFFFFFFF for v in variations]

            placeholders = ",".join("?" * len(crc_list))
            name_placeholders = ",".join("?" * len(variations))
            c.execute(
                f"SELECT id FROM services WHERE plugin_id IN ({placeholders}) OR LOWER(name) IN ({name_placeholders})",
                (*crc_list, *variations),
            )
            row = c.fetchone()
            if row:
                return int(row[0])

            # 3. Suffix matching/normalized translation bridge
            norm_name = clean_name.replace(" ", "_").replace("-", "_")
            c.execute("SELECT id, name FROM services")
            for r in c.fetchall():
                row_name = (
                    r["name"]
                    .lower()
                    .replace("echosync.", "")
                    .replace("echosync/", "")
                    .replace(" ", "_")
                    .replace("-", "_")
                )
                if row_name == norm_name or row_name.endswith(f".{norm_name}") or norm_name.endswith(f".{row_name}"):
                    return int(r["id"])
            return None

    def get_accounts(self, service_id: int | None = None, is_active: bool | None = None) -> list[dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                query = "SELECT id, service_id, account_name, display_name, user_id, account_email, is_active, is_authenticated, last_authenticated_at FROM accounts WHERE 1=1"
                params: list[Any] = []
                if service_id is not None:
                    query += " AND service_id = ?"
                    params.append(service_id)
                if is_active is not None:
                    query += " AND is_active = ?"
                    params.append(1 if is_active else 0)
                c.execute(query, params)
                rows = c.fetchall()
                return [
                    {
                        "id": r[0],
                        "service_id": r[1],
                        "account_name": r[2],
                        "display_name": r[3],
                        "user_id": r[4],
                        "account_email": r[5],
                        "is_active": bool(r[6]),
                        "is_authenticated": bool(r[7]),
                        "last_authenticated_at": r[8],
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Error getting accounts: {e}")
            return []

    def ensure_account(
        self,
        service_id: int,
        account_id: int | None = None,
        account_name: str | None = None,
        display_name: str | None = None,
        user_id: str | None = None,
    ) -> int:
        """Ensure an account row exists for the given service.
        If account_id is provided, attempt to insert with that explicit id; otherwise autogenerate.
        Returns the account id.
        """
        try:
            # If explicit account_id is provided, check existence using a reader
            if account_id is not None:
                with self._get_connection() as conn:
                    c = conn.cursor()
                    c.execute("SELECT id FROM accounts WHERE id = ?", (account_id,))
                    row = c.fetchone()
                    if row:
                        return int(row[0])

                def _insert_with_id(cursor):
                    cursor.execute(
                        """
                        INSERT INTO accounts(id, service_id, account_name, display_name, user_id, is_active, is_authenticated)
                        VALUES(?,?,?,?,?,0,0)
                        """,
                        (account_id, service_id, account_name, display_name, user_id),
                    )
                    return account_id

                execute_write(str(self.database_path), _insert_with_id)
                return int(account_id)
            else:

                def _insert(cursor):
                    cursor.execute(
                        """
                        INSERT INTO accounts(service_id, account_name, display_name, user_id, is_active, is_authenticated)
                        VALUES(?,?,?,?,0,0)
                        """,
                        (service_id, account_name, display_name, user_id),
                    )
                    return cursor.lastrowid

                last_id = execute_write(str(self.database_path), _insert)
                return int(last_id) if last_id is not None else 0
        except Exception as e:
            logger.error(f"Error ensuring account exists: {e}")
            return int(account_id) if account_id is not None else 0

    def upsert_account(
        self,
        service_id: int,
        account_name: str | None = None,
        display_name: str | None = None,
        user_id: str | None = None,
        account_email: str | None = None,
        is_active: bool | None = None,
        is_authenticated: bool | None = None,
        account_id: int | None = None,
    ) -> int:
        """Insert or update an account row using stable identity fields when available."""
        try:
            with self._get_connection() as conn:
                c = conn.cursor()

                row = None
                if account_id is not None:
                    c.execute(
                        "SELECT id FROM accounts WHERE id = ? AND service_id = ?",
                        (account_id, service_id),
                    )
                    row = c.fetchone()

                if row is None and user_id:
                    c.execute(
                        "SELECT id FROM accounts WHERE service_id = ? AND user_id = ?",
                        (service_id, user_id),
                    )
                    row = c.fetchone()

                if row is None and account_name:
                    c.execute(
                        "SELECT id FROM accounts WHERE service_id = ? AND account_name = ?",
                        (service_id, account_name),
                    )
                    row = c.fetchone()

                existing_id = int(row[0]) if row else None

            if existing_id is None:
                new_account_id = self.ensure_account(
                    service_id=service_id,
                    account_id=account_id,
                    account_name=account_name,
                    display_name=display_name,
                    user_id=user_id,
                )
                if not new_account_id:
                    return 0
                existing_id = new_account_id

            assignments = []
            params: list[Any] = []

            if account_name is not None:
                assignments.append("account_name = ?")
                params.append(account_name)
            if display_name is not None:
                assignments.append("display_name = ?")
                params.append(display_name)
            if user_id is not None:
                assignments.append("user_id = ?")
                params.append(user_id)
            if account_email is not None:
                assignments.append("account_email = ?")
                params.append(account_email)
            if is_active is not None:
                assignments.append("is_active = ?")
                params.append(1 if is_active else 0)
            if is_authenticated is not None:
                assignments.append("is_authenticated = ?")
                params.append(1 if is_authenticated else 0)
                if is_authenticated:
                    assignments.append("last_authenticated_at = ?")
                    params.append(int(time.time()))

            assignments.append("updated_at = strftime('%s','now')")

            if params:
                params.append(existing_id)
                execute_write_sql(
                    str(self.database_path),
                    f"UPDATE accounts SET {', '.join(assignments)} WHERE id = ?",
                    tuple(params),
                )

            return existing_id
        except Exception as e:
            logger.error(f"Error upserting account: {e}")
            return int(account_id) if account_id is not None else 0

    def set_active_account(self, service_id: int, account_id: int, exclusive: bool = True) -> bool:
        """Set an account as active.

        Args:
            service_id: The service ID
            account_id: The account ID to activate
            exclusive: If True, deactivates all other accounts for this service (default).
                      If False, allows multiple accounts to be active simultaneously.
        """
        try:

            def _task(cursor):
                if exclusive:
                    # Old behavior: single active account (deactivate all others first)
                    cursor.execute(
                        "UPDATE accounts SET is_active = 0 WHERE service_id = ?",
                        (service_id,),
                    )
                cursor.execute(
                    "UPDATE accounts SET is_active = 1 WHERE id = ? AND service_id = ?",
                    (account_id, service_id),
                )

            execute_write(str(self.database_path), _task)
            return True
        except Exception as e:
            logger.error(f"Error setting active account: {e}")
            return False

    def toggle_account_active(self, account_id: int, is_active: bool) -> bool:
        """Toggle an account's active status (for multi-account support).

        Args:
            account_id: The account ID
            is_active: True to activate, False to deactivate
        """
        try:
            execute_write_sql(
                str(self.database_path),
                "UPDATE accounts SET is_active = ? WHERE id = ?",
                (1 if is_active else 0, account_id),
            )
            return True
        except Exception as e:
            logger.error(f"Error toggling account active status: {e}")
            return False

    def mark_account_authenticated(self, account_id: int) -> bool:
        try:
            execute_write_sql(
                str(self.database_path),
                "UPDATE accounts SET is_authenticated = 1, last_authenticated_at = ? WHERE id = ?",
                (int(time.time()), account_id),
            )
            return True
        except Exception as e:
            logger.error(f"Error marking account authenticated: {e}")
            return False

    def set_account_user_id(self, account_id: int, user_id: str) -> bool:
        try:
            rowcount = execute_write_sql(
                str(self.database_path),
                "UPDATE accounts SET user_id = ? WHERE id = ?",
                (user_id, account_id),
            )
            return bool(rowcount and rowcount > 0)
        except Exception as e:
            logger.error(f"Error setting account user_id: {e}")
            return False

    def delete_account(self, account_id: int) -> bool:
        try:
            rowcount = execute_write_sql(
                str(self.database_path),
                "DELETE FROM accounts WHERE id = ?",
                (account_id,),
            )
            return bool(rowcount and rowcount > 0)
        except Exception as e:
            logger.error(f"Error deleting account: {e}")
            return False

    def update_account_name(self, account_id: int, new_name: str) -> bool:
        try:
            rowcount = execute_write_sql(
                str(self.database_path),
                "UPDATE accounts SET account_name = ?, display_name = ? WHERE id = ?",
                (new_name, new_name, account_id),
            )
            return bool(rowcount and rowcount > 0)
        except Exception as e:
            logger.error(f"Error updating account name: {e}")
            return False

    # Tokens
    def save_account_token(
        self,
        account_id: int,
        access_token: str,
        refresh_token: str | None = None,
        token_type: str = "Bearer",
        expires_at: int | None = None,
        scope: str | None = None,
    ) -> bool:
        try:
            from core.security import encrypt_string

            if access_token:
                access_token = encrypt_string(access_token)
            if refresh_token:
                refresh_token = encrypt_string(refresh_token)

            execute_write_sql(
                str(self.database_path),
                """
                    INSERT INTO account_tokens(account_id, access_token, refresh_token, token_type, expires_at, scope)
                    VALUES(?,?,?,?,?,?)
                    ON CONFLICT(account_id)
                    DO UPDATE SET access_token=excluded.access_token, refresh_token=excluded.refresh_token, token_type=excluded.token_type, expires_at=excluded.expires_at, scope=excluded.scope, updated_at=strftime('%s','now')
                """,
                (
                    account_id,
                    access_token,
                    refresh_token,
                    token_type,
                    expires_at,
                    scope,
                ),
            )
            logger.info(f"Saved tokens for account {account_id} in config.db")
            return True
        except Exception as e:
            logger.error(f"Error saving account token: {e}")
            return False

    def get_account_config(self, account_id: int, key: str | None = None) -> Any:
        """Get account configuration from the details JSON blob."""
        try:
            import json

            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT details FROM accounts WHERE id = ?", (account_id,))
                row = c.fetchone()
                if not row or not row[0]:
                    return None if key else {}

                details = json.loads(row[0])
                if key:
                    return details.get(key)
                return details
        except Exception as e:
            logger.error(f"Error getting account config for {account_id}: {e}")
            return None if key else {}

    def get_account_token(self, account_id: int) -> dict[str, Any] | None:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    SELECT t.access_token, t.refresh_token, t.token_type, t.expires_at, t.scope, s.name as provider
                    FROM account_tokens t
                    LEFT JOIN accounts a ON t.account_id = a.id
                    LEFT JOIN services s ON a.service_id = s.id
                    WHERE t.account_id = ?
                """,
                    (account_id,),
                )
                row = c.fetchone()
                if not row:
                    return None

                access_token, refresh_token, token_type, expires_at, scope, provider = row
                from core.security import decrypt_string

                if access_token:
                    access_token = decrypt_string(access_token)
                if refresh_token:
                    refresh_token = decrypt_string(refresh_token)

                return {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": token_type,
                    "expires_at": expires_at,
                    "scope": scope,
                    "provider": provider or "",
                }
        except Exception as e:
            logger.error(f"Error getting account token: {e}")
            return None

    # Removed account_metadata methods

    # PKCE sessions
    def store_pkce_session(
        self,
        pkce_id: str,
        service: str,
        account_id: int,
        code_verifier: str,
        code_challenge: str,
        redirect_uri: str,
        client_id: str,
        ttl_seconds: int = 600,
    ) -> bool:
        try:
            now = int(time.time())
            execute_write_sql(
                str(self.database_path),
                """
                    INSERT OR REPLACE INTO pkce_sessions(pkce_id, service, account_id, code_verifier, code_challenge, redirect_uri, client_id, created_at, expires_at)
                    VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    pkce_id,
                    service,
                    account_id,
                    code_verifier,
                    code_challenge,
                    redirect_uri,
                    client_id,
                    now,
                    now + ttl_seconds,
                ),
            )
            return True
        except Exception as e:
            logger.error(f"Error storing PKCE session: {e}")
            return False

    def get_pkce_session(self, pkce_id: str) -> dict[str, Any] | None:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT pkce_id, service, account_id, code_verifier, code_challenge, redirect_uri, client_id, created_at, expires_at FROM pkce_sessions WHERE pkce_id = ?",
                    (pkce_id,),
                )
                row = c.fetchone()
                if not row:
                    return None
                return {
                    "pkce_id": row[0],
                    "service": row[1],
                    "account_id": row[2],
                    "code_verifier": row[3],
                    "code_challenge": row[4],
                    "redirect_uri": row[5],
                    "client_id": row[6],
                    "created_at": row[7],
                    "expires_at": row[8],
                }
        except Exception as e:
            logger.error(f"Error fetching PKCE session: {e}")
            return None

    def delete_pkce_session(self, pkce_id: str) -> bool:
        try:
            rowcount = execute_write_sql(
                str(self.database_path),
                "DELETE FROM pkce_sessions WHERE pkce_id = ?",
                (pkce_id,),
            )
            return bool(rowcount and rowcount > 0)
        except Exception as e:
            logger.error(f"Error deleting PKCE session: {e}")
            return False

    def cleanup_expired_pkce_sessions(self) -> None:
        try:
            now = int(time.time())
            execute_write_sql(
                str(self.database_path),
                "DELETE FROM pkce_sessions WHERE expires_at < ?",
                (now,),
            )
        except Exception as e:
            logger.error(f"Error cleaning PKCE sessions: {e}")

    # Download Provider Priority
    def get_download_provider_priority(self) -> list[str]:
        """
        Get the user-defined download provider priority list.
        Returns list of provider names in priority order (highest first).
        Example: ["slskd", "yt_dlp", "torrent"]
        """
        try:
            import json

            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT config_value FROM service_config WHERE service_id IS NULL AND config_key = ?",
                    ("download_provider_priority",),
                )
                row = c.fetchone()
                if not row or not row[0]:
                    # Return default: try all active download providers in their natural order
                    return []
                try:
                    return json.loads(row[0])
                except (json.JSONDecodeError, TypeError):
                    logger.warning("Invalid download_provider_priority format, returning default")
                    return []
        except Exception as e:
            logger.error(f"Error getting download provider priority: {e}")
            return []

    def set_download_provider_priority(self, provider_list: list[str]) -> bool:
        """
        Set the user-defined download provider priority list.

        Args:
            provider_list: List of provider names in priority order (highest first)
            Example: ["slskd", "yt_dlp", "torrent"]

        Returns:
            bool: True if successful
        """
        try:
            import json

            # Store as JSON string in a global (service_id=NULL) setting
            json_value = json.dumps(provider_list)

            # Use a special service_id=NULL for global settings
            execute_write_sql(
                str(self.database_path),
                """
                    INSERT INTO service_config(service_id, config_key, config_value, is_sensitive)
                    VALUES(NULL, ?, ?, 0)
                    ON CONFLICT(service_id, config_key)
                    DO UPDATE SET config_value=excluded.config_value, updated_at=strftime('%s','now')
                """,
                ("download_provider_priority", json_value),
            )
            logger.info(f"Set download provider priority: {provider_list}")
            return True
        except Exception as e:
            logger.error(f"Error setting download provider priority: {e}")
            return False

    # ── Account Mapping helpers ─────────────────────────────────────────────

    def set_account_mapping(
        self,
        account_id_1: int,
        account_id_2: int,
    ) -> bool:
        """Upsert a stateful mapping between two accounts.

        Logic sorts the IDs to ensure source_account_id < mapped_account_id,
        preventing duplicate mappings in reverse order.
        """
        try:
            if account_id_1 == account_id_2:
                return False

            source_id, mapped_id = sorted([int(account_id_1), int(account_id_2)])
            execute_write_sql(
                str(self.database_path),
                """
                    INSERT INTO account_mappings(
                        source_account_id, mapped_account_id
                    ) VALUES(?,?)
                    ON CONFLICT(source_account_id, mapped_account_id)
                    DO UPDATE SET updated_at=strftime('%s','now')
                """,
                (source_id, mapped_id),
            )
            return True
        except Exception as e:
            logger.error(f"Error setting account mapping: {e}")
            return False

    def get_account_mappings(
        self,
        account_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve account mapping rows, optionally filtered by a specific account ID."""
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                query = "SELECT id, source_account_id, mapped_account_id, created_at, updated_at FROM account_mappings WHERE 1=1"
                params: list = []
                if account_id:
                    query += " AND (source_account_id = ? OR mapped_account_id = ?)"
                    params.extend([account_id, account_id])

                c.execute(query, params)
                rows = c.fetchall()
                return [
                    {
                        "id": r[0],
                        "source_account_id": r[1],
                        "mapped_account_id": r[2],
                        "created_at": r[3],
                        "updated_at": r[4],
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Error getting account mappings: {e}")
            return []

    def delete_account_mapping(
        self,
        account_id_1: int,
        account_id_2: int,
    ) -> bool:
        """Remove a specific account mapping row."""
        try:
            source_id, mapped_id = sorted([int(account_id_1), int(account_id_2)])
            rowcount = execute_write_sql(
                str(self.database_path),
                "DELETE FROM account_mappings WHERE source_account_id=? AND mapped_account_id=?",
                (source_id, mapped_id),
            )
            return bool(rowcount and rowcount > 0)
        except Exception as e:
            logger.error(f"Error deleting account mapping: {e}")
            return False

    def delete_account_mappings_for_account(
        self,
        account_id: int,
    ) -> None:
        """Quietly purge all mapping rows for an account being deleted."""
        try:
            execute_write_sql(
                str(self.database_path),
                "DELETE FROM account_mappings WHERE source_account_id=? OR mapped_account_id=?",
                (account_id, account_id),
            )
            logger.info(f"Purged all account mappings involving account {account_id}")
        except Exception as e:
            logger.error(f"Error purging account mappings for account {account_id}: {e}")

    # ── Plugin Snapshot Helpers ──────────────────────────────────────────
    def create_plugin_snapshot(self, plugin_id: int, snapshot_data: str, ttl_hours: int = 24) -> bool:
        try:
            expires_at = int(time.time()) + (ttl_hours * 3600)
            execute_write_sql(
                str(self.database_path),
                """
                    INSERT INTO plugin_snapshots(plugin_id, snapshot_data, expires_at)
                    VALUES(?,?,?)
                    ON CONFLICT(plugin_id) DO UPDATE SET
                        snapshot_data = excluded.snapshot_data,
                        expires_at = excluded.expires_at,
                        created_at = strftime('%s','now')
                """,
                (plugin_id, snapshot_data, expires_at),
            )
            return True
        except Exception as e:
            logger.error(f"Error creating plugin snapshot for {plugin_id}: {e}")
            return False

    def get_plugin_snapshot(self, plugin_id: int) -> dict[str, Any] | None:
        try:
            import json

            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT snapshot_data, expires_at FROM plugin_snapshots WHERE plugin_id = ?",
                    (plugin_id,),
                )
                row = c.fetchone()
                if not row:
                    return None

                # Check expiry
                if row[1] < int(time.time()):
                    self.delete_plugin_snapshot(plugin_id)
                    return None

                return {"snapshot_data": json.loads(row[0]), "expires_at": row[1]}
        except Exception as e:
            logger.error(f"Error getting plugin snapshot for {plugin_id}: {e}")
            return None

    def delete_plugin_snapshot(self, plugin_id: int) -> bool:
        try:
            execute_write_sql(
                str(self.database_path),
                "DELETE FROM plugin_snapshots WHERE plugin_id = ?",
                (plugin_id,),
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting plugin snapshot for {plugin_id}: {e}")
            return False

    def cleanup_expired_snapshots(self) -> None:
        try:
            execute_write_sql(
                str(self.database_path),
                "DELETE FROM plugin_snapshots WHERE expires_at < ?",
                (int(time.time()),),
            )
        except Exception as e:
            logger.error(f"Error cleaning expired plugin snapshots: {e}")

    # =========================================================================
    # System Settings (Hot Live Configuration Key-Value Store)
    # =========================================================================

    @retry_sqlite_io(max_retries=5, base_delay=0.05, max_delay=1.0)
    def get_system_setting(self, key: str, default: Any = None) -> Any:
        """Fetch and deserialize a value from system_settings.

        Attempts JSON deserialization for complex objects, booleans, and numbers;
        falls back to raw string on error.
        """
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
                row = c.fetchone()
                if not row or row[0] is None:
                    return default
                val = row[0]
                if isinstance(val, str):
                    import json

                    try:
                        return json.loads(val)
                    except (json.JSONDecodeError, ValueError):
                        return val
                return val
        except sqlite3.OperationalError as oe:
            err_msg = str(oe).lower()
            if any(token in err_msg for token in ("disk i/o error", "locked", "busy")):
                raise
            logger.error(f"Error getting system setting '{key}': {oe}")
            return default
        except Exception as e:
            logger.error(f"Error getting system setting '{key}': {e}")
            return default

    @retry_sqlite_io(max_retries=5, base_delay=0.05, max_delay=1.0)
    def set_system_setting(self, key: str, value: Any) -> bool:
        """Upsert a key, serialized value, and updated_at timestamp into system_settings."""
        try:
            import json
            import time

            if isinstance(value, (dict, list, bool, int, float)):
                val_str = json.dumps(value)
            elif value is None:
                val_str = json.dumps(None)
            else:
                val_str = str(value)

            now_str = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
            execute_write_sql(
                str(self.database_path),
                """
                INSERT INTO system_settings(key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, val_str, now_str),
            )
            return True
        except sqlite3.OperationalError as oe:
            err_msg = str(oe).lower()
            if any(token in err_msg for token in ("disk i/o error", "locked", "busy")):
                raise
            logger.error(f"Error setting system setting '{key}': {oe}")
            return False
        except Exception as e:
            logger.error(f"Error setting system setting '{key}': {e}")
            return False

    @retry_sqlite_io(max_retries=5, base_delay=0.05, max_delay=1.0)
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Alias for get_system_setting with retry protection."""
        return self.get_system_setting(key, default)

    @retry_sqlite_io(max_retries=5, base_delay=0.05, max_delay=1.0)
    def set_setting(self, key: str, value: Any) -> bool:
        """Alias for set_system_setting with retry protection."""
        return self.set_system_setting(key, value)

    @retry_sqlite_io(max_retries=5, base_delay=0.05, max_delay=1.0)
    def get_all_system_settings(self) -> dict[str, Any]:
        """Return all system_settings as a key-value dictionary with JSON deserialization."""
        try:
            import json

            result = {}
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT key, value FROM system_settings")
                for row in c.fetchall():
                    k, v = row[0], row[1]
                    if v is not None and isinstance(v, str):
                        try:
                            result[k] = json.loads(v)
                        except (json.JSONDecodeError, ValueError):
                            result[k] = v
                    else:
                        result[k] = v
            return result
        except sqlite3.OperationalError as oe:
            err_msg = str(oe).lower()
            if any(token in err_msg for token in ("disk i/o error", "locked", "busy")):
                raise
            logger.error(f"Error retrieving all system settings: {oe}")
            return {}
        except Exception as e:
            logger.error(f"Error retrieving all system settings: {e}")
            return {}

    @retry_sqlite_io(max_retries=5, base_delay=0.05, max_delay=1.0)
    def delete_system_setting(self, key: str) -> bool:
        """Delete a key from system_settings."""
        try:
            execute_write_sql(
                str(self.database_path),
                "DELETE FROM system_settings WHERE key = ?",
                (key,),
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting system setting '{key}': {e}")
            return False

    def seed_default_system_settings(self) -> None:
        """Seed canonical default settings if they are not already populated."""
        defaults = {
            "library_import.renaming_pattern": "{Artist}/{Album}/{Track} - {Title}.{ext}",
            "library_import.singles_pattern": "{Artist}/Singles/{Track} - {Title}.{ext}",
            "metadata_enhancement.prefer_canonical_studio_album": True,
            "storage_locations.library": "/data/library",
        }
        for k, v in defaults.items():
            if self.get_system_setting(k) is None:
                self.set_system_setting(k, v)

    # =========================================================================
    # Quality Profiles & Steps (Relational Storage)
    # =========================================================================

    @staticmethod
    def validate_quality_profiles_fallback_dag(profiles: list[dict[str, Any]]) -> tuple[bool, str | None]:
        """Validate 1-hop fallback profile constraint (no cycles, no chains).

        If Profile B is referenced as `fallback_profile_id` by >= 1 other profile,
        Profile B cannot itself define a `fallback_profile_id`.
        """
        by_id: dict[str, dict[str, Any]] = {}
        for p in profiles:
            if isinstance(p, dict) and p.get("id") is not None:
                by_id[str(p["id"])] = p

        referenced_as_fallback: set[str] = set()
        for pid, p in by_id.items():
            fb = p.get("fallback_profile_id")
            if fb is None or str(fb).strip() == "":
                continue
            fb_id = str(fb).strip()
            if fb_id == pid:
                return False, f"Quality profile '{pid}' cannot reference itself as its own fallback."
            if fb_id not in by_id:
                return False, f"Quality profile '{pid}' references unknown fallback profile '{fb_id}'."
            referenced_as_fallback.add(fb_id)

        for fb_id in referenced_as_fallback:
            fb_prof = by_id.get(fb_id) or {}
            nested_fb = fb_prof.get("fallback_profile_id")
            if nested_fb is not None and str(nested_fb).strip() != "":
                return (
                    False,
                    f"Quality profile '{fb_id}' is already used as a fallback and cannot name its own fallback '{nested_fb}'.",
                )

        return True, None

    def get_quality_profiles(self) -> list[dict[str, Any]]:
        """Retrieve all quality profiles with reconstructed formats and step hierarchies."""
        try:
            import json

            profiles_map: dict[str, dict[str, Any]] = {}
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT id, name, prefer_max_quality FROM quality_profiles")
                for row in c.fetchall():
                    pid = str(row[0])
                    profiles_map[pid] = {
                        "id": pid,
                        "name": str(row[1] or ""),
                        "prefer_max_quality": bool(row[2]),
                        "fallback_profile_id": None,
                        "formats": [],
                        "advanced_filters": {},
                    }

                if not profiles_map:
                    return []

                c.execute("SELECT profile_id, priority, rules FROM quality_profile_steps ORDER BY priority ASC")
                for row in c.fetchall():
                    pid, priority, rules_raw = str(row[0]), row[1], row[2]
                    if pid not in profiles_map:
                        continue
                    rules = {}
                    if rules_raw:
                        if isinstance(rules_raw, str):
                            try:
                                rules = json.loads(rules_raw)
                            except Exception:
                                rules = {}
                        elif isinstance(rules_raw, dict):
                            rules = rules_raw

                    # If rules contains advanced_filters or fallback_profile_id metadata
                    if isinstance(rules, dict) and "fallback_profile_id" in rules and len(rules) == 1:
                        fb_val = rules["fallback_profile_id"]
                        profiles_map[pid]["fallback_profile_id"] = str(fb_val).strip() if fb_val else None
                    elif isinstance(rules, dict) and "advanced_filters" in rules and len(rules) == 1:
                        profiles_map[pid]["advanced_filters"] = rules["advanced_filters"]
                    elif isinstance(rules, dict) and "formats" in rules and len(rules) == 1:
                        profiles_map[pid]["formats"] = rules["formats"]
                    else:
                        profiles_map[pid]["formats"].append(rules)

            for p in profiles_map.values():
                p["steps"] = p["formats"]

            return list(profiles_map.values())
        except Exception as e:
            logger.error(f"Error fetching quality profiles: {e}")
            return []

    def get_quality_profile(self, profile_id: str) -> dict[str, Any] | None:
        """Retrieve a single quality profile by ID."""
        for p in self.get_quality_profiles():
            if str(p.get("id")) == str(profile_id):
                return p
        return None

    def set_quality_profile(self, profile: dict[str, Any]) -> bool:
        """Upsert a single quality profile and its step hierarchy."""
        return self.set_quality_profiles([profile], overwrite_all=False)

    def set_quality_profiles(self, profiles: list[dict[str, Any]], overwrite_all: bool = True) -> bool:
        """Persist quality profiles and steps relationally into quality_profiles and quality_profile_steps."""
        try:
            import json

            # Validate 1-hop fallback DAG against full profile set
            if overwrite_all:
                full_set = [p for p in profiles if isinstance(p, dict)]
            else:
                existing_map = {str(p.get("id")): p for p in self.get_quality_profiles() if isinstance(p, dict)}
                for p in profiles:
                    if isinstance(p, dict) and p.get("id") is not None:
                        existing_map[str(p["id"])] = p
                full_set = list(existing_map.values())

            is_valid, err_msg = self.validate_quality_profiles_fallback_dag(full_set)
            if not is_valid:
                logger.warning(f"Rejected quality profile update: {err_msg}")
                return False

            def _write_profiles(cursor):
                if overwrite_all:
                    cursor.execute("DELETE FROM quality_profile_steps")
                    cursor.execute("DELETE FROM quality_profiles")

                for p in profiles:
                    if not isinstance(p, dict):
                        continue
                    pid = str(p.get("id") or "")
                    name = str(p.get("name") or pid)
                    prefer_max = 1 if p.get("prefer_max_quality") else 0

                    if not overwrite_all:
                        cursor.execute(
                            "DELETE FROM quality_profile_steps WHERE profile_id = ?",
                            (pid,),
                        )
                        cursor.execute("DELETE FROM quality_profiles WHERE id = ?", (pid,))

                    cursor.execute(
                        "INSERT INTO quality_profiles (id, name, prefer_max_quality) VALUES (?, ?, ?)",
                        (pid, name, prefer_max),
                    )

                    formats = p.get("formats") or p.get("types") or p.get("steps") or []
                    for idx, fmt in enumerate(formats):
                        fmt_rules = json.dumps(fmt) if not isinstance(fmt, str) else fmt
                        cursor.execute(
                            "INSERT INTO quality_profile_steps (profile_id, priority, rules) VALUES (?, ?, ?)",
                            (pid, idx, fmt_rules),
                        )

                    # Store fallback_profile_id if provided
                    fb_id = p.get("fallback_profile_id")
                    if fb_id is not None and str(fb_id).strip():
                        fb_rules = json.dumps({"fallback_profile_id": str(fb_id).strip()})
                        cursor.execute(
                            "INSERT INTO quality_profile_steps (profile_id, priority, rules) VALUES (?, ?, ?)",
                            (pid, 9998, fb_rules),
                        )

                    # Store advanced_filters if provided
                    if p.get("advanced_filters"):
                        adv_rules = json.dumps({"advanced_filters": p["advanced_filters"]})
                        cursor.execute(
                            "INSERT INTO quality_profile_steps (profile_id, priority, rules) VALUES (?, ?, ?)",
                            (pid, 9999, adv_rules),
                        )

            execute_write(str(self.database_path), _write_profiles)
            return True
        except Exception as e:
            logger.error(f"Error persisting quality profiles: {e}")
            return False

    def delete_quality_profile(self, profile_id: str) -> bool:
        """Delete a quality profile and its steps by ID."""
        try:
            execute_write_sql(
                str(self.database_path),
                "DELETE FROM quality_profiles WHERE id = ?",
                (str(profile_id),),
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting quality profile '{profile_id}': {e}")
            return False

    # --- Local-First Auth, RBAC, API Keys & Managed Accounts ---

    def _hydrate_user_row(self, conn: sqlite3.Connection, user_row: sqlite3.Row | tuple) -> dict[str, Any]:
        import json

        row_dict = dict(user_row) if hasattr(user_row, "keys") else {
            "id": user_row[0],
            "username": user_row[1],
            "auth_provider": user_row[2],
            "oidc_subject": user_row[3],
            "is_active": user_row[4],
            "created_at": user_row[5],
        }
        c = conn.cursor()
        c.execute(
            """
            SELECT r.name, r.permissions_json
            FROM roles r
            JOIN user_role_assignments ura ON ura.role_id = r.id
            WHERE ura.user_id = ?
            ORDER BY r.name ASC
            """,
            (row_dict["id"],),
        )
        roles: list[str] = []
        scopes: set[str] = set()
        for r_name, perms_json in c.fetchall():
            roles.append(r_name)
            try:
                perms = json.loads(perms_json or "[]")
                if isinstance(perms, list):
                    scopes.update(str(p) for p in perms if p)
            except Exception:
                pass
        return {
            "id": row_dict["id"],
            "username": row_dict["username"],
            "auth_provider": row_dict["auth_provider"],
            "oidc_subject": row_dict["oidc_subject"],
            "is_active": bool(row_dict["is_active"]),
            "created_at": row_dict["created_at"],
            "roles": roles,
            "scopes": sorted(scopes),
        }

    def has_any_users(self) -> bool:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT 1 FROM users LIMIT 1")
                return c.fetchone() is not None
        except Exception:
            return False

    def has_admin_user(self) -> bool:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    SELECT 1
                    FROM users u
                    JOIN user_role_assignments ura ON ura.user_id = u.id
                    JOIN roles r ON r.id = ura.role_id
                    WHERE r.name = 'admin' AND u.is_active = 1
                    LIMIT 1
                    """
                )
                return c.fetchone() is not None
        except Exception:
            return False

    def is_setup_required(self) -> bool:
        return not self.has_admin_user()

    def seed_system_roles(self) -> None:
        import json
        from core.security.rbac import SYSTEM_ROLE_PERMISSIONS
        from core.task_manager import db_write_lease

        def _seed(cursor):
            for role_name, role_perms in SYSTEM_ROLE_PERMISSIONS.items():
                cursor.execute(
                    "INSERT OR IGNORE INTO roles (name, is_system, permissions_json) VALUES (?, 1, ?)",
                    (role_name, json.dumps(list(role_perms))),
                )

        with db_write_lease(task_name="seed_system_roles"):
            execute_write(str(self.database_path), _seed)

    def create_user(
        self,
        username: str,
        password: str | None = None,
        *,
        auth_provider: str = "local",
        oidc_subject: str | None = None,
        roles: list[str] | tuple[str, ...] | None = None,
        is_active: bool = True,
    ) -> dict[str, Any]:
        import json
        import uuid
        from core.security.passwords import hash_password
        from core.security.rbac import SYSTEM_ROLE_PERMISSIONS
        from core.task_manager import db_write_lease

        clean_username = str(username).strip()
        if not clean_username:
            raise ValueError("Username cannot be empty.")

        pw_hash = None
        if password is not None:
            pw_hash = hash_password(password, validate_policy=True)
        elif auth_provider == "local":
            raise ValueError("Password is required for local accounts.")

        target_roles = list(dict.fromkeys(roles or ["member"]))
        user_id = str(uuid.uuid4())

        def _insert(cursor):
            for r_name in target_roles:
                default_perms = list(SYSTEM_ROLE_PERMISSIONS.get(r_name, ()))
                cursor.execute(
                    "INSERT OR IGNORE INTO roles (name, is_system, permissions_json) VALUES (?, ?, ?)",
                    (r_name, 1 if r_name in SYSTEM_ROLE_PERMISSIONS else 0, json.dumps(default_perms)),
                )

            cursor.execute(
                """
                INSERT INTO users (id, username, password_hash, auth_provider, oidc_subject, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, clean_username, pw_hash, auth_provider, oidc_subject, 1 if is_active else 0),
            )
            for r_name in target_roles:
                cursor.execute("SELECT id FROM roles WHERE name = ?", (r_name,))
                role_row = cursor.fetchone()
                if role_row:
                    cursor.execute(
                        "INSERT OR IGNORE INTO user_role_assignments (user_id, role_id) VALUES (?, ?)",
                        (user_id, role_row[0]),
                    )

        with db_write_lease(task_name=f"create_user_{clean_username}"):
            execute_write(str(self.database_path), _insert)

        created = self.get_user_by_id(user_id)
        if not created:
            raise RuntimeError("User creation failed unexpectedly.")
        return created

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT id, username, auth_provider, oidc_subject, is_active, created_at FROM users WHERE id = ?",
                    (str(user_id),),
                )
                row = c.fetchone()
                if not row:
                    return None
                return self._hydrate_user_row(conn, row)
        except Exception:
            return None

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT id, username, auth_provider, oidc_subject, is_active, created_at FROM users WHERE LOWER(username) = LOWER(?)",
                    (str(username).strip(),),
                )
                row = c.fetchone()
                if not row:
                    return None
                return self._hydrate_user_row(conn, row)
        except Exception:
            return None

    def get_user_by_oidc_subject(self, oidc_subject: str) -> dict[str, Any] | None:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT id, username, auth_provider, oidc_subject, is_active, created_at FROM users WHERE oidc_subject = ?",
                    (str(oidc_subject),),
                )
                row = c.fetchone()
                if not row:
                    return None
                return self._hydrate_user_row(conn, row)
        except Exception:
            return None

    def authenticate_local_user(self, username: str, password: str) -> dict[str, Any] | None:
        from core.security.passwords import verify_password

        if not username or not password:
            return None
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    SELECT id, username, password_hash, auth_provider, oidc_subject, is_active, created_at
                    FROM users
                    WHERE LOWER(username) = LOWER(?)
                    """,
                    (str(username).strip(),),
                )
                row = c.fetchone()
                if not row:
                    return None
                is_active = bool(row["is_active"])
                pw_hash = row["password_hash"]
                if not is_active or not pw_hash:
                    return None
                if not verify_password(password, pw_hash):
                    return None
                return self._hydrate_user_row(conn, {
                    "id": row["id"],
                    "username": row["username"],
                    "auth_provider": row["auth_provider"],
                    "oidc_subject": row["oidc_subject"],
                    "is_active": row["is_active"],
                    "created_at": row["created_at"],
                })
        except Exception as e:
            logger.error(f"Error authenticating user '{username}': {e}")
            return None

    def list_users(self) -> list[dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    "SELECT id, username, auth_provider, oidc_subject, is_active, created_at FROM users ORDER BY created_at ASC, username ASC"
                )
                return [self._hydrate_user_row(conn, r) for r in c.fetchall()]
        except Exception:
            return []

    def assign_user_roles(self, user_id: str, role_names: list[str]) -> bool:
        import json
        from core.security.rbac import SYSTEM_ROLE_PERMISSIONS
        from core.task_manager import db_write_lease

        if not self.get_user_by_id(user_id):
            return False

        clean_roles = list(dict.fromkeys(str(r).strip() for r in role_names if str(r).strip()))

        def _assign(cursor):
            cursor.execute("DELETE FROM user_role_assignments WHERE user_id = ?", (user_id,))
            for r_name in clean_roles:
                cursor.execute("SELECT id FROM roles WHERE name = ?", (r_name,))
                row = cursor.fetchone()
                if not row and r_name in SYSTEM_ROLE_PERMISSIONS:
                    cursor.execute(
                        "INSERT INTO roles (name, is_system, permissions_json) VALUES (?, 1, ?)",
                        (r_name, json.dumps(list(SYSTEM_ROLE_PERMISSIONS[r_name]))),
                    )
                    cursor.execute("SELECT id FROM roles WHERE name = ?", (r_name,))
                    row = cursor.fetchone()
                if row:
                    cursor.execute(
                        "INSERT OR IGNORE INTO user_role_assignments (user_id, role_id) VALUES (?, ?)",
                        (user_id, row[0]),
                    )

        with db_write_lease(task_name=f"assign_roles_{user_id}"):
            execute_write(str(self.database_path), _assign)
        return True

    def provision_or_link_oidc_user(
        self,
        *,
        oidc_subject: str,
        username: str,
        role_names: list[str] | None = None,
    ) -> dict[str, Any]:
        from core.task_manager import db_write_lease

        target_roles = role_names or ["member"]
        existing = self.get_user_by_oidc_subject(oidc_subject)
        if existing:
            if not existing["is_active"]:
                raise PermissionError("User account is disabled.")
            self.assign_user_roles(existing["id"], target_roles)
            return self.get_user_by_id(existing["id"]) or existing

        # Link by username only if account does not already belong to another OIDC subject
        by_name = self.get_user_by_username(username)
        if by_name and not by_name.get("oidc_subject"):
            def _link(cursor):
                cursor.execute(
                    "UPDATE users SET oidc_subject = ?, auth_provider = 'oidc' WHERE id = ?",
                    (oidc_subject, by_name["id"]),
                )

            with db_write_lease(task_name=f"link_oidc_{by_name['id']}"):
                execute_write(str(self.database_path), _link)
            self.assign_user_roles(by_name["id"], target_roles)
            return self.get_user_by_id(by_name["id"]) or by_name

        candidate_username = username
        if by_name is not None:
            candidate_username = f"{username}_{oidc_subject[:8]}"

        return self.create_user(
            username=candidate_username,
            password=None,
            auth_provider="oidc",
            oidc_subject=oidc_subject,
            roles=target_roles,
        )

    def list_roles(self) -> list[dict[str, Any]]:
        import json

        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT id, name, is_system, permissions_json FROM roles ORDER BY id ASC")
                out = []
                for row in c.fetchall():
                    perms = json.loads(row["permissions_json"] or "[]")
                    out.append(
                        {
                            "id": row["id"],
                            "name": row["name"],
                            "is_system": bool(row["is_system"]),
                            "permissions": perms,
                        }
                    )
                return out
        except Exception:
            return []

    def create_api_key(
        self,
        *,
        user_id: str,
        name: str,
        scopes: list[str] | tuple[str, ...],
        expires_at: int | None = None,
    ) -> dict[str, Any]:
        import json
        import uuid
        from core.security.tokens import generate_api_key
        from core.task_manager import db_write_lease

        if not self.get_user_by_id(user_id):
            raise ValueError(f"Unknown user_id: {user_id}")

        key_id = str(uuid.uuid4())
        raw_key, key_prefix, key_hash = generate_api_key()
        clean_scopes = sorted(set(str(s).strip() for s in scopes if str(s).strip()))

        with db_write_lease(task_name=f"create_api_key_{user_id}"):
            execute_write_sql(
                str(self.database_path),
                """
                INSERT INTO api_keys (id, user_id, name, key_prefix, key_hash, scopes_json, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (key_id, user_id, name.strip(), key_prefix, key_hash, json.dumps(clean_scopes), expires_at),
            )

        return {
            "id": key_id,
            "user_id": user_id,
            "name": name.strip(),
            "key_prefix": key_prefix,
            "api_key": raw_key,
            "scopes": clean_scopes,
            "expires_at": expires_at,
        }

    def list_api_keys(self, user_id: str | None = None) -> list[dict[str, Any]]:
        import json

        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                if user_id:
                    c.execute(
                        """
                        SELECT id, user_id, name, key_prefix, scopes_json, expires_at, revoked_at, created_at
                        FROM api_keys WHERE user_id = ? ORDER BY created_at DESC
                        """,
                        (user_id,),
                    )
                else:
                    c.execute(
                        """
                        SELECT id, user_id, name, key_prefix, scopes_json, expires_at, revoked_at, created_at
                        FROM api_keys ORDER BY created_at DESC
                        """
                    )
                return [
                    {
                        "id": r["id"],
                        "user_id": r["user_id"],
                        "name": r["name"],
                        "key_prefix": r["key_prefix"],
                        "scopes": json.loads(r["scopes_json"] or "[]"),
                        "expires_at": r["expires_at"],
                        "revoked_at": r["revoked_at"],
                        "created_at": r["created_at"],
                    }
                    for r in c.fetchall()
                ]
        except Exception:
            return []

    def revoke_api_key(self, key_id: str, *, user_id: str | None = None) -> bool:
        import time as _time
        from core.task_manager import db_write_lease

        now = int(_time.time())
        with db_write_lease(task_name=f"revoke_api_key_{key_id}"):
            if user_id:
                execute_write_sql(
                    str(self.database_path),
                    "UPDATE api_keys SET revoked_at = ? WHERE id = ? AND user_id = ? AND revoked_at IS NULL",
                    (now, key_id, user_id),
                )
            else:
                execute_write_sql(
                    str(self.database_path),
                    "UPDATE api_keys SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL",
                    (now, key_id),
                )
        keys = self.list_api_keys(user_id=user_id)
        return any(k["id"] == key_id and k["revoked_at"] is not None for k in keys)

    def verify_api_key(self, raw_key: str) -> tuple[dict[str, Any], list[str]] | None:
        import hmac as _hmac
        import json
        import time as _time
        from core.security.tokens import hash_api_key

        if not raw_key or not raw_key.startswith("es_"):
            return None
        prefix = raw_key[:11]
        candidate_hash = hash_api_key(raw_key)
        now = int(_time.time())
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    SELECT id, user_id, key_hash, scopes_json, expires_at, revoked_at
                    FROM api_keys
                    WHERE key_prefix = ?
                    """,
                    (prefix,),
                )
                for row in c.fetchall():
                    if row["revoked_at"] is not None:
                        continue
                    if row["expires_at"] is not None and int(row["expires_at"]) <= now:
                        continue
                    if _hmac.compare_digest(candidate_hash, row["key_hash"]):
                        user = self.get_user_by_id(row["user_id"])
                        if not user or not user["is_active"]:
                            return None
                        scopes = [str(s) for s in json.loads(row["scopes_json"] or "[]")]
                        return user, scopes
        except Exception:
            return None
        return None

    _PROVIDER_DEFAULT_PLUGIN_IDS: dict[str, int] = {
        "plex": 3021005569,
        "jellyfin": 2305548545,
        "navidrome": 4010168341,
        "spotify": 2391116200,
        "tidal": 3782485548,
        "listenbrainz": 3104832291,
    }
    _MEDIA_SERVER_PROVIDERS: frozenset[str] = frozenset({"plex", "jellyfin", "navidrome"})

    def _resolve_provider_metadata(
        self,
        provider: str,
        category: str | None = None,
        plugin_id: int | None = None,
    ) -> tuple[str, str, int | None]:
        clean_provider = str(provider or "").strip().lower().replace("echosync.", "")
        resolved_cat = (category or "").strip().lower()
        if resolved_cat not in ("streaming", "media_server"):
            resolved_cat = "media_server" if clean_provider in self._MEDIA_SERVER_PROVIDERS else "streaming"
        resolved_pid = plugin_id if plugin_id is not None else self._PROVIDER_DEFAULT_PLUGIN_IDS.get(clean_provider)
        return clean_provider, resolved_cat, resolved_pid

    def bind_external_account(
        self,
        user_id: str,
        provider: str,
        external_account_id: str,
        display_name: str | None = None,
        category: str | None = None,
        plugin_id: int | None = None,
    ) -> bool:
        from core.task_manager import db_write_lease

        if not self.get_user_by_id(user_id):
            return False

        clean_provider, resolved_cat, resolved_pid = self._resolve_provider_metadata(provider, category, plugin_id)
        ext_id = str(external_account_id).strip()
        if not clean_provider or not ext_id:
            return False
        disp = (display_name or ext_id).strip()

        with db_write_lease(task_name=f"bind_external_account_{user_id}"):
            execute_write_sql(
                str(self.database_path),
                """
                INSERT INTO user_external_accounts
                    (user_id, provider, category, external_account_id, display_name, plugin_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, provider, external_account_id)
                DO UPDATE SET
                    display_name = excluded.display_name,
                    category = excluded.category,
                    plugin_id = COALESCE(excluded.plugin_id, user_external_accounts.plugin_id)
                """,
                (user_id, clean_provider, resolved_cat, ext_id, disp, resolved_pid),
            )
            if resolved_cat == "media_server" and resolved_pid is not None:
                execute_write_sql(
                    str(self.database_path),
                    """
                    INSERT OR IGNORE INTO user_managed_accounts (user_id, server_plugin_id, managed_account_id)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, int(resolved_pid), ext_id),
                )
        return True

    def unbind_external_account(self, user_id: str, provider: str, external_account_id: str) -> bool:
        from core.task_manager import db_write_lease

        clean_provider, resolved_cat, resolved_pid = self._resolve_provider_metadata(provider)
        ext_id = str(external_account_id).strip()
        with db_write_lease(task_name=f"unbind_external_account_{user_id}"):
            execute_write_sql(
                str(self.database_path),
                """
                DELETE FROM user_external_accounts
                WHERE user_id = ? AND provider = ? AND external_account_id = ?
                """,
                (user_id, clean_provider, ext_id),
            )
            if resolved_cat == "media_server" and resolved_pid is not None:
                execute_write_sql(
                    str(self.database_path),
                    """
                    DELETE FROM user_managed_accounts
                    WHERE user_id = ? AND server_plugin_id = ? AND managed_account_id = ?
                    """,
                    (user_id, int(resolved_pid), ext_id),
                )
        return True

    def get_user_external_accounts(self, user_id: str) -> list[dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    SELECT id, user_id, provider, category, external_account_id, display_name, plugin_id, created_at
                    FROM user_external_accounts
                    WHERE user_id = ?
                    ORDER BY category ASC, provider ASC, display_name ASC
                    """,
                    (user_id,),
                )
                return [
                    {
                        "id": r["id"],
                        "user_id": r["user_id"],
                        "provider": r["provider"],
                        "category": r["category"],
                        "external_account_id": r["external_account_id"],
                        "display_name": r["display_name"] or r["external_account_id"],
                        "plugin_id": int(r["plugin_id"]) if r["plugin_id"] is not None else None,
                        "created_at": r["created_at"],
                    }
                    for r in c.fetchall()
                ]
        except Exception:
            return []

    def list_all_external_accounts(self, category: str | None = None) -> list[dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                sql = """
                    SELECT uea.id, uea.user_id, u.username, uea.provider, uea.category,
                           uea.external_account_id, uea.display_name, uea.plugin_id, uea.created_at
                    FROM user_external_accounts uea
                    JOIN users u ON u.id = uea.user_id
                    WHERE u.is_active = 1
                """
                params: list[Any] = []
                if category:
                    sql += " AND uea.category = ?"
                    params.append(category)
                sql += " ORDER BY u.username ASC, uea.provider ASC, uea.display_name ASC"
                c.execute(sql, params)
                return [
                    {
                        "id": r["id"],
                        "user_id": r["user_id"],
                        "username": r["username"],
                        "provider": r["provider"],
                        "category": r["category"],
                        "external_account_id": r["external_account_id"],
                        "display_name": r["display_name"] or r["external_account_id"],
                        "plugin_id": int(r["plugin_id"]) if r["plugin_id"] is not None else None,
                        "created_at": r["created_at"],
                    }
                    for r in c.fetchall()
                ]
        except Exception:
            return []

    def reset_user_password(self, user_id: str, new_password: str) -> bool:
        from core.security.passwords import hash_password
        from core.task_manager import db_write_lease

        if not self.get_user_by_id(user_id):
            return False
        pw_hash = hash_password(new_password)
        with db_write_lease(task_name=f"reset_user_password_{user_id}"):
            execute_write_sql(
                str(self.database_path),
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (pw_hash, user_id),
            )
        return True

    def delete_user(self, user_id: str) -> bool:
        from core.task_manager import db_write_lease

        user = self.get_user_by_id(user_id)
        if not user:
            return False
        if "admin" in (user.get("roles") or []):
            admins = [u for u in self.list_users() if "admin" in (u.get("roles") or []) and u.get("is_active", True)]
            if len(admins) <= 1:
                raise ValueError("Cannot delete the last remaining active admin user.")
        with db_write_lease(task_name=f"delete_user_{user_id}"):
            execute_write_sql(str(self.database_path), "DELETE FROM users WHERE id = ?", (user_id,))
        return True

    def assign_managed_account(self, user_id: str, server_plugin_id: int, managed_account_id: str) -> bool:
        from core.task_manager import db_write_lease

        if not self.get_user_by_id(user_id):
            return False
        reverse_provider = {v: k for k, v in self._PROVIDER_DEFAULT_PLUGIN_IDS.items()}
        provider = reverse_provider.get(int(server_plugin_id), str(server_plugin_id))
        with db_write_lease(task_name=f"assign_managed_account_{user_id}"):
            execute_write_sql(
                str(self.database_path),
                """
                INSERT OR IGNORE INTO user_managed_accounts (user_id, server_plugin_id, managed_account_id)
                VALUES (?, ?, ?)
                """,
                (user_id, int(server_plugin_id), str(managed_account_id)),
            )
            execute_write_sql(
                str(self.database_path),
                """
                INSERT OR IGNORE INTO user_external_accounts
                    (user_id, provider, category, external_account_id, display_name, plugin_id)
                VALUES (?, ?, 'media_server', ?, ?, ?)
                """,
                (user_id, provider, str(managed_account_id), str(managed_account_id), int(server_plugin_id)),
            )
        return True

    def remove_managed_account(self, user_id: str, server_plugin_id: int, managed_account_id: str) -> bool:
        from core.task_manager import db_write_lease

        reverse_provider = {v: k for k, v in self._PROVIDER_DEFAULT_PLUGIN_IDS.items()}
        provider = reverse_provider.get(int(server_plugin_id), str(server_plugin_id))
        with db_write_lease(task_name=f"remove_managed_account_{user_id}"):
            execute_write_sql(
                str(self.database_path),
                """
                DELETE FROM user_managed_accounts
                WHERE user_id = ? AND server_plugin_id = ? AND managed_account_id = ?
                """,
                (user_id, int(server_plugin_id), str(managed_account_id)),
            )
            execute_write_sql(
                str(self.database_path),
                """
                DELETE FROM user_external_accounts
                WHERE user_id = ? AND provider = ? AND external_account_id = ?
                """,
                (user_id, provider, str(managed_account_id)),
            )
        return True

    def get_user_managed_accounts(self, user_id: str) -> list[dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    SELECT user_id, server_plugin_id, managed_account_id
                    FROM user_managed_accounts
                    WHERE user_id = ?
                    ORDER BY server_plugin_id ASC, managed_account_id ASC
                    """,
                    (user_id,),
                )
                return [
                    {
                        "user_id": r["user_id"],
                        "server_plugin_id": int(r["server_plugin_id"]),
                        "managed_account_id": r["managed_account_id"],
                    }
                    for r in c.fetchall()
                ]
        except Exception:
            return []


_config_db: ConfigDatabase | None = None
_config_db_instances: dict[str, ConfigDatabase] = {}
_config_db_lock = threading.Lock()


def get_config_database(db_path: Any | None = None) -> ConfigDatabase:
    """Return a shared, thread-safe ConfigDatabase instance."""
    global _config_db
    with _config_db_lock:
        if db_path is None:
            if _config_db is None:
                _config_db = ConfigDatabase()
                try:
                    p = str(_config_db.database_path.resolve())
                    _config_db_instances[p] = _config_db
                except Exception:
                    pass
            return _config_db

        try:
            path_str = str(Path(db_path).resolve())
        except Exception:
            path_str = str(db_path)

        if path_str not in _config_db_instances:
            _config_db_instances[path_str] = ConfigDatabase(db_path=str(db_path))
        return _config_db_instances[path_str]


def get_config_db(db_path: Any | None = None) -> ConfigDatabase:
    """FastAPI Depends provider and alias for get_config_database."""
    return get_config_database(db_path=db_path)


def close_config_database() -> None:
    global _config_db
    with _config_db_lock:
        _config_db = None
        _config_db_instances.clear()


__all__ = [
    "ConfigDatabase",
    "close_config_database",
    "get_config_database",
    "get_config_db",
    "retry_sqlite_io",
]


from sqlalchemy import Boolean, Column, Integer, String  # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import declarative_base  # pyright: ignore[reportMissingImports]

ConfigBase = declarative_base()


class ConfigKVS(ConfigBase):
    __tablename__ = "config_kvs"
    plugin_id = Column(Integer, primary_key=True)
    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)
    is_sensitive = Column(Boolean, default=False, nullable=False)
