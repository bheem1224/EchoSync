from __future__ import annotations
import os
import sqlite3
import re
import time
import contextlib
from typing import Any, Dict, Optional, List, Generator
from pathlib import Path

from core.settings import config_manager
from core.tiered_logger import get_logger

logger = get_logger("config_database")

# Import write helpers after logger to avoid circular issues
from . import execute_write, execute_write_sql, ensure_writer

class ConfigDatabase:
    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.database_path = Path(db_path)
        else:
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
            self._initialize_schema()
        except sqlite3.DatabaseError as de:
            if "malformed database schema" in str(de) or "orphan index" in str(de):
                logger.warning(f"Database schema malformed: {de}. Attempting automatic recovery via VACUUM and REINDEX...")
                try:
                    conn = sqlite3.connect(str(self.database_path), timeout=30.0)
                    conn.execute("VACUUM")
                    conn.execute("REINDEX")
                    conn.close()
                    logger.info("Automatic database recovery completed successfully. Retrying schema initialization...")
                    self._initialize_schema()
                except Exception as ree:
                    logger.error(f"Automatic database recovery failed: {ree}")
                    raise de
            else:
                raise

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
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND sql LIKE '%accounts_temp_migration_swap%'")
                    broken_tables = [r[0] for r in cursor.fetchall()]
                    
                    if 'account_tokens' in broken_tables:
                        logger.warning("Healing corrupted account_tokens schema...")
                        cursor.execute("CREATE TABLE account_tokens_backup AS SELECT * FROM account_tokens")
                        cursor.execute("DROP TABLE account_tokens")
                        cursor.execute('''
                            CREATE TABLE account_tokens (
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
                        ''')
                        cursor.execute("INSERT INTO account_tokens SELECT * FROM account_tokens_backup")
                        cursor.execute("DROP TABLE account_tokens_backup")
                        logger.info("Successfully healed account_tokens schema.")

                    if 'account_mappings' in broken_tables:
                        logger.warning("Healing corrupted account_mappings schema...")
                        cursor.execute("CREATE TABLE account_mappings_backup AS SELECT * FROM account_mappings")
                        cursor.execute("DROP TABLE account_mappings")
                        cursor.execute('''
                            CREATE TABLE account_mappings (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                source_account_id INTEGER NOT NULL,
                                mapped_account_id INTEGER NOT NULL,
                                created_at INTEGER DEFAULT (strftime('%s','now')),
                                updated_at INTEGER DEFAULT (strftime('%s','now')),
                                UNIQUE(source_account_id, mapped_account_id),
                                FOREIGN KEY(source_account_id) REFERENCES accounts(id) ON DELETE CASCADE,
                                FOREIGN KEY(mapped_account_id) REFERENCES accounts(id) ON DELETE CASCADE
                            )
                        ''')
                        cursor.execute("INSERT INTO account_mappings SELECT * FROM account_mappings_backup")
                        cursor.execute("DROP TABLE account_mappings_backup")
                        logger.info("Successfully healed account_mappings schema.")

                # 0. Self-healing: Repair any tables whose foreign keys were rewritten to _old or _temp tables
                heal_table_schemas(cursor)
                
                # Cleanup orphaned triggers/views from DB Browser migrations
                cursor.execute("SELECT type, name FROM sqlite_master WHERE sql LIKE '%accounts_temp_migration_swap%' AND type IN ('trigger', 'view')")
                for t_row in cursor.fetchall():
                    cursor.execute(f"DROP {t_row[0].upper()} IF EXISTS {t_row[1]}")

                # Check if services table exists and has UNIQUE name constraint
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='services'")
                row = cursor.fetchone()
                has_unique_name = False
                if row:
                    sql_str = row[0]
                    col_unique = re.search(r'\bname\b[^,]*\bunique\b', sql_str, re.IGNORECASE) is not None
                    table_unique = re.search(r'\bunique\s*\(\s*name\s*\)', sql_str, re.IGNORECASE) is not None
                    has_unique_name = col_unique or table_unique
                if has_unique_name:
                    logger.info("Migrating services table to remove UNIQUE constraint from name column...")
                    try:
                        cursor.connection.commit()
                        cursor.execute("PRAGMA foreign_keys = OFF")
                        cursor.execute("ALTER TABLE services RENAME TO services_old")
                        cursor.execute("""
                            CREATE TABLE services (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT NOT NULL,
                                plugin_id INTEGER UNIQUE,
                                absolute_install_path TEXT,
                                loaded_modules TEXT,
                                version TEXT,
                                service_type TEXT,
                                description TEXT,
                                is_active INTEGER DEFAULT 1,
                                beta_opt_in INTEGER,
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
                                version, service_type, description, is_active, beta_opt_in, 
                                previous_version_path, verified_source, privileged_mode, permissions, 
                                capabilities, created_at, updated_at
                            )
                            SELECT 
                                id, name, plugin_id, absolute_install_path, loaded_modules, 
                                version, service_type, description, is_active, beta_opt_in, 
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
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        plugin_id INTEGER UNIQUE,
                        absolute_install_path TEXT,
                        loaded_modules TEXT,
                        version TEXT,
                        service_type TEXT,
                        description TEXT,
                        is_active INTEGER DEFAULT 1,
                        beta_opt_in INTEGER,
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
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                if ps_columns and 'plugin_id' not in ps_columns:
                    cursor.execute("DROP TABLE IF EXISTS plugin_snapshots")

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS plugin_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plugin_id INTEGER NOT NULL UNIQUE,
                        snapshot_data TEXT NOT NULL,
                        expires_at INTEGER NOT NULL,
                        created_at INTEGER DEFAULT (strftime('%s','now'))
                    )
                """)

                # UI Component Registry (Sprint 6 — replaces live ui_manifest.json disk parsing)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS ui_components (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        plugin_id INTEGER,
                        tag_name TEXT NOT NULL UNIQUE,
                        component_type TEXT NOT NULL,
                        entry_path TEXT NOT NULL,
                        is_core INTEGER DEFAULT 0,
                        created_at INTEGER DEFAULT (strftime('%s','now')),
                        updated_at INTEGER DEFAULT (strftime('%s','now'))
                    )
                """)


                # Migration: Add missing columns to services table if they don't exist
                cursor.execute("PRAGMA table_info(services)")
                columns = [row[1] for row in cursor.fetchall()]
                if 'absolute_install_path' not in columns:
                    cursor.execute("ALTER TABLE services ADD COLUMN absolute_install_path TEXT")
                if 'loaded_modules' not in columns:
                    cursor.execute("ALTER TABLE services ADD COLUMN loaded_modules TEXT")
                if 'plugin_id' not in columns:
                    cursor.execute("ALTER TABLE services ADD COLUMN plugin_id INTEGER")
                if 'version' not in columns:
                    cursor.execute("ALTER TABLE services ADD COLUMN version TEXT")
                if 'capabilities' not in columns:
                    cursor.execute("ALTER TABLE services ADD COLUMN capabilities TEXT DEFAULT '{}'")
                
                # Cleanup: Drop deprecated tables
                cursor.execute("DROP TABLE IF EXISTS accounts_metadata")
                cursor.execute("DROP TABLE IF EXISTS config_kvs")

                # Indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_services_name ON services(name)")

                cursor.execute("CREATE INDEX IF NOT EXISTS idx_services_plugin_id ON services(plugin_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_service ON accounts(service_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tokens_account ON account_tokens(account_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_pkce_expires ON pkce_sessions(expires_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_account_mappings_source ON account_mappings(source_account_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_account_mappings_mapped ON account_mappings(mapped_account_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_plugin_snapshots_plugin_id ON plugin_snapshots(plugin_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_plugin_snapshots_expires ON plugin_snapshots(expires_at)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_ui_components_plugin_id ON ui_components(plugin_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_ui_components_component_type ON ui_components(component_type)")


                # Inline legacy services migration to avoid schema cache latency on separate connection
                cursor.execute("PRAGMA table_info(services)")
                current_columns = [row[1] for row in cursor.fetchall()]
                if 'plugin_id' in current_columns:
                    import binascii
                    cursor.execute("SELECT id, name FROM services WHERE plugin_id IS NULL OR typeof(plugin_id) = 'text'")
                    rows = cursor.fetchall()
                    if rows:
                        try:
                            from core.nexus_framework.plugin_loader import get_all_plugins
                            all_plugins = get_all_plugins()
                            for r in rows:
                                s_id, s_name = r[0], r[1]
                                resolved_plugin_id_str = s_name
                                resolved_version = '1.0.0'
                                for p in all_plugins:
                                    p_id = p.get('id', '')
                                    p_name = p.get('name', '')
                                    p_folder = p.get('folder_name', '')
                                    norm_s_name = s_name.replace('.', '/')
                                    if s_name.lower() in p_folder.lower() or norm_s_name.lower() in p_folder.lower() or s_name.lower() == p_name.lower() or s_name.lower() in p_id.lower():
                                        resolved_plugin_id_str = p_folder.split('/')[-1]
                                        resolved_version = p.get('version', '1.0.0')
                                        break
                                plugin_id_int = binascii.crc32(resolved_plugin_id_str.encode('utf-8')) & 0xFFFFFFFF
                                cursor.execute("UPDATE services SET plugin_id = ? WHERE id = ?", (plugin_id_int, s_id))
                        except Exception:
                            pass

                # Final Self-healing: Double check that no table references services_old or accounts_temp
                heal_table_schemas(cursor)

            # Run schema creation and inline migrations on writer thread to avoid concurrent-writes
            execute_write(str(self.database_path), _schema)
            logger.info("Config database schema ensured and legacy services migrated")
        except Exception as e:
            logger.error(f"Failed to initialize config schema: {e}", exc_info=True)

    # Service helpers
    def get_or_create_service_id(self, name: str) -> int:
        # Strip channel-suffix (@beta / @stable) produced by SDK._get_plugin_id()
        # so all lookups operate on the canonical plugin name regardless of active channel.
        if name and '@' in name:
            name = name.split('@')[0]

        # 1. Try to find existing using the extremely robust get_service_id
        existing_id = self.get_service_id(name)
        if existing_id:
            return existing_id

        # 2. Register if missing (ONLY if it is core service 'system' OR matches a physically installed plugin)
        import binascii

        resolved_plugin_id_str = name
        resolved_version = '1.0.0'
        resolved_path = None
        is_matched = False
        try:
            from core.nexus_framework.plugin_loader import get_all_plugins
            for p in get_all_plugins():
                p_id = p.get('id', '')
                p_name = p.get('name', '')
                if (name.lower() == p_id.lower() or 
                    p_id.lower().endswith('.' + name.lower()) or 
                    name.lower() == p_name.lower() or 
                    p_name.lower().endswith('.' + name.lower())):
                    resolved_plugin_id_str = p_id
                    resolved_version = p.get('version', '1.0.0')
                    resolved_path = p.get('abs_path')
                    is_matched = True
                    break
        except Exception as e:
            logger.error(f"Failed to resolve plugin details for {name}: {e}")

        if not is_matched and name.lower().startswith('echosync.'):
            plugin_name = name.split('.')[-1]
            from core.settings import config_manager
            from pathlib import Path
            bundle_path = Path(config_manager.get_plugins_dir()) / 'EchoSync' / plugin_name
            if bundle_path.exists():
                resolved_plugin_id_str = name
                resolved_version = '1.0.0'
                resolved_path = str(bundle_path.resolve())
                is_matched = True

        if name.lower() == 'system' or is_matched:
            plugin_id_int = binascii.crc32(resolved_plugin_id_str.lower().encode('utf-8')) & 0xFFFFFFFF
            self.register_service(resolved_plugin_id_str, 'streaming', f"{resolved_plugin_id_str.capitalize()} service", 
                                  absolute_install_path=resolved_path, plugin_id=plugin_id_int, version=resolved_version)

            # 3. Try to find again after registration
            existing_id = self.get_service_id(name)
            if existing_id:
                return existing_id
        else:
            logger.debug(f"Service '{name}' is not physically installed or core. Not registering.")

        return 0

    def register_service(self, name: str, service_type: str, description: str, absolute_install_path: Optional[str] = None, plugin_id: Optional[int] = None, version: Optional[str] = None, loaded_modules: Optional[str] = None, beta_opt_in: Optional[int] = None, verified_source: Optional[int] = None, privileged_mode: Optional[int] = None, permissions: Optional[str] = None, capabilities: Optional[str] = None) -> int:
        import binascii
        if plugin_id is None:
            # Fallback CRC32 generation if not provided (ALWAYS use full lowercase namespace for consistency)
            plugin_id = binascii.crc32(name.lower().encode('utf-8')) & 0xFFFFFFFF

        if absolute_install_path is None:
            # Check if name is a core streaming/built-in service
            core_services = {'system'}
            if name.lower() in core_services:
                from pathlib import Path
                app_root = Path(__file__).parent.parent
                absolute_install_path = str((app_root / "core").resolve())

        try:
            execute_write_sql(
                str(self.database_path), 
                """
                INSERT INTO services(name, service_type, description, absolute_install_path, loaded_modules, plugin_id, version, is_active, beta_opt_in, verified_source, privileged_mode, permissions, capabilities)
                VALUES(?,?,?,?,?,?,?,1,COALESCE(?, 0),COALESCE(?, 0),COALESCE(?, 0),COALESCE(?, '[]'),COALESCE(?, '{}'))
                ON CONFLICT(plugin_id) DO UPDATE SET 
                    name=excluded.name,
                    absolute_install_path=excluded.absolute_install_path,
                    loaded_modules=excluded.loaded_modules,
                    version=excluded.version,
                    is_active=1,
                    beta_opt_in=COALESCE(excluded.beta_opt_in, services.beta_opt_in, 0),
                    verified_source=COALESCE(excluded.verified_source, services.verified_source, 0),
                    privileged_mode=COALESCE(excluded.privileged_mode, services.privileged_mode, 0),
                    permissions=COALESCE(excluded.permissions, services.permissions, '[]'),
                    capabilities=COALESCE(excluded.capabilities, services.capabilities, '{}'),
                    updated_at=strftime('%s','now')
                """, 
                (name, service_type, description, absolute_install_path, loaded_modules, plugin_id, version, beta_opt_in, verified_source, privileged_mode, permissions, capabilities)
            )
        except Exception as e:
            logger.error(f"Error registering service '{name}': {e}")
        
        return 0

    def set_service_config(self, service_id: int, key: str, value: Any, is_sensitive: bool = False) -> bool:
        try:
            from core.security import encrypt_string
            import json
            
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
        except Exception as e:
            logger.error(f"Error setting service config: {e}")
            return False

    def get_service_config(self, service_id: int, key: str) -> Optional[Any]:
        try:
            import contextlib
            import json
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT config_value, is_sensitive FROM service_config WHERE service_id=? AND config_key=?", (service_id, key))
                row = c.fetchone()

                if not row:
                    return None

                value, is_sensitive = row[0], row[1]
                if is_sensitive and value is not None:
                    from core.security import decrypt_string
                    value = decrypt_string(value)
                    
                if isinstance(value, str) and (value.startswith('[') or value.startswith('{')):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        pass
                        
                return value
        except Exception as e:
            logger.error(f"Error getting service config: {e}")
            return None

    def get_all_service_config(self, service_id: int) -> Dict[str, Any]:
        try:
            import contextlib
            import json
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT config_key, config_value, is_sensitive FROM service_config WHERE service_id=?", (service_id,))
                rows = c.fetchall()

                config = {}
                from core.security import decrypt_string
                for key, value, is_sensitive in rows:
                    if is_sensitive and value is not None:
                        try:
                            value = decrypt_string(value)
                        except Exception:
                            pass
                            
                    if isinstance(value, str) and (value.startswith('[') or value.startswith('{')):
                        try:
                            value = json.loads(value)
                        except json.JSONDecodeError:
                            pass
                            
                    config[key] = value

                return config
        except Exception as e:
            logger.error(f"Error reading all service config: {e}")
            return {}

    # Accounts
    def get_service_name(self, service_id: int) -> Optional[str]:
        """Resolve a service ID (PK or plugin_id) to its canonical name."""
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT name FROM services WHERE id=? OR plugin_id=?", (service_id, service_id))
            row = c.fetchone()
            if not row: return None
            return row['name']

    def get_service_id(self, identifier: Any) -> Optional[int]:
        """Resolve a name or plugin_id to the primary integer ID."""
        if identifier is None: return None
        with self._get_connection() as conn:
            c = conn.cursor()
            if isinstance(identifier, (int, str)) and str(identifier).isdigit():
                c.execute("SELECT id FROM services WHERE id=? OR plugin_id=?", (int(identifier), int(identifier)))
                row = c.fetchone()
                if row: return int(row[0])
            else:
                # 1. Check exact name
                c.execute("SELECT id FROM services WHERE name=?", (identifier,))
                row = c.fetchone()
                if row: return int(row[0])
                
                # 2. Check by CRC32 of the identifier (e.g. EchoSync.spotify)
                import binascii
                crc = binascii.crc32(str(identifier).lower().encode('utf-8')) & 0xFFFFFFFF
                c.execute("SELECT id FROM services WHERE plugin_id=? OR name=?", (crc, identifier))
                row = c.fetchone()
                if row: return int(row[0])
                
                # 3. Suffix matching/normalized translation bridge
                norm_name = str(identifier).lower().replace(' ', '_').replace('-', '_')
                c.execute("SELECT id, name FROM services")
                for r in c.fetchall():
                    row_name = r['name'].lower().replace(' ', '_').replace('-', '_')
                    if row_name == norm_name or norm_name.endswith(f".{row_name}") or row_name.endswith(f".{norm_name}"):
                        return int(r['id'])
            return None

    def get_accounts(self, service_id: Optional[int] = None, is_active: Optional[bool] = None) -> List[Dict[str, Any]]:
        try:
            import contextlib
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
            # If explicit account_id is provided, check existence using a reader
            if account_id is not None:
                import contextlib
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
        account_name: Optional[str] = None,
        display_name: Optional[str] = None,
        user_id: Optional[str] = None,
        account_email: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_authenticated: Optional[bool] = None,
        account_id: Optional[int] = None,
    ) -> int:
        """Insert or update an account row using stable identity fields when available."""
        try:
            import contextlib

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

    def get_account_token(self, account_id: int) -> Optional[Dict[str, Any]]:
        try:
            import contextlib
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT t.access_token, t.refresh_token, t.token_type, t.expires_at, t.scope, s.name as provider
                    FROM account_tokens t
                    LEFT JOIN accounts a ON t.account_id = a.id
                    LEFT JOIN services s ON a.service_id = s.id
                    WHERE t.account_id = ?
                """, (account_id,))
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
                    'access_token': access_token, 
                    'refresh_token': refresh_token, 
                    'token_type': token_type, 
                    'expires_at': expires_at, 
                    'scope': scope,
                    'provider': provider or ''
                }
        except Exception as e:
            logger.error(f"Error getting account token: {e}")
            return None

    # Removed account_metadata methods

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
            with self._get_connection() as conn:
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
        account_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve account mapping rows, optionally filtered by a specific account ID."""
        try:
            import contextlib
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
                        'id': r[0],
                        'source_account_id': r[1],
                        'mapped_account_id': r[2],
                        'created_at': r[3],
                        'updated_at': r[4],
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

    def get_plugin_snapshot(self, plugin_id: int) -> Optional[Dict[str, Any]]:
        try:
            import contextlib
            import json
            with self._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT snapshot_data, expires_at FROM plugin_snapshots WHERE plugin_id = ?", (plugin_id,))
                row = c.fetchone()
                if not row:
                    return None
                
                # Check expiry
                if row[1] < int(time.time()):
                    self.delete_plugin_snapshot(plugin_id)
                    return None

                return {
                    'snapshot_data': json.loads(row[0]),
                    'expires_at': row[1]
                }
        except Exception as e:
            logger.error(f"Error getting plugin snapshot for {plugin_id}: {e}")
            return None

    def delete_plugin_snapshot(self, plugin_id: int) -> bool:
        try:
            execute_write_sql(str(self.database_path), "DELETE FROM plugin_snapshots WHERE plugin_id = ?", (plugin_id,))
            return True
        except Exception as e:
            logger.error(f"Error deleting plugin snapshot for {plugin_id}: {e}")
            return False

    def cleanup_expired_snapshots(self) -> None:
        try:
            execute_write_sql(str(self.database_path), "DELETE FROM plugin_snapshots WHERE expires_at < ?", (int(time.time()),))
        except Exception as e:
            logger.error(f"Error cleaning expired plugin snapshots: {e}")


import threading
_config_db: Optional[ConfigDatabase] = None
_config_db_lock = threading.Lock()

def get_config_database() -> ConfigDatabase:
    global _config_db
    if _config_db is None:
        with _config_db_lock:
            if _config_db is None:
                _config_db = ConfigDatabase()
    return _config_db

def close_config_database() -> None:
    global _config_db
    if _config_db is not None:
        # No explicit dispose on sqlite3 Connection, but we can set to None
        _config_db = None

from sqlalchemy import Column, String, Boolean, Integer
from sqlalchemy.orm import declarative_base

ConfigBase = declarative_base()

class ConfigKVS(ConfigBase):
    __tablename__ = "config_kvs"
    plugin_id = Column(Integer, primary_key=True)
    key = Column(String, primary_key=True)
    value = Column(String, nullable=True)
    is_sensitive = Column(Boolean, default=False, nullable=False)
