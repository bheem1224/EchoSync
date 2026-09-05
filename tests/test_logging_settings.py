from fastapi.testclient import TestClient
from web.api_app import create_app

app = create_app(testing=True)
client = TestClient(app)

def test_get_settings_includes_log_level(monkeypatch):
    monkeypatch.setattr(
        "core.settings.config_manager.get_all", lambda: {"foo": "bar"}, raising=False
    )
    monkeypatch.setattr(
        "core.tiered_logger.get_current_log_level", lambda: "DEBUG", raising=False
    )

    resp = client.get("/api/v1/system/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["settings"]["log_level"] == "DEBUG"
    assert data["settings"]["foo"] == "bar"

def test_update_settings_changes_log_level_and_persists(monkeypatch):
    log_calls = []

    def fake_set(lvl):
        log_calls.append(lvl)
        return True

    monkeypatch.setattr("core.tiered_logger.set_log_level", fake_set, raising=False)

    set_calls = []
    monkeypatch.setattr(
        "core.settings.config_manager.set",
        lambda k, v: set_calls.append((k, v)),
        raising=False,
    )

    resp = client.patch(
        "/api/v1/system/settings", json={"log_level": "INFO", "match_threshold": 85}
    )
    assert resp.status_code == 200
    assert ("log_level", "INFO") in set_calls
    assert ("match_threshold", 85) in set_calls
    assert log_calls == ["INFO"]

def test_update_settings_accepts_friendly_names(monkeypatch):
    log_calls = []
    monkeypatch.setattr(
        "core.tiered_logger.set_log_level",
        lambda lvl: log_calls.append(lvl),
        raising=False,
    )
    monkeypatch.setattr(
        "core.settings.config_manager.set", lambda k, v: None, raising=False
    )

    resp = client.patch("/api/v1/system/settings", json={"log_level": "normal"})
    assert resp.status_code == 200
    assert log_calls == ["INFO"]
