from unittest.mock import MagicMock

from core.enums import Capability
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.metadata.engine import MetadataResolutionEngine
from core.metadata.schemas import ResolutionRequest
from database.music_database import (
    Album,
    Artist,
    AudioFingerprint,
    Base,
    LocalMedia,
    MusicDatabase,
    Track,
)
from services.metadata_enhancer import RetroactiveEnhancer


def test_automated_enhance_track_shawn_mendes_parity(tmp_path, monkeypatch):
    """Verify that automated enhance_track() on '01 - There's Nothing Holdin' Me Back.flac'
    yields the exact ground truth MBID 'd2555d82-571d-406c-8e96-21562753cebc' with confidence >= 0.75,
    matching the hardened manual review workflow.
    """
    music_db = MusicDatabase(tmp_path / "music.db")
    Base.metadata.create_all(music_db.engine)

    file_dir = tmp_path / "data" / "library" / "Shawn Mendes" / "Illuminate"
    file_dir.mkdir(parents=True, exist_ok=True)
    audio_file = file_dir / "01 - There's Nothing Holdin' Me Back.flac"
    audio_file.write_bytes(b"dummy flac content")

    target_mbid = "d2555d82-571d-406c-8e96-21562753cebc"
    mock_chromaprint = "AQABz0mSRIqYJEoUB9_xH_shawn_mendes" * 50

    with music_db.session_scope() as session:
        art = Artist(name="Shawn Mendes", normalized_name="shawn mendes")
        alb = Album(title="Illuminate", normalized_title="illuminate", artist=art)
        session.add_all([art, alb])
        session.flush()

        track = Track(
            id=1001,
            title="Where Were You in the Morning?",  # Dirty/divergent embedded title
            normalized_title="where were you in the morning",
            sync_id="sync_shawn_1001",
            duration=199400,
            musicbrainz_id=None,
            isrc=None,
            artist=art,
            album=alb,
            metadata_status={},
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=1001,
            file_path=str(audio_file),
            file_format="flac",
            media_id="media_shawn_001",
        )
        session.add(media)
        session.flush()

        fp = AudioFingerprint(
            media_id="media_shawn_001",
            chromaprint=mock_chromaprint,
            acoustid_id=None,
        )
        session.add(fp)

    monkeypatch.setattr("database.music_database.get_database", lambda: music_db)
    monkeypatch.setattr("database.get_database", lambda: music_db)
    monkeypatch.setattr("services.metadata_enhancer._tagging_write", lambda p, tags: None)
    monkeypatch.setattr(
        "services.metadata_enhancer.RetroactiveEnhancer.tag_file_verified",
        lambda self, p, tags: None,
    )

    import echosync_core

    monkeypatch.setattr(
        echosync_core,
        "extract_metadata",
        lambda p: {
            "title": "Where Were You in the Morning?",
            "artist": "Shawn Mendes",
            "duration": 199.4,
            "duration_ms": 199400,
        },
    )

    dsp_called = []

    def fake_generate_with_dur(p):
        dsp_called.append(p)
        return (mock_chromaprint, 199.4)

    monkeypatch.setattr(FingerprintGenerator, "generate_with_duration", fake_generate_with_dur)

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid_shawn_uuid",
        "recordings": [
            {
                "id": target_mbid,
                "title": "There's Nothing Holdin' Me Back",
                "artist": "Shawn Mendes",
                "duration": 199.4,
                "score": 0.98,
            },
            {
                "id": "2aeeb920-571d-406c-8e96-21562753cebc",
                "title": "Where Were You in the Morning?",
                "artist": "Shawn Mendes",
                "duration": 199.4,
                "score": 0.94,
            },
        ],
        "mbids": [target_mbid, "2aeeb920-571d-406c-8e96-21562753cebc"],
        "score": 0.98,
    }

    mb_calls = []
    mock_mb = MagicMock()

    def fake_mb_get_metadata(mbid):
        mb_calls.append(mbid)
        if mbid == target_mbid:
            return {
                "title": "There's Nothing Holdin' Me Back",
                "artist": "Shawn Mendes",
                "artist_name": "Shawn Mendes",
                "album": "Illuminate",
                "album_title": "Illuminate",
                "recording_id": target_mbid,
                "length": 199400,
                "duration_ms": 199400,
                "release_group": {"primary_type": "Album"},
            }
        return {
            "title": "Where Were You in the Morning?",
            "artist": "Shawn Mendes",
            "album": "Illuminate",
            "recording_id": mbid,
            "length": 199400,
        }

    mock_mb.get_metadata.side_effect = fake_mb_get_metadata

    enhancer = RetroactiveEnhancer()

    def fake_get_plugin(cap, required_algorithm=None):
        if cap == Capability.RESOLVE_FINGERPRINT:
            return mock_acoustid
        if cap == Capability.FETCH_METADATA:
            return mock_mb
        return None

    monkeypatch.setattr(enhancer, "_get_plugin", fake_get_plugin)
    monkeypatch.setattr(enhancer, "_get_mb_plugin", lambda: mock_mb)
    monkeypatch.setattr(enhancer, "_get_spotify_plugin", lambda: None)

    # Execute automated enhance_track
    with music_db.session_scope() as session:
        result = enhancer.enhance_track(1001, session=session)

    # 1. Parity Assertions
    assert result is not None, "enhance_track must return a ResolutionResult"
    assert result.musicbrainz_track_id == target_mbid, f"Expected {target_mbid}, got {result.musicbrainz_track_id}"
    assert result.title == "There's Nothing Holdin' Me Back"
    assert result.confidence_score >= 0.75, f"Confidence score {result.confidence_score} must be >= 0.75"

    # 2. Rust DSP / Audio Re-decoding Assertions (pre-existing chromaprint reused)
    assert len(dsp_called) == 0, "DSP / Audio re-decoding must be 0 when chromaprint is pre-populated in database"

    # 3. Network Egress Assertions: Clear filename match short-circuits secondary MB queries
    assert len(mb_calls) == 1, f"Expected exactly 1 MusicBrainz call on clear match, got {len(mb_calls)}: {mb_calls}"
    assert mb_calls[0] == target_mbid

    # 4. Database Atomicity Assertions
    with music_db.session_scope() as session:
        db_track = session.get(Track, 1001)
        assert db_track.musicbrainz_id == target_mbid
        assert db_track.title == "There's Nothing Holdin' Me Back"
        assert db_track.metadata_status.get("enhanced") is True

        db_fp = session.query(AudioFingerprint).filter_by(media_id="media_shawn_001").first()
        assert db_fp is not None
        assert db_fp.chromaprint == mock_chromaprint
        assert db_fp.acoustid_id == "acoustid_shawn_uuid"


