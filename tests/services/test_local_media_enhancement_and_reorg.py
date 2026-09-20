import os
from unittest.mock import patch

from core.database.repositories.track_repo import MediaTrackTuple, TrackRepository
from core.db.echo_sync_track import EchosyncTrack
from core.matching_engine.fingerprinting import FingerprintMatcher
from core.metadata.adapter import reconcile_media_assignment
from core.path_formatter import ensure_path_invariance
from database.music_database import Album, Artist, AudioFingerprint, Base, LocalMedia, MusicDatabase, Track


def test_media_track_tuple_properties_and_unpacking():
    """Verify MediaTrackTuple supports unpacking, indexing, and transparent attribute delegation."""
    class DummyMedia:
        id = 42
        media_id = "m-42"
        file_path = "/path/to/song.flac"

    class DummyTrack:
        id = 99
        title = "Test Song"

    m = DummyMedia()
    t = DummyTrack()
    tuple_obj = MediaTrackTuple(m, t)

    # Tuple unpacking
    media_out, track_out = tuple_obj
    assert media_out is m
    assert track_out is t

    # Indexing
    assert tuple_obj[0] is m
    assert tuple_obj[1] is t

    # Explicit properties
    assert tuple_obj.media is m
    assert tuple_obj.track is t

    # Attribute delegation to LocalMedia
    assert tuple_obj.id == 42
    assert tuple_obj.media_id == "m-42"
    assert tuple_obj.file_path == "/path/to/song.flac"


def test_stream_media_for_enhancement_batches(tmp_path):
    """Verify stream_media_for_enhancement streams media in bounded batches."""
    music_db = MusicDatabase(tmp_path / "music.db")
    Base.metadata.create_all(music_db.engine)

    with music_db.session_scope() as session:
        artist = Artist(name="Stream Artist", normalized_name="stream artist")
        album = Album(title="Stream Album", normalized_title="stream album", artist=artist)
        session.add_all([artist, album])
        session.flush()

        for i in range(5):
            t = Track(
                title=f"Stream Track {i}",
                normalized_title=f"stream track {i}",
                sync_id=f"stream-sync-{i}",
                artist_id=artist.id,
                album_id=album.id,
                musicbrainz_id=None,
            )
            session.add(t)
            session.flush()
            m = LocalMedia(
                track_id=t.id,
                media_id=f"stream-media-{i}",
                file_path=f"/music/stream_track_{i}.flac",
                file_format="flac",
            )
            session.add(m)
            session.flush()

        # Stream with batch_size=2 and limit=3
        items = list(TrackRepository.stream_media_for_enhancement(session, batch_size=2, limit=3))
        assert len(items) == 3
        for item in items:
            assert isinstance(item, MediaTrackTuple)
            media, track = item
            assert media is not None
            assert track is not None
            assert item.id == media.id


def test_reconcile_by_title_artist_edition_and_duration(tmp_path):
    """Verify reconcile_media_assignment collapses by title, artist, edition within +-3s when similarity >= 0.90."""
    music_db = MusicDatabase(tmp_path / "music.db")
    Base.metadata.create_all(music_db.engine)

    with music_db.session_scope() as session:
        artist = Artist(name="Daft Punk", normalized_name="daft punk")
        album = Album(title="Discovery", normalized_title="discovery", artist=artist)
        session.add_all([artist, album])
        session.flush()

        # Existing Canonical Track with edition "Radio Edit" and duration 240000 ms
        canonical_track = Track(
            title="One More Time",
            normalized_title="one more time",
            sync_id="canonical-sync-1",
            artist_id=artist.id,
            album_id=album.id,
            edition="Radio Edit",
            duration=240000,
            musicbrainz_id=None,
        )
        session.add(canonical_track)
        session.flush()

        canonical_media = LocalMedia(
            track_id=canonical_track.id,
            media_id="can-media-1",
            file_path="/music/One More Time (Radio Edit).flac",
            file_format="flac",
        )
        session.add(canonical_media)
        session.flush()

        canonical_fp = AudioFingerprint(
            media_id=canonical_media.media_id,
            chromaprint="CHROMAPRINT_RADIO_EDIT_CANONICAL",
        )
        session.add(canonical_fp)
        session.flush()

        # New incoming Track to reconcile (duration 241500 ms, within 3.0s delta)
        incoming_track = Track(
            title="One More Time",
            normalized_title="one more time",
            sync_id="incoming-sync-2",
            artist_id=artist.id,
            album_id=album.id,
            edition="Radio Edit",
            duration=241500,
        )
        session.add(incoming_track)
        session.flush()

        incoming_media = LocalMedia(
            track_id=incoming_track.id,
            media_id="inc-media-2",
            file_path="/incoming/One More Time (Radio Edit).mp3",
            file_format="mp3",
        )
        session.add(incoming_media)
        session.flush()

        dto = EchosyncTrack(
            raw_title="One More Time",
            artist_name="Daft Punk",
            edition="Radio Edit",
            duration=241500,
        )

        # Case A: Chromaprint similarity >= 0.90 -> Collapses into canonical_track
        with patch.object(FingerprintMatcher, "get_confidence_score", return_value=0.95):
            res_track = reconcile_media_assignment(
                session=session,
                media=incoming_media,
                enhanced_dto=dto,
                current_chromaprint="CHROMAPRINT_RADIO_EDIT_INCOMING",
            )
            assert res_track.id == canonical_track.id
            assert incoming_media.track_id == canonical_track.id
            # Incoming track row was orphaned and should be pruned
            assert session.get(Track, incoming_track.id) is None


