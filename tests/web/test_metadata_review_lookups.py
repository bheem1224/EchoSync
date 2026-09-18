from unittest.mock import MagicMock, patch

from core.db.echo_sync_track import EchosyncTrack
from database.working_database import ReviewTask, get_working_database
from web.routes.metadata_review import (
    MusicBrainzLookupRequest,
    lookup_review_queue_item_musicbrainz,
)


def test_musicbrainz_lookup_response_structure_on_match(tmp_path):
    file_path = tmp_path / "song.mp3"
    file_path.write_bytes(b"fake audio data")

    db = get_working_database()
    with db.session_scope() as session:
        task = ReviewTask(
            file_path=str(file_path),
            status="pending",
            track_data={"artist_name": "Adele", "title": "Hello"},
        )
        session.add(task)
        session.flush()
        task_id = task.id

    found_track = EchosyncTrack(
        raw_title="Hello",
        artist_name="Adele",
        album_title="25",
        release_year=2015,
        musicbrainz_id="mbid-12345",
    )

    with (
        patch("web.routes.metadata_review.plugin_loader.get_plugin") as mock_get_plugin,
        patch(
            "web.routes.metadata_review._musicbrainz_text_search",
            return_value=found_track,
        ),
    ):
        mock_provider = MagicMock()
        mock_get_plugin.return_value = mock_provider

        req = MusicBrainzLookupRequest(metadata={"artist": "Adele", "title": "Hello"})
        res = lookup_review_queue_item_musicbrainz(task_id, req)

        assert res["success"] is True
        assert res["match_found"] is True
        assert "title" in res["updated_fields"]
        assert "artist" in res["updated_fields"]
        assert "album" in res["updated_fields"]
        assert res["message"] == "Match found"
        assert res["metadata"]["title"] == "Hello"
        assert res["metadata"]["artist"] == "Adele"


def test_musicbrainz_lookup_response_structure_on_no_match(tmp_path):
    file_path = tmp_path / "unknown.mp3"
    file_path.write_bytes(b"fake audio data")

    db = get_working_database()
    with db.session_scope() as session:
        task = ReviewTask(
            file_path=str(file_path),
            status="pending",
            track_data={"artist_name": "Nonexistent", "title": "SongXYZ"},
        )
        session.add(task)
        session.flush()
        task_id = task.id

    with (
        patch("web.routes.metadata_review.plugin_loader.get_plugin") as mock_get_plugin,
        patch("web.routes.metadata_review._musicbrainz_text_search", return_value=None),
    ):
        mock_provider = MagicMock()
        mock_get_plugin.return_value = mock_provider

        req = MusicBrainzLookupRequest(metadata={"artist": "Nonexistent", "title": "SongXYZ"})
        res = lookup_review_queue_item_musicbrainz(task_id, req)

        assert res["success"] is True
        assert res["match_found"] is False
        assert res["updated_fields"] == []
        assert res["message"] == "No matching record found in database"


def test_acoustid_contribution_trigger_on_approval(tmp_path):
    from web.routes.metadata_review import _submit_acoustid_contribution_async

    mock_provider = MagicMock()
    with patch(
        "web.routes.metadata_review.get_plugin_by_capability",
        return_value=mock_provider,
    ):
        # Valid UUID and fingerprint
        _submit_acoustid_contribution_async(
            fingerprint="AQAAZEmSJVkSRUkC",
            duration=180,
            mbid="8543e49e-b79e-4e4b-a25e-38d5e8964e52",
        )
        mock_provider.queue_fingerprint_submission.assert_called_once_with(
            fingerprint="AQAAZEmSJVkSRUkC",
            duration=180,
            mbid="8543e49e-b79e-4e4b-a25e-38d5e8964e52",
        )