def test_chromaprint_reuse_bypasses_dsp_and_audio_decoding(tmp_path, monkeypatch):
    """Verify that when ResolutionRequest provides a chromaprint, neither _execute_waterfall
    nor _resolve_acoustid invokes FingerprintGenerator.generate_with_duration.
    """
    audio_file = tmp_path / "test_track.flac"
    audio_file.write_bytes(b"dummy flac content")

    mock_cp = "PRE_COMPUTED_CHROMAPRINT_STRING_12345"
    dsp_called = []

    def mock_dsp(p):
        dsp_called.append(p)
        return ("GENERATED_FINGERPRINT", 180)

    monkeypatch.setattr(FingerprintGenerator, "generate_with_duration", mock_dsp)

    mock_acoustid = MagicMock()
    acoustid_payloads = []

    def mock_resolve_details(fingerprint, duration):
        acoustid_payloads.append((fingerprint, duration))
        return {
            "acoustid_id": "acoustid_test_id",
            "recordings": [
                {
                    "id": "mbid_test_001",
                    "title": "Test Title",
                    "artist": "Test Artist",
                    "duration": 180.0,
                    "score": 0.95,
                }
            ],
            "mbids": ["mbid_test_001"],
            "score": 0.95,
        }

    mock_acoustid.resolve_fingerprint_details.side_effect = mock_resolve_details

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = {
        "title": "Test Title",
        "artist": "Test Artist",
        "album": "Test Album",
        "recording_id": "mbid_test_001",
        "length": 180000,
        "release_group": {"primary_type": "Album"},
    }

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_test_1",
        file_path=audio_file,
        chromaprint=mock_cp,
        duration=180.0,
        duration_ms=180000,
        baseline_title="Test Title",
        baseline_artist="Test Artist",
    )

    result = engine.resolve_track(req)

    assert result is not None
    assert result.musicbrainz_track_id == "mbid_test_001"
    assert result.chromaprint == mock_cp
    # Verify DSP was never invoked
    assert len(dsp_called) == 0, f"FingerprintGenerator was called {len(dsp_called)} times; expected 0."
    # Verify AcoustID received the pre-computed chromaprint
    assert len(acoustid_payloads) == 1
    assert acoustid_payloads[0][0] == mock_cp


