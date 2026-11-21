"""Test Spotify and Plex routes under FastAPI."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from plugins.EchoSync.plex.routes import router as plex_router
from plugins.EchoSync.spotify.routes import router as spotify_router


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
    resp = client.post(
        "/settings",
        json={
            "client_id": "test_spotify_client_id",
            "client_secret": "test_spotify_client_secret",
        },
    )
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


def test_acoustid_and_tidal_plugin_routes_and_metadata():
    from core.nexus_framework.plugin_loader import get_all_plugins
    from plugins.EchoSync.acoustid.routes import config_router as acoustid_router
    from plugins.EchoSync.tidal.routes import router as tidal_router

    app = FastAPI()
    app.include_router(acoustid_router, prefix="/api/v1/plugins/2136125342")
    app.include_router(tidal_router, prefix="/api/v1/plugins/3106502486")
    client = TestClient(app)

    acoustid_get = client.get("/api/v1/plugins/2136125342/config")
    assert acoustid_get.status_code == 200

    tidal_accounts = client.get("/api/v1/plugins/3106502486/accounts")
    assert tidal_accounts.status_code == 200
    assert "accounts" in tidal_accounts.json()

    plugins = get_all_plugins()
    for p in plugins:
        assert "display_name" in p
        assert "author" in p
        assert p["author"] != "Unknown"
        assert "source_type" in p
        assert "is_configured" in p

