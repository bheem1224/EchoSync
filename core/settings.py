import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Ensure environment variables from project .env are loaded before ConfigManager initializes
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env", override=True)
import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

from core.tiered_logger import get_logger

logger = get_logger("config_manager")

# Defines which keys in the config dict should be encrypted.
SECRETS = [
    # Generic plugin-agnostic secret keys (supports wildcard matching)
    "*client_id",
    "*client_secret",
    "*refresh_token",
    "*access_token",
    "*token",
    "*api_key",
    "*password",
]

# Cold bootstrap keys that are permitted to live in config.json
COLD_BOOTSTRAP_KEYS: frozenset = frozenset(
    {
        "storage",
        "server",
        "logging",
        "database",
        "security",
        "auth",
        "custom_ui_path",
        "cors_origins",
        "dev_mode",
        "safe_mode",
    }
)


def sanitize_legacy_config_json(raw_json: dict) -> tuple[dict, dict]:
    """Separate a legacy config.json into cold bootstrap settings and hot runtime settings."""
    cold_config = {}
    hot_settings = {}
    for key, val in raw_json.items():
        if key in COLD_BOOTSTRAP_KEYS:
            cold_config[key] = val
        else:
            hot_settings[key] = val
    return cold_config, hot_settings


def migrate_legacy_json_to_db(config_json_path: Path, db: Any) -> bool:
    """Migrate stranded runtime settings from config.json into config.db.

    Idempotent: checks 'migration.legacy_config_json_imported' marker first.
    Atomic: writes to config.db first; prunes config.json only upon verified DB commit.
    """
    try:
        if not config_json_path.exists():
            return False

        # 1. Idempotency Check
        migrated_marker = db.get_system_setting("migration.legacy_config_json_imported")
        if str(migrated_marker).lower() in ("true", "1", "yes"):
            return False

        logger.info(
            f"Starting legacy config migration from {config_json_path} to config.db..."
        )

        with open(config_json_path, "r", encoding="utf-8") as f:
            raw_json = json.load(f)

        if not isinstance(raw_json, dict):
            logger.warning(
                f"Invalid config.json format in {config_json_path}; skipping migration."
            )
            return False

        cold_config, hot_settings = sanitize_legacy_config_json(raw_json)

        # 2. Extract and upsert quality profiles
        if "quality_profiles" in hot_settings and isinstance(
            hot_settings["quality_profiles"], list
        ):
            profiles = hot_settings.pop("quality_profiles")
            if profiles:
                db.set_quality_profiles(profiles)
                logger.info(f"Migrated {len(profiles)} quality profile(s) to config.db")

        # 3. Flatten and upsert hot runtime settings into system_settings
        for root_key, root_val in hot_settings.items():
            if isinstance(root_val, dict):
                for sub_k, sub_v in root_val.items():
                    db.set_system_setting(f"{root_key}.{sub_k}", sub_v)
                db.set_system_setting(root_key, root_val)
            else:
                db.set_system_setting(root_key, root_val)

        # Seed defaults for any missing keys
        db.seed_default_system_settings()

        # 4. Set migration completion marker in DB
        db.set_system_setting("migration.legacy_config_json_imported", "true")

        # 5. Atomically prune config.json
        tmp_path = config_json_path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(cold_config, f, indent=2)
        tmp_path.replace(config_json_path)

        logger.info(
            "Successfully migrated runtime settings to config.db and pruned config.json."
        )
        return True
    except Exception as e:
        logger.error(
            f"Legacy config migration failed (transaction aborted): {e}", exc_info=True
        )
        return False