def test_musicbrainz_http_call_count_capped_on_clear_match(tmp_path, monkeypatch):
    """Verify that when AcoustID returns multiple candidates, but candidate 1 is a clear
    filename match, MusicBrainz get_metadata is called at most 1 time.
    """
    audio_file = tmp_path / "01 - Radioactive.flac"
    audio_file.write_bytes(b"dummy audio")

    mock_cp = "RADIOACTIVE_CHROMAPRINT"
    monkeypatch.setattr(FingerprintGenerator, "generate_with_duration", lambda p: (mock_cp, 186.0))

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "acoustid_radioactive",
        "recordings": [
            {
                "id": "mbid_radioactive_canon",
                "title": "Radioactive",
                "artist": "Imagine Dragons",
                "duration": 186.0,
                "score": 0.99,
            },
            {
                "id": "mbid_radioactive_alt",
                "title": "Radioactive (Acoustic)",
                "artist": "Imagine Dragons",
                "duration": 186.0,
                "score": 0.95,
            },
            {
                "id": "mbid_radioactive_remix",
                "title": "Radioactive (dMix)",
                "artist": "Imagine Dragons",
                "duration": 186.0,
                "score": 0.90,
            },
        ],
        "mbids": ["mbid_radioactive_canon", "mbid_radioactive_alt", "mbid_radioactive_remix"],
        "score": 0.99,
    }

    mb_calls = []
    mock_mb = MagicMock()

    def track_mb_calls(mbid):
        mb_calls.append(mbid)
        if mbid == "mbid_radioactive_canon":
            return {
                "title": "Radioactive",
                "artist": "Imagine Dragons",
                "album": "Night Visions",
                "recording_id": "mbid_radioactive_canon",
                "length": 186000,
                "release_group": {"primary_type": "Album"},
            }
        return {
            "title": "Radioactive (Acoustic)",
            "artist": "Imagine Dragons",
            "album": "Night Visions (Deluxe)",
            "recording_id": mbid,
            "length": 186000,
        }

    mock_mb.get_metadata.side_effect = track_mb_calls

    engine = MetadataResolutionEngine(
        acoustid_provider=mock_acoustid,
        metadata_provider=mock_mb,
    )

    req = ResolutionRequest(
        media_id="media_radioactive_1",
        file_path=audio_file,
        chromaprint=mock_cp,
        duration=186.0,
        duration_ms=186000,
        baseline_title="Radioactive",
        baseline_artist="Imagine Dragons",
    )

    result = engine.resolve_track(req)

    assert result is not None
    assert result.musicbrainz_track_id == "mbid_radioactive_canon"
    # Crucial assertion: HTTP call count <= 1 when clear filename match exists
    assert len(mb_calls) == 1, f"Expected <= 1 MusicBrainz call, but got {len(mb_calls)}: {mb_calls}"


def test_review_task_to_dict_includes_proposed_and_detected_metadata():
    """Verify that ReviewTask.to_dict() correctly maps both detected_metadata and
    proposed_metadata properties so FastAPI responses preserve both keys.
    """
    from database.working_database import ReviewTask

    task = ReviewTask(
        id=42,
        file_path="/music/Track 01.flac",
        track_data={
            "title": "Song Title",
            "artist": "Artist Name",
            "album": "Album Title",
            "release_year": 2024,
            "mbid": "mbid_12345",
        },
        status="pending",
        confidence_score=0.92,
    )

    d = task.to_dict()

    assert d["id"] == 42
    assert d["file_path"] == "/music/Track 01.flac"
    assert d["media_id"] == "/music/Track 01.flac"
    assert "detected_metadata" in d
    assert "proposed_metadata" in d
    assert d["detected_metadata"]["title"] == "Song Title"
    assert d["proposed_metadata"]["title"] == "Song Title"
    assert d["proposed_metadata"]["musicbrainz_id"] == "mbid_12345"
    assert d["confidence_score"] == 0.92