def test_import_single_file_updates_existing_track_and_local_media(tmp_path):
    from database import _canonicalize_path
    from database.music_database import Album, Artist, Base, LocalMedia, Track, get_database
    from database.working_database import WorkingBase, get_working_database
    from web.routes.metadata_review import _import_single_file

    music_db = get_database()
    Base.metadata.create_all(music_db.engine)
    WorkingBase.metadata.create_all(get_working_database().engine)

    old_file = tmp_path / "old_artist" / "old_album" / "song.flac"
    old_file.parent.mkdir(parents=True, exist_ok=True)
    old_file.write_bytes(b"audio")

    new_file = tmp_path / "new_artist" / "new_album" / "song.flac"
    new_file.parent.mkdir(parents=True, exist_ok=True)
    new_file.write_bytes(b"audio")

    import uuid

    test_sid = f"sid_{uuid.uuid4().hex[:12]}"
    test_mid = f"mid_{uuid.uuid4().hex[:12]}"

    # Seed an existing track with Unknown Artist
    with music_db.session_scope() as session:
        artist = Artist(name="Unknown Artist", normalized_name="unknown artist")
        album = Album(title="Unknown Album", normalized_title="unknown album", artist=artist)
        track = Track(
            title="Black Rover",
            normalized_title="black rover",
            sync_id=test_sid,
            artist=artist,
            album=album,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=track.id,
            media_id=test_mid,
            file_path=_canonicalize_path(str(old_file)),
            file_format="flac",
        )
        session.add(media)
        session.commit()
        track_id = track.id

    # Call _import_single_file simulating review approval relocation
    metadata_to_apply = {
        "title": "Black Rover",
        "artist": "ビッケブランカ",
        "album": "ウララ",
        "year": 2018,
        "musicbrainz_id": "mbid-rover-123",
    }

    _import_single_file(new_file, metadata_to_apply, old_file_path=old_file)

    # Verify track and local_media were updated in-place without duplicate
    with music_db.session_scope() as session:
        updated_track = session.get(Track, track_id)
        assert updated_track is not None
        assert updated_track.title == "Black Rover"
        assert updated_track.artist.name == "ビッケブランカ"
        assert updated_track.album.title == "ウララ"
        assert updated_track.musicbrainz_id == "mbid-rover-123"

        updated_media = session.query(LocalMedia).filter_by(track_id=track_id).first()
        assert updated_media is not None
        assert updated_media.file_path == _canonicalize_path(str(new_file))


def test_task_790_manual_review_stale_fingerprint_invalidation_and_title_cleansing(tmp_path):
    from database import _canonicalize_path
    from database.music_database import AudioFingerprint, Base, LocalMedia, get_database
    from database.working_database import ReviewTask, WorkingBase, get_working_database
    from web.routes.metadata_review import lookup_review_queue_item_acoustid
    from core.metadata.schemas import ResolutionResult

    music_db = get_database()
    working_db = get_working_database()
    Base.metadata.create_all(music_db.engine)
    WorkingBase.metadata.create_all(working_db.engine)

    # 1. Setup file named 17 - So Long (21).flac
    file_path = tmp_path / "17 - So Long (21).flac"
    file_path.write_bytes(b"mock flac content")
    canon_path = _canonicalize_path(str(file_path))

    # 2. Seed main_db with Track, LocalMedia, and stale bloated AudioFingerprint (>4000 chars)
    import uuid
    from database.music_database import Album, Artist, Track
    stale_fingerprint = "A" * 5000
    test_sid = f"sid_{uuid.uuid4().hex[:12]}"
    test_mid = f"mid_{uuid.uuid4().hex[:12]}"
    with music_db.session_scope() as session:
        artist = Artist(name="ABBA", normalized_name="abba")
        album = Album(title="ABBA", normalized_title="abba", artist=artist)
        track = Track(
            title="So Long (21)",
            normalized_title="so long (21)",
            sync_id=test_sid,
            artist=artist,
            album=album,
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=track.id,
            media_id=test_mid,
            file_path=canon_path,
            file_format="flac",
        )
        session.add(media)
        session.flush()
        af = AudioFingerprint(
            media_id=media.media_id,
            chromaprint=stale_fingerprint,
        )
        session.add(af)
        session.commit()

    # 3. Seed working_db with ReviewTask 790 containing bloated fingerprint and unscrubbed title
    with working_db.session_scope() as session:
        existing_t = session.get(ReviewTask, 790)
        if existing_t:
            session.delete(existing_t)
            session.flush()

        task = ReviewTask(
            id=790,
            file_path=str(file_path),
            status="pending",
            track_data={
                "raw_title": "So Long (21)",
                "title": "So Long (21)",
                "artist_name": "ABBA",
                "fingerprint": stale_fingerprint,
                "duration": 180000,
            },
            detected_metadata={
                "raw_title": "So Long (21)",
                "title": "So Long (21)",
                "artist": "ABBA",
                "fingerprint": stale_fingerprint,
            },
        )
        session.add(task)
        session.commit()

    clamped_hash = "AQAA_CLAMPED_DSP_HASH"
    captured_req = None

    def fake_resolve_track(req, enabled_stages=None):
        nonlocal captured_req
        captured_req = req
        return ResolutionResult(
            media_id=req.media_id,
            title="So Long",
            artist="ABBA",
            album="ABBA",
            confidence_score=0.95,
            resolution_method="acoustid",
            chromaprint=req.chromaprint,
            musicbrainz_track_id="mbid-solong-123",
            acoustid_id="aid-solong-456",
        )

    # 4. Mock _resolve_task_file, echosync_core.fingerprint_and_hash_audio, and MetadataResolutionEngine.resolve_track
    with (
        patch("web.routes.metadata_review._resolve_task_file", return_value=file_path),
        patch("echosync_core.fingerprint_and_hash_audio", return_value=(clamped_hash, 180.0, "fake_hash")),
        patch("core.metadata.engine.MetadataResolutionEngine.resolve_track", side_effect=fake_resolve_track),
    ):
        res = lookup_review_queue_item_acoustid(790)

    # 5. Verify assertions
    assert res["success"] is True
    assert res["match_found"] is True
    assert res["metadata"]["title"] == "So Long"

    # Verify request sent to engine cleansed copy marker and track number
    assert captured_req is not None
    assert captured_req.baseline_title == "So Long"
    assert captured_req.chromaprint == clamped_hash
    assert len(captured_req.chromaprint) <= 4000

    # Verify task in working_db was updated with clamped fingerprint
    with working_db.session_scope() as session:
        t = session.get(ReviewTask, 790)
        assert t.track_data["fingerprint"] == clamped_hash
        assert len(t.track_data["fingerprint"]) <= 4000

    # Verify AudioFingerprint in main_db was updated with clamped fingerprint
    with music_db.session_scope() as session:
        af_rec = session.query(AudioFingerprint).filter_by(media_id=test_mid).first()
        assert af_rec is not None
        assert af_rec.chromaprint == clamped_hash
        assert len(af_rec.chromaprint) <= 4000


