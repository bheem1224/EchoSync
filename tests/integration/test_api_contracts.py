"""
Dynamic API "Smoke Test" suite to validate API contracts before release.
"""

import pytest
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
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
    results: Dict[str, Any]

class PluginResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    version: Optional[str] = None
    enabled: Optional[bool] = None

class TrackResponse(BaseModel):
    id: int
    title: str
    artist: Optional[str] = None
    artist_id: Optional[int] = None
    album: Optional[str] = None
    album_id: Optional[int] = None
    duration: Optional[int] = None
    track_number: Optional[int] = None
    disc_number: Optional[int] = None
    bitrate: Optional[int] = None
    file_format: Optional[str] = None
    isrc: Optional[str] = None
    musicbrainz_id: Optional[str] = None
    stream_url: str

class TrackListResponse(BaseModel):
    page: int
    per_page: int
    total: int
    total_pages: int
    items: List[TrackResponse]


@pytest.fixture
def client():
    # Initialize the test client hooked into the main EchoSync application.
    # Note: EchoSync is a Flask application, so we use Flask's test_client()
    # which provides a compatible interface for these requests.
    app = create_app(testing=True)
    with app.test_client() as client:
        yield client


def test_api_status_contract(client):
    """Validate /api/status contract"""
    response = client.get("/api/status")
    assert response.status_code == 200
    StatusResponse.model_validate(response.json)


def test_api_health_contract(client):
    """Validate /api/health contract"""
    response = client.get("/api/health")
    assert response.status_code == 200
    HealthResponse.model_validate(response.json)


def test_api_plugins_contract(client):
    """Validate /api/plugins contract"""
    response = client.get("/api/plugins")
    if response.status_code in (301, 308):
        response = client.get("/api/plugins/")
    assert response.status_code == 200
    
    # The /api/plugins endpoint returns a JSON array natively.
    data = response.json
    assert isinstance(data, list), "Expected a list of plugins"
    
    for plugin_data in data:
        PluginResponse.model_validate(plugin_data)


def test_api_library_tracks_contract(client):
    """Validate /api/external/library/tracks contract"""
    # Note: The track list endpoint is registered under the external API provider
    response = client.get("/api/external/library/tracks")
    assert response.status_code == 200
    TrackListResponse.model_validate(response.json)
