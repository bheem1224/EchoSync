import json
import os
import sqlite3
from typing import Dict, Any, Optional, Callable
from cryptography.fernet import Fernet
from pathlib import Path
import copy

# Defines which keys in the config dict should be encrypted.
SECRETS = [
    "spotify.client_id",
    "spotify.client_secret",
    "tidal.client_id",
    "tidal.client_secret",
    "plex.token",
    "jellyfin.api_key",
    "navidrome.password",
    "soulseek.api_key",
    "listenbrainz.token",
]

class ConfigManager:
    def __init__(self, config_path: str = "config/config.json"):
        config_dir_env = os.environ.get('SOULSYNC_CONFIG_DIR')
        if config_dir_env:
            # Docker-friendly setup: use a dedicated /config directory
            self.config_dir = Path(config_dir_env)
        else:
            # Default setup: paths relative to the application structure
            self.config_dir = Path(__file__).parent

        # Ensure directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Paths for key and database
        self.key_path = self.config_dir / ".encryption_key"
        self.config_path = self.config_dir / 'config.json' # For migration
        self.database_path = self.config_dir / 'config.db'  # Encrypted config database
        
        print(f"[INFO] Config directory: {self.config_dir}")
        print(f"[INFO] Key file path: {self.key_path}")
        print(f"[INFO] Database path: {self.database_path}")
        
        self.config_data: Dict[str, Any] = {}
        self.cipher: Optional[Fernet] = None
        self._initialize_encryption()
        self._load_config()

    def _initialize_encryption(self):
        """Initialize Fernet cipher from MASTER_KEY or local key file."""
        key = os.getenv("MASTER_KEY")
        if key:
            print("[INFO] Using MASTER_KEY from environment variable.")
            try:
                self.cipher = Fernet(key.encode())
                return
            except Exception as e:
                print(f"[ERROR] Invalid MASTER_KEY: {e}")
                raise

        if self.key_path.exists():
            try:
                with open(self.key_path, 'rb') as f:
                    key = f.read()
                print(f"[INFO] Using encryption key from {self.key_path}.")
                self.cipher = Fernet(key)
                return
            except Exception as e:
                print(f"[ERROR] Failed to load encryption key: {e}")
                raise
        
        # Generate new key only if none exists
        print(f"[WARN] No encryption key found. Generating new key at {self.key_path}.")
        key = Fernet.generate_key()
        try:
            self.key_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.key_path, 'wb') as f:
                f.write(key)
            self.key_path.chmod(0o600)
            print(f"[OK] New key generated and saved to {self.key_path}")
            print(f"[IMPORTANT] For Docker deployments, export this key as MASTER_KEY environment variable:")
            print(f"[IMPORTANT] MASTER_KEY={key.decode()}")
        except Exception as e:
            print(f"[ERROR] Failed to save encryption key: {e}")
            raise
        
        self.cipher = Fernet(key)

    def _encrypt_value(self, value: Any) -> Any:
        """Encrypts a single value if it's a non-empty string."""
        # If it's already encrypted, don't encrypt again
        if isinstance(value, str) and value.startswith("enc:"):
            return value
        if isinstance(value, str) and value and self.cipher:
            return "enc:" + self.cipher.encrypt(value.encode()).decode()
        return value

    def _decrypt_value(self, value: Any) -> Any:
        """Decrypts a single value if it's an encrypted string."""
        if isinstance(value, str) and value.startswith("enc:") and self.cipher:
            try:
                encrypted_val = value[4:]
                decrypted = self.cipher.decrypt(encrypted_val.encode()).decode()
                print(f"[DEBUG] Decrypted value: {encrypted_val[:20]}... → {decrypted[:20] if len(decrypted) > 20 else decrypted}")
                return decrypted
            except Exception as e:
                print(f"[ERROR] Decryption failed for value '{value[:20]}...': {e}")
                print(f"[ERROR] This usually means the encryption key has changed.")
                print(f"[ERROR] Make sure MASTER_KEY environment variable or /config/.encryption_key is consistent.")
                print(f"[DEBUG] Cipher initialized: {self.cipher is not None}")
                return ""  # Return empty string on decryption failure
        elif isinstance(value, str) and value.startswith("enc:"):
            print(f"[WARN] Found encrypted value but cipher is not initialized: {value[:20]}...")
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
            elif current_path in keys_to_transform:
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
            print(f"Warning: Could not ensure database exists: {e}")

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
                print(f"[INFO] Encrypted config loaded from database")
                print(f"[DEBUG] Cipher available: {self.cipher is not None}")
                
                # Decrypt the data
                decrypted_data = self._traverse_and_transform(config_data, self._decrypt_value, SECRETS)
                
                # Verify decryption worked
                has_encrypted = self._has_undecrypted_secrets(decrypted_data)
                if has_encrypted:
                    print(f"[WARNING] Data still contains encrypted values after decryption attempt")
                else:
                    print(f"[OK] Successfully decrypted all secrets")
                
                return decrypted_data
            else:
                print("[INFO] No config found in database")
                return None
        except Exception as e:
            print(f"[WARNING] Could not load config from database: {e}")
            import traceback
            traceback.print_exc()
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
            print(f"[OK] Configuration saved to {self.database_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Could not save config to database: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _load_from_config_file(self) -> Optional[Dict[str, Any]]:
        """Load configuration from config.json file (for migration)."""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                    print(f"[OK] Configuration loaded from {self.config_path}")
                    return config_data
            else:
                return None
        except Exception as e:
            print(f"Warning: Could not load config from file: {e}")
            return None

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "active_media_server": "plex",
            "spotify": {"client_id": "", "client_secret": "", "redirect_uri": "http://127.0.0.1:8888/callback"},
            "tidal": {"client_id": "", "client_secret": "", "redirect_uri": "http://127.0.0.1:8889/tidal/callback"},
            "plex": {"base_url": "", "token": "", "auto_detect": True},
            "jellyfin": {"base_url": "", "api_key": "", "auto_detect": True},
            "navidrome": {"base_url": "", "username": "", "password": "", "auto_detect": True},
            "soulseek": {"slskd_url": "", "api_key": "", "download_path": "./downloads", "transfer_path": "./Transfer"},
            "listenbrainz": {"token": ""},
            "logging": {"path": "logs/app.log", "level": "INFO"},
            "database": {"path": "database/music_library.db", "max_workers": 5},
            "metadata_enhancement": {"enabled": True, "embed_album_art": True},
            "playlist_sync": {"create_backup": True},
            "settings": {"audio_quality": "flac"}
        }

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
        1. Database (primary storage)
        2. config.json (migration from file-based config)
        3. Defaults (fresh install)
        """
        config_data = self._load_from_database()
        if config_data:
            # Trust database as primary source; `_load_from_database` performs
            # its own decryption and integrity checks.
            self.config_data = config_data
            return

        config_data = self._load_from_config_file()
        if config_data:
            print("[MIGRATE] Migrating configuration from config.json to database...")
            if self._save_to_database(config_data):
                print("[OK] Configuration migrated successfully")
                self.config_data = self._traverse_and_transform(config_data, self._decrypt_value, SECRETS) # Ensure in-memory is decrypted
            else:
                print("[WARN] Migration failed - using file-based config")
                self.config_data = config_data
            return

        print("[INFO] No existing configuration found - using defaults")
        config_data = self._get_default_config()
        if self._save_to_database(config_data):
            print("[OK] Default configuration saved to database")
        else:
            print("[WARN] Could not save defaults to database - using in-memory config")
        self.config_data = config_data

    def _save_config(self):
        """Save configuration to database with a fallback to the config file."""
        if not self._save_to_database(self.config_data):
            print("[WARN] Database save failed - attempting file fallback")
            try:
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                encrypted_data = self._traverse_and_transform(copy.deepcopy(self.config_data), self._encrypt_value, SECRETS)
                with open(self.config_path, 'w') as f:
                    json.dump(encrypted_data, f, indent=2)
                print("[OK] Configuration saved to config.json as fallback")
            except Exception as e:
                print(f"[ERROR] Failed to save configuration: {e}")

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
        keys = key.split('.')
        config_level = self.config_data
        for k in keys[:-1]:
            config_level = config_level.setdefault(k, {})
        
        config_level[keys[-1]] = value
        # Persist by calling `_save_to_database` with a pre-encrypted payload.
        # `_encrypt_value` is idempotent (skips values already prefixed with `enc:`),
        # so the database layer will not double-encrypt.
        try:
            encrypted_payload = self._traverse_and_transform(copy.deepcopy(self.config_data), self._encrypt_value, SECRETS)
            self._save_to_database(encrypted_payload)
        except Exception:
            # Fallback to normal save flow if encryption or direct save fails
            self._save_config()

    # ... (rest of the getter methods remain the same) ...
    def get_spotify_config(self) -> Dict[str, str]:
        return self.get('spotify', {})

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

    def is_configured(self) -> bool:
        spotify = self.get_spotify_config()
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
            bool(spotify.get('client_id')) and
            bool(spotify.get('client_secret')) and
            media_server_configured and
            bool(soulseek.get('slskd_url'))
        )

    def validate_config(self) -> Dict[str, bool]:
        active_server = self.get_active_media_server()

        validation = {
            'spotify': bool(self.get('spotify.client_id')) and bool(self.get('spotify.client_secret')),
            'soulseek': bool(self.get('soulseek.slskd_url'))
        }

        # Validate all server types but mark active one
        validation['plex'] = bool(self.get('plex.base_url')) and bool(self.get('plex.token'))
        validation['jellyfin'] = bool(self.get('jellyfin.base_url')) and bool(self.get('jellyfin.api_key'))
        validation['navidrome'] = bool(self.get('navidrome.base_url')) and bool(self.get('navidrome.username')) and bool(self.get('navidrome.password'))
        validation['active_media_server'] = active_server

        return validation

config_manager = ConfigManager()
