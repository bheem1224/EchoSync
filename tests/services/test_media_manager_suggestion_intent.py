import base64

from database.music_database import Artist, Track, ExternalIdentifier
from services.media_manager import MediaManagerService


def test_media_manager_subscribes_to_suggestion_remove_intent(monkeypatch, mock_db):
    subscriptions = []

    def _fake_subscribe(event_name, handler):
        subscriptions.append((event_name, handler))

    monkeypatch.setattr("services.media_manager.get_database", lambda: mock_db)
    monkeypatch.setattr("services.media_manager.event_bus.subscribe", _fake_subscribe)

    manager = MediaManagerService()

    assert manager._subscribed is True
    assert any(name == "SUGGESTION_PLAYLIST_REMOVE_INTENT" for name, _ in subscriptions)


def test_media_manager_handles_suggestion_remove_intent_end_to_end(monkeypatch, mock_db):
    class FakeProvider:
        def __init__(self):
            self.calls = []

        def remove_tracks_from_playlist(self, playlist_id, provider_track_ids):
            self.calls.append((playlist_id, provider_track_ids))
            return True

    fake_provider = FakeProvider()

    monkeypatch.setattr("services.media_manager.get_database", lambda: mock_db)
    monkeypatch.setattr("services.media_manager.event_bus.subscribe", lambda *_args, **_kwargs: None)
    monkeypatch.setattr("services.media_manager.config_manager.get_active_media_server", lambda: "plex")
    monkeypatch.setattr("services.media_manager.ProviderRegistry.create_instance", lambda _name: fake_provider)

    manager = MediaManagerService()

    with mock_db.session_scope() as session:
        artist = Artist(name="The Artist")
        session.add(artist)
        session.flush()

        track = Track(title="The Song", artist_id=artist.id)
        session.add(track)
        session.flush()

        session.add(
            ExternalIdentifier(
                track_id=track.id,
                provider_source="plex",
                provider_item_id="12345",
            )
        )

    payload = "the artist|the song".encode("utf-8")
    sync_id = f"ss:track:meta:{base64.b64encode(payload).decode('ascii')}"

    manager.handle_suggestion_playlist_remove_intent(
        {
            "event": "SUGGESTION_PLAYLIST_REMOVE_INTENT",
            "sync_id": sync_id,
            "playlist_name": "Suggestions for You",
            "user_id": 99,
        }
    )

    assert fake_provider.calls == [("Suggestions for You", ["12345"])]
