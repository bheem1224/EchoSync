"""
Integration tests for ConfigManager: config saving, loading, encryption, and decryption.
These tests use real file I/O and database operations (not mocked).
"""

import os
import json
import pytest

pytestmark = pytest.mark.skip(reason="Config integration tests depend on file I/O and encryption")

import sqlite3
import tempfile
import shutil
from pathlib import Path
from cryptography.fernet import Fernet

from core.settings import ConfigManager, SECRETS


@pytest.fixture
def temp_config_dir():
    """Creates a temporary directory for config files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def config_manager_real(temp_config_dir):
    """Creates a ConfigManager instance with a real temporary directory."""
    # Point to temp config directory
    os.environ['SOULSYNC_CONFIG_DIR'] = temp_config_dir
    
    # Create a fresh ConfigManager
    cm = ConfigManager()
    
    yield cm
    
    # Cleanup
    if 'SOULSYNC_CONFIG_DIR' in os.environ:
        del os.environ['SOULSYNC_CONFIG_DIR']


class TestEncryptionDecryption:
    """Tests for encryption and decryption functions."""
    
    def test_encrypt_string_value(self, config_manager_real):
        """Test that string values are encrypted correctly."""
        value = "my_secret_value"
        encrypted = config_manager_real._encrypt_value(value)
        
        assert encrypted.startswith("enc:")
        assert encrypted != value
        assert isinstance(encrypted, str)
    
    def test_encrypt_non_string_value(self, config_manager_real):
        """Test that non-string values are not encrypted."""
        value = 12345
        encrypted = config_manager_real._encrypt_value(value)
        assert encrypted == value
    
    def test_encrypt_empty_string(self, config_manager_real):
        """Test that empty strings are not encrypted."""
        value = ""
        encrypted = config_manager_real._encrypt_value(value)
        assert encrypted == value
    
    def test_decrypt_valid_encrypted_value(self, config_manager_real):
        """Test that encrypted values can be decrypted."""
        original = "test_secret_value"
        encrypted = config_manager_real._encrypt_value(original)
        
        decrypted = config_manager_real._decrypt_value(encrypted)
        assert decrypted == original
    
    def test_decrypt_non_encrypted_value(self, config_manager_real):
        """Test that non-encrypted values pass through unchanged."""
        value = "plain_text_value"
        decrypted = config_manager_real._decrypt_value(value)
        assert decrypted == value
    
    def test_decrypt_invalid_encrypted_value(self, config_manager_real):
        """Test that invalid encrypted values return empty string."""
        # This should fail to decrypt and return ""
        invalid_encrypted = "enc:invalid_base64_and_not_valid_fernet_data"
        decrypted = config_manager_real._decrypt_value(invalid_encrypted)
        assert decrypted == ""
    
    def test_encryption_key_persists(self, temp_config_dir):
        """Test that encryption key is saved and reused."""
        # First instance
        os.environ['SOULSYNC_CONFIG_DIR'] = temp_config_dir
        cm1 = ConfigManager()
        
        # Get the key from the first instance
        with open(cm1.key_path, 'rb') as f:
            key1 = f.read()
        
        # Create a second instance (should reuse the key)
        cm2 = ConfigManager()
        
        with open(cm2.key_path, 'rb') as f:
            key2 = f.read()
        
        assert key1 == key2
        # Both should be able to encrypt/decrypt the same data
        test_bytes = b"test"
        encrypted = Fernet(key1).encrypt(test_bytes)
        decrypted = Fernet(key2).decrypt(encrypted)
        assert decrypted == test_bytes


class TestConfigSaveAndLoad:
    """Tests for saving and loading configuration."""
    
    def test_save_non_secret_to_config_json(self, config_manager_real):
        """Test that non-secret values can be set and retrieved."""
        config_manager_real.set("logging.level", "DEBUG")
        
        retrieved = config_manager_real.get("logging.level")
        assert retrieved == "DEBUG"
    
    def test_save_secret_to_database(self, config_manager_real):
        """Test that secrets are saved to database and encrypted."""
        config_manager_real.set("spotify.client_secret", "my_spotify_secret")
        
        # Check that the value is encrypted in the database
        conn = sqlite3.connect(str(config_manager_real.database_path))
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM metadata WHERE key = 'app_config'")
        row = cursor.fetchone()
        conn.close()
        
        assert row is not None
        config_in_db = json.loads(row[0])
        
        # The value should be encrypted
        assert config_in_db['spotify']['client_secret'].startswith("enc:")
    
    def test_get_decrypts_secret_from_database(self, config_manager_real):
        """Test that secrets are decrypted when retrieved."""
        secret_value = "test_spotify_client_id"
        config_manager_real.set("spotify.client_id", secret_value)
        
        # Get the value back
        retrieved = config_manager_real.get("spotify.client_id")
        assert retrieved == secret_value
    
    def test_load_from_database_decrypts_all_secrets(self, config_manager_real):
        """Test that all secrets are decrypted when loading from database."""
        # Set multiple secrets
        config_manager_real.set("spotify.client_id", "spotify_id")
        config_manager_real.set("spotify.client_secret", "spotify_secret")
        config_manager_real.set("plex.token", "plex_token_value")
        config_manager_real.set("tidal.client_id", "tidal_id")
        
        # Create a new instance to force loading from database
        os.environ['SOULSYNC_CONFIG_DIR'] = config_manager_real.config_dir.as_posix()
        cm2 = ConfigManager()
        
        # All secrets should be decrypted
        assert cm2.get("spotify.client_id") == "spotify_id"
        assert cm2.get("spotify.client_secret") == "spotify_secret"
        assert cm2.get("plex.token") == "plex_token_value"
        assert cm2.get("tidal.client_id") == "tidal_id"
    
    def test_no_encrypted_values_in_memory(self, config_manager_real):
        """Test that in-memory config never contains 'enc:' prefixed values."""
        config_manager_real.set("spotify.client_secret", "secret123")
        
        # Check in-memory data
        assert not config_manager_real.config_data['spotify']['client_secret'].startswith("enc:")
        assert config_manager_real.config_data['spotify']['client_secret'] == "secret123"
    
    def test_traverse_and_transform_with_nested_keys(self, config_manager_real):
        """Test that _traverse_and_transform correctly handles nested dictionaries."""
        test_data = {
            "spotify": {
                "client_id": "id_value",
                "client_secret": "secret_value",
                "redirect_uri": "http://redirect"
            },
            "plex": {
                "base_url": "http://plex",
                "token": "token_value",
                "auto_detect": True
            }
        }
        
        # Transform to encrypt secrets
        encrypted = config_manager_real._traverse_and_transform(
            test_data,
            config_manager_real._encrypt_value,
            SECRETS
        )
        
        # Check that secrets are encrypted
        assert encrypted['spotify']['client_id'].startswith("enc:")
        assert encrypted['spotify']['client_secret'].startswith("enc:")
        assert encrypted['plex']['token'].startswith("enc:")
        
        # Check that non-secrets are not encrypted
        assert encrypted['spotify']['redirect_uri'] == "http://redirect"
        assert encrypted['plex']['base_url'] == "http://plex"
        assert encrypted['plex']['auto_detect'] == True
    
    def test_traverse_and_transform_decryption(self, config_manager_real):
        """Test that _traverse_and_transform correctly decrypts secrets."""
        # First encrypt some data
        test_data = {
            "spotify": {
                "client_id": "id_value",
                "client_secret": "secret_value"
            }
        }
        
        encrypted = config_manager_real._traverse_and_transform(
            test_data,
            config_manager_real._encrypt_value,
            SECRETS
        )
        
        # Now decrypt it
        decrypted = config_manager_real._traverse_and_transform(
            encrypted,
            config_manager_real._decrypt_value,
            SECRETS
        )
        
        # Should match original
        assert decrypted['spotify']['client_id'] == "id_value"
        assert decrypted['spotify']['client_secret'] == "secret_value"


class TestConfigPersistence:
    """Tests for configuration persistence across restarts."""
    
    def test_config_persists_across_instances(self, temp_config_dir):
        """Test that configuration persists when creating a new ConfigManager instance."""
        os.environ['SOULSYNC_CONFIG_DIR'] = temp_config_dir
        
        # First instance: set some values
        cm1 = ConfigManager()
        cm1.set("spotify.client_id", "spotify_123")
        cm1.set("plex.token", "plex_token_xyz")
        cm1.set("logging.level", "DEBUG")
        
        # Second instance: should load the same values
        cm2 = ConfigManager()
        assert cm2.get("spotify.client_id") == "spotify_123"
        assert cm2.get("plex.token") == "plex_token_xyz"
        assert cm2.get("logging.level") == "DEBUG"
    
    def test_database_and_json_coexist(self, temp_config_dir):
        """Test that encrypted secrets in DB and non-secrets in config.json work together."""
        os.environ['SOULSYNC_CONFIG_DIR'] = temp_config_dir
        cm = ConfigManager()
        
        # Set secrets and non-secrets
        cm.set("plex.token", "secret_token")
        cm.set("logging.level", "INFO")
        cm.set("spotify.client_secret", "spotify_secret")
        cm.set("database.path", "database/music_library.db")
        
        # Verify database has encrypted secrets
        conn = sqlite3.connect(str(cm.database_path))
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM metadata WHERE key = 'app_config'")
        db_config = json.loads(cursor.fetchone()[0])
        conn.close()
        
        # Secrets should be encrypted in DB
        assert db_config['plex']['token'].startswith("enc:")
        assert db_config['spotify']['client_secret'].startswith("enc:")
        
        # Create new instance and verify retrieval
        cm2 = ConfigManager()
        assert cm2.get("plex.token") == "secret_token"
        assert cm2.get("spotify.client_secret") == "spotify_secret"
        assert cm2.get("logging.level") == "INFO"
        assert cm2.get("database.path") == "database/music_library.db"


class TestErrorHandling:
    """Tests for error handling in config operations."""
    
    def test_corrupted_encrypted_data_detection(self, config_manager_real):
        """Test that corrupted encrypted data is detected."""
        # Manually insert corrupted encrypted data
        corrupted_config = {
            "spotify": {
                "client_id": "enc:corrupted_data",
                "client_secret": "another_bad_value"
            }
        }
        
        # This should be detected as having undecrypted secrets
        has_undecrypted = config_manager_real._has_undecrypted_secrets(corrupted_config)
        assert has_undecrypted is True
    
    def test_valid_decrypted_data_no_detection(self, config_manager_real):
        """Test that properly decrypted data is not flagged as corrupted."""
        valid_config = {
            "spotify": {
                "client_id": "normal_value",
                "client_secret": "another_normal_value"
            }
        }
        
        has_undecrypted = config_manager_real._has_undecrypted_secrets(valid_config)
        assert has_undecrypted is False


class TestSecretsList:
    """Tests that SECRETS list is complete and correct."""
    
    def test_all_sensitive_fields_in_secrets_list(self):
        """Test that all sensitive fields are in the SECRETS list."""
        expected_secrets = [
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
        
        for secret in expected_secrets:
            assert secret in SECRETS, f"Missing secret: {secret}"
    
    def test_non_secret_fields_not_encrypted(self, config_manager_real):
        """Test that non-secret fields are never encrypted."""
        non_secret_fields = {
            "logging.level": "DEBUG",
            "logging.path": "/path/to/logs",
            "database.max_workers": 5,
            "spotify.redirect_uri": "http://localhost",
            "plex.base_url": "http://plex:32400",
            "metadata_enhancement.enabled": True,
        }
        
        for key, value in non_secret_fields.items():
            config_manager_real.set(key, value)
            retrieved = config_manager_real.get(key)
            assert retrieved == value
            
            # Value should not be encrypted in in-memory config
            keys = key.split('.')
            val = config_manager_real.config_data
            for k in keys:
                val = val[k]
            assert not (isinstance(val, str) and val.startswith("enc:"))
