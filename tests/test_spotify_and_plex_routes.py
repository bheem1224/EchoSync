"""Test Spotify and Plex routes under FastAPI."""

import pytest
from fastapi.testclient import TestClient
from web.api_app import create_app
from database.config_database import get_config_database
from plugins.EchoSync.plex.routes import router as plex_router
from plugins.EchoSync.Spotify.routes import router as spotify_router
from fastapi import FastAPI


def test_plex_poll_route_syntax():
    app = FastAPI()
    app.include_router(plex_router)
    client = TestClient(app)

    # Test polling non-existent session gives 404 with JSON {"error": "Session not found or expired"},
    # NOT FastAPI 404 ("Not Found" route missing)
    resp = client.get("/auth/poll/b5adea31-test-session")
    assert resp.status_code == 404
    data = resp.json()
    assert data.get("error") == "Session not found or expired"


def test_spotify_settings_and_accounts_routes():
    app = FastAPI()
    app.include_router(spotify_router)
    client = TestClient(app)

    # Test GET settings
    resp = client.get("/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "settings" in data
    assert "redirect_uri" in data["settings"]

    # Test POST settings
    resp = client.post("/settings", json={
        "client_id": "test_spotify_client_id",
        "client_secret": "test_spotify_client_secret"
    })
    assert resp.status_code == 200
    assert resp.json().get("success") is True

    # Verify GET settings returns updated values
    resp = client.get("/settings")
    assert resp.status_code == 200
    assert resp.json()["settings"]["client_id"] == "test_spotify_client_id"
    assert resp.json()["settings"]["client_secret"] == "test_spotify_client_secret"

    # Test GET accounts
    resp = client.get("/accounts")
    assert resp.status_code == 200
    assert "accounts" in resp.json()
