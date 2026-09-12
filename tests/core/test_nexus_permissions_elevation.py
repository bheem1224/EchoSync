import io
import json
import os
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.nexus_framework.plugin_SDK import (
    _DatabaseFacade,
    check_plugin_permission,
    sdk,
)
from core.nexus_framework.plugin_store import (
    PluginStore,
    PrivilegeEscalationError,
    compute_permission_delta,
)
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
def temp_plugins_env(tmp_path, monkeypatch):
    """Sets up a fully isolated, temporary SQLite database and plugin directory."""
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
# 1. Delta Calculator Unit Tests
# ---------------------------------------------------------------------------


def test_delta_identical_permissions():
    manifest = {
        "network_domains": ["api.spotify.com"],
        "permissions": {
            "database": {"read_library": True},
            "privileged_mode": False,
        },
    }
    escalations = compute_permission_delta(manifest, manifest)
    assert escalations == []


def test_delta_reduced_permissions():
    old_manifest = {
        "network_domains": ["api.spotify.com", "accounts.spotify.com"],
        "permissions": {
            "database": {
                "read_library": True,
                "mutate_aliases": True,
            },
            "privileged_mode": True,
        },
    }
    new_manifest = {
        "network_domains": ["api.spotify.com"],
        "permissions": {
            "database": {
                "read_library": True,
                "mutate_aliases": False,
            },
            "privileged_mode": False,
        },
    }
    escalations = compute_permission_delta(old_manifest, new_manifest)
    assert escalations == []


def test_delta_added_network_domains():
    old_manifest = {"network_domains": ["api.spotify.com"]}
    new_manifest = {"network_domains": ["api.spotify.com", "api.vgmdb.info"]}
    escalations = compute_permission_delta(old_manifest, new_manifest)
    assert len(escalations) == 1
    assert escalations[0]["scope"] == "network_domains"
    assert escalations[0]["added"] == ["api.vgmdb.info"]


def test_delta_added_privileged_mode():
    old_manifest = {"permissions": {"privileged_mode": False}}
    new_manifest = {"permissions": {"privileged_mode": True}}
    escalations = compute_permission_delta(old_manifest, new_manifest)
    assert len(escalations) == 1
    assert escalations[0]["scope"] == "privileged_mode"


def test_delta_added_database_scopes():
    old_manifest = {"permissions": {"database": {"read_library": True}}}
    new_manifest = {
        "permissions": {
            "database": {
                "read_library": True,
                "mutate_aliases": True,
                "mutate_attributes": True,
            }
        }
    }
    escalations = compute_permission_delta(old_manifest, new_manifest)
    scopes = {e["scope"] for e in escalations}
    assert scopes == {"database.mutate_aliases", "database.mutate_attributes"}


def test_delta_added_database_read_library():
    old_manifest = {"permissions": {"database": {}}}
    new_manifest = {"permissions": {"database": {"read_library": True}}}
    escalations = compute_permission_delta(old_manifest, new_manifest)
    assert len(escalations) == 1
    assert escalations[0]["scope"] == "database.read_library"


def test_delta_added_wasm_fs_access():
    old_manifest = {"wasm_fs_access": ["/data/cache"]}
    new_manifest = {"wasm_fs_access": ["/data/cache", "/data/temp"]}
    escalations = compute_permission_delta(old_manifest, new_manifest)
    assert len(escalations) == 1
    assert escalations[0]["scope"] == "wasm_fs_access"
    assert escalations[0]["added"] == ["/data/temp"]


def test_delta_staticmethod_exposure():
    old_manifest = {}
    new_manifest = {"privileged": True}
    escalations = PluginStore.compute_permission_delta(old_manifest, new_manifest)
    assert len(escalations) == 1
    assert escalations[0]["scope"] == "privileged_mode"


# ---------------------------------------------------------------------------
# 2. SDK Database Permission Enforcement Tests
# ---------------------------------------------------------------------------


def test_check_plugin_permission_core():
    # Core and system services always have full access
    assert check_plugin_permission("core", "database.read_library") is True
    assert check_plugin_permission("system", "database.mutate_aliases") is True
    assert check_plugin_permission("core.metadata", "database.mutate_attributes") is True


