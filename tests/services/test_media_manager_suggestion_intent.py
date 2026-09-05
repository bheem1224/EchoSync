from database.music_database import Artist, ExternalIdentifier, LocalMedia, Track
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


def test_media_manager_handles_suggestion_remove_intent_end_to_end(
    monkeypatch, mock_db
):
    class FakeProvider:
        def __init__(self):
            self.calls = []

        def remove_tracks_from_playlist(self, playlist_id, provider_track_ids):
            self.calls.append((playlist_id, provider_track_ids))
            return True

    fake_provider = FakeProvider()

    monkeypatch.setattr("services.media_manager.get_database", lambda: mock_db)
    monkeypatch.setattr(
        "services.media_manager.event_bus.subscribe", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        "services.media_manager.PluginRegistry.create_instance",
        lambda _name: fake_provider,
    )

    manager = MediaManagerService()

    with mock_db.session_scope() as session:
        artist = Artist(name="The Artist")
        session.add(artist)
        session.flush()

        track = Track(sync_id="z1z2z3z4", title="The Song", artist_id=artist.id)
        session.add(track)
        session.flush()

        lm = LocalMedia(media_id="lm_9876", track_id=track.id, file_path="/fake/path")
        session.add(lm)
        session.flush()

        from core.settings import config_manager

        active_server = config_manager.get("active_media_server", "plex")
        session.add(
            ExternalIdentifier(
                media_id="lm_9876",
                plugin_source=active_server,
                plugin_item_id="12345",
            )
        )

    payload = b"the artist|the song"
    sync_id = "z1z2z3z4"

    manager.handle_suggestion_playlist_remove_intent(
        {
            "event": "SUGGESTION_PLAYLIST_REMOVE_INTENT",
            "sync_id": sync_id,
            "playlist_name": "Suggestions for You",
            "account_id": 99,
        }
    )

    assert fake_provider.calls == [("Suggestions for You", ["12345"])]
