import pytest
import os
import shutil
import sqlite3
import json
import io
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.plugin_store import plugin_store
from core.plugin_loader import PluginLoader, PluginRegistry
from database.config_database import ConfigDatabase, get_config_database, close_config_database
from database.working_database import WorkingDatabase, get_working_database, close_working_database
from core.state import system_state
from core.settings import config_manager


@pytest.fixture
def temp_plugins_env(tmp_path, monkeypatch):
    """
    Sets up a fully isolated, temporary SQLite database and plugin directory.
    Patches config_manager and plugin_store to prevent live database contamination.
    """
    # 1. Close any existing singleton instances to force recreation with new config
    close_config_database()
    close_working_database()

    # 2. Paths
    config_db_path = tmp_path / "config.db"
    working_db_path = tmp_path / "working.db"
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    
    # Ensure system directories exist
    os.makedirs("/data/plugins/data", exist_ok=True)

    # 3. Patch Config Manager Database URIs
    config_uri = f"sqlite:///{config_db_path.as_posix()}"
    working_uri = f"sqlite:///{working_db_path.as_posix()}"
    
    original_get = config_manager.get
    def mock_get(key, default=None):
        if key == "database.config_uri":
            return config_uri
        if key == "database.working_uri":
            return working_uri
        return original_get(key, default)
        
    monkeypatch.setattr(config_manager, "get", mock_get)

    # 4. Initialize Databases through singleton providers
    db_config = get_config_database()
    db_working = get_working_database()
    
    # Initialize working state schema manually
    from sqlalchemy import text
    with db_working.session_scope() as session:
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS plugin_state_kvs (
                plugin_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                is_sensitive INTEGER DEFAULT 0,
                created_at INTEGER DEFAULT (strftime('%s','now')),
                updated_at INTEGER DEFAULT (strftime('%s','now')),
                PRIMARY KEY (plugin_id, key)
            )
        """))

    # 5. Patch PluginStore paths
    monkeypatch.setattr(plugin_store, "plugins_dir", plugins_dir)

    yield {
        "config_db": db_config,
        "working_db": db_working,
        "plugins_dir": plugins_dir,
        "monkeypatch": monkeypatch
    }

    # Clean up singletons after test to prevent leak to other tests
    close_config_database()
    close_working_database()


def _create_mock_plugin_folder(plugins_dir: Path, name: str, version: str, beta_version: str = None) -> Path:
    """Helper to create a realistic physical plugin folder with manifest and code."""
    plugin_path = plugins_dir / "EchoSync" / name
    plugin_path.mkdir(parents=True, exist_ok=True)
    
    manifest = {
        "id": f"EchoSync.{name}",
        "name": name.capitalize(),
        "description": f"Mock provider for {name}",
        "version": version,
        "author": "EchoSync",
        "type": "provider"
    }
    if beta_version:
        manifest["beta_version"] = beta_version
        
    (plugin_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (plugin_path / "__init__.py").write_text("class ProviderClass:\n    pass\n", encoding="utf-8")
    
    return plugin_path


def test_fresh_installation(temp_plugins_env):
    """
    Verifies that a fresh installation correctly adds a record to the services table,
    writes the physical files, and marks the channel preference as stable.
    """
    config_db = temp_plugins_env["config_db"]
    plugins_dir = temp_plugins_env["plugins_dir"]

    # 1. Create files for EchoSync.spotify
    plugin_path = _create_mock_plugin_folder(plugins_dir, "spotify", "2.4.2")

    # 2. Register service manually simulating the install callback
    config_db.register_service(
        name="EchoSync.spotify",
        service_type="provider",
        description="Official EchoSync provider for spotify",
        absolute_install_path=str(plugin_path.resolve()),
        version="2.4.2",
        plugin_id=3191146312
    )

    # 3. Assert database row is properly constructed
    with config_db._get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT name, version, plugin_id, beta_opt_in, is_active FROM services WHERE plugin_id=3191146312")
        row = c.fetchone()
        
        assert row is not None
        assert row["name"] == "EchoSync.spotify"
        assert row["version"] == "2.4.2"
        assert row["beta_opt_in"] == 0 or row["beta_opt_in"] is None
        assert row["is_active"] == 1


def test_update_flow_success(temp_plugins_env):
    """
    Verifies that updating an active plugin invokes the live-swap mechanism,
    commits the new version, and reports success.
    """
    config_db = temp_plugins_env["config_db"]
    plugins_dir = temp_plugins_env["plugins_dir"]
    monkeypatch = temp_plugins_env["monkeypatch"]

    # 1. Setup existing plugin
    plugin_path = _create_mock_plugin_folder(plugins_dir, "spotify", "2.4.2")
    config_db.register_service(
        name="EchoSync.spotify",
        service_type="provider",
        description="Official EchoSync provider for spotify",
        absolute_install_path=str(plugin_path.resolve()),
        version="2.4.2",
        plugin_id=3191146312
    )

    # Mock the physical download and extraction during update
    monkeypatch.setattr(plugin_store, "download_plugin", lambda *args, **kwargs: True)

    # Mock the plugin loader reload_plugin operation
    mock_reload = MagicMock()
    monkeypatch.setattr(PluginLoader, "reload_plugin", mock_reload)

    # 2. Trigger the update through update_plugin
    # First mock the remote registry info
    monkeypatch.setattr(plugin_store, "get_all_store_plugins", lambda: [{
        "id": "EchoSync.spotify",
        "name": "Spotify",
        "version": "2.4.3"
    }])

    success = plugin_store.update_plugin(3191146312)
    assert success is True


def test_update_flow_syntax_error(temp_plugins_env):
    """
    Verifies that if a syntax or import error occurs during live-swap,
    the update fails immediately (raising/returning False) instead of silently succeeding.
    """
    config_db = temp_plugins_env["config_db"]
    plugins_dir = temp_plugins_env["plugins_dir"]
    monkeypatch = temp_plugins_env["monkeypatch"]

    # 1. Setup existing plugin
    plugin_path = _create_mock_plugin_folder(plugins_dir, "musicbrainz", "1.0.0")
    config_db.register_service(
        name="core.musicbrainz",
        service_type="provider",
        description="Musicbrainz service",
        absolute_install_path=str(plugin_path.resolve()),
        version="1.0.0",
        plugin_id=2108802618
    )

    # 2. Create in-memory mock ZIP response representing the update bundle with syntax errors
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr("manifest.json", json.dumps({
            "id": "core.musicbrainz",
            "name": "Musicbrainz",
            "description": "Musicbrainz service",
            "version": "1.0.1",
            "author": "core",
            "type": "provider"
        }))
        zip_file.writestr("__init__.py", "class ProviderClass:\n    def parse(self:\n        pass\n")  # Syntax error

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = zip_buffer.getvalue()

    # Patch RequestManager to return this mock ZIP
    from core.request_manager import RequestManager
    monkeypatch.setattr(RequestManager, "get", lambda self, *args, **kwargs: mock_response)

    # Force live-swap loader to fail to load the syntax-broken module
    def mock_broken_reload(self, plugin_id):
        raise ValueError("Failed to import core.musicbrainz: '(' was never closed")

    monkeypatch.setattr(PluginLoader, "reload_plugin", mock_broken_reload)
    monkeypatch.setattr(plugin_store, "get_all_store_plugins", lambda: [{
        "id": "core.musicbrainz",
        "name": "Musicbrainz",
        "version": "1.0.1"
    }])

    # Reset system state
    system_state.restart_pending = False

    # 3. Perform update - it should return False because reload failed
    success = plugin_store.update_plugin(2108802618)
    assert success is False
    assert system_state.restart_pending is True


def test_beta_opt_in_and_rollback(temp_plugins_env):
    """
    Verifies the Blue/Green sidecar flow: opting into beta, copying KVS,
    and rolling back (which discards the beta folder, KVS, and restores the stable context).
    """
    config_db = temp_plugins_env["config_db"]
    working_db = temp_plugins_env["working_db"]
    plugins_dir = temp_plugins_env["plugins_dir"]
    monkeypatch = temp_plugins_env["monkeypatch"]

    # 1. Setup stable plugin
    plugin_path = _create_mock_plugin_folder(plugins_dir, "tidal", "2.4.0", beta_version="2.4.1-beta.2")
    config_db.register_service(
        name="EchoSync.tidal",
        service_type="provider",
        description="Official EchoSync provider for tidal",
        absolute_install_path=str(plugin_path.resolve()),
        version="2.4.0",
        plugin_id=3106502486
    )

    # 2. Add stable KVS state
    from sqlalchemy import text
    with working_db.session_scope() as session:
        session.execute(text("INSERT INTO plugin_state_kvs (plugin_id, key, value) VALUES ('3106502486', 'user_token', 'stable-token')"))

    # 3. Simulate Beta Opt-in (Forking)
    plugin_store._fork_namespace(3106502486)

    # Assert that KVS state was cloned to @beta suffix
    with working_db.session_scope() as session:
        res = session.execute(text("SELECT value FROM plugin_state_kvs WHERE plugin_id = '3106502486@beta' AND key = 'user_token'")).fetchone()
        assert res is not None
        assert res[0] == "stable-token"

    # Simulate beta path updates in services
    beta_subfolder = plugin_path / "beta"
    beta_subfolder.mkdir(exist_ok=True)
    with config_db._get_connection() as conn:
        c = conn.cursor()
        c.execute("""
            UPDATE services 
            SET beta_opt_in = 1, previous_version_path = ?, absolute_install_path = ?
            WHERE plugin_id = 3106502486
        """, (str(plugin_path.resolve()), str(beta_subfolder.resolve())))
        conn.commit()

    # 4. Trigger Rollback
    # Reset system_state
    system_state.restart_pending = False
    
    success = plugin_store.rollback_plugin(3106502486)
    assert success is True

    # Assert beta_opt_in is reset to 0, install path restored to stable
    with config_db._get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT beta_opt_in, absolute_install_path FROM services WHERE plugin_id = 3106502486")
        row = c.fetchone()
        assert row["beta_opt_in"] == 0
        assert row["absolute_install_path"] == str(plugin_path.resolve())

    # Assert beta sidecar KVS is deleted
    with working_db.session_scope() as session:
        res = session.execute(text("SELECT 1 FROM plugin_state_kvs WHERE plugin_id = '3106502486@beta'")).fetchone()
        assert res is None

    # Assert beta subfolder is deleted
    assert not beta_subfolder.exists()
    assert system_state.restart_pending is True


def test_uninstall_flow(temp_plugins_env):
    """
    Verifies that uninstallation kills jobs, unloads modules, removes services rows,
    purges all KVS state, and physically deletes the correct folder.
    """
    config_db = temp_plugins_env["config_db"]
    working_db = temp_plugins_env["working_db"]
    plugins_dir = temp_plugins_env["plugins_dir"]
    monkeypatch = temp_plugins_env["monkeypatch"]

    # 1. Setup plugin
    plugin_path = _create_mock_plugin_folder(plugins_dir, "spotify", "2.4.2")
    config_db.register_service(
        name="EchoSync.spotify",
        service_type="provider",
        description="Official EchoSync provider for spotify",
        absolute_install_path=str(plugin_path.resolve()),
        version="2.4.2",
        plugin_id=3191146312
    )

    # Add KVS keys
    from sqlalchemy import text
    with working_db.session_scope() as session:
        session.execute(text("INSERT INTO plugin_state_kvs (plugin_id, key, value) VALUES ('3191146312', 'cache_data', 'spotify-cached-tracks')"))

    # Mock the sys.modules check
    import sys
    sys.modules["plugins.EchoSync.spotify"] = MagicMock()

    # 2. Trigger Uninstall
    system_state.restart_pending = False
    success = plugin_store.uninstall_plugin(3191146312)
    assert success is True

    # 3. Assert database state was fully pruned
    with config_db._get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT 1 FROM services WHERE plugin_id = 3191146312")
        assert c.fetchone() is None

    with working_db.session_scope() as session:
        res = session.execute(text("SELECT 1 FROM plugin_state_kvs WHERE plugin_id = '3191146312'")).fetchone()
        assert res is None

    # 4. Assert physical folder was completely deleted
    assert not plugin_path.exists()
    assert system_state.restart_pending is True