def test_track_local_media_quality_sorting(tmp_path):
    """Verify that Track.local_media and TrackRepository deterministic quality sorting
    orders media files by (bitrate DESC, sample_rate DESC, bit_depth DESC).
    """
    from core.database.repositories.track_repo import TrackRepository
    from database.music_database import Base, LocalMedia, MusicDatabase, Track

    db = MusicDatabase(tmp_path / "music_sorting.db")
    Base.metadata.create_all(db.engine)

    with db.session_scope() as session:
        art = Artist(id=1, name="Test Artist", normalized_name="test artist")
        session.add(art)
        session.flush()
        t = Track(id=1, title="Test Track", sync_id="sync_qual_1", artist_id=art.id)
        session.add(t)
        session.flush()

        # Add 3 media files: low, medium, high quality
        m_low = LocalMedia(
            track_id=1,
            media_id="m_low",
            file_path="/music/low.mp3",
            file_format="mp3",
            bitrate=128000,
            sample_rate=44100,
            bit_depth=16,
        )
        m_med = LocalMedia(
            track_id=1,
            media_id="m_med",
            file_path="/music/med.mp3",
            file_format="mp3",
            bitrate=320000,
            sample_rate=44100,
            bit_depth=16,
        )
        m_high = LocalMedia(
            track_id=1,
            media_id="m_high",
            file_path="/music/high.flac",
            file_format="flac",
            bitrate=1411000,
            sample_rate=96000,
            bit_depth=24,
        )
        session.add_all([m_low, m_med, m_high])

    with db.session_scope() as session:
        track = session.get(Track, 1)
        assert track is not None
        assert len(track.local_media) == 3
        # In-memory and SQL ordered property: highest bitrate is first
        assert track.local_media[0].media_id == "m_high"
        assert track.local_media[1].media_id == "m_med"
        assert track.local_media[2].media_id == "m_low"

        # Track proxy properties delegate to highest quality
        assert track.file_format == "flac"
        assert track.bitrate == 1411000
        assert track.sample_rate == 96000
        assert track.bit_depth == 24

        # TrackRepository.get_media_for_track returns sorted
        repo_media = TrackRepository.get_media_for_track(session, 1)
        assert [m.media_id for m in repo_media] == ["m_high", "m_med", "m_low"]

        # TrackRepository.get_track_with_media returns sorted
        t_obj, media_list = TrackRepository.get_track_with_media(session, "sync_qual_1")
        assert t_obj is not None
        assert [m.media_id for m in media_list] == ["m_high", "m_med", "m_low"]


def test_track_repo_missing_plugin_filter(tmp_path):
    """Verify that TrackRepository.get_tracks_for_enhancement filters tracks missing a target plugin."""
    from core.database.repositories.track_repo import TrackRepository
    from database.music_database import Base, MusicDatabase, Track

    db = MusicDatabase(tmp_path / "music_plugin.db")
    Base.metadata.create_all(db.engine)

    with db.session_scope() as session:
        art = Artist(id=2, name="Plugin Artist", normalized_name="plugin artist")
        session.add(art)
        session.flush()

        # Track 1: missing all satisfied_plugins, marked enhanced=True
        t1 = Track(
            id=1,
            title="Track 1",
            sync_id="sync_p1",
            artist_id=art.id,
            metadata_enhanced=True,
            metadata_status={"enhanced": True},
        )
        # Track 2: has EchoSync.cjk satisfied
        t2 = Track(
            id=2,
            title="Track 2",
            sync_id="sync_p2",
            artist_id=art.id,
            metadata_enhanced=True,
            metadata_status={"satisfied_plugins": ["EchoSync.cjk"]},
        )
        # Track 3: has other plugin satisfied, but missing EchoSync.cjk
        t3 = Track(
            id=3,
            title="Track 3",
            sync_id="sync_p3",
            artist_id=art.id,
            metadata_enhanced=True,
            metadata_status={"satisfied_plugins": ["EchoSync.other"]},
        )
        # Track 4: no metadata_status at all
        t4 = Track(
            id=4,
            title="Track 4",
            sync_id="sync_p4",
            artist_id=art.id,
            metadata_enhanced=False,
            metadata_status=None,
        )
        session.add_all([t1, t2, t3, t4])
        session.flush()

        for idx, trk_id in enumerate([1, 2, 3, 4], start=1):
            session.add(
                LocalMedia(
                    track_id=trk_id,
                    media_id=f"m_plugin_{idx}",
                    file_path=f"/music/p_{idx}.flac",
                    bitrate=320000,
                )
            )

    with db.session_scope() as session:
        # Query specifically for missing "EchoSync.cjk"
        candidates = TrackRepository.get_tracks_for_enhancement(
            session,
            batch_size=10,
            missing_plugin="EchoSync.cjk",
        )
        candidate_ids = {c.id for c in candidates}
        assert 1 in candidate_ids
        assert 3 in candidate_ids
        assert 4 in candidate_ids
        assert 2 not in candidate_ids  # Track 2 already satisfied EchoSync.cjk


