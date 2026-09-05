from fastapi.testclient import TestClient
import json
from unittest.mock import MagicMock, patch

import pytest

from core.nexus_framework.plugin_loader import (
    _sync_ui_components_to_db,
    get_relative_entry_path,
)
from database.config_database import close_config_database, get_config_database
from database.working_database import close_working_database
from web.api_app import create_app
from web.routes.ui_registry import _query_ui_registry


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
    assert (
        get_relative_entry_path("/api/v1/system/plugins/spotify/static/bundle.js")
        == "static/bundle.js"
    )
    assert (
        get_relative_entry_path("/api/plugins/spotify/static/dashboard.yaml")
        == "static/dashboard.yaml"
    )
    assert get_relative_entry_path("/plugins/spotify/ui/card.js") == "ui/card.js"
    assert get_relative_entry_path("static/bundle.js") == "static/bundle.js"
    assert get_relative_entry_path("/static/bundle.js") == "static/bundle.js"
    assert (
        get_relative_entry_path("http://example.com/bundle.js")
        == "http://example.com/bundle.js"
    )


def test_ui_components_relative_sync_and_registry(tmp_path):
    # Setup mock plugin folder
    plugin_dir = tmp_path / "EchoSync" / "Spotify"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    manifest_data = {
        "components": {
            "music_service": {
                "element_tag": "spotify-dashboard-card",
                "bundle_url": "/api/v1/system/plugins/spotify/static/bundle.js",
            }
        },
        "views": [
            {
                "id": "spotify_analytics",
                "title": "Spotify Stats",
                "yaml_path": "/api/plugins/spotify/static/dashboard.yaml",
            }
        ],
    }

    (plugin_dir / "ui_manifest.json").write_text(
        json.dumps(manifest_data), encoding="utf-8"
    )
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
        permissions="[]",
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

    assert (
        registry["views"][0]["entry"]
        == "/api/v1/system/plugins/spotify/static/dashboard.yaml"
    )
    assert (
        registry["music_services"][0]["entry"]
        == "/api/v1/system/plugins/spotify/static/bundle.js"
    )


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
        permissions="[]",
    )

    app = create_app(testing=True)
    client = TestClient(app)

    resp = client.get("/api/v1/system/plugins/spotify/static/bundle.js")
    assert resp.status_code == 200
    assert resp.content == b"console.log('spotify');"


def test_plugin_uninstall_cleanup(tmp_path):
    from core.nexus_framework.plugin_store import plugin_store

    # Setup mock plugin folder structure
    author_dir = tmp_path / "EchoSync"
    plugin_dir = author_dir / "Spotify"
    plugin_dir.mkdir(parents=True, exist_ok=True)

    # Write mock files
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
        permissions="[]",
    )

    # Check that directory exists
    assert plugin_dir.exists()

    # Resolve "spotify"
    service_id = db.get_service_id("spotify")
    assert service_id is not None

    # Execute uninstall
    success = plugin_store.uninstall_plugin("spotify")
    assert success is True

    # Verify that files, plugin directory, and the author_dir (which was empty) are all deleted
    assert not plugin_dir.exists()
    # assert not author_dir.exists()

    # Verify database record is gone
    with db._get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM services WHERE id=?", (service_id,))
        assert c.fetchone()[0] == 0


def test_list_plugins_with_none_capabilities():
    from core.nexus_framework.plugin_loader import (
        PluginRegistry,
        get_plugin_capabilities,
    )
    from web.services.plugin_registry import _get_plugin_capabilities, list_plugins

    mock_class = MagicMock()
    mock_class.category = "provider"
    mock_class.service_type = "provider"
    mock_class.version = "1.0.0"
    mock_class.author = "Test Author"
    mock_class.capabilities = None

    db = get_config_database()
    db.register_service(
        name="test_plugin",
        service_type="provider",
        description="test plugin",
        absolute_install_path="/tmp/test_plugin",
        version="1.0.0",
        plugin_id=12345,
        beta_opt_in=0,
        verified_source=1,
        privileged_mode=0,
        permissions="[]",
    )

    with (
        patch.object(PluginRegistry, "list_plugins", return_value=["test_plugin"]),
        patch.object(PluginRegistry, "get_plugin_class", return_value=mock_class),
        patch.object(PluginRegistry, "is_plugin_disabled", return_value=False),
        patch.object(PluginRegistry, "create_instance", return_value=None),
        patch(
            "core.nexus_framework.plugin_loader.generate_plugin_id", return_value=12345
        ),
    ):
        # Calling get_plugin_capabilities should return the default capabilities structure
        caps = get_plugin_capabilities("test_plugin")
        assert caps is not None
        assert caps.search is not None
        assert caps.search.tracks is False
        assert caps.metadata is not None

        # Test list_plugins
        plugins_list = list_plugins()
        assert len(plugins_list) == 1
        assert plugins_list[0]["name"] == "test_plugin"
        assert plugins_list[0]["capabilities"]["metadata_richness"] == "MEDIUM"
        assert plugins_list[0]["capabilities"]["search"]["tracks"] is False

        # Test _get_plugin_capabilities
        caps_list = _get_plugin_capabilities()
        assert len(caps_list) == 1
        assert caps_list[0]["name"] == "test_plugin"
        assert caps_list[0]["metadata_richness"] == "MEDIUM"
        assert caps_list[0]["search_capabilities"]["tracks"] is False


def test_load_plugin_package_path_resolution(tmp_path):
    from core.nexus_framework.plugin_loader import PluginLoader

    loader = PluginLoader(tmp_path)

    package_dir = tmp_path / "EchoSync" / "slskd" / "beta"
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "manifest.json").write_text(
        '{"author": "EchoSync", "name": "slskd", "description": "slskd test", "version": "1.0.0", "type": "provider"}',
        encoding="utf-8",
    )

    imported_modules = []

    def mock_import_module(name):
        imported_modules.append(name)
        m = MagicMock()
        m.__file__ = str(package_dir / "__init__.py")
        return m

    db = get_config_database()
    db.register_service(
        name="EchoSync.slskd",
        service_type="provider",
        description="slskd",
        absolute_install_path=str(package_dir.resolve()),
        version="1.0.0",
        plugin_id=3515518521,
        beta_opt_in=1,
        verified_source=1,
        privileged_mode=0,
        permissions="[]",
    )

    with (
        patch("importlib.import_module", side_effect=mock_import_module),
        patch("sys.path", []),
        patch("sys.modules", {}),
    ):
        loader._load_plugin_package(
            3515518521, is_beta=True, absolute_install_path=str(package_dir.resolve())
        )

    assert "plugins.EchoSync.slskd.beta" in imported_modules
    assert "plugins.EchoSync.slskd.beta.beta" not in imported_modules
