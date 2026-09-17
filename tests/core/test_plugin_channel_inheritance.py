import json
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from core.nexus_framework.plugin_loader import (
    compute_plugin_crc32,
    resolve_plugin_directory,
)
from database.models import Service
from web.routes.plugins import (
    ChannelPreference,
    _channel_value,
    set_plugin_channel_preference,
)


def test_channel_value_conversion():
    """Verify conversion of various channel inputs to (canonical_str, beta_opt_int)."""
    assert _channel_value("inherit") == ("inherit", None)
    assert _channel_value(ChannelPreference.INHERIT) == ("inherit", None)
    assert _channel_value(None) == ("inherit", None)

    assert _channel_value("beta") == ("beta", 1)
    assert _channel_value(ChannelPreference.BETA) == ("beta", 1)
    assert _channel_value(True) == ("beta", 1)
    assert _channel_value(1) == ("beta", 1)

    assert _channel_value("stable") == ("stable", 0)
    assert _channel_value(ChannelPreference.STABLE) == ("stable", 0)
    assert _channel_value(False) == ("stable", 0)
    assert _channel_value(0) == ("stable", 0)

    with pytest.raises(ValueError):
        _channel_value("invalid_channel")


def test_service_model_hybrid_property():
    """Verify Service ORM model maintains backward-compatible beta_opt_in property."""
    service = Service(name="TestPlugin", channel_preference="inherit")
    assert service.channel_preference == "inherit"
    assert service.beta_opt_in is None

    service.channel_preference = "beta"
    assert service.beta_opt_in == 1

    service.channel_preference = "stable"
    assert service.beta_opt_in == 0

    # Setter via beta_opt_in
    service.beta_opt_in = 1
    assert service.channel_preference == "beta"
    assert service._beta_opt_in == 1

    service.beta_opt_in = False
    assert service.channel_preference == "stable"
    assert service._beta_opt_in == 0

    service.beta_opt_in = None
    assert service.channel_preference == "inherit"
    assert service._beta_opt_in is None


def test_resolve_plugin_directory_inheritance_and_leaves(tmp_path):
    """Verify channel inheritance from global config and stripping of trailing leaves."""
    plugin_root = tmp_path / "my_plugin"
    plugin_root.mkdir()
    (plugin_root / "manifest.json").write_text(json.dumps({"id": "my_plugin", "version": "1.0.0"}))

    beta_dir = plugin_root / "beta"
    beta_dir.mkdir()
    (beta_dir / "manifest.json").write_text(json.dumps({"id": "my_plugin", "version": "2.0.0-beta"}))

    # 1. Global config = 'beta', plugin preference = 'inherit'
    with patch("core.nexus_framework.plugin_loader.config_manager.get", return_value="beta"):
        target_dir, channel = resolve_plugin_directory(
            name="my_plugin",
            channel_preference="inherit",
            absolute_install_path=str(plugin_root),
        )
        assert channel == "beta"
        assert target_dir == beta_dir

    # 2. Global config = 'stable', plugin preference = 'inherit'
    with patch("core.nexus_framework.plugin_loader.config_manager.get", return_value="stable"):
        target_dir, channel = resolve_plugin_directory(
            name="my_plugin",
            channel_preference="inherit",
            absolute_install_path=str(plugin_root),
        )
        assert channel == "root"
        assert target_dir == plugin_root

    # 3. Explicit override: global is 'stable', but plugin explicitly prefers 'beta'
    with patch("core.nexus_framework.plugin_loader.config_manager.get", return_value="stable"):
        target_dir, channel = resolve_plugin_directory(
            name="my_plugin",
            channel_preference="beta",
            absolute_install_path=str(plugin_root),
        )
        assert channel == "beta"
        assert target_dir == beta_dir

    # 4. Trailing leaf stripping: install_path points to /beta leaf, but plugin opts into 'stable'
    with patch("core.nexus_framework.plugin_loader.config_manager.get", return_value="stable"):
        target_dir, channel = resolve_plugin_directory(
            name="my_plugin",
            channel_preference="stable",
            absolute_install_path=str(beta_dir),  # trailing /beta
        )
        assert channel == "root"
        assert target_dir == plugin_root