def test_task_828_legitimate_dense_fingerprint_preserved_without_invalidation(tmp_path):
    """Verifies that legitimate 120s clamped fingerprints (e.g. len=3658 for dynamic music)

    are NOT invalidated or discarded as stale, and are preserved and passed to AcoustID.
    """
    from database.music_database import Base, get_database
    from database.working_database import ReviewTask, WorkingBase, get_working_database
    from web.routes.metadata_review import lookup_review_queue_item_acoustid
    from core.metadata.schemas import ResolutionResult

    music_db = get_database()
    working_db = get_working_database()
    Base.metadata.create_all(music_db.engine)
    WorkingBase.metadata.create_all(working_db.engine)

    file_path = tmp_path / "03 - Shut Up and Dance.flac"
    file_path.write_bytes(b"mock flac content")

    legitimate_dense_fp = "B" * 3658

    with working_db.session_scope() as session:
        task = ReviewTask(
            file_path=str(file_path),
            status="pending",
            track_data={
                "raw_title": "03 - Shut Up and Dance",
                "title": "Shut Up and Dance",
                "artist_name": "WALK THE MOON",
                "fingerprint": legitimate_dense_fp,
                "duration": 199040,
            },
            detected_metadata={
                "title": "Shut Up and Dance",
                "artist": "WALK THE MOON",
                "fingerprint": legitimate_dense_fp,
            },
        )
        session.add(task)
        session.flush()
        task_id = task.id

    captured_req = None

    def fake_resolve_track(req, enabled_stages=None):
        nonlocal captured_req
        captured_req = req
        return ResolutionResult(
            media_id=req.media_id,
            title="Shut Up and Dance",
            artist="WALK THE MOON",
            album="TALKING IS HARD",
            confidence_score=0.95,
            resolution_method="acoustid",
            chromaprint=req.chromaprint,
            musicbrainz_track_id="mbid-shut-up-dance-123",
            acoustid_id="aid-shut-up-dance-456",
        )

    with (
        patch("web.routes.metadata_review._resolve_task_file", return_value=file_path),
        patch("core.metadata.engine.MetadataResolutionEngine.resolve_track", side_effect=fake_resolve_track),
    ):
        res = lookup_review_queue_item_acoustid(task_id)

    assert res["success"] is True
    assert res["match_found"] is True
    assert captured_req is not None
    # Fingerprint was NOT invalidated or set to None
    assert captured_req.chromaprint == legitimate_dense_fp
    assert len(captured_req.chromaprint) == 3658



