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

    monkeypatch.setattr(
        hook_manager,
        "apply_filters",
        lambda event, initial, *args, **kwargs: (
            [] if event == "register_metadata_requirements" else initial
        ),
    )
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


def test_retroactive_enhancer_short_circuits_via_local_fingerprint(
    monkeypatch, tmp_path, caplog
):
    """Verify that a track sharing a chromaprint with an already-enhanced track adopts metadata

    locally without calling MusicBrainzClient.search_recording or AcoustID APIs.
    """
    import logging
    from core.nexus_framework.plugin_loader import PluginRegistry
    from database.music_database import (
        Album,
        Artist,
        AudioFingerprint,
        Base,
        LocalMedia,
        MusicDatabase,
        Track,
    )

    db_path = str(tmp_path / "test_short_circuit.db")
    db = MusicDatabase(db_path)
    Base.metadata.create_all(db.engine)

    # Physical files on disk
    f_enhanced = tmp_path / "daft_punk_track_a.flac"
    f_unenhanced = tmp_path / "daft_punk_track_b.flac"
    f_enhanced.write_bytes(b"dummy audio a")
    f_unenhanced.write_bytes(b"dummy audio b")

    import datetime

    shared_chromaprint = (
        "shared_chromaprint_daft_punk_get_lucky_1234567890_canonical_sample"
    )

    with db.session_scope() as session:
        artist = Artist(name="Daft Punk")
        session.add(artist)
        session.flush()

        album = Album(
            title="Random Access Memories",
            artist_id=artist.id,
            release_date=datetime.date(2013, 5, 17),
            mb_release_id="mb-release-ram-123",
        )
        session.add(album)
        session.flush()

        # Track A: Already enhanced with valid MusicBrainz ID and canonical metadata
        track_a = Track(
            title="Get Lucky",
            artist_id=artist.id,
            album_id=album.id,
            duration=248000,
            musicbrainz_id="mbid-get-lucky-daft-punk",
            isrc="US1234567890",
            metadata_status={"enhanced": True},
        )
        session.add(track_a)
        session.flush()

        media_a = LocalMedia(
            track_id=track_a.id,
            file_path=str(f_enhanced),
            file_format="flac",
            media_id="media_dp_a",
        )
        session.add(media_a)
        session.flush()

        afp_a = AudioFingerprint(
            media_id=media_a.media_id,
            chromaprint=shared_chromaprint,
            acoustid_id="aid-get-lucky-1234",
        )
        session.add(afp_a)

        # Track B: Needs enhancement (missing MBID), but shares the identical chromaprint
        artist_unknown = Artist(name="Unknown Artist")
        session.add(artist_unknown)
        session.flush()

        track_b = Track(
            title="Get Lucky (Radio Version)",
            artist_id=artist_unknown.id,
            album_id=None,
            duration=248000,
            musicbrainz_id=None,
        )
        session.add(track_b)
        session.flush()

        media_b = LocalMedia(
            track_id=track_b.id,
            file_path=str(f_unenhanced),
            file_format="flac",
            media_id="media_dp_b",
        )
        session.add(media_b)
        session.flush()

        afp_b = AudioFingerprint(
            media_id=media_b.media_id,
            chromaprint=shared_chromaprint,
        )
        session.add(afp_b)

    monkeypatch.setattr("database.music_database.get_database", lambda: db)
    monkeypatch.setattr("database.get_database", lambda: db)

    # Intercept tagging writes
    written_tags = []

    def fake_tagging_write(file_path, tags):
        written_tags.append((str(file_path), tags))

    monkeypatch.setattr("services.metadata_enhancer._tagging_write", fake_tagging_write)

    # Mock echosync_core extract_metadata
    import echosync_core

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {"title": "Get Lucky (Radio Version)", "artist": "Daft Punk"},
    )

    # Mock MusicBrainzClient with spy/mock methods that should NOT be called
    mock_mb_client = MagicMock()
    mock_mb_client.capabilities = type("Caps", (), {"supports_batching": False})()
    mock_mb_client.search_recording = MagicMock()
    mock_mb_client.search_recording_strict = MagicMock()
    mock_mb_client.search_metadata = MagicMock()
    mock_mb_client.get_metadata = MagicMock()

    monkeypatch.setattr(
        PluginRegistry,
        "get_plugin",
        lambda name: mock_mb_client,
    )

    # Mock AcoustID provider which should NOT be called
    mock_fp_provider = MagicMock()
    mock_fp_provider.resolve_fingerprint_details = MagicMock()

    enhancer = RetroactiveEnhancer()
    monkeypatch.setattr(enhancer, "_get_plugin", lambda cap, **kwargs: mock_fp_provider)

    from core.matching_engine.fingerprinting import FingerprintGenerator

    monkeypatch.setattr(FingerprintGenerator, "generate", lambda p: shared_chromaprint)

    # Run enhancement pass
    with caplog.at_level(logging.INFO):
        enhancer.enhance_library_metadata(batch_size=10, check_all_files=True)

    # Verification:
    # 1. External APIs were NEVER called (bypassed via short-circuit)
    assert not mock_mb_client.search_recording.called
    assert not mock_mb_client.search_recording_strict.called
    assert not mock_mb_client.search_metadata.called
    assert not mock_fp_provider.resolve_fingerprint_details.called

    # 2. Track B adopted Track A's canonical tags and MBID
    with db.session_scope() as session:
        t_b = session.query(Track).filter(Track.id == track_b.id).first()
        assert t_b.musicbrainz_id == "mbid-get-lucky-daft-punk"
        assert t_b.title == "Get Lucky"
        assert t_b.isrc == "US1234567890"
        assert t_b.metadata_status.get("enhanced") is True

    # 3. Log was generated
    assert any(
        "Metadata resolved via local chromaprint cache" in rec.message
        for rec in caplog.records
    )


