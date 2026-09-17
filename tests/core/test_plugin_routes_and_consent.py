import pytest
from fastapi.testclient import TestClient

from core.nexus_framework.plugin_store import PrivilegeEscalationError, plugin_store
from core.plugins.sdk import compute_plugin_crc32
from database.config_database import close_config_database, get_config_database
from database.working_database import close_working_database
from web.api_app import create_app


@pytest.fixture
def client_env(tmp_path, monkeypatch):
    close_config_database()
    close_working_database()

    config_db_path = tmp_path / "config.db"
    working_db_path = tmp_path / "working.db"
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)

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
    monkeypatch.setattr(config_manager, "get_plugins_dir", lambda: plugins_dir)

    app = create_app()
    # Bypass auth for test
    from web.auth import require_auth

    app.dependency_overrides[require_auth] = lambda: {"user": "test_admin"}

    client = TestClient(app)
    config_db = get_config_database()

    try:
        yield {
            "client": client,
            "config_db": config_db,
            "plugins_dir": plugins_dir,
            "monkeypatch": monkeypatch,
        }
    finally:
        close_config_database()
        close_working_database()


def test_update_route_returns_403_consent_required_payload(client_env):
    """
    Verifies that /api/v1/system/plugins/update returns HTTP 403 with
    status="consent_required" and scopes list when privilege escalation is detected.
    """
    client = client_env["client"]
    config_db = client_env["config_db"]
    monkeypatch = client_env["monkeypatch"]

    plugin_id = compute_plugin_crc32("EchoSync.spotify")
    config_db.register_service(
        name="spotify",
        service_type="metadata",
        description="Spotify",
        plugin_id=plugin_id,
        version="1.0.0",
    )

    escalation_diff = [
        {"scope": "database.mutate_aliases", "description": "Mutate aliases in library"},
        {"scope": "network_domains", "added": ["api.musixmatch.com"]},
    ]

    def mock_update(pid, force_consent=False):
        if not force_consent:
            raise PrivilegeEscalationError(escalation_diff, plugin_id=pid)
        return True

    monkeypatch.setattr(plugin_store, "update_plugin", mock_update)

    # 1. Update without consent -> 403 consent_required
    resp = client.post(
        "/api/v1/system/plugins/update",
        json={"plugin": {"id": "EchoSync.spotify", "version": "2.0.0"}},
    )
    assert resp.status_code == 403
    data = resp.json()
    assert data["status"] == "consent_required"
    assert data["requires_consent"] is True
    assert data["scopes"] == escalation_diff
    assert data["escalations"] == escalation_diff
    assert data["plugin_id"] == str(plugin_id)

    # 2. Update with force_consent query parameter -> 200 OK
    resp_force = client.post(
        "/api/v1/system/plugins/update?force_consent=true",
        json={"plugin": {"id": "EchoSync.spotify", "version": "2.0.0"}},
    )
    assert resp_force.status_code == 200
    assert resp_force.json() == {"success": True}

    # 3. Update with consent_granted in json payload -> 200 OK
    resp_body_consent = client.post(
        "/api/v1/system/plugins/update",
        json={"plugin": {"id": "EchoSync.spotify", "version": "2.0.0"}, "consent_granted": True},
    )
    assert resp_body_consent.status_code == 200
    assert resp_body_consent.json() == {"success": True}


def test_delete_plugin_endpoint(client_env):
    """
    Verifies that DELETE /api/v1/system/plugins/{plugin_id} cleanly uninstalls the plugin.
    """
    client = client_env["client"]
    config_db = client_env["config_db"]
    monkeypatch = client_env["monkeypatch"]

    plugin_id = compute_plugin_crc32("EchoSync.custom_plugin")
    config_db.register_service(
        name="custom_plugin",
        service_type="sideload",
        description="Custom Plugin",
        plugin_id=plugin_id,
        version="1.0.0",
    )

    uninstalled_ids = []
    monkeypatch.setattr(
        plugin_store,
        "uninstall_plugin",
        lambda pid: uninstalled_ids.append(pid) or True,
    )

    resp = client.delete(f"/api/v1/system/plugins/{plugin_id}")
    assert resp.status_code == 200
    assert resp.json() == {"success": True}
    assert plugin_id in uninstalled_ids