def test_check_plugin_permission_manifest_denied(temp_plugins_env):
    plugins_dir = temp_plugins_env["plugins_dir"]
    plugin_path = plugins_dir / "test_author" / "test_plugin"
    plugin_path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "test_plugin",
        "author": "test_author",
        "permissions": {
            "database": {"read_library": False},
        },
    }
    (plugin_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    assert check_plugin_permission("test_author.test_plugin", "database.read_library") is False
    assert check_plugin_permission("test_author.test_plugin", "database.mutate_aliases") is False


def test_check_plugin_permission_manifest_granted(temp_plugins_env):
    plugins_dir = temp_plugins_env["plugins_dir"]
    plugin_path = plugins_dir / "test_author" / "test_plugin"
    plugin_path.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": "test_plugin",
        "author": "test_author",
        "permissions": {
            "database": {
                "read_library": True,
                "mutate_aliases": True,
                "mutate_attributes": True,
            },
        },
    }
    (plugin_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    assert check_plugin_permission("test_author.test_plugin", "database.read_library") is True
    assert check_plugin_permission("test_author.test_plugin", "database.mutate_aliases") is True
    assert check_plugin_permission("test_author.test_plugin", "database.mutate_attributes") is True

    facade = _DatabaseFacade("test_author.test_plugin")
    assert facade.can_read_library() is True
    assert facade.can_mutate_aliases() is True
    assert facade.can_mutate_attributes() is True


def test_sdk_get_database_connection_denied_raises_permission_error(monkeypatch):
    monkeypatch.setattr(sdk, "_get_plugin_id", lambda: "untrusted_author.untrusted_plugin")
    with pytest.raises(PermissionError) as exc_info:
        sdk.get_database_connection(require_library=True)
    assert "read_library" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 3. Pre-Execution Gate & Hot-Swap Abort Tests
# ---------------------------------------------------------------------------


def _create_mock_zip(manifest: dict, extra_files: dict = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifest))
        if extra_files and "__init__.py" in extra_files:
            for fname, content in extra_files.items():
                z.writestr(fname, content)
        else:
            z.writestr("__init__.py", "class Provider:\n    pass\n")
            if extra_files:
                for fname, content in extra_files.items():
                    z.writestr(fname, content)
    return buf.getvalue()


def test_update_escalation_aborts_without_mutating_target(temp_plugins_env):
    """
    When an update introduces privilege escalation and force_consent=False,
    PrivilegeEscalationError is raised, target files remain untouched,
    and services table in config.db is not modified.
    """
    plugins_dir = temp_plugins_env["plugins_dir"]
    config_db = temp_plugins_env["config_db"]
    monkeypatch = temp_plugins_env["monkeypatch"]

    # 1. Existing plugin on disk and registered in config.db
    author = "EchoSync"
    name = "Spotify"
    plugin_path = plugins_dir / author / name
    plugin_path.mkdir(parents=True, exist_ok=True)

    old_manifest = {
        "name": name,
        "author": author,
        "version": "1.0.0",
        "network_domains": ["api.spotify.com"],
        "permissions": {"database": {"read_library": True}},
    }
    (plugin_path / "manifest.json").write_text(json.dumps(old_manifest), encoding="utf-8")
    (plugin_path / "__init__.py").write_text("# Old version 1.0.0\n", encoding="utf-8")

    plugin_id_int = 12345678
    config_db.register_service(
        name=name,
        service_type="metadata",
        description="Spotify",
        absolute_install_path=str(plugin_path.resolve()),
        plugin_id=plugin_id_int,
        version="1.0.0",
        permissions=json.dumps(old_manifest["permissions"]),
        privileged_mode=0,
    )

    # 2. Mock new artifact zip requesting elevated permissions: mutate_aliases + new domain
    new_manifest = {
        "name": name,
        "author": author,
        "version": "2.0.0",
        "network_domains": ["api.spotify.com", "api.musixmatch.com"],
        "permissions": {
            "database": {
                "read_library": True,
                "mutate_aliases": True,
            }
        },
    }
    zip_bytes = _create_mock_zip(new_manifest, {"__init__.py": "# New version 2.0.0\n"})

    class MockResponse:
        status_code = 200
        content = zip_bytes
        headers = {}

    from core.request_manager import RequestManager

    monkeypatch.setattr(RequestManager, "get", lambda *args, **kwargs: MockResponse())

    store = PluginStore()
    plugin_info = {
        "id": f"{author}.{name}",
        "download_url": "https://raw.githubusercontent.com/bheem1224/EchoSync/main/plugins/release.zip",
        "version": "2.0.0",
    }

    # 3. Attempt download with force_consent=False -> Expect PrivilegeEscalationError
    with pytest.raises(PrivilegeEscalationError) as exc_info:
        store.download_plugin(
            plugin_info,
            channel="stable",
            force_consent=False,
            is_update=True,
            target_plugin_id=plugin_id_int,
        )

    escalations = exc_info.value.escalations
    scopes = {e["scope"] for e in escalations}
    assert "network_domains" in scopes
    assert "database.mutate_aliases" in scopes
    assert exc_info.value.plugin_id == plugin_id_int

    # 4. Verify physical files and database state were NOT touched
    init_content = (plugin_path / "__init__.py").read_text(encoding="utf-8")
    assert "# Old version 1.0.0" in init_content

    with config_db._get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT version, permissions FROM services WHERE plugin_id=?", (plugin_id_int,))
        row = c.fetchone()
        assert row["version"] == "1.0.0"
        stored_perms = json.loads(row["permissions"])
        assert stored_perms.get("database", {}).get("mutate_aliases") is None


