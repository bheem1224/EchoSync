"""
Unit tests for Plugin Update Channel Resolution & Permission Seeding.
"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.matching_engine.echo_sync_track import (
    DownloadStatus,
    EchosyncTrack,
    QualityTag,
    Track,
)
from core.nexus_framework.permissions import (
    DEFAULT_BASE_PERMISSIONS,
    SAFE_BASE_SCOPES,
    seed_base_permissions,
)
from core.nexus_framework.plugin_SDK import (
    check_plugin_permission,
    sdk,
)
from core.nexus_framework.plugin_store import PluginStore
from core.plugins.sdk import compute_plugin_crc32
from core.settings import config_manager
from database.config_database import (
    close_config_database,
    get_config_database,
)
from database.working_database import (
    close_working_database,
    get_working_database,
)


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Sets up an isolated SQLite test database and mock plugins environment."""
    close_config_database()
    close_working_database()

    config_db_path = tmp_path / "config.db"
    working_db_path = tmp_path / "working.db"
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)

    os.makedirs(tmp_path / "data/plugins/data", exist_ok=True)

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
    monkeypatch.setattr(config_manager, "get_plugins_dir", lambda: plugins_dir)
    monkeypatch.setattr(config_manager, "plugins_path", plugins_dir)

    db_config = get_config_database()
    db_working = get_working_database()

    try:
        yield {
            "tmp_path": tmp_path,
            "plugins_dir": plugins_dir,
            "config_db": db_config,
            "working_db": db_working,
            "monkeypatch": monkeypatch,
        }
    finally:
        close_config_database()
        close_working_database()


# ---------------------------------------------------------------------------
# 1. Compatibility Shim Tests
# ---------------------------------------------------------------------------


def test_legacy_echo_sync_track_shim():
    """Verify that core.matching_engine.echo_sync_track successfully re-exports canonical symbols."""
    assert Track is EchosyncTrack
    assert DownloadStatus.COMPLETE.value == "complete"
    assert QualityTag.FLAC_24BIT.value == "FLAC 24-bit"

    t = Track(raw_title="Test Track", artist_name="Test Artist", album_title="Test Album")
    assert t.raw_title == "Test Track"


# ---------------------------------------------------------------------------
# 2. Permission Auto-Seeding & Evaluation Tests
# ---------------------------------------------------------------------------


def test_seed_base_permissions_utility():
    """Verify seed_base_permissions helper appends SAFE_BASE_SCOPES to empty or existing permissions."""
    seeded_empty = seed_base_permissions([])
    assert "database.read_library" in seeded_empty
    assert "metadata.read" in seeded_empty

    seeded_existing = seed_base_permissions(["network_domains"])
    assert "network_domains" in seeded_existing
    assert "database.read_library" in seeded_existing
    assert "metadata.read" in seeded_existing

    # Dictionary input normalization
    seeded_dict = seed_base_permissions({"database": {"mutate_aliases": True}})
    assert "database.mutate_aliases" in seeded_dict
    assert "database.read_library" in seeded_dict
    assert "metadata.read" in seeded_dict


def test_check_plugin_permission_supports_list_and_dict(isolated_env):
    """Verify check_plugin_permission correctly evaluates permissions in both list and dict formats from services table."""
    db = isolated_env["config_db"]
    p_id_list = 1111111111
    p_id_dict = 2222222222

    # 1. List format in DB
    db.register_service(
        name="EchoSync.list_plugin",
        service_type="provider",
        description="Test List Plugin",
        plugin_id=p_id_list,
        version="1.0.0",
        permissions=json.dumps(["database.read_library", "metadata.read"]),
    )

    # 2. Dict format in DB
    db.register_service(
        name="EchoSync.dict_plugin",
        service_type="provider",
        description="Test Dict Plugin",
        plugin_id=p_id_dict,
        version="1.0.0",
        permissions=json.dumps({"database": {"read_library": True}, "metadata": {"read": True}}),
    )

    # Check list format plugin
    assert check_plugin_permission("EchoSync.list_plugin", "database.read_library") is True
    assert check_plugin_permission("EchoSync.list_plugin", "metadata.read") is True
    assert check_plugin_permission("EchoSync.list_plugin", "database.mutate_aliases") is False

    # Check dict format plugin
    assert check_plugin_permission("EchoSync.dict_plugin", "database.read_library") is True
    assert check_plugin_permission("EchoSync.dict_plugin", "metadata.read") is True
    assert check_plugin_permission("EchoSync.dict_plugin", "database.mutate_aliases") is False