def test_resolve_plugin_directory_plugin_json_support(tmp_path):
    """Verify plugin.json is respected alongside manifest.json per architectural directive."""
    plugin_root = tmp_path / "custom_plugin"
    plugin_root.mkdir()
    beta_dir = plugin_root / "beta"
    beta_dir.mkdir()
    (beta_dir / "plugin.json").write_text(json.dumps({"id": "custom_plugin", "version": "0.9.0-beta"}))

    target_dir, channel = resolve_plugin_directory(
        name="custom_plugin",
        channel_preference="beta",
        absolute_install_path=str(plugin_root),
    )
    assert channel == "beta"
    assert target_dir == beta_dir


def test_resolve_plugin_directory_beta_only(tmp_path):
    plugin_root = tmp_path / "beta_only"
    beta_dir = plugin_root / "beta"
    beta_dir.mkdir(parents=True)
    (beta_dir / "plugin.json").write_text(json.dumps({"id": "beta_only"}))

    target_dir, channel = resolve_plugin_directory(
        name="beta_only",
        channel_preference="stable",
        absolute_install_path=str(plugin_root),
    )

    assert target_dir == beta_dir
    assert channel == "beta"


def test_resolve_plugin_directory_root_only(tmp_path):
    plugin_root = tmp_path / "root_only"
    plugin_root.mkdir()
    (plugin_root / "plugin.json").write_text(json.dumps({"id": "root_only"}))

    target_dir, channel = resolve_plugin_directory(
        name="root_only",
        channel_preference="beta",
        absolute_install_path=str(plugin_root),
    )

    assert target_dir == plugin_root
    assert channel == "root"


def test_set_plugin_channel_preference_isolation(tmp_path):
    """Verify setting channel preference updates exactly one row without touching siblings."""
    db_file = tmp_path / "test_config.db"
    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            plugin_id INTEGER UNIQUE,
            channel_preference TEXT DEFAULT 'inherit',
            beta_opt_in INTEGER,
            is_active INTEGER DEFAULT 1
        )
    """)
    plugin_a_id = compute_plugin_crc32("plugin.alpha")
    plugin_b_id = compute_plugin_crc32("plugin.beta")

    cursor.execute(
        "INSERT INTO services (name, plugin_id, channel_preference, beta_opt_in) VALUES (?, ?, ?, ?)",
        ("plugin.alpha", plugin_a_id, "inherit", None),
    )
    cursor.execute(
        "INSERT INTO services (name, plugin_id, channel_preference, beta_opt_in) VALUES (?, ?, ?, ?)",
        ("plugin.beta", plugin_b_id, "inherit", None),
    )
    conn.commit()
    conn.close()

    mock_db = MagicMock()
    mock_db._open_connection.side_effect = lambda: sqlite3.connect(str(db_file))

    with patch("database.config_database.get_config_database", return_value=mock_db):
        res = set_plugin_channel_preference(plugin_a_id, "beta")
        assert res == {"plugin_id": plugin_a_id, "channel_preference": "beta"}

    # Verify rows in DB
    verify_conn = sqlite3.connect(str(db_file))
    verify_conn.row_factory = sqlite3.Row
    c = verify_conn.cursor()

    c.execute("SELECT plugin_id, channel_preference, beta_opt_in FROM services WHERE plugin_id=?", (plugin_a_id,))
    row_a = c.fetchone()
    assert row_a["channel_preference"] == "beta"
    assert row_a["beta_opt_in"] == 1

    # Sibling MUST NOT be modified
    c.execute("SELECT plugin_id, channel_preference, beta_opt_in FROM services WHERE plugin_id=?", (plugin_b_id,))
    row_b = c.fetchone()
    assert row_b["channel_preference"] == "inherit"
    assert row_b["beta_opt_in"] is None

    verify_conn.close()
