import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from database.config_database import get_config_database, close_config_database
from database.working_database import close_working_database
from core.nexus_framework.plugin_loader import _sync_ui_components_to_db, get_relative_entry_path
from web.routes.ui_registry import _query_ui_registry
from web.api_app import create_app


@pytest.fixture(autouse=True)
def setup_temp_db(tmp_path, monkeypatch):
    # Close singletons
    close_config_database()
    close_working_database()

    config_db_path = tmp_path / "config.db"
    working_db_path = tmp_path / "working.db"
    
    config_uri = f"sqlite:///{config_db_path.as_posix()}"
    working_uri = f"sqlite:///{working_db_path.as_posix()}"
    
    from core.settings import config_manager
    original_get = config_manager.get
    def mock_get(key, default=None):
        if key == "database.config_uri":
            return config_uri
        if key == "database.working_uri":
            return working_uri
        return original_get(key, default)
        
    monkeypatch.setattr(config_manager, "get", mock_get)
    monkeypatch.setattr(config_manager, "get_plugins_dir", lambda: tmp_path)
    monkeypatch.setattr(config_manager, "plugins_path", tmp_path)

    # Mock the plugin state table query inside cleanup jobs during boot to avoid sqlite missing table error
    with patch("sqlalchemy.engine.base.Engine.connect", MagicMock()):
        yield tmp_path

    close_config_database()
    close_working_database()


def test_get_relative_entry_path():
    assert get_relative_entry_path("/api/system/plugins/spotify/static/bundle.js") == "static/bundle.js"
    assert get_relative_entry_path("/api/plugins/spotify/static/dashboard.yaml") == "static/dashboard.yaml"
    assert get_relative_entry_path("/plugins/spotify/ui/card.js") == "ui/card.js"
    assert get_relative_entry_path("static/bundle.js") == "static/bundle.js"
    assert get_relative_entry_path("/static/bundle.js") == "static/bundle.js"
    assert get_relative_entry_path("http://example.com/bundle.js") == "http://example.com/bundle.js"


def test_ui_components_relative_sync_and_registry(tmp_path):
    # Setup mock plugin folder
    plugin_dir = tmp_path / "EchoSync" / "Spotify"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    
    manifest_data = {
        "components": {
            "music_service": {
                "element_tag": "spotify-dashboard-card",
                "bundle_url": "/api/system/plugins/spotify/static/bundle.js"
            }
        },
        "views": [
            {
                "id": "spotify_analytics",
                "title": "Spotify Stats",
                "yaml_path": "/api/plugins/spotify/static/dashboard.yaml"
            }
        ]
    }
    
    (plugin_dir / "ui_manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")
    (plugin_dir / "manifest.json").write_text("{}", encoding="utf-8")

    db = get_config_database()
    db.register_service(
        name="Spotify",
        service_type="provider",
        description="Spotify provider",
        absolute_install_path=str(plugin_dir.resolve()),
        version="2.4.2",
        plugin_id=239116200,
        beta_opt_in=0,
        verified_source=1,
        privileged_mode=0,
        permissions="[]"
    )

    # Sync to DB
    _sync_ui_components_to_db(239116200, str(plugin_dir.resolve()))

    # Verify stored in DB is relative
    with db._get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT tag_name, entry_path FROM ui_components ORDER BY tag_name")
        rows = c.fetchall()
        assert len(rows) == 2
        
        # es-view-spotify_analytics
        assert rows[0]["tag_name"] == "es-view-spotify_analytics"
        assert rows[0]["entry_path"] == "static/dashboard.yaml"
        
        # spotify-dashboard-card
        assert rows[1]["tag_name"] == "spotify-dashboard-card"
        assert rows[1]["entry_path"] == "static/bundle.js"

    # Query registry (simulating UI discovery)
    registry = _query_ui_registry()
    assert "views" in registry
    assert "music_services" in registry

    assert registry["views"][0]["entry"] == "/api/system/plugins/spotify/static/dashboard.yaml"
    assert registry["music_services"][0]["entry"] == "/api/system/plugins/spotify/static/bundle.js"


def test_static_serving(tmp_path):
    # Setup mock plugin folder with static asset
    plugin_dir = tmp_path / "EchoSync" / "Spotify"
    static_dir = plugin_dir / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    
    (static_dir / "bundle.js").write_text("console.log('spotify');", encoding="utf-8")
    (plugin_dir / "manifest.json").write_text("{}", encoding="utf-8")

    db = get_config_database()
    db.register_service(
        name="Spotify",
        service_type="provider",
        description="Spotify provider",
        absolute_install_path=str(plugin_dir.resolve()),
        version="2.4.2",
        plugin_id=239116200,
        beta_opt_in=0,
        verified_source=1,
        privileged_mode=0,
        permissions="[]"
    )

    app = create_app(testing=True)
    client = app.test_client()

    resp = client.get("/api/system/plugins/spotify/static/bundle.js")
    assert resp.status_code == 200
    assert resp.data == b"console.log('spotify');"
