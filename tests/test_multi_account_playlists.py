from fastapi.testclient import TestClient
import zlib
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from core.db.echo_sync_track import EchosyncTrack

# reuse client fixture from other tests

spotify_id = zlib.crc32(b"EchoSync.spotify") & 0xFFFFFFFF


def create_test_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    # register blueprints manually if necessary
    from web.api_app import create_app

    return create_app(testing=True)


@pytest.fixture
def client():
    from web.api_app import create_app

    app = create_app(testing=True)
    with TestClient(app) as c:
        yield c


def test_provider_settings_route_uses_service_config(client, monkeypatch):
    """GET /api/plugins/<provider>/settings should surface database credentials.

    This test exercises the end-to-end path used by the web UI.  We patch
    ``ConfigDatabase`` such that the "database" value differs from the
    legacy config and ensure the route prefers the former.
    """

    class FakeSpotifyPluginClass:
        name = "EchoSync.spotify"

    from core.nexus_framework.plugin_loader import PluginRegistry

    monkeypatch.setattr(
        PluginRegistry,
        "get_plugin_class",
        lambda name: (
            FakeSpotifyPluginClass
            if name in ("spotify", spotify_id, str(spotify_id))
            else None
        ),
    )

    class FakeConfigDB:
        def get_or_create_service_id(self, name):
            return 1

        def get_service_config(self, sid, key):
            if key == "client_id":
                return "db1"
            if key == "client_secret":
                return "db2"
            if key == "redirect_uri":
                return None
            return None

    with patch(
        "database.config_database.get_config_database", return_value=FakeConfigDB()
    ):
        resp = client.get(f"/api/plugins/{spotify_id}/settings")
        assert resp.status_code == 200
        data = resp.json()
        settings = data.get("settings", {})
        assert settings.get("client_id") == "db1"
        assert settings.get("client_secret") == "db2"
        assert "https://" in settings.get("redirect_uri")
        assert ":5001/api/oauth/callback/plugins/spotify" in settings.get(
            "redirect_uri"
        )


def test_provider_credentials_route_uses_plugins_callback_path(client, monkeypatch):
    """GET /api/plugins/<provider>/credentials should surface the plugin callback URI."""

    class FakeSpotifyPluginClass:
        name = "EchoSync.spotify"

    from core.nexus_framework.plugin_loader import PluginRegistry

    monkeypatch.setattr(
        PluginRegistry,
        "get_plugin_class",
        lambda name: (
            FakeSpotifyPluginClass
            if name in ("spotify", spotify_id, str(spotify_id))
            else None
        ),
    )

    class FakeConfigDB:
        def get_or_create_service_id(self, name):
            return 1

        def get_service_config(self, sid, key):
            if key == "client_id":
                return "db1"
            if key == "client_secret":
                return "db2"
            return None

    with patch(
        "database.config_database.get_config_database", return_value=FakeConfigDB()
    ):
        resp = client.get(f"/api/plugins/{spotify_id}/credentials")
        assert resp.status_code == 200
        data = resp.json()
        credentials = data.get("credentials", {})
        assert credentials.get("client_id") == "db1"
        assert credentials.get("client_secret") == "db2"
        assert ":5001/api/oauth/callback/plugins/spotify" in credentials.get(
            "redirect_uri"
        )


def test_provider_settings_route_normalizes_plugin_ids_for_service_storage(
    client, monkeypatch
):
    class FakeSpotifyPluginClass:
        name = "EchoSync.spotify"

    from core.nexus_framework.plugin_loader import PluginRegistry

    monkeypatch.setattr(
        PluginRegistry,
        "get_plugin_class",
        lambda name: (
            FakeSpotifyPluginClass
            if name in ("spotify", spotify_id, str(spotify_id))
            else None
        ),
    )

    class FakeConfigDB:
        def __init__(self):
            self.requested_name = None

        def get_or_create_service_id(self, name):
            self.requested_name = name
            return 1

        def get_service_config(self, sid, key):
            return None

        def set_service_config(self, service_id, key, value, is_sensitive=False):
            return True

    fake_db = FakeConfigDB()
    monkeypatch.setattr("database.config_database.get_config_database", lambda: fake_db)
    monkeypatch.setattr(
        "core.nexus_framework.plugin_loader.get_all_plugins",
        lambda: [{"id": "EchoSync.spotify", "name": "spotify"}],
    )

    resp = client.post(
        f"/api/plugins/{spotify_id}/settings",
        json={"client_id": "db1", "client_secret": "db2"},
    )
    assert resp.status_code == 200
    assert fake_db.requested_name == "EchoSync.spotify"


