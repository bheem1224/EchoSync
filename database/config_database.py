from __future__ import annotations
import os
import sqlite3
import time
from typing import Any, Dict, Optional, List
from pathlib import Path

from config.settings import config_manager
from utils.logging_config import get_logger

logger = get_logger("config_database")

class ConfigDatabase:
    def __init__(self, db_path: Optional[str] = None):
        # Use encrypted config database path from ConfigManager
        self.database_path = Path(db_path) if db_path else Path(config_manager.database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.database_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    def _initialize_schema(self):
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                # Services
                c.execute("""
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
                c.execute("""
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
                c.execute("""
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
                c.execute("""
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
                c.execute("""
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
                c.execute("""
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
                c.execute("CREATE INDEX IF NOT EXISTS idx_services_name ON services(name)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_accounts_service ON accounts(service_id)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_tokens_account ON account_tokens(account_id)")
                c.execute("CREATE INDEX IF NOT EXISTS idx_pkce_expires ON pkce_sessions(expires_at)")
                conn.commit()
                logger.info("Config database schema ensured")
        except Exception as e:
            logger.error(f"Failed to initialize config schema: {e}")

    # Service helpers
    def get_or_create_service_id(self, name: str) -> int:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM services WHERE name = ?", (name,))
            row = c.fetchone()
            if row:
                return int(row[0])
            return self.register_service(name, name.capitalize(), 'streaming', f"{name.capitalize()} service")

    def register_service(self, name: str, display_name: str, service_type: str, description: str) -> int:
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("INSERT OR IGNORE INTO services(name, display_name, service_type, description) VALUES(?,?,?,?)", (name, display_name, service_type, description))
            conn.commit()
            return self.get_or_create_service_id(name)

    def set_service_config(self, service_id: int, key: str, value: Any, is_sensitive: bool = False) -> bool:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    INSERT INTO service_config(service_id, config_key, config_value, is_sensitive)
                    VALUES(?,?,?,?)
                    ON CONFLICT(service_id, config_key)
                    DO UPDATE SET config_value=excluded.config_value, is_sensitive=excluded.is_sensitive, updated_at=strftime('%s','now')
                    """,
                    (service_id, key, value, 1 if is_sensitive else 0),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting service config: {e}")
            return False

    def get_service_config(self, service_id: int, key: str) -> Optional[str]:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT config_value FROM service_config WHERE service_id=? AND config_key=?", (service_id, key))
                row = c.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"Error reading service config: {e}")
            return None

    # Accounts
    def get_accounts(self, service_id: Optional[int] = None, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        try:
            with self._get_connection() as conn:
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
            with self._get_connection() as conn:
                c = conn.cursor()
                if account_id is not None:
                    # Check if exists
                    c.execute("SELECT id FROM accounts WHERE id = ?", (account_id,))
                    row = c.fetchone()
                    if row:
                        return int(row[0])
                    # Insert with explicit id
                    c.execute(
                        """
                        INSERT INTO accounts(id, service_id, account_name, display_name, user_id, is_active, is_authenticated)
                        VALUES(?,?,?,?,?,0,0)
                        """,
                        (account_id, service_id, account_name, display_name, user_id),
                    )
                    conn.commit()
                    return int(account_id)
                else:
                    c.execute(
                        """
                        INSERT INTO accounts(service_id, account_name, display_name, user_id, is_active, is_authenticated)
                        VALUES(?,?,?,?,0,0)
                        """,
                        (service_id, account_name, display_name, user_id),
                    )
                    conn.commit()
                    last_id = c.lastrowid if c.lastrowid is not None else 0
                    return int(last_id)
        except Exception as e:
            logger.error(f"Error ensuring account exists: {e}")
            return int(account_id) if account_id is not None else 0

    def set_active_account(self, service_id: int, account_id: int) -> bool:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE accounts SET is_active = 0 WHERE service_id = ?", (service_id,))
                c.execute("UPDATE accounts SET is_active = 1 WHERE id = ? AND service_id = ?", (account_id, service_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting active account: {e}")
            return False

    def mark_account_authenticated(self, account_id: int) -> bool:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE accounts SET is_authenticated = 1, last_authenticated_at = ? WHERE id = ?", (int(time.time()), account_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error marking account authenticated: {e}")
            return False

    def set_account_user_id(self, account_id: int, user_id: str) -> bool:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE accounts SET user_id = ? WHERE id = ?", (user_id, account_id))
                conn.commit()
                return c.rowcount > 0
        except Exception as e:
            logger.error(f"Error setting account user_id: {e}")
            return False

    def delete_account(self, account_id: int) -> bool:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
                conn.commit()
                return c.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting account: {e}")
            return False

    def update_account_name(self, account_id: int, new_name: str) -> bool:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE accounts SET account_name = ?, display_name = ? WHERE id = ?", (new_name, new_name, account_id))
                conn.commit()
                return c.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating account name: {e}")
            return False

    # Tokens
    def save_account_token(self, account_id: int, access_token: str, refresh_token: Optional[str] = None, token_type: str = 'Bearer', expires_at: Optional[int] = None, scope: Optional[str] = None) -> bool:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    INSERT INTO account_tokens(account_id, access_token, refresh_token, token_type, expires_at, scope)
                    VALUES(?,?,?,?,?,?)
                    ON CONFLICT(account_id)
                    DO UPDATE SET access_token=excluded.access_token, refresh_token=excluded.refresh_token, token_type=excluded.token_type, expires_at=excluded.expires_at, scope=excluded.scope, updated_at=strftime('%s','now')
                    """,
                    (account_id, access_token, refresh_token, token_type, expires_at, scope),
                )
                conn.commit()
                logger.info(f"Saved tokens for account {account_id} in config.db")
                return True
        except Exception as e:
            logger.error(f"Error saving account token: {e}")
            return False

    def get_account_token(self, account_id: int) -> Optional[Dict[str, Any]]:
        try:
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT access_token, refresh_token, token_type, expires_at, scope FROM account_tokens WHERE account_id = ?", (account_id,))
                row = c.fetchone()
                if not row:
                    return None
                return {
                    'access_token': row[0], 'refresh_token': row[1], 'token_type': row[2], 'expires_at': row[3], 'scope': row[4]
                }
        except Exception as e:
            logger.error(f"Error getting account token: {e}")
            return None

    # PKCE sessions
    def store_pkce_session(self, pkce_id: str, service: str, account_id: int, code_verifier: str, code_challenge: str, redirect_uri: str, client_id: str, ttl_seconds: int = 600) -> bool:
        try:
            now = int(time.time())
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute(
                    """
                    INSERT OR REPLACE INTO pkce_sessions(pkce_id, service, account_id, code_verifier, code_challenge, redirect_uri, client_id, created_at, expires_at)
                    VALUES(?,?,?,?,?,?,?,?,?)
                    """,
                    (pkce_id, service, account_id, code_verifier, code_challenge, redirect_uri, client_id, now, now + ttl_seconds),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error storing PKCE session: {e}")
            return False

    def get_pkce_session(self, pkce_id: str) -> Optional[Dict[str, Any]]:
        try:
            with self._get_connection() as conn:
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
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM pkce_sessions WHERE pkce_id = ?", (pkce_id,))
                conn.commit()
                return c.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting PKCE session: {e}")
            return False

    def cleanup_expired_pkce_sessions(self) -> None:
        try:
            now = int(time.time())
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM pkce_sessions WHERE expires_at < ?", (now,))
                conn.commit()
        except Exception as e:
            logger.error(f"Error cleaning PKCE sessions: {e}")


_config_db: Optional[ConfigDatabase] = None

def get_config_database() -> ConfigDatabase:
    global _config_db
    if _config_db is None:
        _config_db = ConfigDatabase()
    return _config_db
