from pathlib import Path
from unittest.mock import MagicMock

from core.db.echo_sync_track import EchosyncTrack
from services.metadata_enhancer import RetroactiveEnhancer


def test_identify_file_handles_single_echosync_track_from_search_metadata(monkeypatch):
    enhancer = RetroactiveEnhancer()
    file_path = Path("/data/downloads/test_track.flac")

    # Mock provider search_metadata returning a SINGLE EchosyncTrack object (not a list)
    returned_track = EchosyncTrack(
        raw_title="Gangsta as I Wanna Be",
        artist_name="Spice 1",
        album_title="Thug Reunion",
        musicbrainz_id="b33979f4-030a-40f6-8946-63f807e96524",
    )

    mock_provider = MagicMock()
    mock_provider.search_metadata.return_value = returned_track
    mock_provider.get_metadata.return_value = returned_track

    # Mock echosync_core.extract_metadata
    import echosync_core

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda path: {
            "title": "Gangsta as I Wanna Be",
            "artist": "Spice 1",
            "album": "Thug Reunion",
        },
    )

    # Mock _get_plugin on enhancer
    monkeypatch.setattr(enhancer, "_get_plugin", lambda cap, **kwargs: mock_provider)

    metadata, confidence = enhancer.identify_file(file_path)

    assert metadata is not None
    assert confidence >= 0.85


def test_tag_file_and_tagging_write_handles_call_without_name_error(tmp_path):
    import wave

    enhancer = RetroactiveEnhancer()
    fake_file = tmp_path / "test_song.wav"
    with wave.open(str(fake_file), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b"\x00\x00" * 44100)

    metadata = {
        "title": "Lovely",
        "artist": "Billie Eilish, Khalid",
        "album": "Lovely",
        "musicbrainz_id": "9fac88f3-f646-4099-926e-544180929d7f",
    }

    # Calling tag_file must not raise NameError for _tagging_write
    enhancer.tag_file(fake_file, metadata)


def test_echosync_track_from_orm_and_media_properties(tmp_path):
    """Verify EchosyncTrack.from_orm builds nested EchosyncMedia objects for all associated LocalMedia rows."""
    from database.music_database import Artist, Base, LocalMedia, MusicDatabase, Track

    db_path = str(tmp_path / "test_orm_track.db")
    db = MusicDatabase(db_path)
    Base.metadata.create_all(db.engine)

    with db.session_scope() as session:
        artist = Artist(name="Daft Punk")
        session.add(artist)
        session.flush()

        track = Track(
            title="Get Lucky",
            artist_id=artist.id,
            duration=248000,
            musicbrainz_id="mbid-12345",
            isrc="US1234567890",
        )
        session.add(track)
        session.flush()

        m1 = LocalMedia(
            track_id=track.id,
            file_path="/music/Daft Punk/Get Lucky.flac",
            file_format="flac",
            bitrate=900000,
            media_id="media001",
        )
        m2 = LocalMedia(
            track_id=track.id,
            file_path="/music/Daft Punk/Get Lucky.mp3",
            file_format="mp3",
            bitrate=320000,
            media_id="media002",
        )
        session.add_all([m1, m2])
        session.flush()

        orm_track = session.query(Track).filter_by(id=track.id).first()
        echo_track = EchosyncTrack.from_orm(orm_track)

        assert echo_track.title == "Get Lucky"
        assert echo_track.artist == "Daft Punk"
        assert echo_track.musicbrainz_id == "mbid-12345"
        assert echo_track.isrc == "US1234567890"
        assert echo_track.duration == 248000
        assert len(echo_track.media) == 2
        assert echo_track.media[0].media_id == "media001"
        assert echo_track.media[0].file_path == "/music/Daft Punk/Get Lucky.flac"
        assert echo_track.media[1].media_id == "media002"
        assert echo_track.media[1].file_path == "/music/Daft Punk/Get Lucky.mp3"
        assert echo_track.file_path == "/music/Daft Punk/Get Lucky.flac"