def test_providers_playlist_route_includes_account_id(client, monkeypatch):
    """The providers playlist endpoint should return playlists with account_id for multi-account providers."""
    spotify_id = "spotify"

    class FakeConfigDB:
        def get_or_create_service_id(self, name):
            return 77

        def get_accounts(self, service_id=None, is_active=None):
            assert service_id == 77
            assert is_active in (True, None)
            return [
                {
                    "id": 10,
                    "display_name": "First",
                    "account_name": "First",
                    "user_id": "plex-user-1",
                },
                {
                    "id": 20,
                    "display_name": "Second",
                    "account_name": "Second",
                    "user_id": "plex-user-2",
                },
            ]

    # fake storage service to return two spotify accounts
    fake_storage = MagicMock()
    fake_storage.list_accounts.return_value = [
        {"id": 1, "display_name": "First"},
        {"id": 2, "display_name": "Second"},
    ]
    monkeypatch.setattr(
        "services.storage_service.get_storage_service", lambda: fake_storage
    )
    monkeypatch.setattr(
        "core.file_handling.storage.get_storage_service", lambda: fake_storage
    )
    monkeypatch.setattr(
        "database.config_database.get_config_database", lambda: FakeConfigDB()
    )

    # fake SpotifyClient to return one playlist per account with distinctive id
    class FakeSpotifyClient:
        # provider registry expects a `name` attribute on the class
        name = "spotify"

        def __init__(self, account_id=None):
            self.account_id = account_id

        def is_configured(self):
            return True

        def get_user_playlists(self):
            # return a list with a single dict
            return [
                {
                    "id": f"pl{self.account_id}",
                    "name": f"Playlist {self.account_id}",
                    "track_count": 5,
                }
            ]

    monkeypatch.setattr(
        "plugins.EchoSync.spotify.client.SpotifyClient", FakeSpotifyClient
    )
    from core.nexus_framework.plugin_loader import PluginRegistry

    monkeypatch.setattr(
        PluginRegistry,
        "get_plugin_class",
        lambda name: FakeSpotifyClient if name in ("spotify", spotify_id) else None,
    )
    monkeypatch.setattr(
        PluginRegistry,
        "get_provider_class",
        lambda name: FakeSpotifyClient if name in ("spotify", spotify_id) else None,
        raising=False,
    )
    monkeypatch.setattr(
        PluginRegistry,
        "create_instance",
        lambda name, *args, **kwargs: (
            FakeSpotifyClient(account_id=kwargs.get("account_id"))
            if name in ("spotify", spotify_id)
            else None
        ),
    )
    monkeypatch.setattr(PluginRegistry, "is_plugin_disabled", lambda name: False)
    monkeypatch.setattr(
        PluginRegistry, "is_provider_disabled", lambda name: False, raising=False
    )

    resp = client.get(f"/api/plugins/{spotify_id}/playlists")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plugin"] == "spotify"
    items = data["items"]
    # we should have two items, one per account
    assert len(items) == 2
    # each item should include account_id field
    assert any(item.get("account_id") == 1 for item in items)
    assert any(item.get("account_id") == 2 for item in items)
    assert any(item.get("target_user_id") == "plex-user-1" for item in items)
    assert any(item.get("target_user_id") == "plex-user-2" for item in items)
    # Since we removed account name suffix from the UI string, we check source_account_name instead
    assert items[0]["source_account_name"] in ["First", "Second"]


