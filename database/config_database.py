from __future__ import annotations
import os
import sqlite3
import time
from typing import Any, Dict, Optional, List
from pathlib import Path

from core.settings import config_manager
from core.tiered_logger import get_logger

logger = get_logger("config_database")

# Import write helpers after logger to avoid circular issues
from . import execute_write, execute_write_sql, ensure_writer

class ConfigDatabase:
    def __init__(self, db_path: Optional[str] = None):
        # Use encrypted config database path from ConfigManager
        self.database_path = Path(db_path) if db_path else Path(config_manager.database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        # Ensure writer queue is running for this DB
        try:
            ensure_writer(str(self.database_path))
        except Exception:
            # best-effort; don't fail startup if writer can't be created
            pass
        self._initialize_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.database_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _initialize_schema(self):
        try:
            def _schema(cursor):
                # Services
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS services (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        display_name TEXT,
                        service_type TEXT,
                        description TEXT,
                        created_at INTEGER DEFAULT (strftime('%s','now')),
                        updated_at INTEGER DEFAULT (strftime('%s','now'))
                    )
                """)
                # Service config (sensitive values allowed)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS service_config (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                # Account metadata (optional)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS account_metadata (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        account_id INTEGER NOT NULL,
                        metadata_key TEXT NOT NULL,
                        metadata_value TEXT,
                        created_at INTEGER DEFAULT (strftime('%s','now')),
                        updated_at INTEGER DEFAULT (strftime('%s','now')),
                        UNIQUE(account_id, metadata_key),
                        FOREIGN KEY(account_id) REFERENCES accounts(id) ON DELETE CASCADE
                    )
                """)
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
                # Indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_services_name ON services(name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_service ON accounts(service_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tokens_account ON account_tokens(account_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pkce_expires ON pkce_sessions(expires_at)")

            # Run schema creation on writer thread to avoid concurrent-writes
            execute_write(str(self.database_path), _schema)
            logger.info("Config database schema ensured")
        except Exception as e:
            logger.error(f"Failed to initialize config schema: {e}")

    # Service helpers
    def get_or_create_service_id(self, name: str) -> int:
        import contextlib
        with contextlib.closing(self._get_connection()) as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM services WHERE name = ?", (name,))
            row = c.fetchone()
            if row:
                return int(row[0])
        return self.register_service(name, name.capitalize(), 'streaming', f"{name.capitalize()} service")

    def register_service(self, name: str, display_name: str, service_type: str, description: str) -> int:
        try:
            execute_write_sql(str(self.database_path), "INSERT OR IGNORE INTO services(name, display_name, service_type, description) VALUES(?,?,?,?)", (name, display_name, service_type, description))
        except Exception:
            pass
        return self.get_or_create_service_id(name)

    def set_service_config(self, service_id: int, key: str, value: Any, is_sensitive: bool = False) -> bool:
        try:
            from core.security import encrypt_string
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
        except Exception as e:
            logger.error(f"Error setting service config: {e}")
            return False

    def get_service_config(self, service_id: int, key: str) -> Optional[str]:
        try:
            import contextlib
            with contextlib.closing(self._get_connection()) as conn:
                c = conn.cursor()
                c.execute("SELECT config_value, is_sensitive FROM service_config WHERE service_id=? AND config_key=?", (service_id, key))
                row = c.fetchone()

                if not row:
                    return None

                value, is_sensitive = row[0], row[1]
                if is_sensitive and value is not None:
                    from core.security import decrypt_string
                    value = decrypt_string(value)

                return value
        except Exception as e:
            logger.error(f"Error reading service config: {e}")
            return None

    # Accounts
    def get_accounts(self, service_id: Optional[int] = None, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        try:
            import contextlib
            with contextlib.closing(self._get_connection()) as conn:
                c = conn.cursor()
                query = "SELECT id, service_id, account_name, display_name, user_id, account_email, is_active, is_authenticated, last_authenticated_at FROM accounts WHERE 1=1"
                params: list[Any] = []
                if service_id is not None:
                    query += " AND service_id = ?"; params.append(service_id)
                if is_active is not None:
                    query += " AND is_active = ?"; params.append(1 if is_active else 0)
                c.execute(query, params)
                rows = c.fetchall()
                return [
                    {
                        'id': r[0], 'service_id': r[1], 'account_name': r[2], 'display_name': r[3], 'user_id': r[4],
                        'account_email': r[5], 'is_active': bool(r[6]), 'is_authenticated': bool(r[7]), 'last_authenticated_at': r[8]
                    }
                    for r in rows
                ]
        except Exception as e:
            logger.error(f"Error getting accounts: {e}")
            return []

    def ensure_account(self, service_id: int, account_id: Optional[int] = None, account_name: Optional[str] = None, display_name: Optional[str] = None, user_id: Optional[str] = None) -> int:
        """Ensure an account row exists for the given service.
        If account_id is provided, attempt to insert with that explicit id; otherwise autogenerate.
        Returns the account id.
        """
        try:
            # If explicit account_id is provided, check existence using a reader
            if account_id is not None:
                import contextlib
                with contextlib.closing(self._get_connection()) as conn:
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
                    cursor.execute("UPDATE accounts SET is_active = 0 WHERE service_id = ?", (service_id,))
                cursor.execute("UPDATE accounts SET is_active = 1 WHERE id = ? AND service_id = ?", (account_id, service_id))

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
            execute_write_sql(str(self.database_path), "UPDATE accounts SET is_active = ? WHERE id = ?", (1 if is_active else 0, account_id))
            return True
        except Exception as e:
            logger.error(f"Error toggling account active status: {e}")
            return False

    def mark_account_authenticated(self, account_id: int) -> bool:
        try:
            execute_write_sql(str(self.database_path), "UPDATE accounts SET is_authenticated = 1, last_authenticated_at = ? WHERE id = ?", (int(time.time()), account_id))
            return True
        except Exception as e:
            logger.error(f"Error marking account authenticated: {e}")
            return False

    def set_account_user_id(self, account_id: int, user_id: str) -> bool:
        try:
            rowcount = execute_write_sql(str(self.database_path), "UPDATE accounts SET user_id = ? WHERE id = ?", (user_id, account_id))
            return (rowcount and rowcount > 0)
        except Exception as e:
            logger.error(f"Error setting account user_id: {e}")
            return False

    def delete_account(self, account_id: int) -> bool:
        try:
            rowcount = execute_write_sql(str(self.database_path), "DELETE FROM accounts WHERE id = ?", (account_id,))
            return (rowcount and rowcount > 0)
        except Exception as e:
            logger.error(f"Error deleting account: {e}")
            return False

    def update_account_name(self, account_id: int, new_name: str) -> bool:
        try:
            rowcount = execute_write_sql(str(self.database_path), "UPDATE accounts SET account_name = ?, display_name = ? WHERE id = ?", (new_name, new_name, account_id))
            return (rowcount and rowcount > 0)
        except Exception as e:
            logger.error(f"Error updating account name: {e}")
            return False

    # Tokens
    def save_account_token(self, account_id: int, access_token: str, refresh_token: Optional[str] = None, token_type: str = 'Bearer', expires_at: Optional[int] = None, scope: Optional[str] = None) -> bool:
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
                (account_id, access_token, refresh_token, token_type, expires_at, scope),
            )
            logger.info(f"Saved tokens for account {account_id} in config.db")
            return True
        except Exception as e:
            logger.error(f"Error saving account token: {e}")
            return False

    def get_account_config(self, account_id: int, key: str = None) -> Any:
        """Get account configuration from the details JSON blob."""
        try:
            import json
            import contextlib
            with contextlib.closing(self._get_connection()) as conn:
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

    def get_account_token(self, account_id: int) -> Optional[Dict[str, Any]]:
        try:
            import contextlib
            with contextlib.closing(self._get_connection()) as conn:
                c = conn.cursor()
                c.execute("SELECT access_token, refresh_token, token_type, expires_at, scope FROM account_tokens WHERE account_id = ?", (account_id,))
                row = c.fetchone()
                if not row:
                    return None

                access_token, refresh_token, token_type, expires_at, scope = row
                from core.security import decrypt_string

                if access_token:
                    access_token = decrypt_string(access_token)
                if refresh_token:
                    refresh_token = decrypt_string(refresh_token)

                return {
                    'access_token': access_token, 'refresh_token': refresh_token, 'token_type': token_type, 'expires_at': expires_at, 'scope': scope
                }
        except Exception as e:
            logger.error(f"Error getting account token: {e}")
            return None

    # Account metadata (per-account configuration like client_id, client_secret)
    def set_account_metadata(self, account_id: int, key: str, value: str, is_sensitive: bool = False) -> bool:
        """Set per-account metadata (credentials, etc)."""
        try:
            logger.info(f"ConfigDB.set_account_metadata: account_id={account_id}, key={key}, value_length={len(value) if value else 0}, is_sensitive={is_sensitive}")
            logger.info(f"ConfigDB: Database path = {self.database_path}")
            
            from core.security import encrypt_string
            if is_sensitive and value is not None:
                value = encrypt_string(str(value))

            # Store the value
            logger.info(f"ConfigDB: Executing SQL INSERT/UPDATE on account_metadata table")
            rowcount = execute_write_sql(
                str(self.database_path),
                """
                    INSERT INTO account_metadata(account_id, metadata_key, metadata_value, updated_at)
                    VALUES(?,?,?, strftime('%s','now'))
                    ON CONFLICT(account_id, metadata_key) DO UPDATE SET
                        metadata_value = excluded.metadata_value,
                        updated_at = strftime('%s','now')
                """,
                (account_id, key, value),
            )
            logger.info(f"ConfigDB: Rows affected = {rowcount}")
            
            # Verify it was saved
            import contextlib
            with contextlib.closing(self._get_connection()) as conn:
                c = conn.cursor()
                c.execute("SELECT metadata_value FROM account_metadata WHERE account_id = ? AND metadata_key = ?", (account_id, key))
                row = c.fetchone()
                logger.info(f"ConfigDB: Verification read - row exists: {row is not None}, stored_value_length: {len(row[0]) if row and row[0] else 0}")
            
            return True
        except Exception as e:
            logger.error(f"Error setting account metadata: {e}", exc_info=True)
            return False

    def get_account_metadata(self, account_id: int, key: str) -> Optional[str]:
        """Get per-account metadata (credentials, etc)."""
        try:
            logger.info(f"ConfigDB.get_account_metadata: account_id={account_id}, key={key}")
            logger.info(f"ConfigDB: Database path = {self.database_path}")
            import contextlib
            with contextlib.closing(self._get_connection()) as conn:
                c = conn.cursor()
                c.execute("SELECT metadata_value FROM account_metadata WHERE account_id = ? AND metadata_key = ?", (account_id, key))
                row = c.fetchone()
                logger.info(f"ConfigDB: Row found: {row is not None}, value_length: {len(row[0]) if row and row[0] else 0}")
                if not row or row[0] is None:
                    return None
                value = row[0]

                if value and value.startswith('enc:'):
                    from core.security import decrypt_string
                    value = decrypt_string(value)

                logger.info(f"ConfigDB: Returning value length: {len(value) if value else 0}")
                return value
        except Exception as e:
            logger.error(f"Error getting account metadata: {e}", exc_info=True)
            return None

    def delete_account_metadata(self, account_id: int, key: str) -> bool:
        """Delete per-account metadata."""
        try:
            rowcount = execute_write_sql(str(self.database_path), "DELETE FROM account_metadata WHERE account_id = ? AND metadata_key = ?", (account_id, key))
            return (rowcount and rowcount > 0)
        except Exception as e:
            logger.error(f"Error deleting account metadata: {e}")
            return False

    # PKCE sessions
    def store_pkce_session(self, pkce_id: str, service: str, account_id: int, code_verifier: str, code_challenge: str, redirect_uri: str, client_id: str, ttl_seconds: int = 600) -> bool:
        try:
            now = int(time.time())
            execute_write_sql(
                str(self.database_path),
                """
                    INSERT OR REPLACE INTO pkce_sessions(pkce_id, service, account_id, code_verifier, code_challenge, redirect_uri, client_id, created_at, expires_at)
                    VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (pkce_id, service, account_id, code_verifier, code_challenge, redirect_uri, client_id, now, now + ttl_seconds),
            )
            return True
        except Exception as e:
            logger.error(f"Error storing PKCE session: {e}")
            return False

    def get_pkce_session(self, pkce_id: str) -> Optional[Dict[str, Any]]:
        try:
            import contextlib
            with contextlib.closing(self._get_connection()) as conn:
                c = conn.cursor()
                c.execute("SELECT pkce_id, service, account_id, code_verifier, code_challenge, redirect_uri, client_id, created_at, expires_at FROM pkce_sessions WHERE pkce_id = ?", (pkce_id,))
                row = c.fetchone()
                if not row:
                    return None
                return {
                    'pkce_id': row[0], 'service': row[1], 'account_id': row[2], 'code_verifier': row[3], 'code_challenge': row[4], 'redirect_uri': row[5], 'client_id': row[6], 'created_at': row[7], 'expires_at': row[8]
                }
        except Exception as e:
            logger.error(f"Error fetching PKCE session: {e}")
            return None

    def delete_pkce_session(self, pkce_id: str) -> bool:
        try:
            rowcount = execute_write_sql(str(self.database_path), "DELETE FROM pkce_sessions WHERE pkce_id = ?", (pkce_id,))
            return (rowcount and rowcount > 0)
        except Exception as e:
            logger.error(f"Error deleting PKCE session: {e}")
            return False

    def cleanup_expired_pkce_sessions(self) -> None:
        try:
            now = int(time.time())
            execute_write_sql(str(self.database_path), "DELETE FROM pkce_sessions WHERE expires_at < ?", (now,))
        except Exception as e:
            logger.error(f"Error cleaning PKCE sessions: {e}")

    # Download Provider Priority
    def get_download_provider_priority(self) -> List[str]:
        """
        Get the user-defined download provider priority list.
        Returns list of provider names in priority order (highest first).
        Example: ["slskd", "yt_dlp", "torrent"]
        """
        try:
            import json
            import contextlib
            with contextlib.closing(self._get_connection()) as conn:
                c = conn.cursor()
                c.execute("SELECT config_value FROM service_config WHERE service_id IS NULL AND config_key = ?", ("download_provider_priority",))
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

    def set_download_provider_priority(self, provider_list: List[str]) -> bool:
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


_config_db: Optional[ConfigDatabase] = None

def get_config_database() -> ConfigDatabase:
    global _config_db
    if _config_db is None:
        _config_db = ConfigDatabase()
    return _config_db
