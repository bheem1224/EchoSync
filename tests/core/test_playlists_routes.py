"""Tests for Playlists API routes."""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.event_bus import event_bus
from web.routes.playlists import api_v1_router, legacy_router, router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    app.include_router(api_v1_router)
    app.include_router(legacy_router)
    return TestClient(app)


def test_sync_events_missing_job(client):
    resp = client.get("/api/v1/core/playlists/sync/events")
    assert resp.status_code == 200
    assert resp.json().get("error") == "job query parameter required"


def test_sync_events_with_job_and_since(client):
    job_name = "test:sync:job:123"
    event_bus.publish(job_name, "test_event", {"data": "ok"})

    # Primary core prefix (since=-1 returns all events from 0)
    resp = client.get(f"/api/v1/core/playlists/sync/events?job={job_name}&since=-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("job") == job_name
    assert "events" in data
    assert data.get("count") >= 1

    # Alias api/v1 prefix
    resp_v1 = client.get(f"/api/v1/playlists/sync/events?job={job_name}")
    assert resp_v1.status_code == 200
    assert resp_v1.json().get("job") == job_name
    assert resp_v1.json().get("count") >= 1


def test_plex_sync_client_resolution_failure():
    from web.routes.playlists import _sync_to_plex

    # When Plex plugin is not available or cannot connect, _run_sync should gracefully handle it
    with patch(
        "plugins.EchoSync.plex.client.PlexClient", side_effect=ImportError("No plex")
    ):
        with (
            patch(
                "core.nexus_framework.plugin_loader.PluginRegistry.get_plugin_class",
                return_value=None,
            ),
            patch(
                "core.nexus_framework.plugin_loader.PluginRegistry.get_plugin",
                return_value=None,
            ),
        ):
            result = _sync_to_plex(
                payload={},
                source="spotify",
                target="plex",
                playlist_name="Test Playlist",
                matches=[{"target_identifier": "12345"}],
                download_missing=False,
                sync_mode="direct",
            )
            assert result.get("accepted") is True
            job_name = result.get("job")
            assert job_name is not None
            assert "sync/events" in result.get("events_path")