class ConfigManager:
    def set_service_credentials(
        self,
        service_name: str,
        credentials: dict,
        sensitive_keys=None,
        register_if_missing=True,
    ) -> bool:
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
        sensitive_keys = sensitive_keys or [
            "client_secret",
            "access_token",
            "refresh_token",
        ]
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

    def get_service_credentials(self, service_name: str) -> dict:
        """
        Get all credentials/config for a service from the database.
        - service_name: e.g. 'spotify', 'tidal'
        Returns a dict of all config keys and values.
        """
        from database.config_database import get_config_database

        db = get_config_database()
        try:
            service_id = db.get_or_create_service_id(service_name)
            if not service_id:
                return {}
            return db.get_all_service_config(service_id)
        except Exception as e:
            logger.error(f"get_service_credentials failed: {e}")
            return {}

    def __init__(self, config_path: str = "config/config.json"):
        # STEP 1: Set config_dir from ENV (NOT from config.json)
        # config_dir is special: it's set only by ENV variables (for encryption key security)
        config_dir_env = os.environ.get("ECHOSYNC_CONFIG_DIR")
        if config_dir_env:
            self.config_dir = Path(config_dir_env)
        elif os.name != "nt" and Path("/config").exists() and os.path.isdir("/config"):
            # Running in container with a mounted /config (Unix/Docker)
            self.config_dir = Path("/config")
        else:
            # Default setup: paths relative to the application structure (dev)
            self.config_dir = Path(__file__).parent.parent / "config"

        # STEP 2: Set data_dir from ENV (takes precedence over config.json)
        data_dir_env = os.environ.get("ECHOSYNC_DATA_DIR")
        if data_dir_env:
            self.data_dir = Path(data_dir_env)
        elif os.name != "nt" and Path("/data").exists() and os.path.isdir("/data"):
            # Running in container with a mounted /data (Unix/Docker)
            self.data_dir = Path("/data")
        else:
            # Fallback to a data directory next to the project for local dev
            self.data_dir = Path(__file__).parent.parent / "data"

        # Log config and data directories at INFO level
        logger.info(f"Config directory: {self.config_dir}")
        logger.info(f"Data directory: {self.data_dir}")

        # At DEBUG level, also log the source (ENV vs default)
        if config_dir_env:
            logger.debug("Config directory from ECHOSYNC_CONFIG_DIR")
        else:
            logger.debug("Config directory from fallback default")

        if data_dir_env:
            logger.debug("Data directory from ECHOSYNC_DATA_DIR")
        else:
            logger.debug("Data directory from fallback default")

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Paths for encrypted config database (in config_dir)
        # Encryption key is stored in .env file via MASTER_KEY variable only (no file backup)
        self.config_path = (
            self.config_dir / "config.json"
        )  # For migration and non-secret JSON
        self.database_path = (
            self.config_dir / "config.db"
        )  # Encrypted config database (secrets)

        # Media library DB goes in data_dir (user-visible, non-secret)
        self.media_db_path = self.data_dir / "music_library.db"

        # Plugins directory goes in data_dir
        self.plugins_path = self.data_dir / "plugins"

        # STEP 3: Set individual storage paths from ENV (take precedence over data_dir and config.json)
        download_dir_env = os.environ.get("ECHOSYNC_DOWNLOAD_DIR")
        library_dir_env = os.environ.get("ECHOSYNC_LIBRARY_DIR")
        log_dir_env = os.environ.get("ECHOSYNC_LOG_DIR")

        # Initialize with data_dir defaults
        self.downloads_path = self.data_dir / "downloads"
        self.library_path = self.data_dir / "library"  # Default to 'library'
        self.logs_path = self.data_dir / "logs"

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

        self.config_data: dict[str, Any] = {}
        self.cipher: Fernet | None = None
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

        # Migrate legacy runtime keys into config.db if present
        try:
            from database.config_database import get_config_database

            db = get_config_database()
            migrate_legacy_json_to_db(self.config_path, db)
        except Exception as e:
            logger.debug(f"Config DB migration deferred at init: {e}")

    def _initialize_encryption(self):
        """Initialize Fernet cipher from MASTER_KEY environment variable.

        The encryption key is stored in .env file and loaded as MASTER_KEY environment variable.
        If no key exists, a new one is generated and automatically written to .env file.
        There is no backup file - only the ENV variable and .env persistence.
        """
        # Track if we auto-generated a key for WebUI warning
        self._auto_generated_key = False
        self._generated_key_value = None

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
        logger.warning("No MASTER_KEY found. Auto-generating encryption key...")
        new_key = Fernet.generate_key().decode("utf-8")

        # Track that we generated this key
        self._auto_generated_key = True
        self._generated_key_value = new_key

        # Save to .env file for persistence
        self._persist_key_to_env(new_key)

        # Set in current environment so initialization completes
        os.environ["MASTER_KEY"] = new_key
        logger.warning(
            "Encryption key auto-generated. Pass MASTER_KEY as env variable to persist across restarts."
        )

        self.cipher = Fernet(new_key.encode())

    def _persist_key_to_env(self, key: str):
        """Write the encryption key to .env file for persistence."""
        env_path = Path(__file__).parent.parent / ".env"

        try:
            env_path.parent.mkdir(parents=True, exist_ok=True)

            # Read existing .env file
            existing_content = ""
            if env_path.exists():
                try:
                    with open(env_path, "r") as f:
                        existing_content = f.read()
                except PermissionError:
                    logger.debug(
                        "Cannot read .env file (permission denied). Attempting to write anyway..."
                    )

            # Remove old MASTER_KEY line if it exists
            lines = existing_content.split("\n") if existing_content else []
            lines = [
                line for line in lines if not line.strip().startswith("MASTER_KEY=")
            ]

            # Add new MASTER_KEY at the top
            lines.insert(0, f"MASTER_KEY={key}")

            # Write back to .env with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    with open(env_path, "w") as f:
                        f.write("\n".join(lines))
                    logger.debug("Encryption key persisted to .env")
                    return
                except PermissionError:
                    if attempt < max_retries - 1:
                        import time

                        logger.debug(
                            f"Retrying .env write (attempt {attempt + 1}/{max_retries})..."
                        )
                        time.sleep(1)
                    else:
                        raise
        except Exception as e:
            logger.warning(f"Could not persist encryption key to .env: {e}")
            logger.warning("The key will be lost on next startup unless manually set!")
            logger.warning(
                f"Manually add this line to your .env file: MASTER_KEY={key}"
            )

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
            except Exception:
                logger.warning("Decryption failed: The encryption key may have changed")
                return ""  # Return empty string on decryption failure
        elif isinstance(value, str) and value.startswith("enc:"):
            logger.warning("Found encrypted value but cipher is not initialized")
            return value
        return value

    def _traverse_and_transform(
        self,
        data: dict[str, Any],
        transform: Callable,
        keys_to_transform: list,
        path: str = "",
    ) -> dict[str, Any]:
        """Recursively traverses a dict and applies a transformation to specified keys."""
        output = {}
        for key, value in data.items():
            # Build the full path to this key (e.g., "spotify.client_id")
            current_path = f"{path}.{key}" if path else key

            if isinstance(value, dict):
                # Recursively process nested dicts
                output[key] = self._traverse_and_transform(
                    value, transform, keys_to_transform, current_path
                )
            elif self._path_matches_any(current_path, keys_to_transform):
                # Transform this value because its path matches a secret key
                output[key] = transform(value)
            else:
                output[key] = value
        return output

    def _load_from_config_file(self) -> dict[str, Any] | None:
        """Load configuration from config.json file (for migration)."""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    config_data = json.load(f)
                    logger.debug(f"Configuration loaded from {self.config_path}")
                    return config_data
            else:
                return None
        except Exception as e:
            logger.debug(f"Could not load config from file: {e}")
            return None

    def _get_default_config(self) -> dict[str, Any]:
        """Get default cold bootstrap configuration."""
        cfg = {
            "custom_ui_path": "",
            "server": {"host": "0.0.0.0", "port": 5000},
            "logging": {"path": str(self.logs_path / "app.log"), "level": "INFO"},
            "database": {"path": str(self.media_db_path), "max_workers": 2},
            "storage": {
                "data_dir": str(self.data_dir),
                "config_dir": str(self.config_dir),
                "download_dir": str(self.downloads_path),
                "library_dir": str(self.library_path),
                "log_dir": str(self.logs_path),
                "plugins_dir": str(self.plugins_path),
            },
        }
        return cfg

    def _has_undecrypted_secrets(self, config_data: dict[str, Any]) -> bool:
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
        2. Defaults (fresh install)
        """
        # Start with defaults as base
        config_data = self._get_default_config()

        # Load non-secrets from config.json
        json_data = self._load_from_config_file()
        if json_data:
            logger.debug("Loaded non-secrets from config.json")
            config_data = self._deep_merge(config_data, json_data)

        self.config_data = config_data

        # Apply storage paths from config if they exist (overrides initial paths)
        self._apply_storage_paths_from_config()

        # If we have no JSON file yet, save current config to JSON for future edits
        if not json_data or "custom_ui_path" not in json_data:
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
            storage_config = self.config_data.get("storage", {})

            # First, check if data_dir is specified and update if so
            if storage_config.get("data_dir"):
                self.data_dir = Path(storage_config["data_dir"])
                logger.debug(f"Applied data_dir from config.json: {self.data_dir}")
                # Update derived defaults based on new data_dir
                # Only update if the individual paths weren't explicitly set
                if not storage_config.get("download_dir"):
                    self.downloads_path = self.data_dir / "downloads"
                if not storage_config.get("library_dir"):
                    self.library_path = self.data_dir / "library"
                if not storage_config.get("log_dir"):
                    self.logs_path = self.data_dir / "logs"
                if not storage_config.get("plugins_dir"):
                    self.plugins_path = self.data_dir / "plugins"
                # Also update media_db_path to be under new data_dir
                self.media_db_path = self.data_dir / "music_library.db"

            # Then apply any explicit path overrides
            if storage_config.get("download_dir"):
                self.downloads_path = Path(storage_config["download_dir"])
                logger.debug(f"Applied download_dir from config: {self.downloads_path}")

            if storage_config.get("library_dir"):
                self.library_path = Path(storage_config["library_dir"])
                logger.debug(f"Applied library_dir from config: {self.library_path}")

            if storage_config.get("log_dir"):
                self.logs_path = Path(storage_config["log_dir"])
                logger.debug(f"Applied log_dir from config: {self.logs_path}")

            if storage_config.get("plugins_dir"):
                self.plugins_path = Path(storage_config["plugins_dir"])
                logger.debug(f"Applied plugins_dir from config: {self.plugins_path}")

            if storage_config.get("config_dir"):
                new_config_dir = Path(storage_config["config_dir"])
                # Only log the difference, don't change config_dir itself to avoid breaking encryption
                if new_config_dir != self.config_dir:
                    logger.debug(
                        f"Config specifies different config_dir: {new_config_dir}"
                    )
                    logger.debug(
                        "config_dir cannot be changed after initialization (encryption key location)"
                    )

            # Apply logging path from config if specified
            logging_config = self.config_data.get("logging", {})
            if logging_config.get("path"):
                log_path = Path(logging_config["path"])
                # If it's a relative path, make it relative to logs_path
                if not log_path.is_absolute():
                    log_path = self.logs_path / log_path.name
                    self.config_data["logging"]["path"] = str(log_path.resolve())
                    logger.debug(f"Updated logging path to: {log_path}")

            # Update database path in config to match media_db_path
            db_config = self.config_data.get("database", {})
            db_config["path"] = str(self.media_db_path.resolve())

            # Create directories if they don't exist
            self.downloads_path.mkdir(parents=True, exist_ok=True)
            self.library_path.mkdir(parents=True, exist_ok=True)
            self.logs_path.mkdir(parents=True, exist_ok=True)
            self.media_db_path.parent.mkdir(parents=True, exist_ok=True)

            # Update config with resolved paths so they're saved to config.json
            # This makes config.json the source of truth
            self.config_data["storage"]["data_dir"] = str(self.data_dir.resolve())
            self.config_data["storage"]["config_dir"] = str(self.config_dir.resolve())
            self.config_data["storage"]["download_dir"] = str(
                self.downloads_path.resolve()
            )
            self.config_data["storage"]["library_dir"] = str(
                self.library_path.resolve()
            )
            self.config_data["storage"]["log_dir"] = str(self.logs_path.resolve())
            self.config_data["storage"]["plugins_dir"] = str(
                self.plugins_path.resolve()
            )

        except Exception as e:
            print(f"[WARN] Could not apply storage paths from config: {e}")

    def _normalize_database_workers(self):
        """Ensure database.max_workers is sensible for the configured DB.

        Behavior:
         - If DB path looks like SQLite (.db or contains 'sqlite'), clamp to 1..4 and default to 2.
         - Otherwise clamp to 1..10 and default to 4.
        """
        try:
            db_cfg = self.config_data.get("database") or {}
            raw = db_cfg.get("max_workers")
            try:
                val = int(raw)
            except Exception:
                val = None

            db_path = (db_cfg.get("path") or "").lower()
            is_sqlite = db_path.endswith(".db") or "sqlite" in db_path

            if is_sqlite:
                if val is None:
                    val = 2
                val = max(1, min(val, 4))
            else:
                if val is None:
                    val = 4
                val = max(1, min(val, 10))

            self.config_data.setdefault("database", {})["max_workers"] = val
        except Exception as e:
            print(f"[WARN] Could not normalize database.max_workers: {e}")

    def _deep_merge(
        self, base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        """Recursively merge override dict into base dict."""
        result = copy.deepcopy(base)
        for key, value in override.items():
            if (
                isinstance(value, dict)
                and key in result
                and isinstance(result[key], dict)
            ):
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
            with open(self.config_path, "w") as f:
                json.dump(non_secrets, f, indent=2)
            print(f"[OK] Non-secrets saved to {self.config_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save non-secrets to JSON: {e}")
            return False

    def _extract_non_secrets(
        self, data: dict[str, Any], path: str = ""
    ) -> dict[str, Any]:
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

    def _extract_secrets(self, data: dict[str, Any], path: str = "") -> dict[str, Any]:
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

    def _get_db(self):
        """Get the ConfigDatabase instance matching this ConfigManager's database_path."""
        try:
            from database.config_database import get_config_database

            return get_config_database(db_path=self.database_path)
        except Exception:
            return None

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value, checking hot config.db first, then cold config.json."""
        root_key = key.split(".")[0]
        if root_key not in COLD_BOOTSTRAP_KEYS:
            try:
                db = self._get_db()
                if db:
                    db_val = db.get_system_setting(key)
                    if db_val is not None:
                        return db_val
            except Exception:
                pass

        keys = key.split(".")
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

        Hot runtime keys are persisted to config.db (system_settings).
        Cold bootstrap keys are saved to plaintext config.json.
        """
        root_key = key.split(".")[0]
        if root_key not in COLD_BOOTSTRAP_KEYS:
            try:
                db = self._get_db()
                if db:
                    db.set_system_setting(key, value)
            except Exception:
                pass

        keys = key.split(".")
        config_level = self.config_data
        for k in keys[:-1]:
            config_level = config_level.setdefault(k, {})

        config_level[keys[-1]] = value

        # Save non-secrets to plaintext JSON only if cold bootstrap key
        if root_key in COLD_BOOTSTRAP_KEYS:
            self._save_non_secrets_to_json()

    def get_plugin_channel(self, plugin_id: Any) -> str:
        """Get the active update channel ('stable' or 'beta') for a plugin."""
        if not plugin_id:
            return "stable"
        try:
            from database.config_database import get_config_database

            db = get_config_database()
            db_id = db.get_service_id(plugin_id)
            if db_id:
                with db._get_connection() as conn:
                    c = conn.cursor()
                    c.execute("SELECT beta_opt_in FROM services WHERE id=?", (db_id,))
                    row = c.fetchone()
                    if row and row[0] is not None:
                        return "beta" if row[0] else "stable"
        except Exception:
            pass
        return "beta" if self.get("ui.beta_plugin_ui", False) else "stable"

    def get_active_download_client(self) -> str | None:
        """Get the configured active download client name (checking config.db first)."""
        try:
            db = self._get_db()
            if db:
                val = db.get_system_setting("active_download_client")
                if val is not None:
                    return str(val)
        except Exception:
            pass
        return self.get("active_download_client")

    def set_active_download_client(self, client_name: str | None) -> bool:
        """Set and persist the active download client name."""
        try:
            db = self._get_db()
            if db:
                db.set_system_setting("active_download_client", client_name)
        except Exception:
            pass
        self.set("active_download_client", client_name)
        return True

    def get_active_media_server(self) -> str:
        """Get the configured active media server name (checking config.db first)."""
        try:
            db = self._get_db()
            if db:
                val = db.get_system_setting("active_media_server")
                if val is not None:
                    return str(val)
        except Exception:
            pass
        return self.get("active_media_server", "plex")

    def set_active_media_server(self, server_name: str) -> bool:
        """Set and persist the active media server name."""
        try:
            db = self._get_db()
            if db:
                db.set_system_setting("active_media_server", server_name)
        except Exception:
            pass
        self.set("active_media_server", server_name)
        return True

    def get_settings(self) -> dict[str, Any]:
        """Return the full non-secret configuration (alias for get_all)."""
        return self.get_all()

    def save_settings(self, config: dict[str, Any]) -> bool:
        """Save a full non-secret configuration dictionary."""
        try:
            self.config_data = self._deep_merge(self.config_data, config)
            return self._save_non_secrets_to_json()
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False

    def get_all(self) -> dict[str, Any]:
        """Return the full configuration suitable for the UI, merging hot settings from config.db."""
        try:
            non_secrets = self._extract_non_secrets(self.config_data)
            result = copy.deepcopy(non_secrets)
            try:
                db = self._get_db()
                if db:
                    hot_settings = db.get_all_system_settings()
                    for k, v in hot_settings.items():
                        parts = k.split(".")
                        curr = result
                        for part in parts[:-1]:
                            if part not in curr or not isinstance(curr[part], dict):
                                curr[part] = {}
                            curr = curr[part]
                        curr[parts[-1]] = v
            except Exception:
                pass
            return result
        except Exception as e:
            print(f"[ERROR] get_all failed: {e}")
            return {}

    def get_quality_profiles(self) -> list:
        """Return the stored quality profiles list (prefers config.db)."""
        try:
            db = self._get_db()
            if db:
                profiles = db.get_quality_profiles()
                if profiles:
                    return profiles
        except Exception:
            pass
        try:
            profiles = self.config_data.get("quality_profiles")
            return profiles if isinstance(profiles, list) else []
        except Exception as e:
            print(f"[ERROR] get_quality_profiles failed: {e}")
            return []

    def set_quality_profiles(self, profiles: list) -> bool:
        """Validate/normalize and persist quality profiles to config.db."""
        try:
            if not isinstance(profiles, list):
                raise ValueError("profiles must be a list")

            # Normalize each profile and formats
            def _norm_profile(p):
                np = dict(p)
                np["id"] = str(np.get("id", ""))
                np["name"] = str(np.get("name", ""))
                formats = np.get("formats") or np.get("types") or np.get("steps") or []
                norm_formats = []
                for f in formats:
                    nf = dict(f)
                    try:
                        nf["min_size_mb"] = int(nf.get("min_size_mb") or 0)
                    except Exception:
                        nf["min_size_mb"] = 0
                    try:
                        nf["max_size_mb"] = int(nf.get("max_size_mb") or 0)
                    except Exception:
                        nf["max_size_mb"] = 0
                    try:
                        nf["priority"] = int(nf.get("priority") or 0)
                    except Exception:
                        nf["priority"] = 0

                    for arrk in ("bitrates", "bit_depths", "sample_rates"):
                        val = nf.get(arrk)
                        if val is None:
                            nf[arrk] = []
                        elif isinstance(val, list):
                            nf[arrk] = [str(x) for x in val]
                        else:
                            nf[arrk] = [str(val)]

                    nf["type"] = str(nf.get("type") or nf.get("format") or "")
                    norm_formats.append(nf)
                np["formats"] = norm_formats
                return np

            normalized = [_norm_profile(p) for p in profiles]
            db = self._get_db()
            if db:
                db.set_quality_profiles(normalized)
            self.config_data["quality_profiles"] = normalized
            return True
        except Exception as e:
            print(f"[ERROR] set_quality_profiles failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    def get_database_config(self) -> dict[str, str]:
        return self.get("database", {})

    def get_logging_config(self) -> dict[str, str]:
        return self.get("logging", {})

    def get_plugins_dir(self) -> Path:
        """Returns the absolute path to the plugins directory."""
        return self.plugins_path

    def get_data_dir(self) -> Path:
        """Returns the absolute path to the data root directory."""
        return self.data_dir

    def get_config_dir(self) -> Path:
        """Returns the absolute path to the configuration root directory."""
        return self.config_dir

    def get_disabled_plugins(self) -> list[str]:
        """Return the list of disabled providers/plugins."""
        return self.get("disabled_plugins", [])

    def set_disabled_plugins(self, disabled_list: list[str]):
        """Set the list of disabled plugins."""
        self.set("disabled_plugins", disabled_list)

    def disable_plugin(self, provider_id: str) -> bool:
        """Add a provider/plugin to the disabled list in canonical numeric string format."""
        disabled = self.get_disabled_plugins()
        pid_str = str(provider_id).strip()
        from core.nexus_framework.plugin_loader import generate_plugin_id

        canon_id = (
            int(pid_str) if pid_str.isdigit() else generate_plugin_id(pid_str.lower())
        )
        canon_id_str = str(canon_id)

        target_ids = {canon_id}
        target_names = {pid_str.lower()}
        clean_name = (
            pid_str.lower().replace("echosync.", "").replace("echosync/", "").strip()
        )
        target_names.add(clean_name)
        target_names.add(f"echosync.{clean_name}")
        target_ids.add(generate_plugin_id(clean_name))
        target_ids.add(generate_plugin_id(f"echosync.{clean_name}"))

        try:
            from database.config_database import get_config_database

            db = get_config_database()
            with db._open_connection() as conn:
                c = conn.cursor()
                if pid_str.isdigit():
                    c.execute(
                        "SELECT name, plugin_id FROM services WHERE plugin_id=? OR id=?",
                        (int(pid_str), int(pid_str)),
                    )
                else:
                    c.execute(
                        "SELECT name, plugin_id FROM services WHERE lower(name)=lower(?)",
                        (pid_str,),
                    )
                row = c.fetchone()
                if row:
                    r_name = row["name"].lower()
                    r_clean = (
                        r_name.replace("echosync.", "").replace("echosync/", "").strip()
                    )
                    target_names.update({r_name, r_clean, f"echosync.{r_clean}"})
                    if row["plugin_id"]:
                        target_ids.add(row["plugin_id"])
                        target_ids.add(generate_plugin_id(r_clean))
                        target_ids.add(generate_plugin_id(f"echosync.{r_clean}"))
        except Exception:
            pass

        # Filter out existing unnormalized variants and append canonical ID
        new_disabled = []
        for item in disabled:
            item_str = str(item).strip()
            item_clean = (
                item_str.lower()
                .replace("echosync.", "")
                .replace("echosync/", "")
                .strip()
            )
            item_ids = {
                int(item_str)
                if item_str.isdigit()
                else generate_plugin_id(item_str.lower()),
                generate_plugin_id(item_clean),
                generate_plugin_id(f"echosync.{item_clean}"),
            }
            if (
                item_str.lower() in target_names
                or item_clean in target_names
                or (item_ids & target_ids)
            ):
                continue
            new_disabled.append(item)

        new_disabled.append(canon_id_str)
        self.set("disabled_plugins", new_disabled)
        logger.info(
            f"Plugin {provider_id} (canonical ID: {canon_id_str}) has been disabled."
        )
        return True

    def enable_plugin(self, provider_id: str) -> bool:
        """Remove a provider/plugin from the disabled list (matches by name, id, or canonical id)."""
        disabled = self.get_disabled_plugins()
        if not disabled:
            return False

        pid_str = str(provider_id).strip()
        from core.nexus_framework.plugin_loader import generate_plugin_id

        canon_id = (
            int(pid_str) if pid_str.isdigit() else generate_plugin_id(pid_str.lower())
        )
        target_ids = {canon_id}
        target_names = {pid_str.lower()}
        clean_name = (
            pid_str.lower().replace("echosync.", "").replace("echosync/", "").strip()
        )
        target_names.add(clean_name)
        target_names.add(f"echosync.{clean_name}")
        target_ids.add(generate_plugin_id(clean_name))
        target_ids.add(generate_plugin_id(f"echosync.{clean_name}"))

        try:
            from database.config_database import get_config_database

            db = get_config_database()
            with db._open_connection() as conn:
                c = conn.cursor()
                if pid_str.isdigit():
                    c.execute(
                        "SELECT name, plugin_id FROM services WHERE plugin_id=? OR id=?",
                        (int(pid_str), int(pid_str)),
                    )
                else:
                    c.execute(
                        "SELECT name, plugin_id FROM services WHERE lower(name)=lower(?)",
                        (pid_str,),
                    )
                row = c.fetchone()
                if row:
                    r_name = row["name"].lower()
                    r_clean = (
                        r_name.replace("echosync.", "").replace("echosync/", "").strip()
                    )
                    target_names.update({r_name, r_clean, f"echosync.{r_clean}"})
                    if row["plugin_id"]:
                        target_ids.add(row["plugin_id"])
                        target_ids.add(generate_plugin_id(r_clean))
                        target_ids.add(generate_plugin_id(f"echosync.{r_clean}"))
        except Exception:
            pass

        new_disabled = []
        removed = False
        for item in disabled:
            item_str = str(item).strip()
            item_clean = (
                item_str.lower()
                .replace("echosync.", "")
                .replace("echosync/", "")
                .strip()
            )
            item_ids = {
                int(item_str)
                if item_str.isdigit()
                else generate_plugin_id(item_str.lower()),
                generate_plugin_id(item_clean),
                generate_plugin_id(f"echosync.{item_clean}"),
            }
            if (
                item_str.lower() in target_names
                or item_clean in target_names
                or (item_ids & target_ids)
            ):
                removed = True
                continue
            new_disabled.append(item)

        if removed:
            self.set("disabled_plugins", new_disabled)
            logger.info(f"Plugin {provider_id} has been enabled.")
            return True
        return False

    def get_generated_encryption_key(self) -> str | None:
        """Return the auto-generated MASTER_KEY if it was created during this session."""
        if getattr(self, "_auto_generated_key", False):
            return getattr(self, "_generated_key_value", None)
        return None

    def was_encryption_key_auto_generated(self) -> bool:
        """Return True if the encryption key was auto-generated during this session."""
        return getattr(self, "_auto_generated_key", False)


config_manager = ConfigManager()


def get_setting(key: str, default: Any = None) -> Any:
    """Retrieve a setting from config_manager (for backward compatibility)."""
    return config_manager.get(key, default)


def set_setting(key: str, value: Any) -> None:
    """Save a setting in config_manager (for backward compatibility)."""
    config_manager.set(key, value)