def test_enhance_library_metadata_enhances_all_associated_files(monkeypatch, tmp_path):
    """Verify RetroactiveEnhancer.enhance_library_metadata processes and tags ALL associated media files."""
    from core.nexus_framework.plugin_loader import PluginRegistry
    from database.music_database import (
        Artist,
        AudioFingerprint,
        Base,
        LocalMedia,
        MusicDatabase,
        Track,
    )

    db_path = str(tmp_path / "test_multi_enhance.db")
    db = MusicDatabase(db_path)
    Base.metadata.create_all(db.engine)

    # Create real test files on disk
    f1 = tmp_path / "track_v1.flac"
    f2 = tmp_path / "track_v2.mp3"
    f1.write_bytes(b"dummy flac content")
    f2.write_bytes(b"dummy mp3 content")

    with db.session_scope() as session:
        artist = Artist(name="Justice")
        session.add(artist)
        session.flush()

        track = Track(title="Genesis", artist_id=artist.id, duration=234000)
        session.add(track)
        session.flush()

        m1 = LocalMedia(
            track_id=track.id, file_path=str(f1), file_format="flac", media_id="med_f1"
        )
        m2 = LocalMedia(
            track_id=track.id, file_path=str(f2), file_format="mp3", media_id="med_f2"
        )
        session.add_all([m1, m2])

    monkeypatch.setattr("database.music_database.get_database", lambda: db)
    monkeypatch.setattr("database.get_database", lambda: db)

    # Track tagging writes
    written_paths = []

    def fake_tagging_write(file_path, tags):
        written_paths.append((str(file_path), tags))

    monkeypatch.setattr("services.metadata_enhancer._tagging_write", fake_tagging_write)

    # Mock echosync_core extract_metadata
    import echosync_core

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {"title": "Genesis", "artist": "Justice"},
    )

    # Mock MusicBrainz plugin
    mock_mb = MagicMock()
    mock_mb.capabilities = type("Caps", (), {"supports_batching": False})()
    mock_mb.get_metadata.return_value = {
        "isrc": "FR1234567890",
        "mbid": "mbid-justice-genesis",
    }
    monkeypatch.setattr(PluginRegistry, "get_plugin", lambda name: mock_mb)

    # Mock fingerprint provider
    mock_fp_provider = MagicMock()
    mock_fp_provider.resolve_fingerprint_details.return_value = {
        "mbids": ["mbid-justice-genesis"],
        "acoustid_id": "acoustid-uuid-1234",
    }

    enhancer = RetroactiveEnhancer()
    monkeypatch.setattr(enhancer, "_get_plugin", lambda cap, **kwargs: mock_fp_provider)

    # Mock FingerprintGenerator
    from core.matching_engine.fingerprinting import FingerprintGenerator

    monkeypatch.setattr(
        FingerprintGenerator, "generate", lambda p: f"chromaprint_dummy_hash_{p}"
    )

    # Run enhancement pass
    enhancer.enhance_library_metadata(batch_size=10, check_all_files=True)

    # Verify both physical files received tag writes
    written_files = [wp[0] for wp in written_paths]
    assert str(f1) in written_files
    assert str(f2) in written_files

    # Verify database was updated
    with db.session_scope() as session:
        t = session.query(Track).filter_by(title="Genesis").first()
        assert t.musicbrainz_id == "mbid-justice-genesis"
        assert t.isrc == "FR1234567890"
        assert t.metadata_status.get("enhanced") is True

        # Verify AudioFingerprints were created for all media IDs
        fps = session.query(AudioFingerprint).all()
        assert len(fps) == 2
        fp_media_ids = {fp.media_id for fp in fps}
        assert "med_f1" in fp_media_ids
        assert "med_f2" in fp_media_ids