def test_reorganize_library_on_enhancement_setting_and_path_refresh(tmp_path):
    """Verify physical file relocation and mtime/file_size update when reorganize_library_on_enhancement is enabled."""
    music_db = MusicDatabase(tmp_path / "music.db")
    Base.metadata.create_all(music_db.engine)

    library_dir = tmp_path / "library"
    library_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = tmp_path / "staging"
    staging_dir.mkdir(parents=True, exist_ok=True)

    test_file = staging_dir / "raw_track.flac"
    test_file.write_bytes(b"flac audio data for test")
    initial_mtime = 1234567.0
    os.utime(test_file, (initial_mtime, initial_mtime))

    with music_db.session_scope() as session:
        artist = Artist(name="Artist Alpha", normalized_name="artist alpha")
        album = Album(title="Album Beta", normalized_title="album beta", artist=artist)
        session.add_all([artist, album])
        session.flush()

        track = Track(
            title="Track Gamma",
            normalized_title="track gamma",
            sync_id="sync-reorg-1",
            artist_id=artist.id,
            album_id=album.id,
            echosync_signature="valid_sig_reorg",
            track_number=1,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=track.id,
            media_id="m-reorg-1",
            file_path=str(test_file),
            file_format="flac",
            mtime=initial_mtime,
            file_size_bytes=len(b"flac audio data for test"),
        )
        session.add(media)
        session.flush()

        from core.io_gatekeeper import Gatekeeper

        orig_roots = Gatekeeper._get_default_allowed_roots

        def mock_roots(gk_self):
            roots = orig_roots(gk_self)
            roots.append(tmp_path.resolve())
            return roots

        # Test Case 1: When disabled -> File does NOT move
        with (
            patch("core.path_formatter.get_reorganize_library_on_enhancement", return_value=False),
            patch("core.settings.config_manager.get", return_value=str(library_dir)),
            patch.object(Gatekeeper, "_get_default_allowed_roots", side_effect=mock_roots, autospec=True),
        ):
            target = ensure_path_invariance(session, track, media)
            assert target == test_file
            assert test_file.exists()

        # Test Case 2: When enabled -> File moves, media.file_path, mtime, and file_size_bytes update
        with (
            patch("core.path_formatter.get_reorganize_library_on_enhancement", return_value=True),
            patch("core.settings.config_manager.get", return_value=str(library_dir)),
            patch.object(Gatekeeper, "_get_default_allowed_roots", side_effect=mock_roots, autospec=True),
        ):
            target = ensure_path_invariance(session, track, media)
            assert target != test_file
            assert target.exists()
            assert not test_file.exists()
            assert media.file_path == str(target)
            assert media.file_size_bytes == len(b"flac audio data for test")
            assert media.mtime == target.stat().st_mtime


def test_orphan_track_pruning_in_enhancement_loop(tmp_path):
    """Verify orphaned tracks left with 0 media files are pruned by the enhancement commit loop."""
    from services.metadata_enhancer import RetroactiveEnhancer
    from core.metadata.schemas import ResolutionResult

    music_db = MusicDatabase(tmp_path / "music.db")
    Base.metadata.create_all(music_db.engine)

    audio_file = tmp_path / "song.flac"
    audio_file.write_bytes(b"dummy audio for orphan test")

    with music_db.session_scope() as session:
        artist = Artist(name="Artist One", normalized_name="artist one")
        album = Album(title="Album One", normalized_title="album one", artist=artist)
        session.add_all([artist, album])
        session.flush()

        # Track 1: Canonical track needing enhancement
        t1 = Track(
            title="Hit Song",
            normalized_title="hit song",
            sync_id="canonical-hit",
            artist_id=artist.id,
            album_id=album.id,
            musicbrainz_id=None,
        )
        session.add(t1)
        session.flush()

        m1 = LocalMedia(
            track_id=t1.id,
            media_id="m-hit-1",
            file_path=str(audio_file),
            file_format="flac",
        )
        session.add(m1)
        session.flush()

        fp1 = AudioFingerprint(media_id=m1.media_id, chromaprint="CHROMAPRINT_HIT")
        session.add(fp1)

        # Track 2: Orphan track with NO media files
        t_orphan = Track(
            title="Orphan Song",
            normalized_title="orphan song",
            sync_id="orphan-sync-999",
            artist_id=artist.id,
            album_id=album.id,
        )
        session.add(t_orphan)
        session.flush()
        orphan_track_id = t_orphan.id

    enhancer = RetroactiveEnhancer()
    mock_res = ResolutionResult(
        title="Hit Song",
        artist="Artist One",
        album="Album One",
        musicbrainz_track_id="mbid-hit-123",
        confidence_score=0.98,
    )

    with (
        patch("database.music_database.get_database", return_value=music_db),
        patch("echosync_core.extract_metadata", return_value={"title": "Hit Song"}),
        patch("echosync_core.fingerprint_and_hash_audio", return_value=("CHROMAPRINT_HIT", 180.0, "pcm_hash_1")),
        patch("core.metadata.engine.MetadataResolutionEngine.resolve_track", return_value=mock_res),
        patch.object(enhancer, "tag_file_verified", return_value={}),
        patch("core.path_formatter.get_reorganize_library_on_enhancement", return_value=False),
    ):
        enhancer._enhance_library_metadata_loop(job_id="test_orphan_job", batch_size=10, limit=1, force_refresh=True)

    with music_db.session_scope() as session:
        # Orphan track should be pruned
        assert session.get(Track, orphan_track_id) is None
        # Canonical track with media still exists
        assert session.get(Track, t1.id) is not None