def test_update_force_consent_completes_hot_swap(temp_plugins_env):
    """
    When force_consent=True is supplied, the update succeeds,
    files are replaced, and new permissions are stored in config.db.
    """
    plugins_dir = temp_plugins_env["plugins_dir"]
    config_db = temp_plugins_env["config_db"]
    monkeypatch = temp_plugins_env["monkeypatch"]

    author = "EchoSync"
    name = "Spotify"
    plugin_path = plugins_dir / author / name
    plugin_path.mkdir(parents=True, exist_ok=True)

    old_manifest = {
        "name": name,
        "author": author,
        "version": "1.0.0",
        "permissions": {"database": {"read_library": True}},
    }
    (plugin_path / "manifest.json").write_text(json.dumps(old_manifest), encoding="utf-8")
    (plugin_path / "__init__.py").write_text("# Old version 1.0.0\n", encoding="utf-8")

    plugin_id_int = 12345678
    config_db.register_service(
        name=name,
        service_type="metadata",
        description="Spotify",
        absolute_install_path=str(plugin_path.resolve()),
        plugin_id=plugin_id_int,
        version="1.0.0",
        permissions=json.dumps(old_manifest["permissions"]),
        privileged_mode=0,
    )

    new_manifest = {
        "name": name,
        "author": author,
        "version": "2.0.0",
        "permissions": {
            "database": {
                "read_library": True,
                "mutate_aliases": True,
            }
        },
    }
    zip_bytes = _create_mock_zip(new_manifest, {"__init__.py": "# New version 2.0.0\n"})

    class MockResponse:
        status_code = 200
        content = zip_bytes
        headers = {}

    from core.request_manager import RequestManager

    monkeypatch.setattr(RequestManager, "get", lambda *args, **kwargs: MockResponse())

    # Mock reload_plugin to simulate hot swap
    reloaded_plugin_ids = []
    from core.nexus_framework.plugin_loader import PluginLoader

    monkeypatch.setattr(
        PluginLoader,
        "reload_plugin",
        lambda self, p_id: reloaded_plugin_ids.append(p_id),
    )

    store = PluginStore()
    plugin_info = {
        "id": f"{author}.{name}",
        "download_url": "https://raw.githubusercontent.com/bheem1224/EchoSync/main/plugins/release.zip",
        "version": "2.0.0",
    }

    result = store.download_plugin(
        plugin_info,
        channel="stable",
        force_consent=True,
        is_update=True,
        target_plugin_id=plugin_id_int,
    )

    assert result is True
    assert plugin_id_int in reloaded_plugin_ids

    # Verify physical file updated
    init_content = (plugin_path / "__init__.py").read_text(encoding="utf-8")
    assert "# New version 2.0.0" in init_content

    # Verify database updated with new permissions
    with config_db._get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT version, permissions FROM services WHERE plugin_id=?", (plugin_id_int,))
        row = c.fetchone()
        assert row["version"] == "2.0.0"
        stored_perms = json.loads(row["permissions"])
        assert stored_perms["database"]["mutate_aliases"] is True