def test_retroactive_enhancer_falls_back_to_text_on_acoustid_miss(
    monkeypatch, tmp_path
):
    """Verify RetroactiveEnhancer falls back to text search waterfall when AcoustID returns 0 matches."""
    from core.nexus_framework.plugin_loader import PluginRegistry
    from database.music_database import Artist, Base, LocalMedia, MusicDatabase, Track

    db_path = str(tmp_path / "test_waterfall_fallback.db")
    db = MusicDatabase(db_path)
    Base.metadata.create_all(db.engine)

    f_classical = tmp_path / "bach_brandenburg.flac"
    f_classical.write_bytes(b"dummy classical flac content")

    with db.session_scope() as session:
        artist = Artist(name="Johann Sebastian Bach")
        session.add(artist)
        session.flush()

        track = Track(
            title="Brandenburg Concerto No. 3 in G Major, BWV 1048: I. Allegro",
            artist_id=artist.id,
            duration=340000,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=track.id,
            file_path=str(f_classical),
            file_format="flac",
            media_id="bach_media_01",
        )
        session.add(media)

    monkeypatch.setattr("database.music_database.get_database", lambda: db)
    monkeypatch.setattr("database.get_database", lambda: db)

    # Track tagging writes
    written_tags_list = []

    def fake_tagging_write(file_path, tags):
        written_tags_list.append((str(file_path), tags))

    monkeypatch.setattr("services.metadata_enhancer._tagging_write", fake_tagging_write)

    # Mock extract_metadata returning initial basic tags
    import echosync_core

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Brandenburg Concerto No. 3 in G Major, BWV 1048: I. Allegro",
            "artist": "Johann Sebastian Bach",
        },
    )

    # Mock AcoustID resolving ZERO matches
    mock_fp_provider = MagicMock()
    mock_fp_provider.resolve_fingerprint_details.return_value = {
        "mbids": [],
        "acoustid_id": None,
    }

    enhancer = RetroactiveEnhancer()
    monkeypatch.setattr(enhancer, "_get_plugin", lambda cap, **kwargs: mock_fp_provider)

    # Mock FingerprintGenerator
    from core.matching_engine.fingerprinting import FingerprintGenerator

    monkeypatch.setattr(
        FingerprintGenerator, "generate", lambda p: "chromaprint_classical_hash"
    )

    # Mock MusicBrainz text search returning a valid matched track
    mock_mb = MagicMock()
    mock_mb.capabilities = type("Caps", (), {"supports_batching": False})()

    classical_mb_track = EchosyncTrack(
        raw_title="Brandenburg Concerto No. 3 in G Major, BWV 1048: I. Allegro",
        artist_name="Johann Sebastian Bach",
        album_title="Brandenburg Concertos",
        musicbrainz_id="mbid-bach-brandenburg-3",
        isrc="DE1234567890",
        duration=340000,
    )
    mock_mb.search_metadata.return_value = [classical_mb_track]
    mock_mb.get_metadata.return_value = classical_mb_track
    monkeypatch.setattr(
        PluginRegistry,
        "get_plugin",
        lambda name: mock_mb if name == "musicbrainz" else None,
    )

    # Run enhancement pass
    enhancer.enhance_library_metadata(batch_size=10, check_all_files=True)

    # Verify text search was executed and track was enhanced
    assert len(written_tags_list) > 0
    assert written_tags_list[0][0] == str(f_classical)
    assert written_tags_list[0][1].get("musicbrainz_id") == "mbid-bach-brandenburg-3"

    with db.session_scope() as session:
        t = (
            session.query(Track)
            .filter_by(
                title="Brandenburg Concerto No. 3 in G Major, BWV 1048: I. Allegro"
            )
            .first()
        )
        assert t.musicbrainz_id == "mbid-bach-brandenburg-3"
        assert t.isrc == "DE1234567890"
        assert t.metadata_status.get("enhanced") is True


