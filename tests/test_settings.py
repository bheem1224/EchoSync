import os
import json
import pytest
from unittest.mock import patch, mock_open, MagicMock
from core.settings import ConfigManager, SECRETS

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
    """Test loading configuration from database (with JSON as base)."""
    # With split persistence, JSON is loaded first (as non-secrets base),
    # then DB secrets merge in
    sample_db_data = {"spotify": {"client_id": "id", "client_secret": "enc:secret"}}
    
    mocker.patch.object(ConfigManager, "_load_from_database", return_value=sample_db_data)
    mocker.patch.object(ConfigManager, "_load_from_config_file", return_value=None)
    
    base_config_manager._load_config()

    # Verify data was loaded from DB
    assert base_config_manager.config_data['spotify']['client_id'] == 'id'

def test_load_config_migrates_from_file(base_config_manager: ConfigManager, mocker):
    """Test that JSON-based non-secrets are loaded and merged with defaults."""
    sample_json = {"logging": {"level": "DEBUG"}}  # Non-secret
    
    mocker.patch.object(ConfigManager, "_load_from_database", return_value=None)
    mocker.patch.object(ConfigManager, "_load_from_config_file", return_value=sample_json)
    mocker.patch.object(ConfigManager, "_save_non_secrets_to_json")  # Don't write during test

    base_config_manager._load_config()

    # Verify JSON data was merged in
    assert base_config_manager.config_data['logging']['level'] == 'DEBUG'

def test_load_config_uses_defaults(base_config_manager: ConfigManager, mocker):
    """Test that default configuration is used and saved to JSON when no config exists."""
    mocker.patch.object(ConfigManager, "_load_from_database", return_value=None)
    mocker.patch.object(ConfigManager, "_load_from_config_file", return_value=None)
    mock_save_json = mocker.patch.object(ConfigManager, "_save_non_secrets_to_json", return_value=True)

    base_config_manager._load_config()

    # Verify defaults were loaded
    assert base_config_manager.get('active_media_server') == 'plex'
    # Verify non-secrets were saved to JSON for future edits
    mock_save_json.assert_called_once()
    
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

    # Configure the required fields using multi-account structure
    live_cm.set("spotify_accounts", [
        {"id": 1, "client_id": "sid", "client_secret": "sec", "redirect_uri": "http://localhost:8008/api/spotify/callback"}
    ])
    live_cm.set("active_spotify_account_id", 1)
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

def test_spotify_multi_account_helpers(live_cm: ConfigManager):
    """Test multi-account add/update/activate/get helpers."""
    # Initially empty
    assert live_cm.get_spotify_accounts() == []
    assert live_cm.get_active_spotify_account() is None
    
    # Add first account
    acc1 = live_cm.add_spotify_account({
        'name': 'Personal',
        'client_id': 'client1',
        'client_secret': 'secret1',
        'redirect_uri': 'http://localhost:8008/api/spotify/callback'
    })
    assert acc1['id'] == 1
    assert acc1['name'] == 'Personal'
    assert live_cm.get('active_spotify_account_id') == 1  # Auto-set active
    
    # Add second account
    acc2 = live_cm.add_spotify_account({
        'name': 'Work',
        'client_id': 'client2',
        'client_secret': 'secret2',
        'redirect_uri': 'http://localhost:8008/api/spotify/callback'
    })
    assert acc2['id'] == 2
    assert live_cm.get('active_spotify_account_id') == 1  # Remains first
    
    # Get all accounts
    accounts = live_cm.get_spotify_accounts()
    assert len(accounts) == 2
    
    # Get active account
    active = live_cm.get_active_spotify_account()
    assert active['id'] == 1
    assert active['name'] == 'Personal'
    
    # Switch active account
    live_cm.set_active_spotify_account(2)
    active = live_cm.get_active_spotify_account()
    assert active['id'] == 2
    assert active['name'] == 'Work'
    
    # Update account
    updated = live_cm.update_spotify_account(2, {'refresh_token': 'new_refresh'})
    assert updated['refresh_token'] == 'new_refresh'
    assert updated['name'] == 'Work'
    
    # Get active credentials
    creds = live_cm.get_spotify_active_credentials()
    assert creds['client_id'] == 'client2'
    assert creds['refresh_token'] == 'new_refresh'
    assert creds['id'] == 2
    assert creds['name'] == 'Work'