def test_retroactive_enhancer_backfill_missing_fingerprints_telemetry(
    monkeypatch, tmp_path
):
    """Verify backfill_missing_fingerprints computes chromaprints and emits job_progress telemetry."""
    from core.event_bus import event_bus
    from database.music_database import (
        Artist,
        AudioFingerprint,
        Base,
        LocalMedia,
        MusicDatabase,
        Track,
    )

    db_path = str(tmp_path / "test_backfill.db")
    db = MusicDatabase(db_path)
    Base.metadata.create_all(db.engine)

    f1 = tmp_path / "song1.flac"
    f2 = tmp_path / "song2.flac"
    f1.write_bytes(b"dummy song 1")
    f2.write_bytes(b"dummy song 2")

    with db.session_scope() as session:
        artist = Artist(name="Test Artist")
        session.add(artist)
        session.flush()

        t1 = Track(title="Song 1", artist_id=artist.id)
        t2 = Track(title="Song 2", artist_id=artist.id)
        session.add_all([t1, t2])
        session.flush()

        m1 = LocalMedia(
            track_id=t1.id, file_path=str(f1), file_format="flac", media_id="m1"
        )
        m2 = LocalMedia(
            track_id=t2.id, file_path=str(f2), file_format="flac", media_id="m2"
        )
        session.add_all([m1, m2])

    monkeypatch.setattr("database.music_database.get_database", lambda: db)
    monkeypatch.setattr("database.get_database", lambda: db)

    # Track event_bus progress events
    progress_events = []

    def on_progress(payload):
        if (
            isinstance(payload, dict)
            and payload.get("job_name") == "retroactive_metadata_enhancement"
        ):
            progress_events.append(payload)

    event_bus.subscribe("job_progress", on_progress)

    enhancer = RetroactiveEnhancer()
    # Mock fingerprinting
    import echosync_core

    monkeypatch.setattr(
        echosync_core,
        "fingerprint_audio",
        lambda p, trim_silence=True: (f"cp_{Path(p).stem}", 120),
    )

    count = enhancer.backfill_missing_fingerprints(batch_size=1)
    assert count == 2

    with db.session_scope() as session:
        fps = session.query(AudioFingerprint).all()
        assert len(fps) == 2
        fp_map = {fp.media_id: fp.chromaprint for fp in fps}
        assert fp_map["m1"] == "cp_song1"
        assert fp_map["m2"] == "cp_song2"

    assert len(progress_events) >= 2
    assert progress_events[-1]["current"] == 2
    assert progress_events[-1]["percentage"] == 100.0