def test_get_tracks_for_enhancement_prioritizes_bad_metadata(tmp_path, monkeypatch):
    """Verify TrackRepository.get_tracks_for_enhancement prioritizes Unknown Artist / Unknown Album over normal tracks."""
    from core.hook_manager import hook_manager
    monkeypatch.setattr(hook_manager, "apply_filters", lambda event, initial, *args, **kwargs: [] if event == "register_metadata_requirements" else initial)
    from core.database.repositories.track_repo import TrackRepository
    from database.music_database import (
        Album,
        Artist,
        Base,
        LocalMedia,
        MusicDatabase,
        Track,
    )

    db_path = str(tmp_path / "test_priority.db")
    db = MusicDatabase(db_path)
    Base.metadata.create_all(db.engine)

    with db.session_scope() as session:
        a_known = Artist(name="Daft Punk")
        a_unknown = Artist(name="Unknown Artist")
        session.add_all([a_known, a_unknown])
        session.flush()

        alb_known = Album(title="Discovery", artist_id=a_known.id)
        alb_unknown = Album(title="Unknown Album", artist_id=a_known.id)
        session.add_all([alb_known, alb_unknown])
        session.flush()

        # Track 1: Normal track missing MBID
        t1 = Track(
            title="One More Time",
            artist_id=a_known.id,
            album_id=alb_known.id,
            musicbrainz_id=None,
        )
        # Track 2: Unknown Artist
        t2 = Track(
            title="2 Days Into College",
            artist_id=a_unknown.id,
            album_id=alb_known.id,
            musicbrainz_id=None,
        )
        # Track 3: Unknown Album
        t3 = Track(
            title="Aerodynamic",
            artist_id=a_known.id,
            album_id=alb_unknown.id,
            musicbrainz_id=None,
        )
        # Track 4: Already enhanced track
        t4 = Track(
            title="Harder Better Faster Stronger",
            artist_id=a_known.id,
            album_id=alb_known.id,
            musicbrainz_id="mbid-hbfs",
        )

        session.add_all([t1, t2, t3, t4])
        session.flush()

        m1 = LocalMedia(
            track_id=t1.id,
            file_path="/music/t1.flac",
            file_format="flac",
            media_id="m1",
        )
        m2 = LocalMedia(
            track_id=t2.id,
            file_path="/music/Aimee Carty/2 Days Into College/01.flac",
            file_format="flac",
            media_id="m2",
        )
        m3 = LocalMedia(
            track_id=t3.id,
            file_path="/music/t3.flac",
            file_format="flac",
            media_id="m3",
        )
        m4 = LocalMedia(
            track_id=t4.id,
            file_path="/music/t4.flac",
            file_format="flac",
            media_id="m4",
        )
        session.add_all([m1, m2, m3, m4])

    with db.session_scope() as session:
        results = TrackRepository.get_tracks_for_enhancement(
            session, batch_size=10, check_all_files=False
        )
        # Priority 1: t2 (Unknown Artist) must be first
        # Priority 2: t3 (Unknown Album) must be second
        # Priority 5: t1 (Missing MBID) must be third
        assert len(results) == 3
        assert results[0].id == t2.id
        assert results[1].id == t3.id
        assert results[2].id == t1.id


