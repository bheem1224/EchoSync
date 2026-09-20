import os
from unittest.mock import patch

from core.database.repositories.track_repo import TrackRepository
from core.db.echo_sync_track import EchosyncTrack
from core.metadata.adapter import prune_orphaned_track_if_empty, reconcile_media_assignment
from database.music_database import Album, Artist, AudioFingerprint, Base, LocalMedia, MusicDatabase, Track



def test_get_media_for_enhancement_priorities_and_filtering(tmp_path):
    music_db = MusicDatabase(tmp_path / "music.db")
    Base.metadata.create_all(music_db.engine)

    with music_db.session_scope() as session:
        artist = Artist(name="Test Artist", normalized_name="test artist")
        album = Album(title="Test Album", normalized_title="test album", artist=artist)
        session.add_all([artist, album])
        session.flush()

        # Track 1: missing signature and missing mbid
        t1 = Track(
            title="Track 1",
            normalized_title="track 1",
            sync_id="sync-1",
            artist_id=artist.id,
            album_id=album.id,
            musicbrainz_id=None,
        )
        session.add(t1)
        session.flush()
        m1 = LocalMedia(
            track_id=t1.id,
            media_id="media-1",
            file_path="/music/track1.flac",
            file_format="flac",
        )
        session.add(m1)

        # Track 2: fully enhanced with signature
        t2 = Track(
            title="Track 2",
            normalized_title="track 2",
            sync_id="sync-2",
            artist_id=artist.id,
            album_id=album.id,
            musicbrainz_id="mbid-2",
            metadata_status={"enhanced": True, "echosync_signature": "valid_sig"},
        )
        session.add(t2)
        session.flush()
        m2 = LocalMedia(
            track_id=t2.id,
            media_id="media-2",
            file_path="/music/track2.flac",
            file_format="flac",
        )
        session.add(m2)
        session.flush()

        # Normal pass without force_refresh: returns media 1 (missing mbid)
        candidates = TrackRepository.get_media_for_enhancement(session, batch_size=50)
        assert len(candidates) == 1
        assert candidates[0].id == m1.id

        # Exclude media 1
        candidates_ex = TrackRepository.get_media_for_enhancement(session, batch_size=50, exclude_ids={m1.id})
        assert len(candidates_ex) == 0

        # force_refresh=True: returns both media files
        candidates_forced = TrackRepository.get_media_for_enhancement(session, batch_size=50, force_refresh=True)
        assert len(candidates_forced) == 2



def test_reconcile_media_assignment_collapse_editions(tmp_path):
    music_db = MusicDatabase(tmp_path / "music.db")
    Base.metadata.create_all(music_db.engine)

    with music_db.session_scope() as session:
        artist = Artist(name="Daft Punk", normalized_name="daft punk")
        album = Album(title="Discovery", normalized_title="discovery", artist=artist)
        session.add_all([artist, album])
        session.flush()

        # Canonical Track 1
        t1 = Track(
            title="One More Time",
            normalized_title="one more time",
            sync_id="t1-sync",
            artist_id=artist.id,
            album_id=album.id,
            musicbrainz_id="rec-12345",
        )
        session.add(t1)
        session.flush()

        m1 = LocalMedia(
            track_id=t1.id,
            media_id="m1-id",
            file_path="/music/One More Time (Lossless).flac",
            file_format="flac",
        )
        session.add(m1)
        session.flush()

        fp1 = AudioFingerprint(media_id=m1.media_id, chromaprint="CHROMAPRINT_COMMON_TEST_123")
        session.add(fp1)

        # Duplicate Track 2 (e.g. from MP3 import)
        t2 = Track(
            title="One More Time",
            normalized_title="one more time",
            sync_id="t2-sync",
            artist_id=artist.id,
            album_id=album.id,
            musicbrainz_id=None,
        )
        session.add(t2)
        session.flush()

        m2 = LocalMedia(
            track_id=t2.id,
            media_id="m2-id",
            file_path="/music/One More Time (Radio Edit).mp3",
            file_format="mp3",
        )
        session.add(m2)
        session.flush()

        # Enhanced DTO resolved for m2 matching t1's MBID
        dto = EchosyncTrack(
            raw_title="One More Time (Radio Edit)",
            artist_name="Daft Punk",
            album_title="Discovery",
            musicbrainz_id="rec-12345",
        )

        with patch("core.matching_engine.fingerprinting.FingerprintMatcher.get_confidence_score", return_value=0.98):
            reconciled = reconcile_media_assignment(
                session=session,
                media=m2,
                enhanced_dto=dto,
                current_chromaprint="CHROMAPRINT_COMMON_TEST_123",
            )

        # m2 should now be collapsed under t1
        assert reconciled.id == t1.id
        assert m2.track_id == t1.id

        # Orphaned t2 should be pruned
        assert session.get(Track, t2.id) is None


