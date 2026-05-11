import pytest
import zipfile
import io
import json
import os
import shutil
import binascii
from pathlib import Path
from unittest.mock import MagicMock, patch
from core.plugin_loader import PluginLoader
from core.plugin_store import PluginStore
from database.config_database import ConfigDatabase

@pytest.fixture
def temp_plugins_dir(tmp_path):
    d = tmp_path / "plugins"
    d.mkdir()
    return d

@pytest.fixture
def mock_db(tmp_path):
    db_path = tmp_path / "config.db"
    db = ConfigDatabase(str(db_path))
    # Schema is initialized by ConfigDatabase constructor
    return db

PROJECT_ROOT = Path(__file__).parent.parent.parent

@pytest.fixture
def plugin_loader(temp_plugins_dir):
    with patch('core.settings.config_manager.get_plugins_dir', return_value=str(temp_plugins_dir)):
        loader = PluginLoader(PROJECT_ROOT)
        return loader

@pytest.fixture
def plugin_store(temp_plugins_dir):
    with patch('core.settings.config_manager.get_plugins_dir', return_value=str(temp_plugins_dir)):
        store = PluginStore()
        return store

def create_plugin_zip(manifest_data):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr("manifest.json", json.dumps(manifest_data))
        z.writestr("__init__.py", "from core.plugin_SDK import PluginBase\nclass ProviderClass(PluginBase):\n    pass")
    return buf.getvalue()

def test_plugin_install_nested_path(plugin_store, temp_plugins_dir, mock_db):
    """Test that EchoSync.tidal installs into EchoSync/tidal/ folder."""
    plugin_info = {
        "id": "EchoSync.tidal",
        "name": "Tidal",
        "version": "1.0.0",
        "download_url": "http://example.com/tidal.zip"
    }
    
    zip_content = create_plugin_zip({
        "id": "EchoSync.tidal",
        "name": "Tidal",
        "version": "1.0.0"
    })
    
    with patch('core.request_manager.RequestManager.get') as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = zip_content
        mock_get.return_value = mock_resp
        
        with patch('database.config_database.get_config_database', return_value=mock_db):
            success = plugin_store.download_plugin(plugin_info)
            
            assert success is True
            # Verify folder structure
            expected_path = temp_plugins_dir / "EchoSync" / "tidal"
            assert expected_path.exists()
            assert (expected_path / "manifest.json").exists()
            
            # Verify DB state
            with mock_db._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT namespace, plugin_id FROM services WHERE name='EchoSync.tidal'")
                row = c.fetchone()
                assert row is not None
                assert row[0] == "EchoSync.tidal"
                # Check 32-bit CRC32 ID
                expected_id = binascii.crc32(b"tidal") & 0xFFFFFFFF
                assert row[1] == expected_id

def test_plugin_loader_discovery(plugin_loader, temp_plugins_dir):
    """Test that PluginLoader discovers plugins in nested folders."""
    # Create a nested plugin manually
    plugin_path = temp_plugins_dir / "EchoSync" / "spotify"
    plugin_path.mkdir(parents=True)
    with open(plugin_path / "manifest.json", "w") as f:
        json.dump({"id": "EchoSync.spotify", "version": "1.2.3"}, f)
    with open(plugin_path / "__init__.py", "w") as f:
        f.write("pass")

    from core.plugin_loader import get_all_plugins
    empty_dir = temp_plugins_dir / "empty_core"
    empty_dir.mkdir()
    
    with patch.dict(os.environ, {"ECHOSYNC_CORE_PLUGINS_DIR": str(empty_dir)}):
        with patch('core.settings.config_manager.get_plugins_dir', return_value=str(temp_plugins_dir)):
            plugins = get_all_plugins()
            
            found = [p for p in plugins if p['folder_name'] == 'EchoSync/spotify']
            assert len(found) == 1
            # In test, manifest ID is provided as EchoSync.spotify
            assert found[0]['id'] == 'EchoSync.spotify'

def test_hotswap_id_resolution(plugin_loader, mock_db, temp_plugins_dir):
    """Test that reload_plugin correctly resolves the 32-bit integer ID."""
    plugin_id_str = "EchoSync.tidal"
    plugin_id_int = binascii.crc32(b"tidal") & 0xFFFFFFFF
    
    # 1. Manually register in DB
    with mock_db._get_connection() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO services (name, namespace, plugin_id) VALUES (?, ?, ?)",
                  (plugin_id_str, plugin_id_str, plugin_id_int))
        conn.commit()
    
    # 2. Create the plugin folder
    plugin_path = temp_plugins_dir / "EchoSync" / "tidal"
    plugin_path.mkdir(parents=True)
    with open(plugin_path / "manifest.json", "w") as f:
        json.dump({"id": plugin_id_str, "version": "2.0.0"}, f)
    with open(plugin_path / "__init__.py", "w") as f:
        f.write("from core.plugin_SDK import PluginBase\nclass ProviderClass(PluginBase):\n    pass")

    with patch('database.config_database.get_config_database', return_value=mock_db):
        with patch.object(plugin_loader, '_load_plugin_package') as mock_load:
            plugin_loader.reload_plugin(plugin_id_int)
            
            # Verify it resolved to the correct folder and called loader
            mock_load.assert_called_once()
            # Arguments: name, parent_dir_name, source_type...
            assert mock_load.call_args[0][0] == "EchoSync/tidal"

def test_version_stamping_on_load(plugin_loader, mock_db, temp_plugins_dir):
    """Test that the services table is updated with the version during loading."""
    plugin_id_str = "EchoSync.version_test"
    
    # 1. Register in DB
    mock_db.register_service(
        name=plugin_id_str,
        display_name="Version Test",
        service_type="provider",
        description="test",
        namespace=plugin_id_str,
        plugin_id=12345
    )
        
    # 2. Create the plugin folder and manifest
    plugin_path = temp_plugins_dir / "EchoSync" / "version_test"
    plugin_path.mkdir(parents=True)
    manifest_data = {"id": plugin_id_str, "version": "3.1.4"}
    with open(plugin_path / "manifest.json", "w") as f:
        json.dump(manifest_data, f)
    with open(plugin_path / "__init__.py", "w") as f:
        f.write("pass")

    # Mocking the actual module loading
    with patch('importlib.import_module') as mock_import:
        mock_module = MagicMock()
        class MockProvider:
            pass
        mock_module.ProviderClass = MockProvider
        mock_import.return_value = mock_module
        
        with patch('database.config_database.get_config_database', return_value=mock_db):
            # We must ensure PluginLoader.app_root is the parent of temp_plugins_dir for path resolution
            plugin_loader.app_root = temp_plugins_dir.parent
            plugin_loader.plugins_dir = temp_plugins_dir
            
            # Simulate _load_plugin_package which calls _update_db_version
            plugin_loader._load_plugin_package("EchoSync/version_test", "plugins", "community")
            
            # Verify version was stamped
            with mock_db._get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT version, namespace, name FROM services WHERE name=?", (plugin_id_str,))
                row = c.fetchone()
                assert row is not None, f"Service {plugin_id_str} not found in database"
                assert row[0] == "3.1.4", f"Version mismatch: expected 3.1.4, got {row[0]} (namespace: {row[1]}, name: {row[2]})"
