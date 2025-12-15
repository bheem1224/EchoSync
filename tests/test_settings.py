import os
import json
import pytest
from unittest.mock import patch, mock_open
from config.settings import ConfigManager, SECRETS

from cryptography.fernet import Fernet

@pytest.fixture
def mock_config_manager(mocker):
    """Fixture to create a ConfigManager with mocked file and db interactions."""
    # Generate a valid Fernet key for testing
    valid_key = Fernet.generate_key()

    # Mock file operations
    mocker.patch("pathlib.Path.exists", return_value=False)
    mocker.patch("builtins.open", mock_open())
    mocker.patch("os.getenv", return_value=None)
    mocker.patch("pathlib.Path.chmod")

    # Mock database operations
    mocker.patch("sqlite3.connect")

    # Mock the IO methods at initialization
    mocker.patch.object(ConfigManager, "_load_from_database", return_value=None)
    mocker.patch.object(ConfigManager, "_load_from_config_file", return_value=None)

    # Patch the entire encryption initialization
    mocker.patch.object(ConfigManager, "_initialize_encryption")

    # Initialize ConfigManager
    cm = ConfigManager()
    
    # Manually set the cipher with our valid key
    cm.cipher = Fernet(valid_key)
    
    return cm

def test_initialization(mock_config_manager: ConfigManager):
    """Test that the ConfigManager initializes."""
    assert mock_config_manager is not None
    assert mock_config_manager.config_data is not None
    assert mock_config_manager.cipher is not None

def test_encryption_decryption(mock_config_manager: ConfigManager):
    """Test the internal encryption and decryption methods."""
    original_value = "my_secret_password"
    encrypted_value = mock_config_manager._encrypt_value(original_value)

    assert isinstance(encrypted_value, str)
    assert encrypted_value.startswith("enc:")
    assert encrypted_value != original_value

    decrypted_value = mock_config_manager._decrypt_value(encrypted_value)
    assert decrypted_value == original_value

def test_set_and_get_secret(mock_config_manager: ConfigManager):
    """Test setting and getting a secret value, ensuring it's encrypted and decrypted."""
    # We patch _save_config to prevent it from running, as we only want to test the in-memory logic here.
    with patch.object(mock_config_manager, '_save_config') as mock_save:
        secret_key = "spotify.client_secret"
        secret_value = "my_spotify_secret"

        # Set the secret value
        mock_config_manager.set(secret_key, secret_value)

        # The value in config_data should be the raw (unencrypted) value for live session
        keys = secret_key.split('.')
        temp_val = mock_config_manager.config_data
        for k in keys:
            temp_val = temp_val[k]
        assert temp_val == secret_value

        # The get method should return the decrypted (original) value
        retrieved_value = mock_config_manager.get(secret_key)
        assert retrieved_value == secret_value
        
        # Ensure that save was called
        mock_save.assert_called_once()

def test_traverse_and_transform_encryption(mock_config_manager: ConfigManager):
    """Test the traversal function for encryption."""
    sample_config = {
        "spotify": {"client_id": "my_id", "client_secret": "my_secret"},
        "plex": {"token": "plex_token"},
        "settings": {"audio_quality": "flac"}
    }
    
    encrypted_config = mock_config_manager._traverse_and_transform(sample_config, mock_config_manager._encrypt_value, SECRETS)
    
    # Check that secrets are encrypted
    assert encrypted_config["spotify"]["client_secret"].startswith("enc:")
    assert encrypted_config["plex"]["token"].startswith("enc:")
    
    # Check that non-secrets are untouched
    assert encrypted_config["spotify"]["client_id"].startswith("enc:") # client_id is also a secret
    assert encrypted_config["settings"]["audio_quality"] == "flac"

def test_save_to_database_encrypts_secrets(mock_config_manager: ConfigManager, mocker):
    """Verify that data sent to the database is encrypted."""
    # Get a fresh mock for just the db connection in this test
    mock_conn = mocker.patch("sqlite3.connect")
    mock_cursor = mock_conn.return_value.cursor.return_value

    sample_config = {
        "spotify": {"client_id": "id", "client_secret": "secret"},
        "settings": {"audio_quality": "flac"}
    }

    # Call the save method directly
    mock_config_manager._save_to_database(sample_config)
    
    # Verify the data passed to the database was a JSON string with encrypted values
    saved_json_str = mock_cursor.execute.call_args[0][1][0]
    saved_data = json.loads(saved_json_str)
    
    assert saved_data["spotify"]["client_id"].startswith("enc:")
    assert saved_data["spotify"]["client_secret"].startswith("enc:")
    assert saved_data["settings"]["audio_quality"] == "flac"