def test_trust_gate_rejects_divergent_candidate(tmp_path, monkeypatch):
    """Verify that a candidate with divergent title is rejected, not written, and staged for manual review."""
    from core.nexus_framework.plugin_loader import PluginRegistry
    from database.music_database import (
        Album,
        Artist,
        Base,
        LocalMedia,
        MusicDatabase,
        Track,
    )
    from database.working_database import (
        SuggestionStagingQueue,
        WorkingBase,
        WorkingDatabase,
    )
    from services.metadata_enhancer import RetroactiveEnhancer

    music_db = MusicDatabase(tmp_path / "music.db")
    Base.metadata.create_all(music_db.engine)

    working_db = WorkingDatabase(tmp_path / "working.db")
    WorkingBase.metadata.create_all(working_db.engine)

    audio_file = tmp_path / "00 - My Way.flac"
    audio_file.write_bytes(b"dummy audio data for my way")

    with music_db.session_scope() as session:
        artist = Artist(name="Calvin Harris", normalized_name="calvin harris")
        album = Album(
            title="Unknown Album",
            normalized_title="unknown album",
            artist=artist,
        )
        session.add_all([artist, album])
        session.flush()

        track = Track(
            title="My Way",
            normalized_title="my way",
            sync_id="sync_calvin_harris_my_way",
            musicbrainz_id="mbid-my-way-initial",
            artist=artist,
            album=album,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=track.id,
            file_path=str(audio_file),
            file_format="flac",
            media_id="media_my_way_01",
        )
        session.add(media)

    monkeypatch.setattr("database.music_database.get_database", lambda: music_db)
    monkeypatch.setattr("database.get_database", lambda: music_db)
    monkeypatch.setattr(
        "database.working_database.get_working_database", lambda: working_db
    )

    written_tags = []
    monkeypatch.setattr(
        "services.metadata_enhancer._tagging_write",
        lambda p, tags: written_tags.append((p, tags)),
    )

    import echosync_core

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "My Way",
            "artist": "Calvin Harris",
            "album": "Unknown Album",
            "mbid": "mbid-my-way-initial",
        },
    )

    # Candidate incorrectly returns "We Found Love"
    mock_mb = MagicMock()
    mock_mb.capabilities = type("Caps", (), {"supports_batching": False})()
    mock_mb.get_metadata.return_value = {
        "title": "We Found Love",
        "artist": "Calvin Harris",
        "album": "18 Months",
        "year": 2011,
        "isrc": "GBARL1101234",
    }
    monkeypatch.setattr(
        PluginRegistry,
        "get_plugin",
        lambda name: mock_mb,
    )

    enhancer = RetroactiveEnhancer()
    enhancer.enhance_library_metadata(batch_size=1, limit=1, check_all_files=False)

    # 1. Tags were NOT written to disk
    assert len(written_tags) == 0

    # 2. File still exists at its original path (not moved to downloads)
    assert audio_file.exists()

    # 3. Track in music.db did not adopt the divergent title
    with music_db.session_scope() as session:
        t = session.query(Track).filter_by(sync_id="sync_calvin_harris_my_way").first()
        assert t.title == "My Way"
        assert t.title != "We Found Love"
        assert t.metadata_status.get("trust_gate_rejected") is True

    # 4. Staged in SuggestionStagingQueue as MANUAL_REVIEW / METADATA_DIVERGENCE
    with working_db.session_scope() as w_session:
        staged = (
            w_session.query(SuggestionStagingQueue)
            .filter_by(
                sync_id="sync_calvin_harris_my_way",
                reason="METADATA_DIVERGENCE",
            )
            .first()
        )
        assert staged is not None
        assert staged.status == "MANUAL_REVIEW"
        assert staged.context_data["candidate_metadata"]["title"] == "We Found Love"