def test_reconcile_media_assignment_decouple_diverging(tmp_path):
    music_db = MusicDatabase(tmp_path / "music.db")
    Base.metadata.create_all(music_db.engine)

    with music_db.session_scope() as session:
        artist = Artist(name="Daft Punk", normalized_name="daft punk")
        album = Album(title="Discovery", normalized_title="discovery", artist=artist)
        session.add_all([artist, album])
        session.flush()

        # Track 1 has TWO media files erroneously grouped
        t1 = Track(
            title="Aerodynamic",
            normalized_title="aerodynamic",
            sync_id="t1-sync",
            artist_id=artist.id,
            album_id=album.id,
            musicbrainz_id="rec-aerodynamic",
        )
        session.add(t1)
        session.flush()

        m1 = LocalMedia(
            track_id=t1.id,
            media_id="m1-id",
            file_path="/music/Aerodynamic.flac",
            file_format="flac",
        )
        m2 = LocalMedia(
            track_id=t1.id,
            media_id="m2-id",
            file_path="/music/Digital Love.flac",
            file_format="flac",
        )
        session.add_all([m1, m2])
        session.flush()

        fp1 = AudioFingerprint(media_id=m1.media_id, chromaprint="CP_AERODYNAMIC")
        session.add(fp1)
        session.flush()

        # m2 resolves to Digital Love (different MBID & acoustic identity)
        dto_digital_love = EchosyncTrack(
            raw_title="Digital Love",
            artist_name="Daft Punk",
            album_title="Discovery",
            musicbrainz_id="rec-digital-love",
        )

        with patch("core.matching_engine.fingerprinting.FingerprintMatcher.get_confidence_score", return_value=0.20):
            decoupled_track = reconcile_media_assignment(
                session=session,
                media=m2,
                enhanced_dto=dto_digital_love,
                current_chromaprint="CP_DIGITAL_LOVE",
            )

        # m2 should now be decoupled into its own track
        assert decoupled_track.id != t1.id
        assert m2.track_id == decoupled_track.id
        assert decoupled_track.title == "Digital Love"
        assert decoupled_track.musicbrainz_id == "rec-digital-love"

        # m1 remains under t1
        assert m1.track_id == t1.id
        assert session.get(Track, t1.id) is not None


def test_prune_orphaned_track_if_empty(tmp_path):
    music_db = MusicDatabase(tmp_path / "music.db")
    Base.metadata.create_all(music_db.engine)

    with music_db.session_scope() as session:
        artist = Artist(name="Solo Artist", normalized_name="solo artist")
        album = Album(title="Solo Album", normalized_title="solo album", artist=artist)
        session.add_all([artist, album])
        session.flush()

        track = Track(
            title="Orphan Track",
            normalized_title="orphan track",
            sync_id="orphan-sync",
            artist_id=artist.id,
            album_id=album.id,
        )
        session.add(track)
        session.flush()

        track_id = track.id
        artist_id = artist.id
        album_id = album.id

        # No LocalMedia attached: pruning should remove track, album, and artist
        pruned = prune_orphaned_track_if_empty(session, track_id)
        assert pruned is True
        assert session.get(Track, track_id) is None
        assert session.get(Album, album_id) is None
        assert session.get(Artist, artist_id) is None


def test_enhancer_loop_updates_media_mtime_and_file_size(tmp_path):
    from services.metadata_enhancer import RetroactiveEnhancer
    from core.metadata.schemas import ResolutionResult

    music_db = MusicDatabase(tmp_path / "music.db")
    Base.metadata.create_all(music_db.engine)

    # Create dummy physical audio file
    audio_file = tmp_path / "test_track.flac"
    audio_file.write_bytes(b"dummy flac content")
    initial_mtime = 1000000.0
    os.utime(audio_file, (initial_mtime, initial_mtime))

    with music_db.session_scope() as session:
        artist = Artist(name="Unknown", normalized_name="unknown")
        album = Album(title="Unknown", normalized_title="unknown", artist=artist)
        session.add_all([artist, album])
        session.flush()

        track = Track(
            title="Unknown Track",
            normalized_title="unknown track",
            sync_id="sync-test-mtime",
            artist_id=artist.id,
            album_id=album.id,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=track.id,
            media_id="m-mtime-1",
            file_path=str(audio_file),
            file_format="flac",
            mtime=initial_mtime,
            file_size_bytes=len(b"dummy flac content"),
        )
        session.add(media)
        session.flush()

    enhancer = RetroactiveEnhancer()

    # Mock resolution engine and plugins
    mock_res = ResolutionResult(
        title="Resolved Title",
        artist="Resolved Artist",
        album="Resolved Album",
        musicbrainz_track_id="mbid-resolved-1",
        confidence_score=0.95,
    )

    with (
        patch("database.music_database.get_database", return_value=music_db),
        patch("echosync_core.extract_metadata", return_value={"title": "Unknown Track"}),
        patch("echosync_core.fingerprint_and_hash_audio", return_value=("CP_RESOLVED", 180.0, "pcm_hash_1")),
        patch("core.metadata.engine.MetadataResolutionEngine.resolve_track", return_value=mock_res),
        patch.object(
            enhancer,
            "tag_file_verified",
            side_effect=lambda path, tags: audio_file.write_bytes(b"enhanced flac content with tags"),
        ),
    ):
        enhancer._enhance_library_metadata_loop(job_id="test_job", batch_size=10, limit=1)

    with music_db.session_scope() as session:
        updated_media = session.query(LocalMedia).filter_by(media_id="m-mtime-1").first()
        assert updated_media is not None
        # mtime and file_size_bytes should be updated to match the modified file
        assert updated_media.file_size_bytes == len(b"enhanced flac content with tags")
        assert updated_media.mtime != initial_mtime
        assert updated_media.track.title == "Resolved Title"
        assert updated_media.track.musicbrainz_id == "mbid-resolved-1"

