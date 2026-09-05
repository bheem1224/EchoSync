from core import system_jobs


def test_register_all_system_jobs_registers_expected_defaults(monkeypatch):
    calls = []

    class FakeJobQueue:
        def register_job(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(system_jobs, "job_queue", FakeJobQueue())

    system_jobs.register_all_system_jobs()

    by_name = {call["name"]: call for call in calls}

    assert "database_update" in by_name
    assert by_name["database_update"]["enabled"] is True
    assert by_name["database_update"]["interval_seconds"] == 21600

    assert "media_server_scan" in by_name
    assert by_name["media_server_scan"]["enabled"] is True
    assert by_name["media_server_scan"]["interval_seconds"] == 10800

    assert "suggestion_engine_daily_playlists" in by_name
    assert by_name["suggestion_engine_daily_playlists"]["enabled"] is True
    assert by_name["suggestion_engine_daily_playlists"]["interval_seconds"] == 86400

    assert "auto_import_scan" in by_name
    assert by_name["auto_import_scan"]["enabled"] is True
    assert by_name["auto_import_scan"]["interval_seconds"] == 10800


def test_system_jobs_accept_kwargs(monkeypatch):
    """Verify all registered system job functions tolerate **kwargs without raising TypeError."""
    calls = []

    class FakeJobQueue:
        def register_job(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(system_jobs, "job_queue", FakeJobQueue())
    system_jobs.register_all_system_jobs()

    for call in calls:
        func = call["func"]
        # Verify function can be invoked with arbitrary kwargs without raising TypeError
        try:
            func(force_scan=True, full_refresh=True, extraneous_param="test")
        except TypeError as e:
            if "unexpected keyword argument" in str(e):
                raise AssertionError(
                    f"Job function for '{call['name']}' failed kwargs tolerance: {e}"
                )
        except Exception:
            # Other runtime exceptions (e.g. DB connection) are acceptable here as long as signature accepts kwargs
            pass


def test_database_update_handles_unregistered_local_server(monkeypatch):
    """Verify run_database_update gracefully skips Step 1 when Local Server plugin is not registered."""
    from core.nexus_framework.plugin_loader import PluginRegistry

    calls = []

    class FakeJobQueue:
        def register_job(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(system_jobs, "job_queue", FakeJobQueue())
    system_jobs.register_all_system_jobs()

    by_name = {call["name"]: call for call in calls}
    db_update_func = by_name["database_update"]["func"]

    # Ensure local server plugin is unregistered
    local_id = 1133147422
    PluginRegistry._plugins.pop(local_id, None)

    # Executing db_update_func should not raise ValueError or crash
    db_update_func()


def test_external_identifier_sync_executes(monkeypatch, tmp_path):
    """Verify external_identifier_sync executes without crash and ingests mappings."""
    from core.nexus_framework.plugin_loader import PluginRegistry
    from database.music_database import (
        Artist,
        Base,
        ExternalIdentifier,
        LocalMedia,
        MusicDatabase,
        Track,
    )

    db_path = str(tmp_path / "test_music.db")
    test_db = MusicDatabase(db_path)
    Base.metadata.create_all(test_db.engine)

    # Insert a test track and local media
    with test_db.session_scope() as session:
        artist = Artist(name="Test Artist")
        session.add(artist)
        session.flush()
        track = Track(title="Test Title", artist_id=artist.id)
        session.add(track)
        session.flush()
        media = LocalMedia(
            track_id=track.id,
            file_path="/data/music/Test Artist/Test Title.mp3",
            media_id="testmed1",
        )
        session.add(media)

    monkeypatch.setattr("database.get_database", lambda: test_db)

    from core.nexus_framework.plugin_SDK import MediaServerProvider

    # Mock provider
    class MockProvider(MediaServerProvider):
        name = "plex"
        plugin_id = "EchoSync.plex"
        capabilities = type("Caps", (), {"supports_library_scan": True})()

        def authenticate(self):
            return True

        def get_identifier_mappings(self):
            return [
                {
                    "file_path": "/data/music/Test Artist/Test Title.mp3",
                    "plugin_source": "plex",
                    "plugin_item_id": "998877",
                    "title": "Test Title",
                    "artist_name": "Test Artist",
                }
            ]

    provider_id = 3021005569
    PluginRegistry._plugins[provider_id] = MockProvider
    monkeypatch.setattr(
        PluginRegistry, "get_plugins_by_type", lambda *args, **kwargs: [provider_id]
    )

    calls = []

    class FakeJobQueue:
        def register_job(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(system_jobs, "job_queue", FakeJobQueue())
    system_jobs.register_all_system_jobs()

    by_name = {call["name"]: call for call in calls}
    sync_func = by_name["external_identifier_sync"]["func"]

    # Mock config database
    class MockConfigDb:
        def get_or_create_service_id(self, name):
            return 1

        def get_accounts(self, service_id):
            return [1]

        def get_service_config(self, service_id, key):
            return "http://localhost:32400"

    monkeypatch.setattr(
        "database.config_database.get_config_database", lambda: MockConfigDb()
    )
    monkeypatch.setattr(PluginRegistry, "create_instance", lambda p_id: MockProvider())

    sync_func()

    # Verify ExternalIdentifier record was created
    with test_db.session_scope() as session:
        ext = (
            session.query(ExternalIdentifier)
            .filter(ExternalIdentifier.plugin_source == "plex")
            .first()
        )
        assert ext is not None
        assert ext.plugin_item_id == "998877"
        assert ext.media_id == "testmed1"


def test_track_media_file_properties(tmp_path):
    """Verify Track convenience properties (file_path, bitrate, etc.) work via LocalMedia relationship."""
    from database.music_database import Artist, Base, LocalMedia, MusicDatabase, Track

    db_path = str(tmp_path / "test_props.db")
    db = MusicDatabase(db_path)
    Base.metadata.create_all(db.engine)

    with db.session_scope() as session:
        artist = Artist(name="Artist A")
        session.add(artist)
        session.flush()
        track = Track(title="Song A", artist_id=artist.id)
        session.add(track)
        session.flush()
        media = LocalMedia(
            track_id=track.id,
            file_path="/music/a.mp3",
            file_format="mp3",
            bitrate=320000,
            sample_rate=44100,
            bit_depth=16,
            channels=2,
            file_size_bytes=5000000,
            media_id="med12345",
        )
        session.add(media)
        session.flush()

        loaded_track = session.query(Track).filter(Track.id == track.id).first()
        assert loaded_track.file_path == "/music/a.mp3"
        assert loaded_track.file_format == "mp3"
        assert loaded_track.bitrate == 320000
        assert loaded_track.sample_rate == 44100
        assert loaded_track.file_size_bytes == 5000000