def test_force_refresh_includes_enhanced_tracks(tmp_path, monkeypatch):
    """Verify force_refresh includes tracks with enhanced == True."""
    from database.music_database import (
        Album,
        Artist,
        Base,
        LocalMedia,
        MusicDatabase,
        Track,
    )
    from services.metadata_enhancer import RetroactiveEnhancer

    db = MusicDatabase(tmp_path / "test_force_refresh.db")
    Base.metadata.create_all(db.engine)

    with db.session_scope() as session:
        artist = Artist(name="Artist A")
        album = Album(title="Album A", artist=artist)
        session.add_all([artist, album])
        session.flush()

        # Track already marked as enhanced
        t_enhanced = Track(
            title="Song Enhanced",
            artist=artist,
            album=album,
            musicbrainz_id="mbid-enhanced-1",
            metadata_status={"enhanced": True},
        )
        session.add(t_enhanced)
        session.flush()

        media = LocalMedia(
            track_id=t_enhanced.id,
            file_path=str(tmp_path / "song.flac"),
            file_format="flac",
            media_id="m_enhanced_1",
        )
        session.add(media)

    monkeypatch.setattr("database.music_database.get_database", lambda: db)
    monkeypatch.setattr("database.get_database", lambda: db)

    enhancer = RetroactiveEnhancer()

    # Without force_refresh, enhanced tracks are skipped
    with db.session_scope() as session:
        tracks_normal = enhancer.get_tracks_for_enhancement(
            session=session, force_refresh=False
        )
        assert len(tracks_normal) == 0

        # With force_refresh=True, enhanced track is included
        tracks_forced = enhancer.get_tracks_for_enhancement(
            session=session, force_refresh=True
        )
        assert len(tracks_forced) == 1
        assert tracks_forced[0].title == "Song Enhanced"


def test_revert_track_metadata_from_disk(tmp_path, monkeypatch):
    """Verify revert_track_metadata_from_disk restores track metadata from physical file tags."""
    from database.music_database import (
        Album,
        Artist,
        Base,
        LocalMedia,
        MusicDatabase,
        Track,
    )
    from services.metadata_enhancer import revert_track_metadata_from_disk

    db = MusicDatabase(tmp_path / "test_revert.db")
    Base.metadata.create_all(db.engine)

    flac_path = tmp_path / "00 - My Way.flac"
    flac_path.write_bytes(b"dummy flac data")

    with db.session_scope() as session:
        artist = Artist(name="Corrupted Artist")
        album = Album(title="Corrupted Album", artist=artist)
        session.add_all([artist, album])
        session.flush()

        # Track was falsely overwritten with wrong title, mbid, and marked enhanced
        track = Track(
            title="We Found Love",
            normalized_title="we found love",
            musicbrainz_id="erroneous-mbid-12345",
            isrc="ERRONEOUS_ISRC_999",
            metadata_status={"enhanced": True},
            artist=artist,
            album=album,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=track.id,
            file_path=str(flac_path),
            file_format="flac",
            media_id="media_my_way_revert",
        )
        session.add(media)
        track_id = track.id

    monkeypatch.setattr("database.music_database.get_database", lambda: db)
    monkeypatch.setattr("database.get_database", lambda: db)

    import echosync_core

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "My Way",
            "artist": "Calvin Harris",
            "album": "Chilled House",
        },
    )

    success = revert_track_metadata_from_disk(track_id)
    assert success is True

    with db.session_scope() as session:
        t = session.get(Track, track_id)
        assert t.title == "My Way"
        assert t.normalized_title == "my way"
        assert t.musicbrainz_id is None
        assert t.isrc is None
        assert t.metadata_status.get("enhanced") is False
        assert t.metadata_status.get("reverted_from_disk") is True


def test_acoustid_candidate_penalizes_remix_disambiguation():
    """Verify 'Hey, Soul Sister (Country Mix)' is rejected in favor of the canonical studio cut."""
    from services.metadata_enhancer import select_best_acoustid_recording

    # Candidate 1: "Country Mix" remix candidate (has closer duration delta: 50ms)
    cand_remix = {
        "title": "Hey, Soul Sister (Country Mix)",
        "disambiguation": "Country Mix",
        "recording_id": "mbid-remix-001",
        "length": 216050,
        "releases": [
            {
                "id": "rel-single-1",
                "title": "Hey, Soul Sister (Country Mix) - Single",
                "status": "Official",
                "release-group": {
                    "id": "rg-single-1",
                    "primary-type": "Single",
                    "secondary-types": ["Remix"],
                },
            }
        ],
    }

    # Candidate 2: Canonical studio album cut (has slightly higher duration delta: 250ms)
    cand_studio = {
        "title": "Hey, Soul Sister",
        "disambiguation": "",
        "recording_id": "mbid-studio-002",
        "length": 216250,
        "releases": [
            {
                "id": "rel-album-2",
                "title": "Save Me, San Francisco",
                "status": "Official",
                "release-group": {
                    "id": "rg-album-2",
                    "primary-type": "Album",
                    "secondary-types": [],
                },
            }
        ],
    }

    class MockProvider:
        def get_metadata(self, mbid: str):
            if mbid == "mbid-remix-001":
                return cand_remix
            if mbid == "mbid-studio-002":
                return cand_studio
            return None

    provider = MockProvider()

    best_meta, best_mbid, conf = select_best_acoustid_recording(
        candidate_mbids=["mbid-remix-001", "mbid-studio-002"],
        file_duration_ms=216000,
        metadata_provider=provider,
        baseline_title="Hey, Soul Sister",
        filename="Hey, Soul Sister.flac",
        max_duration_delta_ms=2000,
    )

    assert best_mbid == "mbid-studio-002"
    assert best_meta is not None
    assert best_meta["recording_id"] == "mbid-studio-002"
    assert best_meta["title"] == "Hey, Soul Sister"