def test_enhance_library_metadata_respects_limit(monkeypatch, tmp_path):
    """Verify RetroactiveEnhancer.enhance_library_metadata processes only up to limit tracks."""
    from core.nexus_framework.plugin_loader import PluginRegistry
    from database.music_database import Artist, Base, LocalMedia, MusicDatabase, Track

    db_path = str(tmp_path / "test_limit.db")
    db = MusicDatabase(db_path)
    Base.metadata.create_all(db.engine)

    f1 = tmp_path / "track1.flac"
    f2 = tmp_path / "track2.flac"
    f3 = tmp_path / "track3.flac"
    f1.write_bytes(b"dummy")
    f2.write_bytes(b"dummy")
    f3.write_bytes(b"dummy")

    with db.session_scope() as session:
        artist = Artist(name="Artist Test")
        session.add(artist)
        session.flush()

        t1 = Track(title="Song 1", artist_id=artist.id, duration=200000)
        t2 = Track(title="Song 2", artist_id=artist.id, duration=200000)
        t3 = Track(title="Song 3", artist_id=artist.id, duration=200000)
        session.add_all([t1, t2, t3])
        session.flush()

        m1 = LocalMedia(
            track_id=t1.id, file_path=str(f1), file_format="flac", media_id="med_1"
        )
        m2 = LocalMedia(
            track_id=t2.id, file_path=str(f2), file_format="flac", media_id="med_2"
        )
        m3 = LocalMedia(
            track_id=t3.id, file_path=str(f3), file_format="flac", media_id="med_3"
        )
        session.add_all([m1, m2, m3])

    monkeypatch.setattr("database.music_database.get_database", lambda: db)
    monkeypatch.setattr("database.get_database", lambda: db)
    monkeypatch.setattr("services.metadata_enhancer._tagging_write", lambda p, t: None)

    import echosync_core

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {"title": "Song", "artist": "Artist Test"},
    )

    mock_mb = MagicMock()
    mock_mb.capabilities = type("Caps", (), {"supports_batching": False})()
    mock_mb.get_metadata.return_value = {"isrc": "US123", "mbid": "mbid-mock"}
    monkeypatch.setattr(
        PluginRegistry,
        "get_plugin",
        lambda name: mock_mb if name == "musicbrainz" else None,
    )

    mock_fp = MagicMock()
    mock_fp.resolve_fingerprint_details.return_value = {
        "mbids": ["mbid-mock"],
        "acoustid_id": "aid-mock",
    }
    enhancer = RetroactiveEnhancer()
    monkeypatch.setattr(enhancer, "_get_plugin", lambda cap, **kwargs: mock_fp)

    from core.matching_engine.fingerprinting import FingerprintGenerator

    monkeypatch.setattr(FingerprintGenerator, "generate", lambda p: "chromaprint_dummy")

    # Run with limit = 1
    enhancer.enhance_library_metadata(batch_size=5, limit=1, check_all_files=True)

    with db.session_scope() as session:
        enhanced_count = (
            session.query(Track).filter(Track.musicbrainz_id == "mbid-mock").count()
        )
        assert enhanced_count == 1


def test_enhance_library_metadata_recovers_artist_and_album_from_path(
    monkeypatch, tmp_path
):
    """Verify RetroactiveEnhancer recovers Unknown Artist and Unknown Album from folder path structure."""
    from core.nexus_framework.plugin_loader import PluginRegistry
    from database.music_database import (
        Album,
        Artist,
        Base,
        LocalMedia,
        MusicDatabase,
        Track,
    )

    db_path = str(tmp_path / "test_path_recovery.db")
    db = MusicDatabase(db_path)
    Base.metadata.create_all(db.engine)

    # Path structure: tmp_path / "Jennifer Lopez" / "Ain't Your Mama" / "01 - Ain't Your Mama.flac"
    song_dir = tmp_path / "Jennifer Lopez" / "Ain't Your Mama"
    song_dir.mkdir(parents=True, exist_ok=True)
    flac_file = song_dir / "01 - Ain't Your Mama.flac"
    flac_file.write_bytes(b"dummy audio data")

    with db.session_scope() as session:
        a_unk = Artist(name="Unknown Artist")
        session.add(a_unk)
        session.flush()

        alb_unk = Album(title="Unknown Album", artist_id=a_unk.id)
        session.add(alb_unk)
        session.flush()

        track = Track(title="Ain't Your Mama", artist_id=a_unk.id, album_id=alb_unk.id)
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=track.id,
            file_path=str(flac_file),
            file_format="flac",
            media_id="jlo_media_01",
        )
        session.add(media)

    monkeypatch.setattr("database.music_database.get_database", lambda: db)
    monkeypatch.setattr("database.get_database", lambda: db)

    written_tags = []
    monkeypatch.setattr(
        "services.metadata_enhancer._tagging_write",
        lambda p, tags: written_tags.append((p, tags)),
    )

    import echosync_core

    # Mock extract_metadata returning no artist/album tags (simulating bad initial metadata)
    monkeypatch.setattr(
        echosync_core, "extract_metadata", lambda p: {"title": "Ain't Your Mama"}
    )

    mock_mb = MagicMock()
    mock_mb.capabilities = type("Caps", (), {"supports_batching": False})()

    jlo_track = EchosyncTrack(
        raw_title="Ain't Your Mama",
        artist_name="Jennifer Lopez",
        album_title="Ain't Your Mama",
        musicbrainz_id="mbid-jlo-aint-your-mama",
        isrc="USJLO1234567",
        duration=218000,
    )
    mock_mb.search_metadata.return_value = [jlo_track]
    mock_mb.get_metadata.return_value = jlo_track
    monkeypatch.setattr(
        PluginRegistry,
        "get_plugin",
        lambda name: mock_mb if name == "musicbrainz" else None,
    )

    mock_fp = MagicMock()
    mock_fp.resolve_fingerprint_details.return_value = {
        "mbids": [],
        "acoustid_id": None,
    }
    enhancer = RetroactiveEnhancer()
    monkeypatch.setattr(enhancer, "_get_plugin", lambda cap, **kwargs: mock_fp)

    from core.matching_engine.fingerprinting import FingerprintGenerator

    monkeypatch.setattr(FingerprintGenerator, "generate", lambda p: "cp_jlo_hash")

    # Run enhancer with limit=1
    enhancer.enhance_library_metadata(batch_size=1, limit=1, check_all_files=False)

    with db.session_scope() as session:
        t = session.query(Track).filter_by(title="Ain't Your Mama").first()
        assert t.musicbrainz_id == "mbid-jlo-aint-your-mama"
        assert t.artist.name == "Jennifer Lopez"
        assert t.album.title == "Ain't Your Mama"
        assert t.artist.name != "Unknown Artist"
        assert t.album.title != "Unknown Album"


