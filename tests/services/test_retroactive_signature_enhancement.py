from unittest.mock import MagicMock

import pytest
from sqlalchemy import or_

from core.database.repositories.track_repo import TrackRepository
from database.music_database import Album, Artist, Base, LocalMedia, MusicDatabase, Track
from services.metadata_enhancer import build_native_tag_payload
from services.retroactive_metadata_worker import run_retroactive_metadata_worker


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_signature.db"
    db = MusicDatabase(str(db_file))
    Base.metadata.create_all(db.engine)
    return db


def test_track_hybrid_properties_orm_and_sql(test_db):
    """Verify Track hybrid properties: echosync_signature, metadata_enhanced, musicbrainz_track_id."""
    with test_db.session_scope() as session:
        artist = Artist(name="Daft Punk")
        session.add(artist)
        session.flush()

        t1 = Track(
            title="One More Time",
            artist_id=artist.id,
            musicbrainz_id="mbid-111",
            metadata_status={"enhanced": True, "echosync_signature": "sig-aaa"},
        )
        t2 = Track(
            title="Aerodynamic",
            artist_id=artist.id,
            musicbrainz_id="mbid-222",
            metadata_status={"enhanced": True},  # Missing signature
        )
        t3 = Track(
            title="Digital Love",
            artist_id=artist.id,
            musicbrainz_id=None,
            metadata_status={"enhanced": False},
        )
        session.add_all([t1, t2, t3])

    with test_db.session_scope() as session:
        # 1. Getter tests
        track1 = session.query(Track).filter_by(title="One More Time").first()
        assert track1.metadata_enhanced is True
        assert track1.echosync_signature == "sig-aaa"
        assert track1.musicbrainz_track_id == "mbid-111"

        track2 = session.query(Track).filter_by(title="Aerodynamic").first()
        assert track2.metadata_enhanced is True
        assert track2.echosync_signature is None
        assert track2.musicbrainz_track_id == "mbid-222"

        # 2. Setter tests
        track2.echosync_signature = "sig-bbb"
        track2.metadata_enhanced = True
        track2.musicbrainz_track_id = "mbid-updated"
        session.flush()
        assert track2.metadata_status.get("echosync_signature") == "sig-bbb"
        assert track2.musicbrainz_id == "mbid-updated"

        # 3. SQL expression filtering
        # Filter for tracks missing signature
        missing_sig = (
            session.query(Track)
            .filter(
                or_(
                    Track.echosync_signature.is_(None),
                    Track.echosync_signature == "",
                )
            )
            .all()
        )
        assert len(missing_sig) == 1
        assert missing_sig[0].title == "Digital Love"

        # Filter by musicbrainz_track_id IS NULL
        missing_mbid = session.query(Track).filter(Track.musicbrainz_track_id.is_(None)).all()
        assert len(missing_mbid) == 1
        assert missing_mbid[0].title == "Digital Love"


def test_candidate_selection_yields_tracks_missing_signature_when_check_all_files_false(test_db, monkeypatch):
    """Verify get_tracks_for_enhancement yields tracks missing echosync_signature even with check_all_files=False."""
    from core.hook_manager import hook_manager

    monkeypatch.setattr(
        hook_manager,
        "apply_filters",
        lambda event, initial, *args, **kwargs: [] if event == "register_metadata_requirements" else initial,
    )

    with test_db.session_scope() as session:
        artist = Artist(name="Daft Punk")
        album = Album(title="Discovery", artist=artist)
        session.add_all([artist, album])
        session.flush()

        # Track 1: Fully enhanced with v2.5 signature
        t1 = Track(
            title="One More Time",
            artist_id=artist.id,
            album_id=album.id,
            musicbrainz_id="mbid-111",
            metadata_status={"enhanced": True, "echosync_signature": "sig-complete"},
        )
        # Track 2: Legacy enhanced track (has MBID and enhanced: True, but lacks echosync_signature)
        t2 = Track(
            title="Harder Better Faster Stronger",
            artist_id=artist.id,
            album_id=album.id,
            musicbrainz_id="mbid-222",
            metadata_status={"enhanced": True},
        )
        # Track 3: Unenhanced track (no MBID)
        t3 = Track(
            title="Crescendolls",
            artist_id=artist.id,
            album_id=album.id,
            musicbrainz_id=None,
            metadata_status={"enhanced": False},
        )
        session.add_all([t1, t2, t3])
        session.flush()

        m1 = LocalMedia(track_id=t1.id, file_path="/music/t1.flac", file_format="flac", media_id="m1")
        m2 = LocalMedia(track_id=t2.id, file_path="/music/t2.flac", file_format="flac", media_id="m2")
        m3 = LocalMedia(track_id=t3.id, file_path="/music/t3.flac", file_format="flac", media_id="m3")
        session.add_all([m1, m2, m3])

    with test_db.session_scope() as session:
        # A. When require_signature=False: Legacy track t2 (enhanced: True, MBID present) is skipped
        legacy_candidates = TrackRepository.get_tracks_for_enhancement(
            session, batch_size=10, check_all_files=False, require_signature=False
        )
        candidate_ids = [t.id for t in legacy_candidates]
        assert t2.id not in candidate_ids
        assert t3.id in candidate_ids
        assert t1.id not in candidate_ids

        # B. When require_signature=True: Legacy track t2 IS yielded because it lacks echosync_signature
        sig_candidates = TrackRepository.get_tracks_for_enhancement(
            session, batch_size=10, check_all_files=False, require_signature=True
        )
        sig_candidate_ids = [t.id for t in sig_candidates]
        assert t2.id in sig_candidate_ids
        assert t3.id in sig_candidate_ids
        assert t1.id not in sig_candidate_ids  # t1 has valid signature and is skipped


def test_build_native_tag_payload_includes_echosync_signature():
    """Verify build_native_tag_payload exports echosync_signature and ECHOSYNC_SIGNATURE."""
    track = {
        "title": "Starboy",
        "artist": "The Weeknd",
        "album": "Starboy",
        "musicbrainz_track_id": "mbid-starboy",
        "echosync_signature": "blake3_signature_test_12345",
    }
    payload = build_native_tag_payload(track)
    assert payload["echosync_signature"] == "blake3_signature_test_12345"
    assert payload["ECHOSYNC_SIGNATURE"] == "blake3_signature_test_12345"


def test_retroactive_metadata_worker_two_phase_execution(monkeypatch):
    """Verify run_retroactive_metadata_worker executes Phase 1 fingerprinting and Phase 2 signature enhancement."""
    mock_enhancer = MagicMock()
    monkeypatch.setattr(
        "services.retroactive_metadata_worker.RetroactiveEnhancer",
        lambda: mock_enhancer,
    )

    run_retroactive_metadata_worker(
        batch_size=25,
        check_all_files=False,
        limit=100,
        force_refresh=False,
        require_signature=True,
    )

    # Phase 1: backfill_missing_fingerprints was called
    mock_enhancer.backfill_missing_fingerprints.assert_called_once()
    assert mock_enhancer.backfill_missing_fingerprints.call_args.kwargs["batch_size"] == 25

    # Phase 2: enhance_library_metadata was called with require_signature=True
    mock_enhancer.enhance_library_metadata.assert_called_once_with(
        batch_size=25,
        check_all_files=False,
        limit=100,
        force_refresh=False,
        require_signature=True,
    )