def test_enhance_track_delegates_to_metadata_resolution_engine_and_persists_atomically(
    tmp_path, monkeypatch
):
    """Verify RetroactiveEnhancer.enhance_track delegates to MetadataResolutionEngine

    and atomically writes chromaprint and acoustid_id to the database.
    """
    from database.music_database import (
        Artist,
        AudioFingerprint,
        Base,
        LocalMedia,
        MusicDatabase,
        Track,
    )

    db_path = str(tmp_path / "test_enhance_track.db")
    db = MusicDatabase(db_path)
    Base.metadata.create_all(db.engine)

    fake_file = tmp_path / "midnight_city.flac"
    fake_file.write_bytes(b"dummy audio flac data")

    with db.session_scope() as session:
        artist = Artist(name="M83")
        session.add(artist)
        session.flush()

        track = Track(
            title="Midnight City",
            artist_id=artist.id,
            duration=243000,
            sync_id="sync_m83_001",
        )
        session.add(track)
        session.flush()
        track_id = track.id

        media = LocalMedia(
            track_id=track.id,
            file_path=str(fake_file),
            file_format="flac",
            media_id="media_m83_001",
        )
        session.add(media)

    monkeypatch.setattr("database.music_database.get_database", lambda: db)
    monkeypatch.setattr("database.get_database", lambda: db)

    # Mock tagging write
    tagged_files = []
    monkeypatch.setattr(
        "services.metadata_enhancer.RetroactiveEnhancer.tag_file_verified",
        lambda self, p, tags: tagged_files.append((p, tags)),
    )

    # Mock echosync_core.extract_metadata
    import echosync_core

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Midnight City",
            "artist": "M83",
            "duration_ms": 243000,
            "channels": 2,
        },
    )

    dummy_cp = "E" * 60
    from core.matching_engine.fingerprinting import FingerprintGenerator

    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (dummy_cp, 243.0),
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid_m83_win",
        "mbids": ["mbid_m83_midnight"],
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = {
        "title": "Midnight City",
        "artist": "M83",
        "album": "Hurry Up, We're Dreaming",
        "release_id": "rel_m83_huwd",
        "length": 243000,
        "release_group": {"primary_type": "Album"},
    }

    from core.enums import Capability

    enhancer = RetroactiveEnhancer()
    monkeypatch.setattr(
        enhancer,
        "_get_plugin",
        lambda cap, **kw: mock_acoustid
        if cap == Capability.RESOLVE_FINGERPRINT
        else mock_mb,
    )
    monkeypatch.setattr(enhancer, "_get_mb_plugin", lambda: mock_mb)

    with db.session_scope() as session:
        result = enhancer.enhance_track(track_id, session=session)

    assert result is not None
    assert result.musicbrainz_track_id == "mbid_m83_midnight"
    assert result.acoustid_id == "acoustid_m83_win"
    assert result.chromaprint == dummy_cp
    assert result.confidence_score == 0.95

    with db.session_scope() as session:
        db_track = session.get(Track, track_id)
        assert db_track.musicbrainz_id == "mbid_m83_midnight"
        assert db_track.metadata_status.get("enhanced") is True

        db_fp = (
            session.query(AudioFingerprint).filter_by(media_id="media_m83_001").first()
        )
        assert db_fp is not None
        assert db_fp.chromaprint == dummy_cp
        assert db_fp.acoustid_id == "acoustid_m83_win"