def test_manager_file_mutation_media_id_enforcement():
    """Verify that file mutations (retag, rename) strictly require media_id and return 400 when missing."""
    import pytest
    from fastapi import HTTPException

    from web.routes.manager import RenameFileRequest, RetagRequest, rename_track, retag_track

    # Missing payload
    with pytest.raises(HTTPException) as exc_info:
        retag_track(track_id="1", payload=None)
    assert exc_info.value.status_code == 400
    assert "media_id is required" in exc_info.value.detail

    # Payload with empty media_id
    with pytest.raises(HTTPException) as exc_info:
        retag_track(track_id="1", payload=RetagRequest(media_id="", tags={"title": "New"}))
    assert exc_info.value.status_code == 400
    assert "media_id is required" in exc_info.value.detail

    # Rename missing payload
    with pytest.raises(HTTPException) as exc_info:
        rename_track(track_id="1", payload=None)
    assert exc_info.value.status_code == 400
    assert "media_id is required" in exc_info.value.detail

    # Rename with empty media_id
    with pytest.raises(HTTPException) as exc_info:
        rename_track(track_id="1", payload=RenameFileRequest(media_id="", new_filename="test.flac"))
    assert exc_info.value.status_code == 400
    assert "media_id is required" in exc_info.value.detail


def test_manager_streaming_resolution(tmp_path, monkeypatch):
    """Verify stream_manager_track resolves media_id directly or falls back to track.local_media[0]."""
    from database.music_database import Base, LocalMedia, MusicDatabase, Track
    from web.routes.manager import stream_manager_track

    f_high = tmp_path / "high.flac"
    f_high.write_bytes(b"high audio")
    f_low = tmp_path / "low.mp3"
    f_low.write_bytes(b"low audio")

    db = MusicDatabase(tmp_path / "stream_test.db")
    Base.metadata.create_all(db.engine)

    with db.session_scope() as session:
        art = Artist(id=3, name="Stream Artist", normalized_name="stream artist")
        session.add(art)
        session.flush()
        t = Track(id=10, title="Stream Track", sync_id="sync_stream_10", artist_id=art.id)
        session.add(t)
        session.flush()

        m_low = LocalMedia(
            track_id=10,
            media_id="m_stream_low",
            file_path=str(f_low),
            bitrate=128000,
        )
        m_high = LocalMedia(
            track_id=10,
            media_id="m_stream_high",
            file_path=str(f_high),
            bitrate=320000,
        )
        session.add_all([m_low, m_high])

    monkeypatch.setattr("web.routes.manager.get_database", lambda: db)

    # 1. Resolve explicitly by media_id
    resp_low = stream_manager_track(media_id="m_stream_low")
    assert resp_low.path == str(f_low)

    # 2. Resolve by track_id omitting media_id -> falls back to highest quality
    resp_best = stream_manager_track(track_id="10")
    assert resp_best.path == str(f_high)

    # 3. Resolve by sync_id omitting media_id -> falls back to highest quality
    resp_sync = stream_manager_track(sync_id="sync_stream_10")
    assert resp_sync.path == str(f_high)


def test_retroactive_worker_targeted_plugin_pass(tmp_path, monkeypatch):
    """Verify run_retroactive_metadata_worker with target_plugin runs enrich_plugin_metadata
    and skips Phase 1 DSP fingerprinting.
    """
    from database.music_database import Base, MusicDatabase, Track
    from services.retroactive_metadata_worker import run_retroactive_metadata_worker

    db = MusicDatabase(tmp_path / "worker_plugin.db")
    Base.metadata.create_all(db.engine)

    with db.session_scope() as session:
        art = Artist(id=4, name="Jay Chou", normalized_name="jay chou")
        session.add(art)
        session.flush()
        t = Track(
            id=100,
            title="Anime Song 晴天",
            sync_id="sync_cjk_100",
            artist_id=art.id,
            metadata_enhanced=True,
            metadata_status={"enhanced": True},
        )
        session.add(t)
        session.flush()

        session.add(
            LocalMedia(
                track_id=100,
                media_id="m_cjk_100",
                file_path="/music/cjk_100.flac",
                bitrate=320000,
            )
        )

    monkeypatch.setattr("database.music_database.get_database", lambda: db)
    monkeypatch.setattr("database.get_database", lambda: db)

    fp_called = []
    monkeypatch.setattr(
        "services.metadata_enhancer.RetroactiveEnhancer.backfill_missing_fingerprints",
        lambda self, *a, **kw: fp_called.append(True),
    )

    # Execute worker with target_plugin="EchoSync.cjk"
    run_retroactive_metadata_worker(target_plugin="EchoSync.cjk")

    # Assert Phase 1 was skipped
    assert len(fp_called) == 0

    # Assert track now has satisfied_plugins containing "EchoSync.cjk"
    with db.session_scope() as session:
        updated_track = session.get(Track, 100)
        assert updated_track is not None
        assert updated_track.is_plugin_satisfied("EchoSync.cjk")
        assert "EchoSync.cjk" in updated_track.satisfied_plugins
