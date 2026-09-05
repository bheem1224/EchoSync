"""
Unit tests for Cold vs. Hot Configuration Migration and Boundary Realignment.

Validates:
- config.db schema initialization and default seed values for system_settings.
- config.db CRUD for system_settings and relational quality_profiles.
- Transactional migration from legacy config.json to config.db and cold sanitization.
- ConfigManager transparent read/write routing (hot -> config.db, cold -> config.json).
- web.routes.system PATCH /settings allowlist including library_import.
- core.path_formatter hot retrieval from config.db.
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import web.routes.system as system_route_module
from core.settings import (
    COLD_BOOTSTRAP_KEYS,
    ConfigManager,
    migrate_legacy_json_to_db,
)
from database.config_database import ConfigDatabase
from web.auth import require_auth


@pytest.fixture
def temp_dirs():
    tmp_config = tempfile.mkdtemp(prefix="echosync_test_cfg_")
    tmp_data = tempfile.mkdtemp(prefix="echosync_test_data_")
    yield Path(tmp_config), Path(tmp_data)
    shutil.rmtree(tmp_config, ignore_errors=True)
    shutil.rmtree(tmp_data, ignore_errors=True)


@pytest.fixture
def fresh_db(temp_dirs):
    config_dir, _ = temp_dirs
    db_path = config_dir / "config.db"
    return ConfigDatabase(db_path=db_path)


def test_system_settings_seed_and_crud(fresh_db):
    """Verify default system_settings are seeded and CRUD methods work."""
    # Check seeded defaults
    singles_pat = fresh_db.get_system_setting("library_import.singles_pattern")
    assert singles_pat == "{Artist}/Singles/{Track} - {Title}.{ext}"

    pref_studio = fresh_db.get_system_setting(
        "metadata_enhancement.prefer_canonical_studio_album"
    )
    assert pref_studio is True

    # Set new setting
    fresh_db.set_system_setting("theme", "dark")
    assert fresh_db.get_system_setting("theme") == "dark"

    # Set complex dictionary setting
    dict_val = {"auto_import": True, "strict_mode": False}
    fresh_db.set_system_setting("library_import", dict_val)
    retrieved = fresh_db.get_system_setting("library_import")
    assert retrieved == dict_val

    # Get all settings
    all_settings = fresh_db.get_all_system_settings()
    assert "theme" in all_settings
    assert all_settings["theme"] == "dark"
    assert "library_import" in all_settings

    # Delete setting
    assert fresh_db.delete_system_setting("theme") is True
    assert fresh_db.get_system_setting("theme") is None


def test_quality_profiles_relational_crud(fresh_db):
    """Verify relational quality_profiles and quality_profile_steps CRUD."""
    profiles = [
        {
            "id": "lossless_pref",
            "name": "Lossless Preferred",
            "prefer_max_quality": True,
            "steps": [
                {"priority": 1, "format": "FLAC", "bitrate": 1411},
                {"priority": 2, "format": "MP3", "bitrate": 320},
            ],
        },
        {
            "id": "compact",
            "name": "Compact MP3",
            "prefer_max_quality": False,
            "steps": [
                {"priority": 1, "format": "MP3", "bitrate": 320},
            ],
        },
    ]

    # Insert profiles
    success = fresh_db.set_quality_profiles(profiles)
    assert success is True

    # Retrieve all
    stored = fresh_db.get_quality_profiles()
    assert len(stored) == 2
    by_id = {p["id"]: p for p in stored}
    assert "lossless_pref" in by_id
    assert by_id["lossless_pref"]["name"] == "Lossless Preferred"
    assert by_id["lossless_pref"]["prefer_max_quality"] is True
    assert len(by_id["lossless_pref"]["steps"]) == 2
    assert by_id["lossless_pref"]["steps"][0]["format"] == "FLAC"

    # Retrieve single
    single = fresh_db.get_quality_profile("compact")
    assert single is not None
    assert single["name"] == "Compact MP3"
    assert len(single["steps"]) == 1

    # Update single
    single["name"] = "Compact MP3 Renamed"
    single["prefer_max_quality"] = True
    fresh_db.set_quality_profile(single)
    updated = fresh_db.get_quality_profile("compact")
    assert updated["name"] == "Compact MP3 Renamed"
    assert updated["prefer_max_quality"] is True

    # Delete single
    assert fresh_db.delete_quality_profile("compact") is True
    assert fresh_db.get_quality_profile("compact") is None
    assert len(fresh_db.get_quality_profiles()) == 1


def test_legacy_json_migration_and_sanitization(temp_dirs):
    """Verify legacy runtime keys are migrated into config.db and pruned from config.json."""
    config_dir, data_dir = temp_dirs
    json_path = config_dir / "config.json"
    db_path = config_dir / "config.db"

    # Simulate a legacy config.json containing both cold and hot settings
    legacy_config = {
        "server": {"host": "127.0.0.1", "port": 5050},
        "storage": {"library_dir": str(data_dir / "music")},
        "logging": {"level": "DEBUG"},
        "metadata_enhancement": {
            "enabled": True,
            "prefer_canonical_studio_album": False,
            "naming_template": "{Artist}/{Album}/{Title}.{ext}",
        },
        "library_import": {
            "singles_pattern": "{Artist}/Standalone/{Title}.{ext}",
        },
        "quality_profiles": [
            {
                "id": "migrated_profile",
                "name": "Migrated Profile",
                "prefer_max_quality": True,
                "steps": [{"priority": 1, "format": "FLAC"}],
            }
        ],
        "file_rename_template": "{Track} - {Title}.{ext}",
        "scan_interval": 3600,
        "match_threshold": 85,
        "theme": "nord",
        "active_download_client": "slskd",
        "active_media_server": "plex",
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(legacy_config, f)

    db = ConfigDatabase(db_path=db_path)
    res = migrate_legacy_json_to_db(json_path, db)
    assert res is True

    # Check migrated values in DB
    assert db.get_system_setting("theme") == "nord"
    assert db.get_system_setting("scan_interval") == 3600
    assert db.get_system_setting("match_threshold") == 85
    assert db.get_system_setting("active_download_client") == "slskd"
    assert db.get_system_setting("active_media_server") == "plex"
    meta_setting = db.get_system_setting("metadata_enhancement")
    assert meta_setting["prefer_canonical_studio_album"] is False
    assert meta_setting["naming_template"] == "{Artist}/{Album}/{Title}.{ext}"

    imported_profiles = db.get_quality_profiles()
    assert len(imported_profiles) == 1
    assert imported_profiles[0]["id"] == "migrated_profile"

    # Check sanitized config.json: only COLD keys remain
    with open(json_path, "r", encoding="utf-8") as f:
        clean_json = json.load(f)

    for k in clean_json:
        assert k in COLD_BOOTSTRAP_KEYS, (
            f"Hot key {k} should have been pruned from config.json!"
        )

    assert "server" in clean_json
    assert "storage" in clean_json
    assert "logging" in clean_json
    assert "quality_profiles" not in clean_json
    assert "theme" not in clean_json
    assert "metadata_enhancement" not in clean_json


def test_config_manager_transparent_routing(temp_dirs, monkeypatch):
    """Verify ConfigManager routes hot keys to config.db and cold keys to config.json."""
    config_dir, data_dir = temp_dirs
    monkeypatch.setenv("ECHOSYNC_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("ECHOSYNC_DATA_DIR", str(data_dir))

    db = ConfigDatabase(db_path=config_dir / "config.db")
    monkeypatch.setattr("database.config_database._config_db", db)

    cm = ConfigManager()
    monkeypatch.setattr("core.settings.config_manager", cm)

    # Set hot key
    cm.set("theme", "solarized")
    # Verify it is in config.db
    assert db.get_system_setting("theme") == "solarized"
    # Verify get() retrieves it
    assert cm.get("theme") == "solarized"

    # Verify config.json does NOT contain theme
    with open(cm.config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "theme" not in data

    # Set cold key
    cm.set("logging.level", "WARNING")
    assert cm.get("logging.level") == "WARNING"
    with open(cm.config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["logging"]["level"] == "WARNING"

    # Verify active download client helper
    cm.set_active_download_client("aria2")
    assert cm.get_active_download_client() == "aria2"
    assert db.get_system_setting("active_download_client") == "aria2"


def test_system_settings_api_patch_allowlist(monkeypatch, temp_dirs):
    """Verify PATCH /api/v1/system/settings accepts library_import and persists to config.db."""
    config_dir, data_dir = temp_dirs
    monkeypatch.setenv("ECHOSYNC_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("ECHOSYNC_DATA_DIR", str(data_dir))

    db = ConfigDatabase(db_path=config_dir / "config.db")
    monkeypatch.setattr("database.config_database._config_db", db)

    cm = ConfigManager()
    monkeypatch.setattr(system_route_module, "config_manager", cm)
    monkeypatch.setattr("core.settings.config_manager", cm)

    app = FastAPI()
    app.include_router(system_route_module.router)
    app.dependency_overrides[require_auth] = lambda: True
    client = TestClient(app)

    # Attempt PATCH with library_import (previously rejected with 400)
    payload = {
        "library_import": {
            "singles_pattern": "{Artist}/Tracks/{Title}.{ext}",
            "renaming_pattern": "{Artist}/{Album}/{Track}. {Title}.{ext}",
        },
        "theme": "dark",
    }
    resp = client.patch("/api/v1/system/settings", json=payload)
    assert resp.status_code == 200, resp.text
    assert resp.json().get("success") is True

    # Verify persisted in config.db
    lib_val = db.get_system_setting("library_import")
    assert lib_val["singles_pattern"] == "{Artist}/Tracks/{Title}.{ext}"
    assert db.get_system_setting("theme") == "dark"

    # Rejection test: unknown key must return 400
    bad_resp = client.patch(
        "/api/v1/system/settings", json={"malicious_key": "exploit"}
    )
    assert bad_resp.status_code == 400
    assert "Rejected unknown settings keys" in bad_resp.text


def test_path_formatter_reads_hot_db(monkeypatch, temp_dirs):
    """Verify core.path_formatter queries config.db system_settings directly."""
    config_dir, data_dir = temp_dirs
    monkeypatch.setenv("ECHOSYNC_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("ECHOSYNC_DATA_DIR", str(data_dir))

    db = ConfigDatabase(db_path=config_dir / "config.db")
    monkeypatch.setattr("database.config_database.get_config_database", lambda: db)

    from core.path_formatter import (
        get_library_preferences,
        get_prefer_canonical_studio_album,
        get_singles_pattern,
    )

    # Test initial defaults from seeded DB
    assert get_prefer_canonical_studio_album() is True
    assert get_singles_pattern() == "{Artist}/Singles/{Track} - {Title}.{ext}"

    # Update system_settings in DB
    db.set_system_setting(
        "library_import.singles_pattern", "{Artist}/Singles2/{Title}.{ext}"
    )
    db.set_system_setting("metadata_enhancement.prefer_canonical_studio_album", False)
    db.set_system_setting("storage_locations.library", "/custom/music/path")
    db.set_system_setting(
        "library_import.renaming_pattern", "{Artist} - {Album}/{Track} {Title}.{ext}"
    )

    assert get_singles_pattern() == "{Artist}/Singles2/{Title}.{ext}"
    assert get_prefer_canonical_studio_album() is False
    root, pattern = get_library_preferences()
    assert root == "/custom/music/path"
    assert pattern == "{Artist} - {Album}/{Track} {Title}.{ext}"