def test_analyze_playlists_honors_account_id(client, monkeypatch):
    """analyze_playlists should instantiate provider per-account when account_id supplied."""
    fake_storage = MagicMock()
    fake_storage.list_accounts.return_value = [{"id": 1}, {"id": 2}]
    monkeypatch.setattr(
        "core.file_handling.storage.get_storage_service", lambda: fake_storage
    )

    called = []

    class FakeSpotifyClient:
        name = "EchoSync.spotify"
        # Add capabilities to bypass strict capability check in analyze route
        from core.nexus_framework.plugin_SDK import (
            MetadataRichness,
            PlaylistSupport,
            ProviderCapabilities,
            SearchCapabilities,
        )

        capabilities = ProviderCapabilities(
            name="spotify",
            supports_playlists=PlaylistSupport.READ_WRITE,
            search=SearchCapabilities(
                tracks=True, artists=True, albums=True, playlists=True
            ),
            metadata=MetadataRichness.HIGH,
            supports_user_auth=True,
        )

        def __init__(self, account_id=None):
            self.account_id = account_id

        def is_configured(self):
            return True

        def get_playlist_tracks(self, playlist_id, **kwargs):
            # record invocation for assertion
            called.append((self.account_id, playlist_id))

            # return a minimal track object with attributes used in analysis
            class Track:
                def __init__(self, title, artist_name, album_title, duration):
                    self.title = title
                    self.raw_title = title
                    self.artist_name = artist_name
                    self.album_title = album_title
                    self.duration = duration
                    self.identifiers = {}
                    self.plugin_context = {}

            return [Track(f"t_{playlist_id}", "A", "B", 1234)]

    monkeypatch.setattr(
        "plugins.EchoSync.spotify.client.SpotifyClient", FakeSpotifyClient
    )
    from core.nexus_framework.plugin_loader import PluginRegistry

    monkeypatch.setattr(
        PluginRegistry, "get_plugin_class", lambda name: FakeSpotifyClient
    )
    monkeypatch.setattr(
        "core.nexus_framework.plugin_loader.get_plugin_capabilities",
        lambda name: FakeSpotifyClient.capabilities,
    )

    payload = {
        "source": "spotify",
        "playlists": [
            {"id": "p1", "name": "P1", "account_id": 1},
            {"id": "p2", "name": "P2", "account_id": 2},
        ],
        "quality_profile": "Auto",
        "target": "plex",
    }

    resp = client.post("/api/v1/core/playlists/analyze", json=payload)
    assert resp.status_code == 200
    # ensure provider was called separately for each account/playlist
    assert (1, "p1") in called
    assert (2, "p2") in called


def test_download_missing_hydrates_from_full_source_track_payload(client, monkeypatch):
    queued = []
    process_calls = []

    class FakeDownloadManager:
        def queue_download(self, track):
            queued.append(track)
            return 123

        def process_downloads_now(self):
            process_calls.append(True)

    monkeypatch.setattr(
        "services.download_manager.get_download_manager", lambda: FakeDownloadManager()
    )

    source_track = EchosyncTrack(
        raw_title="My Song",
        artist_name="My Artist",
        album_title="My Album",
        duration=210000,
        isrc="USRC17607839",
        identifiers={"spotify": "spotify-track-id"},
    )

    resp = client.post(
        "/api/v1/core/playlists/download-missing",
        json={
            "missing": [
                {
                    "title": "My Song",
                    "artist": "My Artist",
                    "album": "My Album",
                    "source_track": source_track.to_dict(),
                }
            ]
        },
    )

    assert resp.status_code == 200
    assert len(queued) == 1
    assert queued[0].duration == 210000
    assert queued[0].isrc == "USRC17607839"
    assert process_calls == [True]


def test_download_missing_preserves_duration_and_isrc_from_fallback_fields(
    client, monkeypatch
):
    queued = []
    process_calls = []

    class FakeDownloadManager:
        def queue_download(self, track):
            queued.append(track)
            return 124

        def process_downloads_now(self):
            process_calls.append(True)

    monkeypatch.setattr(
        "services.download_manager.get_download_manager", lambda: FakeDownloadManager()
    )

    resp = client.post(
        "/api/v1/core/playlists/download-missing",
        json={
            "missing": [
                {
                    "title": "Fallback Song",
                    "artist": "Fallback Artist",
                    "album": "Fallback Album",
                    "duration": 198000,
                    "isrc": "GBUM71029604",
                    "source_identifier": "spotify-fallback-id",
                }
            ]
        },
    )

    assert resp.status_code == 200
    assert len(queued) == 1
    assert queued[0].duration == 198000
    assert queued[0].isrc == "GBUM71029604"
    assert queued[0].identifiers.get("spotify") == "spotify-fallback-id"
    assert process_calls == [True]