def test_reconcile_services_auto_seeds_missing_base_permissions(isolated_env):
    """Verify reconcile_services backfills SAFE_BASE_SCOPES into services without base permissions."""
    db = isolated_env["config_db"]
    plugins_dir = isolated_env["plugins_dir"]

    # Setup a physical plugin on disk with empty permissions in manifest
    author_dir = plugins_dir / "EchoSync"
    plugin_dir = author_dir / "spotify"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    manifest_data = {
        "id": "EchoSync.spotify",
        "name": "Spotify",
        "version": "2.4.3-beta.98",
        "permissions": {},
    }
    (plugin_dir / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")

    crc32_id = compute_plugin_crc32("EchoSync.spotify")

    # Register in DB with empty permissions
    db.register_service(
        name="Spotify",
        service_type="provider",
        description="Spotify",
        plugin_id=crc32_id,
        version="2.4.3-beta.98",
        permissions="{}",
    )

    # Run reconcile_services
    from core.nexus_framework.plugin_loader import PluginLoader

    loader = PluginLoader(isolated_env["tmp_path"])
    loader.reconcile_services()

    # Verify that config.db row now contains SAFE_BASE_SCOPES
    conn = db._open_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT permissions FROM services WHERE plugin_id=?", (crc32_id,))
        row = c.fetchone()
        assert row is not None
        perms = json.loads(row[0])
        assert "database.read_library" in perms
        assert "metadata.read" in perms
    finally:
        conn.close()

    # Verify check_plugin_permission now succeeds for EchoSync.spotify
    assert check_plugin_permission("EchoSync.spotify", "database.read_library") is True


# ---------------------------------------------------------------------------
# 3. Tri-State Channel Resolution & Artifact Resolution Tests
# ---------------------------------------------------------------------------


def test_tri_state_channel_resolution(isolated_env):
    """
    Verify Tri-State preference hierarchy:
    1) Explicit request param (channel / target_version)
    2) services.beta_opt_in
    3) Global config_manager ui.beta_plugin_ui
    """
    db = isolated_env["config_db"]
    store = PluginStore()
    plugin_crc = compute_plugin_crc32("EchoSync.plex")

    # Register plugin with beta_opt_in = 0 (stable override in DB)
    db.register_service(
        name="EchoSync.plex",
        service_type="provider",
        description="Plex",
        plugin_id=plugin_crc,
        version="2.4.3-beta.98",
        beta_opt_in=0,
    )

    mock_plugin_info = {
        "id": "EchoSync.plex",
        "name": "EchoSync.plex",
        "version": "2.4.2",
        "beta_version": "2.4.3-beta.99",
        "download_url": "https://raw.githubusercontent.com/bheem1224/EchoSync/main/plugins/EchoSync/plex/releases/v2.4.2.zip",
        "beta_url": "https://raw.githubusercontent.com/bheem1224/EchoSync/main/plugins/EchoSync/plex/beta.zip",
    }

    with patch.object(store, "get_all_store_plugins", return_value=[mock_plugin_info]):
        with patch.object(store, "download_plugin", return_value=True) as mock_download:
            # Case 1: Explicit target_version containing '-beta' forces beta channel despite beta_opt_in=0
            store.update_plugin(plugin_crc, target_version="2.4.3-beta.99")
            mock_download.assert_called_with(
                mock_plugin_info,
                channel="beta",
                force_consent=False,
                is_update=True,
                target_plugin_id=plugin_crc,
            )

        with patch.object(store, "download_plugin", return_value=True) as mock_download:
            # Case 2: Explicit channel='beta' forces beta channel
            store.update_plugin(plugin_crc, channel="beta")
            mock_download.assert_called_with(
                mock_plugin_info,
                channel="beta",
                force_consent=False,
                is_update=True,
                target_plugin_id=plugin_crc,
            )

        with patch.object(store, "download_plugin", return_value=True) as mock_download:
            # Case 3: No explicit channel or version -> uses beta_opt_in=0 -> 'stable'
            store.update_plugin(plugin_crc)
            mock_download.assert_called_with(
                mock_plugin_info,
                channel="stable",
                force_consent=False,
                is_update=True,
                target_plugin_id=plugin_crc,
            )

    # Change beta_opt_in to 1 in DB
    conn = db._open_connection()
    try:
        conn.execute("UPDATE services SET beta_opt_in = 1 WHERE plugin_id=?", (plugin_crc,))
        conn.commit()
    finally:
        conn.close()

    with patch.object(store, "get_all_store_plugins", return_value=[mock_plugin_info]):
        with patch.object(store, "download_plugin", return_value=True) as mock_download:
            # Case 4: With beta_opt_in=1 and no explicit params -> resolves to 'beta'
            store.update_plugin(plugin_crc)
            mock_download.assert_called_with(
                mock_plugin_info,
                channel="beta",
                force_consent=False,
                is_update=True,
                target_plugin_id=plugin_crc,
            )


def test_download_plugin_beta_does_not_fallback_to_stable(isolated_env):
    """Verify that when downloading channel='beta', it targets beta_url / beta.zip and does not fallback to stable."""
    store = PluginStore()
    plugin_crc = compute_plugin_crc32("EchoSync.plex")

    plugin_info = {
        "id": "EchoSync.plex",
        "name": "EchoSync.plex",
        "version": "2.4.2",
        "download_url": "https://raw.githubusercontent.com/bheem1224/EchoSync/main/plugins/EchoSync/plex/releases/v2.4.2.zip",
        # Note: beta_url omitted to test fallback to {base_url}/beta.zip
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 404

    with patch("core.request_manager.RequestManager.get", return_value=mock_resp) as mock_get:
        # download_plugin for beta channel
        success = store.download_plugin(plugin_info, channel="beta", target_plugin_id=plugin_crc)
        assert success is False
        # Verify it requested https://raw.githubusercontent.com/bheem1224/EchoSync/main/plugins/EchoSync/plex/beta.zip
        assert mock_get.call_count == 1
        called_url = mock_get.call_args[0][0]
        assert called_url.endswith("beta.zip")
        assert "releases/v2.4.2.zip" not in called_url


def test_spotify_cache_manager_database_connection_with_seeded_permissions(isolated_env):
    """Verify that Spotify acquires database engine without raising lacks permissions.database.read_library."""
    db = isolated_env["config_db"]
    crc32_id = compute_plugin_crc32("EchoSync.spotify")
    db.register_service(
        name="EchoSync.spotify",
        service_type="provider",
        description="Spotify",
        plugin_id=crc32_id,
        version="2.4.3-beta.98",
        permissions=json.dumps(["database.read_library", "metadata.read"]),
    )

    with patch.object(sdk, "_get_plugin_id", return_value="EchoSync.spotify"):
        engine = sdk.get_database_connection(write_access=True)
        assert engine is not None