def test_enhance_library_metadata_bad_metadata_with_mbid_does_not_pass_trust_gate(
    tmp_path, monkeypatch
):
    from core.nexus_framework.plugin_loader import PluginRegistry
    from database.music_database import (
        Album,
        Artist,
        Base,
        LocalMedia,
        MusicDatabase,
        Track,
    )
    from services.metadata_enhancer import RetroactiveEnhancer

    db = MusicDatabase(tmp_path / "test.db")
    Base.metadata.create_all(db.engine)
    flac_file = tmp_path / "song.flac"
    flac_file.write_bytes(b"flac data")

    with db.session_scope() as session:
        unk_artist = Artist(name="Unknown Artist", normalized_name="unknown artist")
        unk_album = Album(
            title="Unknown Album", normalized_title="unknown album", artist=unk_artist
        )
        session.add_all([unk_artist, unk_album])
        session.flush()

        # Track has an existing MBID on file or DB, but bad artist/album
        track = Track(
            title="거미줄 (VENOM)",
            normalized_title="거미줄 (venom)",
            sync_id="test_sid_venom",
            musicbrainz_id="mbid-venom-123",
            artist=unk_artist,
            album=unk_album,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=track.id,
            file_path=str(flac_file),
            file_format="flac",
            media_id="venom_media_01",
        )
        session.add(media)

    monkeypatch.setattr("database.music_database.get_database", lambda: db)
    monkeypatch.setattr("database.get_database", lambda: db)

    written_tags = []
    monkeypatch.setattr(
        "services.metadata_enhancer._tagging_write",
        lambda p, tags: written_tags.append((p, tags)),
    )

    import echosync_core

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {"musicbrainz_id": "mbid-venom-123", "title": "거미줄 (VENOM)"},
    )

    mock_mb = MagicMock()
    mock_mb.capabilities = type("Caps", (), {"supports_batching": False})()
    mock_mb.get_metadata.return_value = {
        "title": "VENOM",
        "artist": "Stray Kids",
        "album": "ODDINARY",
        "year": 2022,
        "isrc": "KRA382200001",
    }
    monkeypatch.setattr(
        PluginRegistry,
        "get_plugin",
        lambda name: (
            mock_mb if name == 1990722619 or name == "EchoSync.musicbrainz" else None
        ),
    )

    enhancer = RetroactiveEnhancer()
    enhancer.enhance_library_metadata(batch_size=1, limit=1, check_all_files=False)

    # Verify that targeted fetch ran and updated artist, album, title, and ISRC in DB
    with db.session_scope() as session:
        t = session.query(Track).filter_by(sync_id="test_sid_venom").first()
        assert t.title == "VENOM"
        assert t.artist.name == "Stray Kids"
        assert t.album.title == "ODDINARY"
        assert t.isrc == "KRA382200001"
        assert t.artist.name != "Unknown Artist"
