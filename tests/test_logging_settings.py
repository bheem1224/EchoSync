"""Tests for exposing and modifying log level via settings API."""

from flask import Flask
import pytest

import core.tiered_logger as tiered
from web.routes import system as system_routes


def test_get_settings_includes_log_level(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(system_routes.bp)
    client = app.test_client()

    # stub config_manager.get_all to return an arbitrary payload
    monkeypatch.setattr("core.settings.config_manager.get_all", lambda: {"foo": "bar"}, raising=False)
    # stub logger level
    monkeypatch.setattr("core.tiered_logger.get_current_log_level", lambda: "DEBUG", raising=False)

    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["settings"]["log_level"] == "DEBUG"
    assert data["settings"]["foo"] == "bar"


def test_update_settings_changes_log_level_and_persists(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(system_routes.bp)
    client = app.test_client()

    # capture calls
    log_calls = []
    def fake_set(lvl):
        log_calls.append(lvl)
        return True
    monkeypatch.setattr("core.tiered_logger.set_log_level", fake_set, raising=False)

    set_calls = []
    monkeypatch.setattr("core.settings.config_manager.set", lambda k, v: set_calls.append((k, v)), raising=False)

    # post both log_level and another key
    resp = client.post("/api/settings", json={"log_level": "INFO", "another": 123})
    assert resp.status_code == 200
    assert ("log_level", "INFO") in set_calls
    assert ("another", 123) in set_calls
    assert log_calls == ["INFO"]


def test_update_settings_accepts_friendly_names(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(system_routes.bp)
    client = app.test_client()

    log_calls = []
    monkeypatch.setattr("core.tiered_logger.set_log_level", lambda lvl: log_calls.append(lvl), raising=False)
    monkeypatch.setattr("core.settings.config_manager.set", lambda k, v: None, raising=False)

    # send 'normal' which should be normalized to INFO
    resp = client.post("/api/settings", json={"log_level": "normal"})
    assert resp.status_code == 200
    assert log_calls == ["INFO"]
