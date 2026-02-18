import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Ensure environment variables from project .env are loaded before ConfigManager initializes
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=True)
import sqlite3
from typing import Dict, Any, Optional, Callable
from cryptography.fernet import Fernet
from pathlib import Path
import copy
from database import get_database
from core.tiered_logger import get_logger

logger = get_logger("config_manager")

# Defines which keys in the config dict should be encrypted.
SECRETS = [
    # Single-account legacy keys
    "spotify.client_id",
    "spotify.client_secret",
    # Multi-account Spotify secrets (wildcards supported)
    "spotify.accounts.*.client_id",
    "spotify.accounts.*.client_secret",
    "spotify.accounts.*.refresh_token",
    "spotify.accounts.*.access_token",
    # Tidal single-account legacy keys
    "tidal.client_id",
    "tidal.client_secret",
    # Multi-account Tidal secrets (wildcards supported)
    "tidal.accounts.*.client_id",
    "tidal.accounts.*.client_secret",
    "tidal.accounts.*.refresh_token",
    "tidal.accounts.*.access_token",
    # Other service secrets
    "plex.token",
    "jellyfin.api_key",
    "navidrome.password",
    "soulseek.api_key",
    "listenbrainz.token",
]


class ConfigManager:
    def set_service_credentials(self, service_name: str, credentials: dict, sensitive_keys=None, register_if_missing=True) -> bool:
        """
        Centralized helper to store service credentials/configs in the database.
        - service_name: e.g. 'spotify', 'tidal'
        - credentials: dict of key/values to store (e.g. client_id, client_secret, redirect_uri)
        - sensitive_keys: list of keys to mark as sensitive (default: ['client_secret', 'access_token', 'refresh_token'])
        - register_if_missing: auto-register service if not present
        Returns True if all writes succeed, False otherwise.
        """
        from database.config_database import get_config_database
        db = get_config_database()
        sensitive_keys = sensitive_keys or ['client_secret', 'access_token', 'refresh_token']
        try:
            # Use public methods of ConfigDatabase to ensure correct DB context
            service_id = db.get_or_create_service_id(service_name)
            if not service_id:
                logger.error(f"Could not find or register service: {service_name}")
                return False

            all_ok = True
            for k, v in credentials.items():
                is_sensitive = k in sensitive_keys
                ok = db.set_service_config(service_id, k, v, is_sensitive=is_sensitive)
                if not ok:
                    logger.error(f"Failed to set {k} for {service_name}")
                    all_ok = False
            return all_ok
        except Exception as e:
            logger.error(f"set_service_credentials failed: {e}")
            return False

    def __init__(self, config_path: str = "config/config.json"):
        # STEP 1: Set config_dir from ENV (NOT from config.json)
        # config_dir is special: it's set only by ENV variables (for encryption key security)
        config_dir_env = os.environ.get('SOULSYNC_CONFIG_DIR')
        if config_dir_env:
            self.config_dir = Path(config_dir_env)
        elif Path('/config').exists() and os.path.isdir('/config'):
            # Running in container with a mounted /config (Unix/Docker)
            self.config_dir = Path('/config')
        else:
            # Default setup: paths relative to the application structure (dev)
            self.config_dir = Path(__file__).parent.parent / 'config'

        # STEP 2: Set data_dir from ENV (takes precedence over config.json)
        data_dir_env = os.environ.get('SOULSYNC_DATA_DIR')
        if data_dir_env:
            self.data_dir = Path(data_dir_env)
        elif Path('/data').exists() and os.path.isdir('/data'):
            # Running in container with a mounted /data (Unix/Docker)
            self.data_dir = Path('/data')
        else:
            # Fallback to a data directory next to the project for local dev
            self.data_dir = Path(__file__).parent.parent / 'data'
        
        # Log config and data directories at INFO level
        logger.info(f"Config directory: {self.config_dir}")
        logger.info(f"Data directory: {self.data_dir}")
        
        # At DEBUG level, also log the source (ENV vs default)
        if config_dir_env:
            logger.debug(f"Config directory from SOULSYNC_CONFIG_DIR")
        else:
            logger.debug(f"Config directory from fallback default")
        
        if data_dir_env:
            logger.debug(f"Data directory from SOULSYNC_DATA_DIR")
        else:
            logger.debug(f"Data directory from fallback default")

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Paths for encrypted config database (in config_dir)
        # Encryption key is stored in .env file via MASTER_KEY variable only (no file backup)
        self.config_path = self.config_dir / 'config.json'  # For migration and non-secret JSON
        self.database_path = self.config_dir / 'config.db'  # Encrypted config database (secrets)
        
        # Media library DB goes in data_dir (user-visible, non-secret)
        self.media_db_path = self.data_dir / 'music_library.db'
        
        # Plugins directory goes in data_dir
        self.plugins_path = self.data_dir / 'plugins'

        # STEP 3: Set individual storage paths from ENV (take precedence over data_dir and config.json)
        download_dir_env = os.environ.get('SOULSYNC_DOWNLOAD_DIR')
        library_dir_env = os.environ.get('SOULSYNC_LIBRARY_DIR')
        log_dir_env = os.environ.get('SOULSYNC_LOG_DIR')
        
        # Initialize with data_dir defaults
        self.downloads_path = self.data_dir / 'downloads'
        self.library_path = self.data_dir / 'library'  # Default to 'library'
        self.logs_path = self.data_dir / 'logs'
        
        # Override with ENV variables if set
        if download_dir_env:
            self.downloads_path = Path(download_dir_env)
            logger.info(f"Downloads directory: {self.downloads_path}")
        else:
            logger.debug(f"Downloads directory (default): {self.downloads_path}")
        
        if library_dir_env:
            self.library_path = Path(library_dir_env)
            logger.info(f"Library directory: {self.library_path}")
        else:
            logger.debug(f"Library directory (default): {self.library_path}")
        
        if log_dir_env:
            self.logs_path = Path(log_dir_env)
            logger.info(f"Logs directory: {self.logs_path}")
        else:
            logger.debug(f"Logs directory (default): {self.logs_path}")
        
        logger.debug(f"Config database: {self.database_path}")
        logger.debug(f"Media DB: {self.media_db_path}")
        logger.debug(f"Plugins directory: {self.plugins_path}")
        
        self.config_data: Dict[str, Any] = {}
        self.cipher: Optional[Fernet] = None
        self._initialize_encryption()
        self._load_config()
        
        # Ensure data directories exist for logs/downloads/library/plugins
        try:
            self.downloads_path.mkdir(parents=True, exist_ok=True)
            self.library_path.mkdir(parents=True, exist_ok=True)
            self.logs_path.mkdir(parents=True, exist_ok=True)
            self.plugins_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create data directories: {e}")

    def _initialize_encryption(self):
        """Initialize Fernet cipher from MASTER_KEY environment variable.
        
        The encryption key is stored in .env file and loaded as MASTER_KEY environment variable.
        If no key exists, a new one is generated and automatically written to .env file.
        There is no backup file - only the ENV variable and .env persistence.
        """
        # First, try to get key from environment variable
        key = os.getenv("MASTER_KEY")
        
        if key:
            # Key is set in environment (either from .env or explicit)
            logger.debug("Using MASTER_KEY from environment variable")
            try:
                self.cipher = Fernet(key.encode())
                return
            except Exception as e:
                logger.error(f"Invalid MASTER_KEY in environment: {e}")
                raise
        
        # No key in environment - generate new one and persist to .env
        logger.debug("No MASTER_KEY found. Generating new encryption key...")
        new_key = Fernet.generate_key().decode('utf-8')
        
        # Save to .env file for persistence
        self._persist_key_to_env(new_key)
        
        # Set in current environment so initialization completes
        os.environ['MASTER_KEY'] = new_key
        logger.debug(f"New encryption key generated and will persist to .env")
        
        self.cipher = Fernet(new_key.encode())
    
    def _persist_key_to_env(self, key: str):
        """Write the encryption key to .env file for persistence."""
        env_path = Path(__file__).parent.parent / '.env'
        
        try:
            env_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Read existing .env file
            existing_content = ""
            if env_path.exists():
                try:
                    with open(env_path, 'r') as f:
                        existing_content = f.read()
                except PermissionError:
                    logger.debug("Cannot read .env file (permission denied). Attempting to write anyway...")
            
            # Remove old MASTER_KEY line if it exists
            lines = existing_content.split('\n') if existing_content else []
            lines = [line for line in lines if not line.strip().startswith('MASTER_KEY=')]
            
            # Add new MASTER_KEY at the top
            lines.insert(0, f"MASTER_KEY={key}")
            
            # Write back to .env with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    with open(env_path, 'w') as f:
                        f.write('\n'.join(lines))
                    logger.debug(f"Encryption key persisted to .env")
                    return
                except PermissionError:
                    if attempt < max_retries - 1:
                        import time
                        logger.debug(f"Retrying .env write (attempt {attempt + 1}/{max_retries})...")
                        time.sleep(1)
                    else:
                        raise
        except Exception as e:
            logger.warning(f"Could not persist encryption key to .env: {e}")
            logger.warning(f"The key will be lost on next startup unless manually set!")
            logger.warning(f"Manually add this line to your .env file: MASTER_KEY={key}")

    def _path_matches_any(self, key_path: str, patterns: list) -> bool:
        """Return True if key_path matches any of the patterns (supports '*' wildcards)."""
        try:
            import fnmatch
            return any(fnmatch.fnmatchcase(key_path, pattern) for pattern in patterns)
        except Exception:
            # Fallback to exact match if fnmatch isn't available
            return key_path in patterns

    def _is_secret_path(self, key_path: str) -> bool:
        """Check if a config key path should be treated as secret (supports wildcards)."""
        return self._path_matches_any(key_path, SECRETS)

    def _encrypt_value(self, value: Any) -> Any:
        """Encrypts a single value if it's a non-empty string."""
        # If it's already encrypted, don't encrypt again
        if isinstance(value, str) and value.startswith("enc:"):
            return value
        if isinstance(value, str) and value and self.cipher:
            return "enc:" + self.cipher.encrypt(value.encode()).decode()
        return value

    def _decrypt_value(self, value: Any) -> Any:
        """Decrypts a single value if it's an encrypted string.
        
        SECURITY: Never logs the decrypted value itself, only success/failure.
        """
        if isinstance(value, str) and value.startswith("enc:") and self.cipher:
            try:
                encrypted_val = value[4:]
                decrypted = self.cipher.decrypt(encrypted_val.encode()).decode()
                return decrypted
            except Exception as e:
                logger.warning(f"Decryption failed: The encryption key may have changed")
                return ""  # Return empty string on decryption failure
        elif isinstance(value, str) and value.startswith("enc:"):
            logger.warning(f"Found encrypted value but cipher is not initialized")
            return value
        return value

    def _traverse_and_transform(self, data: Dict[str, Any], transform: Callable, keys_to_transform: list, path: str = "") -> Dict[str, Any]:
        """Recursively traverses a dict and applies a transformation to specified keys."""
        output = {}
        for key, value in data.items():
            # Build the full path to this key (e.g., "spotify.client_id")
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, dict):
                # Recursively process nested dicts
                output[key] = self._traverse_and_transform(value, transform, keys_to_transform, current_path)
            elif self._path_matches_any(current_path, keys_to_transform):
                # Transform this value because its path matches a secret key
                output[key] = transform(value)
            else:
                output[key] = value
        return output
    
    def _ensure_database_exists(self):
        """Ensure database file and metadata table exist"""
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.database_path))
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"Could not ensure database exists: {e}")

    def _load_from_database(self) -> Optional[Dict[str, Any]]:
        """Load configuration from database and decrypt secrets."""
        try:
            self._ensure_database_exists()
            conn = sqlite3.connect(str(self.database_path))
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM metadata WHERE key = 'app_config'")
            row = cursor.fetchone()
            conn.close()

            if row and row[0]:
                config_data = json.loads(row[0])
                logger.debug(f"Encrypted config loaded from database")
                
                # Decrypt the data
                decrypted_data = self._traverse_and_transform(config_data, self._decrypt_value, SECRETS)
                
                # Verify decryption worked
                has_encrypted = self._has_undecrypted_secrets(decrypted_data)
                if has_encrypted:
                    logger.warning(f"Data still contains encrypted values after decryption attempt")
                else:
                    logger.debug(f"All secrets decrypted successfully")
                
                return decrypted_data
            else:
                logger.debug("No config found in database")
                return None
        except Exception as e:
            logger.debug(f"Could not load config from database: {e}")
            return None

    def _save_to_database(self, config_data: Dict[str, Any]) -> bool:
        """Encrypt secrets and save configuration to database."""
        try:
            self._ensure_database_exists()
            
            encrypted_data = self._traverse_and_transform(copy.deepcopy(config_data), self._encrypt_value, SECRETS)

            conn = sqlite3.connect(str(self.database_path))
            cursor = conn.cursor()

            config_json = json.dumps(encrypted_data, indent=2)
            cursor.execute("""
                INSERT OR REPLACE INTO metadata (key, value, updated_at)
                VALUES ('app_config', ?, CURRENT_TIMESTAMP)
            """, (config_json,))

            conn.commit()
            conn.close()
            logger.debug(f"Configuration saved to database")
            return True
        except Exception as e:
            logger.error(f"Could not save config to database: {e}")
            return False

    def _load_from_config_file(self) -> Optional[Dict[str, Any]]:
        """Load configuration from config.json file (for migration)."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                    logger.debug(f"Configuration loaded from {self.config_path}")
                    return config_data
            else:
                return None
        except Exception as e:
            logger.debug(f"Could not load config from file: {e}")
            return None

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        # Use container-friendly defaults when available, fall back to project-relative paths
        cfg = {
            "active_media_server": "plex",
            "spotify": {"client_id": "", "client_secret": "", "redirect_uri": "http://127.0.0.1:8008/api/spotify/callback"},
            # Multi-account Spotify support
            "spotify_accounts": [],
            "active_spotify_account_id": None,
            "tidal": {"client_id": "", "client_secret": "", "redirect_uri": "http://127.0.0.1:8889/tidal/callback"},
            # Multi-account Tidal support
            "tidal_accounts": [],
            "active_tidal_account_id": None,
            "plex": {"base_url": "", "token": "", "auto_detect": True, "path_mappings": []},
            "jellyfin": {"base_url": "", "api_key": "", "auto_detect": True},
            "navidrome": {"base_url": "", "username": "", "password": "", "auto_detect": True},
            "soulseek": {"slskd_url": "", "api_key": ""},
            "active_download_client": None,
            "listenbrainz": {"token": ""},
            "logging": {"path": str(self.logs_path / 'app.log'), "level": "INFO"},
            "database": {"path": str(self.media_db_path), "max_workers": 2},
            "metadata_enhancement": {
                "enabled": True,
                "embed_album_art": True,
                "auto_import": False,
                "naming_template": "{Artist}/{Album}/{Track} - {Title}.{ext}",
                "conflict_resolution": "replace",
                "confidence_threshold": 90,
                "overwrite_tags": True
            },
            "playlist_sync": {"create_backup": True},
            "file_organization": {
                "enabled": True,
                "templates": {
                    "album_path": "$albumartist/$albumartist - $album/$track - $title",
                    "single_path": "$artist/$artist - $title/$title",
                    "playlist_path": "$playlist/$artist - $title"
                }
            },
            "download": {
                "concurrency": 2,
                "retry_count": 3,
                "min_free_space_mb": 500
            },
            "discovery_pool": {
                "lookback_period_days": 90,
                "max_tracks": 5000,
                "new_releases_only": False
            },
            "quality_profile": {
                "preset": "balanced",
                "allowed_file_types": ["flac", "mp3_320", "mp3_256"],
                "min_file_size_mb": 0,
                "max_file_size_mb": 150,
                "min_bit_depth": 16,
                "min_bitrate_kbps": 256,
                "min_length_seconds": 0
            },
            "settings": {"audio_quality": "flac"},
            # Storage paths - Docker-first approach
            # Users can map /config and /data, or override individual paths
            "storage": {
                "data_dir": str(self.data_dir),
                "config_dir": str(self.config_dir),
                "download_dir": str(self.downloads_path),
                "library_dir": str(self.library_path),
                "log_dir": str(self.logs_path),
                "plugins_dir": str(self.plugins_path)
            },
            # Provider/Plugin management
            "disabled_providers": []  # List of provider/plugin names to disable (e.g., ["spotify", "tidal"])
        }
        return cfg

    def _has_undecrypted_secrets(self, config_data: Dict[str, Any]) -> bool:
        """Check if config has encrypted values that weren't decrypted (bad cipher)."""
        def check_for_encrypted(obj):
            if isinstance(obj, dict):
                for v in obj.values():
                    if check_for_encrypted(v):
                        return True
            elif isinstance(obj, str) and obj.startswith("enc:"):
                return True
            return False
        return check_for_encrypted(config_data)

    def _load_config(self):
        """
        Load configuration with priority:
        1. config.json (non-secrets, user-editable)
        2. config.db (secrets only, encrypted)
        3. Defaults (fresh install)
        """
        # Start with defaults as base
        config_data = self._get_default_config()
        
        # Load non-secrets from config.json
        json_data = self._load_from_config_file()
        if json_data:
            logger.debug("Loaded non-secrets from config.json")
            config_data = self._deep_merge(config_data, json_data)
        
        # Load secrets from database (encrypted)
        db_data = self._load_from_database()
        if db_data:
            logger.debug("Loaded secrets from database")
            config_data = self._deep_merge(config_data, db_data)
            # Verify decryption worked
            if self._has_undecrypted_secrets(config_data):
                logger.warning("Some encrypted values still encrypted after load - key mismatch?")
        
        self.config_data = config_data
        
        # Apply storage paths from config if they exist (overrides initial paths)
        self._apply_storage_paths_from_config()
        
        # If we have no JSON file yet, save current config to JSON for future edits
        if not json_data:
            self._save_non_secrets_to_json()
        # Normalize certain config entries (e.g., database workers)
        self._normalize_database_workers()

    def _apply_storage_paths_from_config(self):
        """Apply storage paths from loaded config to override initial defaults.
        
        Priority: 
        1. If data_dir is set, update self.data_dir and derive paths from it
        2. If individual paths (download_dir, library_dir, log_dir) are set, use those
        3. Otherwise use the initial defaults
        
        This allows Docker-first approach: map /config and /data, or override individually.
        """
        try:
            storage_config = self.config_data.get('storage', {})
            
            # First, check if data_dir is specified and update if so
            if storage_config.get('data_dir'):
                self.data_dir = Path(storage_config['data_dir'])
                logger.debug(f"Applied data_dir from config.json: {self.data_dir}")
                # Update derived defaults based on new data_dir
                # Only update if the individual paths weren't explicitly set
                if not storage_config.get('download_dir'):
                    self.downloads_path = self.data_dir / 'downloads'
                if not storage_config.get('library_dir'):
                    self.library_path = self.data_dir / 'library'
                if not storage_config.get('log_dir'):
                    self.logs_path = self.data_dir / 'logs'
                if not storage_config.get('plugins_dir'):
                    self.plugins_path = self.data_dir / 'plugins'
                # Also update media_db_path to be under new data_dir
                self.media_db_path = self.data_dir / 'music_library.db'
            
            # Then apply any explicit path overrides
            if storage_config.get('download_dir'):
                self.downloads_path = Path(storage_config['download_dir'])
                logger.debug(f"Applied download_dir from config: {self.downloads_path}")
            
            if storage_config.get('library_dir'):
                self.library_path = Path(storage_config['library_dir'])
                logger.debug(f"Applied library_dir from config: {self.library_path}")
            
            if storage_config.get('log_dir'):
                self.logs_path = Path(storage_config['log_dir'])
                logger.debug(f"Applied log_dir from config: {self.logs_path}")

            if storage_config.get('plugins_dir'):
                self.plugins_path = Path(storage_config['plugins_dir'])
                logger.debug(f"Applied plugins_dir from config: {self.plugins_path}")
            
            if storage_config.get('config_dir'):
                new_config_dir = Path(storage_config['config_dir'])
                # Only log the difference, don't change config_dir itself to avoid breaking encryption
                if new_config_dir != self.config_dir:
                    logger.debug(f"Config specifies different config_dir: {new_config_dir}")
                    logger.debug("config_dir cannot be changed after initialization (encryption key location)")
            
            # Apply logging path from config if specified
            logging_config = self.config_data.get('logging', {})
            if logging_config.get('path'):
                log_path = Path(logging_config['path'])
                # If it's a relative path, make it relative to logs_path
                if not log_path.is_absolute():
                    log_path = self.logs_path / log_path.name
                    self.config_data['logging']['path'] = str(log_path.resolve())
                    logger.debug(f"Updated logging path to: {log_path}")
            
            # Update database path in config to match media_db_path
            db_config = self.config_data.get('database', {})
            db_config['path'] = str(self.media_db_path.resolve())
            
            # Create directories if they don't exist
            self.downloads_path.mkdir(parents=True, exist_ok=True)
            self.library_path.mkdir(parents=True, exist_ok=True)
            self.logs_path.mkdir(parents=True, exist_ok=True)
            self.media_db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Update config with resolved paths so they're saved to config.json
            # This makes config.json the source of truth
            self.config_data['storage']['data_dir'] = str(self.data_dir.resolve())
            self.config_data['storage']['config_dir'] = str(self.config_dir.resolve())
            self.config_data['storage']['download_dir'] = str(self.downloads_path.resolve())
            self.config_data['storage']['library_dir'] = str(self.library_path.resolve())
            self.config_data['storage']['log_dir'] = str(self.logs_path.resolve())
            self.config_data['storage']['plugins_dir'] = str(self.plugins_path.resolve())
            
        except Exception as e:
            print(f"[WARN] Could not apply storage paths from config: {e}")
    
    def _normalize_database_workers(self):
        """Ensure database.max_workers is sensible for the configured DB.

        Behavior:
         - If DB path looks like SQLite (.db or contains 'sqlite'), clamp to 1..4 and default to 2.
         - Otherwise clamp to 1..10 and default to 4.
        """
        try:
            db_cfg = self.config_data.get('database') or {}
            raw = db_cfg.get('max_workers')
            try:
                val = int(raw)
            except Exception:
                val = None

            db_path = (db_cfg.get('path') or '').lower()
            is_sqlite = db_path.endswith('.db') or 'sqlite' in db_path

            if is_sqlite:
                if val is None:
                    val = 2
                val = max(1, min(val, 4))
            else:
                if val is None:
                    val = 4
                val = max(1, min(val, 10))

            self.config_data.setdefault('database', {})['max_workers'] = val
        except Exception as e:
            print(f"[WARN] Could not normalize database.max_workers: {e}")
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge override dict into base dict."""
        result = copy.deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _save_non_secrets_to_json(self) -> bool:
        """Save only non-secret values to config.json for user editing."""
        try:
            # Extract only non-secrets from config_data
            non_secrets = self._extract_non_secrets(self.config_data)
            
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(non_secrets, f, indent=2)
            print(f"[OK] Non-secrets saved to {self.config_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save non-secrets to JSON: {e}")
            return False
    
    def _extract_non_secrets(self, data: Dict[str, Any], path: str = "") -> Dict[str, Any]:
        """Extract only non-secret values from config data."""
        result = {}
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, dict):
                # Recurse into nested dicts
                nested = self._extract_non_secrets(value, current_path)
                if nested:  # Only add non-empty nested dicts
                    result[key] = nested
            elif not self._is_secret_path(current_path):
                # Include non-secret values
                result[key] = value
        
        return result
    
    def _extract_secrets(self, data: Dict[str, Any], path: str = "") -> Dict[str, Any]:
        """Extract only secret values from config data."""
        result = {}
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, dict):
                # Recurse into nested dicts
                nested = self._extract_secrets(value, current_path)
                if nested:  # Only add non-empty nested dicts
                    result[key] = nested
            elif self._is_secret_path(current_path):
                # Include secret values
                result[key] = value
        
        return result

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value, decrypting if necessary."""
        keys = key.split('.')
        value = self.config_data
        
        # Traverse the dictionary
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        # Check if the retrieved value's path is in SECRETS
        if key in SECRETS:
             return self._decrypt_value(value)

        return value

    def set(self, key: str, value: Any):
        """Set a configuration value and persist it.
        
        Secrets are saved to encrypted config.db.
        Non-secrets are saved to plaintext config.json.
        """
        keys = key.split('.')
        config_level = self.config_data
        for k in keys[:-1]:
            config_level = config_level.setdefault(k, {})
        
        config_level[keys[-1]] = value
        
        # Determine where to persist this value
        if self._is_secret_path(key):
            # Save secrets to encrypted database
            secrets_only = self._extract_secrets(self.config_data)
            encrypted_secrets = self._traverse_and_transform(secrets_only, self._encrypt_value, SECRETS)
            self._save_to_database(encrypted_secrets)
        else:
            # Save non-secrets to plaintext JSON
            self._save_non_secrets_to_json()

    # ... (rest of the getter methods remain the same) ...
    def get_spotify_config(self) -> Dict[str, str]:
        return self.get('spotify', {})

    def get_spotify_accounts(self) -> list:
        """Return list of Spotify account dicts."""
        return self.get('spotify_accounts', []) or []

    def add_spotify_account(self, account: Dict[str, Any]) -> Dict[str, Any]:
        """Add a Spotify account entry. Auto-assign incremental id if missing."""
        accounts = self.get_spotify_accounts()
        # Determine next id
        existing_ids = [acc.get('id') for acc in accounts if acc.get('id') is not None]
        next_id = (max(existing_ids) + 1) if existing_ids else 1
        account = dict(account)
        if account.get('id') is None:
            account['id'] = next_id
        accounts.append(account)
        self.set('spotify_accounts', accounts)
        # If no active account, set this one
        if not self.get('active_spotify_account_id'):
            self.set('active_spotify_account_id', account['id'])
        return account

    def update_spotify_account(self, account_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update fields for a Spotify account by id."""
        accounts = self.get_spotify_accounts()
        updated = None
        for i, acc in enumerate(accounts):
            if acc.get('id') == account_id:
                acc = {**acc, **updates}
                accounts[i] = acc
                updated = acc
                break
        if updated:
            self.set('spotify_accounts', accounts)
        return updated

    def set_active_spotify_account(self, account_id: Optional[int]) -> None:
        """Set active Spotify account id (or None)."""
        self.set('active_spotify_account_id', account_id)

    def get_active_spotify_account(self) -> Optional[Dict[str, Any]]:
        """Return the active Spotify account dict, if set."""
        active_id = self.get('active_spotify_account_id')
        if not active_id:
            return None
        for acc in self.get_spotify_accounts():
            if acc.get('id') == active_id:
                return acc
        return None

    def get_spotify_active_credentials(self) -> Dict[str, Any]:
        """
        Return the credentials for the active Spotify account, falling back to global only for redirect_uri.
        In practice, client_id and client_secret are at the account level, and global tokens are not used.
        """
        spotify_config = self.get_spotify_config()
        redirect_uri = spotify_config.get('redirect_uri', "http://127.0.0.1:8008/api/spotify/callback")
        active = self.get_active_spotify_account()
        if active:
            return {
                'client_id': active.get('client_id', ''),
                'client_secret': active.get('client_secret', ''),
                'redirect_uri': redirect_uri,
                'refresh_token': active.get('refresh_token'),
                'access_token': active.get('access_token'),
                'user_id': active.get('user_id'),
                'id': active.get('id'),
                'name': active.get('name')
            }
        # No active account: return empty credentials except for redirect_uri
        return {
            'client_id': '',
            'client_secret': '',
            'redirect_uri': redirect_uri,
            'refresh_token': None,
            'access_token': None,
            'user_id': None,
            'id': None,
            'name': None
        }

    # --- Tidal multi-account helpers ---
    def get_tidal_accounts(self) -> list:
        return self.get('tidal_accounts', []) or []

    def add_tidal_account(self, account: Dict[str, Any]) -> Dict[str, Any]:
        accounts = self.get_tidal_accounts()
        existing_ids = [acc.get('id') for acc in accounts if acc.get('id') is not None]
        next_id = (max(existing_ids) + 1) if existing_ids else 1
        account = dict(account)
        if account.get('id') is None:
            account['id'] = next_id
        accounts.append(account)
        self.set('tidal_accounts', accounts)
        if not self.get('active_tidal_account_id'):
            self.set('active_tidal_account_id', account['id'])
        return account

    def update_tidal_account(self, account_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        accounts = self.get_tidal_accounts()
        updated = None
        for i, acc in enumerate(accounts):
            if acc.get('id') == account_id:
                acc = {**acc, **updates}
                accounts[i] = acc
                updated = acc
                break
        if updated:
            self.set('tidal_accounts', accounts)
        return updated

    def set_active_tidal_account(self, account_id: Optional[int]) -> None:
        self.set('active_tidal_account_id', account_id)

    def get_active_tidal_account(self) -> Optional[Dict[str, Any]]:
        active_id = self.get('active_tidal_account_id')
        if not active_id:
            return None
        for acc in self.get_tidal_accounts():
            if acc.get('id') == active_id:
                return acc
        return None

    def get_plex_config(self) -> Dict[str, str]:
        return self.get('plex', {})

    def get_jellyfin_config(self) -> Dict[str, str]:
        return self.get('jellyfin', {})

    def get_navidrome_config(self) -> Dict[str, str]:
        return self.get('navidrome', {})

    def get_soulseek_config(self) -> Dict[str, str]:
        return self.get('soulseek', {})

    def get_settings(self) -> Dict[str, Any]:
        return self.get('settings', {})

    def get_all(self) -> Dict[str, Any]:
        """Return the full non-secret configuration suitable for the UI.

        This exposes only non-secret values (the same subset saved to config.json).
        """
        try:
            # Return a deep copy of non-secret config to avoid accidental mutation
            non_secrets = self._extract_non_secrets(self.config_data)
            return copy.deepcopy(non_secrets)
        except Exception as e:
            print(f"[ERROR] get_all failed: {e}")
            return {}

    def get_quality_profiles(self) -> list:
        """Return the stored quality profiles list (no defaults merged)."""
        try:
            profiles = self.config_data.get('quality_profiles')
            return profiles if isinstance(profiles, list) else []
        except Exception as e:
            print(f"[ERROR] get_quality_profiles failed: {e}")
            return []

    def set_quality_profiles(self, profiles: list) -> bool:
        """Validate/normalize and persist quality profiles as top-level key.

        Returns True on success, False otherwise.
        """
        try:
            if not isinstance(profiles, list):
                raise ValueError('profiles must be a list')

            # Normalize each profile and formats
            def _norm_profile(p):
                np = dict(p)
                np['id'] = str(np.get('id', ''))
                np['name'] = str(np.get('name', ''))
                formats = np.get('formats') or np.get('types') or []
                norm_formats = []
                for f in formats:
                    nf = dict(f)
                    # numeric fields
                    try:
                        nf['min_size_mb'] = int(nf.get('min_size_mb') or 0)
                    except Exception:
                        nf['min_size_mb'] = 0
                    try:
                        nf['max_size_mb'] = int(nf.get('max_size_mb') or 0)
                    except Exception:
                        nf['max_size_mb'] = 0
                    try:
                        nf['priority'] = int(nf.get('priority') or 0)
                    except Exception:
                        nf['priority'] = 0

                    # ensure arrays
                    for arrk in ('bitrates', 'bit_depths', 'sample_rates'):
                        val = nf.get(arrk)
                        if val is None:
                            nf[arrk] = []
                        elif isinstance(val, list):
                            nf[arrk] = [str(x) for x in val]
                        else:
                            nf[arrk] = [str(val)]

                    nf['type'] = str(nf.get('type') or nf.get('format') or '')
                    norm_formats.append(nf)
                np['formats'] = norm_formats
                return np

            normalized = [_norm_profile(p) for p in profiles]

            # Set into in-memory config and persist non-secrets JSON
            self.config_data['quality_profiles'] = normalized
            self._save_non_secrets_to_json()
            return True
        except Exception as e:
            print(f"[ERROR] set_quality_profiles failed: {e}")
            import traceback; traceback.print_exc()
            return False

    def get_database_config(self) -> Dict[str, str]:
        return self.get('database', {})

    def get_logging_config(self) -> Dict[str, str]:
        return self.get('logging', {})

    def get_active_media_server(self) -> str:
        return self.get('active_media_server', 'plex')

    def set_active_media_server(self, server: str):
        """Set the active media server (plex, jellyfin, or navidrome)"""
        if server not in ['plex', 'jellyfin', 'navidrome']:
            raise ValueError(f"Invalid media server: {server}")
        self.set('active_media_server', server)

    def get_active_media_server_config(self) -> Dict[str, str]:
        """Get configuration for the currently active media server"""
        active_server = self.get_active_media_server()
        if active_server == 'plex':
            return self.get_plex_config()
        elif active_server == 'jellyfin':
            return self.get_jellyfin_config()
        elif active_server == 'navidrome':
            return self.get_navidrome_config()
        else:
            return {}

    def get_active_download_client(self) -> Optional[str]:
        """Get the currently active download client."""
        return self.get('active_download_client')

    def set_active_download_client(self, client_name: str):
        """Set the active download client."""
        self.set('active_download_client', client_name)

    def is_configured(self) -> bool:
        # Check Spotify credentials (global or active account overrides)
        spotify_creds = self.get_spotify_active_credentials()
        spotify_configured = bool(spotify_creds.get('client_id')) and bool(spotify_creds.get('client_secret')) and bool(spotify_creds.get('redirect_uri'))
        
    def get_disabled_providers(self) -> list:
        """Get list of disabled providers/plugins from config"""
        return self.get('disabled_providers', [])

    def set_disabled_providers(self, disabled_list: list) -> None:
        """Set list of disabled providers/plugins"""
        self.set('disabled_providers', disabled_list)

    def disable_provider(self, name: str) -> None:
        """Disable a provider/plugin by adding it to the disabled list"""
        disabled = self.get_disabled_providers()
        if name not in disabled:
            disabled.append(name)
            self.set_disabled_providers(disabled)

    def enable_provider(self, name: str) -> None:
        """Enable a provider/plugin by removing it from the disabled list"""
        disabled = self.get_disabled_providers()
        if name in disabled:
            disabled.remove(name)
            self.set_disabled_providers(disabled)

    def is_configured(self) -> bool:
        # Check Spotify credentials (global or active account overrides)
        spotify_creds = self.get_spotify_active_credentials()
        spotify_configured = bool(spotify_creds.get('client_id')) and bool(spotify_creds.get('client_secret')) and bool(spotify_creds.get('redirect_uri'))
        
        active_server = self.get_active_media_server()
        soulseek = self.get_soulseek_config()

        # Check active media server configuration
        media_server_configured = False
        if active_server == 'plex':
            plex = self.get_plex_config()
            media_server_configured = bool(plex.get('base_url')) and bool(plex.get('token'))
        elif active_server == 'jellyfin':
            jellyfin = self.get_jellyfin_config()
            media_server_configured = bool(jellyfin.get('base_url')) and bool(jellyfin.get('api_key'))
        elif active_server == 'navidrome':
            navidrome = self.get_navidrome_config()
            media_server_configured = bool(navidrome.get('base_url')) and bool(navidrome.get('username')) and bool(navidrome.get('password'))

        return (
            spotify_configured and
            media_server_configured and
            bool(soulseek.get('slskd_url'))
        )

    def validate_config(self) -> Dict[str, bool]:
        active_server = self.get_active_media_server()

        # Check global Spotify app credentials
        spotify_valid = bool(self.get('spotify.client_id')) and bool(self.get('spotify.client_secret'))

        validation = {
            'spotify': spotify_valid,
            'soulseek': bool(self.get('soulseek.slskd_url'))
        }

        # Validate all server types but mark active one
        validation['plex'] = bool(self.get('plex.base_url')) and bool(self.get('plex.token'))
        validation['jellyfin'] = bool(self.get('jellyfin.base_url')) and bool(self.get('jellyfin.api_key'))
        validation['navidrome'] = bool(self.get('navidrome.base_url')) and bool(self.get('navidrome.username')) and bool(self.get('navidrome.password'))
        # Set to True if the active media server is configured, False otherwise
        validation['active_media_server'] = bool(active_server)
        validation['active_download_client'] = bool(self.get('active_download_client'))

        return validation

    def get_service_credentials(self, service_name: str) -> Dict[str, Any]:
        """
        Retrieve credentials for a specific service from the config database.
        - service_name: Name of the service (e.g., 'plex', 'spotify').
        Returns a dictionary of credentials or an empty dictionary if not found.
        """
        try:
            from database.config_database import get_config_database
            config_db = get_config_database()
            
            # Get the service ID first
            service_id = config_db.get_or_create_service_id(service_name)
            
            if not service_id:
                return {}
            
            # Get all config values for this service
            result = {}
            with config_db._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT config_key, config_value FROM service_config WHERE service_id = ?", (service_id,))
                rows = c.fetchall()
                for row in rows:
                    result[row[0]] = row[1]
            
            return result
        except Exception as e:
            logger.error(f"Error retrieving credentials for {service_name}: {e}")
            return {}
    
    def get_storage_paths(self) -> Dict[str, Path]:
        """Get the actual storage paths being used by the application.
        
        Returns:
            Dict with keys: download_dir, library_dir, log_dir, config_dir, data_dir, media_db, plugins
            Values are Path objects representing the resolved absolute paths.
        """
        return {
            'download_dir': self.downloads_path,
            'library_dir': self.library_path,
            'log_dir': self.logs_path,
            'config_dir': self.config_dir,
            'data_dir': self.data_dir,
            'media_db': self.media_db_path,
            'plugins': self.plugins_path
        }
    
    def get_download_dir(self) -> Path:
        """Get the downloads directory path."""
        return self.downloads_path
    
    def get_library_dir(self) -> Path:
        """Get the library directory path (formerly transfer_dir)."""
        return self.library_path
    
    def get_log_dir(self) -> Path:
        """Get the logs directory path."""
        return self.logs_path
    
    def get_config_dir(self) -> Path:
        """Get the config directory path."""
        return self.config_dir
    
    def get_media_db_path(self) -> Path:
        """Get the media library database path."""
        return self.media_db_path
    
    def get_plugins_dir(self) -> Path:
        """Get the plugins directory path."""
        return self.plugins_path

config_manager = ConfigManager()

def get_setting(key: str, default: Any = None) -> Any:
    """Retrieve a specific setting by key."""
    try:
        config = config_manager.get_settings()
        return config.get(key, default)
    except Exception as e:
        print(f"[ERROR] Failed to retrieve setting '{key}': {e}")
        return default

def set_setting(key: str, value: Any) -> None:
    """
    Set a configuration setting.

    Args:
        key (str): The setting key.
        value (Any): The value to set.
    """
    # Placeholder implementation
    logger.info(f"Setting {key} to {value}")
    # Actual implementation should persist the setting to a database or file
    pass
