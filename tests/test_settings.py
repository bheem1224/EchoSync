import os
import json
import pytest
from unittest.mock import patch, mock_open, MagicMock
from config.settings import ConfigManager, SECRETS

from cryptography.fernet import Fernet

# --- Fixtures ---

@pytest.fixture
def clean_env():
    """Fixture to ensure a clean environment for each test."""
    original_env = os.environ.copy()
    os.environ.clear()
    yield
    os.environ.clear()
    os.environ.update(original_env)

@pytest.fixture
def mock_fs(mocker):
    """Mocks out file system interactions."""
    mocker.patch("pathlib.Path.exists", return_value=False)
    mocker.patch("builtins.open", mock_open())
    mocker.patch("pathlib.Path.chmod")
    mocker.patch("pathlib.Path.mkdir")
    mocker.patch("sqlite3.connect")

@pytest.fixture
def base_config_manager(clean_env, mock_fs):
    """Provides a ConfigManager instance with basic mocks, allowing for more targeted patching in tests."""
    with patch.object(ConfigManager, '_load_config'): # Prevent loading during init
        cm = ConfigManager()
    return cm

# --- Tests for Initialization and Key Management ---

def test_initialize_encryption_from_env(base_config_manager: ConfigManager):
    """Test that the encryption key is loaded from the MASTER_KEY environment variable."""
    test_key = Fernet.generate_key()
    with patch.dict(os.environ, {"MASTER_KEY": test_key.decode()}), \
         patch('builtins.open', mock_open()) as mock_file:
        
        base_config_manager._initialize_encryption()
        
        assert base_config_manager.cipher is not None
        # Verify the key was not written to a file
        mock_file.assert_not_called()

def test_initialize_encryption_from_file(base_config_manager: ConfigManager, mocker):
    """Test that the encryption key is loaded from an existing key file."""
    test_key = Fernet.generate_key()
    
    mocker.patch("pathlib.Path.exists", return_value=True)
    mocker.patch("builtins.open", mock_open(read_data=test_key))
    
    base_config_manager._initialize_encryption()
    
    assert base_config_manager.cipher is not None
    # We can't directly compare Fernet objects, but we can check if it decrypts a known value
    encrypted = Fernet(test_key).encrypt(b'test')
    assert base_config_manager.cipher.decrypt(encrypted) == b'test'

@patch("pathlib.Path.exists", return_value=False)
def test_initialize_encryption_generates_new_key(mock_exists, base_config_manager: ConfigManager):
    """Test that a new encryption key is generated if none exists."""
    m = mock_open()
    with patch("builtins.open", m), \
         patch("pathlib.Path.chmod") as mock_chmod:
        
        base_config_manager._initialize_encryption()
        
        assert base_config_manager.cipher is not None
        # Verify that a new key was written to the file
        m.assert_called_once_with(base_config_manager.key_path, 'wb')
        assert m().write.call_args[0][0] is not None # Check that *some* key was written
        mock_chmod.assert_called_once_with(0o600)


# --- Tests for Loading Logic ---

def test_load_config_from_database(base_config_manager: ConfigManager, mocker):
    """Test loading configuration from the database as the primary source."""
    sample_data = {"spotify": {"client_id": "id", "client_secret": "enc:something"}}
    
    mock_load_db = mocker.patch.object(ConfigManager, "_load_from_database", return_value=sample_data)
    mock_load_file = mocker.patch.object(ConfigManager, "_load_from_config_file")
    
    base_config_manager._load_config()

    mock_load_db.assert_called_once()
    mock_load_file.assert_not_called()
    assert base_config_manager.config_data['spotify']['client_id'] == 'id'

