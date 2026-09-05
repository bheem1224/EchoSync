from fastapi.testclient import TestClient

"""
Dynamic API "Smoke Test" suite to validate API contracts before release.
"""

from typing import Any

import pytest
from pydantic import BaseModel

from web.api_app import create_app

# --- Pydantic Contract Models ---
# Defined here to represent the actual expected response structure
# and validate the Svelte frontend's required contracts.


class StatusResponse(BaseModel):
    status: str
    platform: str
    python_version: str
    uptime: int
    restart_pending: bool


class HealthResponse(BaseModel):
    status: str
    results: dict[str, Any]
    timestamp: str | None = None
    summary: dict[str, Any] | None = None
    library: dict[str, Any] | None = None


class PluginResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    category: str | None = None
    version: str | None = None
    enabled: bool | None = None


class TrackResponse(BaseModel):
    id: int
    title: str
    artist: str | None = None
    artist_id: int | None = None
    album: str | None = None
    album_id: int | None = None
    duration: int | None = None
    track_number: int | None = None
    disc_number: int | None = None
    bitrate: int | None = None
    file_format: str | None = None
    isrc: str | None = None
    musicbrainz_id: str | None = None
    stream_url: str


class TrackListResponse(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    items: list[TrackResponse]


@pytest.fixture
def client():
    # Initialize the test client hooked into the main EchoSync application.
    # Note: EchoSync is a Flask application, so we use Flask's test_client()
    # which provides a compatible interface for these requests.
    app = create_app(testing=True)
    with TestClient(app) as client:
        yield client


def test_api_status_contract(client):
    """Validate /api/v1/system/status contract"""
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    StatusResponse.model_validate(response.json())


def test_api_health_contract(client):
    """Validate /api/v1/system/health contract"""
    response = client.get("/api/v1/system/health")
    assert response.status_code == 200
    HealthResponse.model_validate(response.json())


def test_api_plugins_contract(client):
    """Validate /api/v1/system/plugins contract"""
    response = client.get("/api/v1/system/plugins")
    if response.status_code in (301, 308):
        response = client.get("/api/v1/system/plugins/")
    assert response.status_code == 200

    payload = response.json()
    data = payload.get("plugins", payload) if isinstance(payload, dict) else payload
    assert isinstance(data, list), "Expected a list of plugins"

    for plugin_data in data:
        PluginResponse.model_validate(plugin_data)


def test_api_library_tracks_contract(client, monkeypatch, tmp_path):
    import os

    from database.music_database import Base, get_database

    db = get_database(os.path.join(str(tmp_path), "music.db"))
    Base.metadata.create_all(db.engine)
    monkeypatch.setattr("web.routes.local_metadata.get_database", lambda: db)
    """Validate /api/v1/system/library/tracks contract"""
    # Note: The track list endpoint is registered under the external API provider
    response = client.get("/api/v1/system/library/tracks")
    assert response.status_code == 200
    TrackListResponse.model_validate(response.json())