def test_load_config_migrates_from_file(base_config_manager: ConfigManager, mocker):
    """Test migration from a config.json file when the database is empty."""
    sample_data = {"spotify": {"client_id": "id_from_file"}}
    
    mocker.patch.object(ConfigManager, "_load_from_database", return_value=None)
    mocker.patch.object(ConfigManager, "_load_from_config_file", return_value=sample_data)
    mock_save_db = mocker.patch.object(ConfigManager, "_save_to_database", return_value=True)

    base_config_manager._load_config()

    mock_save_db.assert_called_once_with(sample_data)
    assert base_config_manager.config_data['spotify']['client_id'] == 'id_from_file'

def test_load_config_uses_defaults(base_config_manager: ConfigManager, mocker):
    """Test that default configuration is used when no other source is available."""
    mocker.patch.object(ConfigManager, "_load_from_database", return_value=None)
    mocker.patch.object(ConfigManager, "_load_from_config_file", return_value=None)
    mock_save_db = mocker.patch.object(ConfigManager, "_save_to_database", return_value=True)

    base_config_manager._load_config()

    mock_save_db.assert_called_once()
    assert base_config_manager.get('active_media_server') == 'plex' # Check a default value
    
# --- Tests for Encryption/Decryption ---

@pytest.fixture
def live_cm():
    """A more 'live' ConfigManager fixture that initializes fully."""
    with patch.dict(os.environ, {}, clear=True), \
         patch("pathlib.Path.exists", return_value=False), \
         patch("builtins.open", mock_open()), \
         patch("pathlib.Path.chmod"), \
         patch("pathlib.Path.mkdir"), \
         patch("sqlite3.connect"):
        
        # Prevent loading from db/file on init, start with defaults
        with patch.object(ConfigManager, "_load_from_database", return_value=None), \
             patch.object(ConfigManager, "_load_from_config_file", return_value=None):
            cm = ConfigManager()
    return cm


def test_decryption_failure(live_cm: ConfigManager):
    """Test that a bad encrypted value results in an empty string."""
    bad_encrypted_value = "enc:not_a_valid_encrypted_string"
    decrypted = live_cm._decrypt_value(bad_encrypted_value)
    assert decrypted == ""

def test_get_non_secret(live_cm: ConfigManager):
    """Test that getting a non-secret value works correctly."""
    assert live_cm.get("settings.audio_quality") == "flac"

def test_end_to_end_set_and_get_secret(live_cm: ConfigManager):
    """Test the full flow of setting a secret and ensuring it's encrypted in the database."""
    secret_key = "plex.token"
    secret_value = "my_super_secret_plex_token"

    mock_save_db = MagicMock(return_value=True)
    live_cm._save_to_database = mock_save_db

    # Set the secret
    live_cm.set(secret_key, secret_value)
    
    # Verify get() returns the decrypted value
    assert live_cm.get(secret_key) == secret_value
    
    # Verify that when _save_to_database is called, the value is encrypted
    mock_save_db.assert_called_once()
    # The first arg of the first call is the config data dict
    saved_config_data = mock_save_db.call_args[0][0] 
    
    assert saved_config_data['plex']['token'].startswith("enc:")
    assert saved_config_data['plex']['token'] != secret_value

# --- Tests for Utility Methods ---

def test_is_configured(live_cm: ConfigManager):
    """Test the is_configured logic."""
    # Initially, it's not configured
    assert live_cm.is_configured() is False

    # Configure the required fields
    live_cm.set("spotify.client_id", "sid")
    live_cm.set("spotify.client_secret", "sec")
    live_cm.set("plex.base_url", "http://server")
    live_cm.set("plex.token", "tok")
    live_cm.set("soulseek.slskd_url", "http://slsk")
    
    # It should now be configured
    assert live_cm.is_configured() is True
    
    # Test with Jellyfin as active server
    live_cm.set("active_media_server", "jellyfin")
    assert live_cm.is_configured() is False # Jellyfin is not configured
    
    live_cm.set("jellyfin.base_url", "http://jelly")
    live_cm.set("jellyfin.api_key", "key")
    assert live_cm.is_configured() is True