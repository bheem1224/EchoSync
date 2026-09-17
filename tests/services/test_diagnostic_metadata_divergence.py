import logging
from unittest.mock import MagicMock

from core.db.echo_sync_track import EchosyncTrack
from core.matching_engine.fingerprinting import FingerprintGenerator
from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import PROFILE_EXACT_SYNC
from database.music_database import (
    Album,
    Artist,
    AudioFingerprint,
    Base,
    LocalMedia,
    MusicDatabase,
    Track,
)
from database.working_database import ReviewTask, WorkingBase, WorkingDatabase
from services.metadata_enhancer import RetroactiveEnhancer
from web.routes.metadata_review import lookup_review_queue_item_acoustid


def test_diagnostic_retroactive_enhancer_divergence_track_2491(tmp_path, monkeypatch, caplog):
    """
    Test 1: RetroactiveEnhancer path for Track 2491 (Resolved).
    Demonstrates:
    - FingerprintGenerator.generate_with_duration() populates duration from audio inspection.
    - Track.duration is populated immediately even if initial database duration was None.
    - AcoustID lookup is NOT bypassed: resolve_fingerprint_details is called with duration=219.
    - AcoustID resolves MBID 4b05f421-21bb-4810-a1f0-53c40dd2952b for 'My Way'.
    - AudioFingerprint is atomically persisted with acoustid_id.
    - Track is updated with canonical title 'My Way' and MBID.
    """
    caplog.set_level(logging.DEBUG)

    music_db = MusicDatabase(tmp_path / "music.db")
    Base.metadata.create_all(music_db.engine)
    working_db = WorkingDatabase(tmp_path / "working.db")
    WorkingBase.metadata.create_all(working_db.engine)

    file_dir = tmp_path / "data" / "library" / "Calvin Harris" / "Chilled House, Session 8"
    file_dir.mkdir(parents=True, exist_ok=True)
    audio_file = file_dir / "00 - My Way.flac"
    audio_file.write_bytes(b"dummy audio content")

    with music_db.session_scope() as session:
        artist_unk = Artist(name="Unknown Artist", normalized_name="unknown artist")
        album_unk = Album(title="Unknown Album", normalized_title="unknown album", artist=artist_unk)
        session.add_all([artist_unk, album_unk])
        session.flush()

        track = Track(
            id=2491,
            title="00 - My Way",
            normalized_title="00 - my way",
            sync_id="sync_2491_test",
            duration=None,  # Crucial: duration is NULL initially in database
            musicbrainz_id=None,
            isrc=None,
            artist=artist_unk,
            album=album_unk,
            metadata_status={},
        )
        session.add(track)
        session.flush()

        media = LocalMedia(
            track_id=2491,
            file_path=str(audio_file),
            file_format="flac",
            media_id="media_2491_uuid",
        )
        session.add(media)

    monkeypatch.setattr("database.music_database.get_database", lambda: music_db)
    monkeypatch.setattr("database.get_database", lambda: music_db)
    monkeypatch.setattr("database.working_database.get_working_database", lambda: working_db)
    monkeypatch.setattr("services.metadata_enhancer._tagging_write", lambda p, tags: None)
    monkeypatch.setattr(
        "services.metadata_enhancer.RetroactiveEnhancer.tag_file_verified",
        lambda self, p, tags: None,
    )

    import echosync_core

    monkeypatch.setattr(echosync_core, "extract_metadata", lambda p: {})

    mock_chromaprint = "AQABz0mSRIqYJEoUB9_xH" * 300
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (mock_chromaprint, 219),
    )

    acoustid_called = []
    mock_acoustid = MagicMock()

    def fake_resolve_fingerprint_details(fp, dur):
        acoustid_called.append((fp, dur))
        return {
            "acoustid_id": "848149e9-798b-4ea7-90c7-2c9e7e725068",
            "mbids": ["4b05f421-21bb-4810-a1f0-53c40dd2952b"],
            "score": 1.0,
        }

    mock_acoustid.resolve_fingerprint_details.side_effect = fake_resolve_fingerprint_details

    mock_mb = MagicMock()
    mock_mb.capabilities = type("Caps", (), {"supports_batching": False})()
    mock_mb.get_metadata.return_value = {
        "title": "My Way",
        "artist": "Calvin Harris",
        "album": "Chilled House, Session 8",
        "recording_id": "4b05f421-21bb-4810-a1f0-53c40dd2952b",
        "isrc": "GBARL1601007",
        "length": 219000,
        "duration_ms": 219000,
    }

    enhancer = RetroactiveEnhancer()

    from core.enums import Capability

    def fake_get_plugin(cap, required_algorithm=None):
        if cap == Capability.RESOLVE_FINGERPRINT:
            return mock_acoustid
        if cap == Capability.FETCH_METADATA:
            return mock_mb
        return None

    monkeypatch.setattr(enhancer, "_get_plugin", fake_get_plugin)
    monkeypatch.setattr(enhancer, "_get_mb_plugin", lambda: mock_mb)
    monkeypatch.setattr(enhancer, "_get_spotify_plugin", lambda: None)

    enhancer.enhance_library_metadata(batch_size=1, limit=1, check_all_files=False)

    with music_db.session_scope() as session:
        t = session.get(Track, 2491)
        fps = session.query(AudioFingerprint).filter_by(media_id="media_2491_uuid").all()
        acoustid_id_in_db = fps[0].acoustid_id if fps else None
        chromaprint_in_db = fps[0].chromaprint if fps else None

    # Assertions: AcoustID was invoked and persisted atomically
    assert len(acoustid_called) == 1, (
        "AcoustID must NOT be bypassed when duration is computed via generate_with_duration"
    )
    assert acoustid_called[0][1] == 219
    assert acoustid_id_in_db == "848149e9-798b-4ea7-90c7-2c9e7e725068", (
        "acoustid_id must be populated in audio_fingerprints"
    )
    assert chromaprint_in_db == mock_chromaprint
    assert t.title == "My Way"
    assert t.musicbrainz_id == "4b05f421-21bb-4810-a1f0-53c40dd2952b"
    assert t.isrc == "GBARL1601007"


def test_diagnostic_manual_review_ui_acoustid_success_track_2491(tmp_path, monkeypatch):
    """
    Test 2: Manual Review UI path for Track 2491.
    Demonstrates:
    - FingerprintGenerator.generate_with_duration() extracts both chromaprint AND duration from audio.
    - lookup_review_queue_item_acoustid calls resolve_fingerprint_details(fp, duration).
    - Resolves exact MBID 4b05f421-21bb-4810-a1f0-53c40dd2952b for 'My Way'.
    - Populates acoustid_id='848149e9-798b-4ea7-90c7-2c9e7e725068' and musicbrainz_id.
    """
    working_db = WorkingDatabase(tmp_path / "working.db")
    WorkingBase.metadata.create_all(working_db.engine)

    file_dir = tmp_path / "data" / "library" / "Calvin Harris" / "Chilled House, Session 8"
    file_dir.mkdir(parents=True, exist_ok=True)
    audio_file = file_dir / "00 - My Way.flac"
    audio_file.write_bytes(b"dummy audio content")

    with working_db.session_scope() as session:
        task = ReviewTask(
            id=101,
            file_path=str(audio_file),
            status="pending",
            track_data={
                "title": "00 - My Way",
                "raw_title": "00 - My Way",
                "artist_name": "Calvin Harris",
                "album_title": "Chilled House, Session 8",
            },
        )
        session.add(task)

    monkeypatch.setattr("web.routes.metadata_review.get_working_database", lambda: working_db)
    monkeypatch.setattr(
        "core.settings.config_manager.get",
        lambda k: str(tmp_path / "data" / "library") if "library_dir" in k else None,
    )

    # Manual UI calls generate_with_duration:
    mock_chromaprint = "AQABz0mSRIqYJEoUB9_xH" * 300
    mock_duration = 219  # 3 minutes 39 seconds
    monkeypatch.setattr(
        FingerprintGenerator,
        "generate_with_duration",
        lambda p: (mock_chromaprint, mock_duration),
    )

    mock_acoustid = MagicMock()
    mock_acoustid.resolve_fingerprint_details.return_value = {
        "acoustid_id": "848149e9-798b-4ea7-90c7-2c9e7e725068",
        "mbids": ["4b05f421-21bb-4810-a1f0-53c40dd2952b"],
        "score": 0.99,
    }

    mock_mb = MagicMock()
    mock_mb.get_metadata.return_value = {
        "title": "My Way",
        "artist": "Calvin Harris",
        "album": "Chilled House, Session 8",
        "isrc": "GBARL1601004",
    }

    monkeypatch.setattr("web.routes.metadata_review._get_fingerprint_provider", lambda: mock_acoustid)
    monkeypatch.setattr("web.routes.metadata_review._get_metadata_provider", lambda: mock_mb)

    response = lookup_review_queue_item_acoustid(task_id=101, _=None)

    assert response["success"] is True
    assert response["match_found"] is True
    assert response["task"]["detected_metadata"]["acoustid_id"] == "848149e9-798b-4ea7-90c7-2c9e7e725068"
    assert response["task"]["detected_metadata"]["musicbrainz_id"] == "4b05f421-21bb-4810-a1f0-53c40dd2952b"
    assert response["task"]["detected_metadata"]["title"] == "My Way"
    assert response["task"]["detected_metadata"]["artist"] == "Calvin Harris"


def test_diagnostic_matching_engine_rejects_unsanitized_prefix_due_to_compilation_album():
    """
    Test 3: Demonstrate why text waterfall fails when filename prefix '00 - ' is not sanitized.
    - When raw_title is '00 - My Way' and album is a compilation ('Chilled House, Session 8'),
      WeightedMatchingEngine(PROFILE_EXACT_SYNC) gives score=82.0%.
    - Since 82.0% < 85.0% threshold in search_metadata_waterfall, MusicBrainz match is REJECTED.
    - When raw_title is properly sanitized to 'My Way', score=90.0% >= 85.0%, and match PASSES.
    """
    engine = WeightedMatchingEngine(PROFILE_EXACT_SYNC)

    # Candidate from MusicBrainz (e.g. single release or standard album)
    candidate = EchosyncTrack(
        raw_title="My Way",
        artist_name="Calvin Harris",
        album_title="Weekend Goals",
        musicbrainz_id="7c19a86e-e32f-4fbf-955e-603067ed5c43",
    )

    # Case A: Un-sanitized query track emitted by RetroactiveEnhancer
    unsanitized_source = EchosyncTrack(
        raw_title="00 - My Way",
        artist_name="Calvin Harris",
        album_title="Chilled House, Session 8",
    )
    res_unsanitized = engine.calculate_match(unsanitized_source, candidate)
    score_unsanitized = res_unsanitized.confidence_score if res_unsanitized else 0.0

    # Case B: Sanitized query track (as should happen via TrackParser/trust gate)
    sanitized_source = EchosyncTrack(
        raw_title="My Way",
        artist_name="Calvin Harris",
        album_title="Chilled House, Session 8",
    )
    res_sanitized = engine.calculate_match(sanitized_source, candidate)
    score_sanitized = res_sanitized.confidence_score if res_sanitized else 0.0

    print(f"\nUn-sanitized score: {score_unsanitized:.1f}%")
    print(f"Sanitized score: {score_sanitized:.1f}%")

    assert score_unsanitized < 85.0, f"Un-sanitized score {score_unsanitized}% must fall below 85% waterfall threshold"
    assert score_sanitized >= 85.0, f"Sanitized score {score_sanitized}% must meet or exceed 85% waterfall threshold"


def test_diagnostic_waterfall_prefix_sanitization(monkeypatch):
    """
    Test 4: search_metadata_waterfall must sanitize numeric track prefixes (e.g. '00 - My Way' -> 'My Way').
    """
    enhancer = RetroactiveEnhancer()

    captured_queries = []
    mock_mb = MagicMock()
    mock_mb.capabilities = type("Caps", (), {"supports_batching": False})()

    def fake_search_metadata(query_track, limit=10):
        captured_queries.append(query_track.raw_title)
        return [
            EchosyncTrack(
                raw_title="My Way",
                artist_name="Calvin Harris",
                album_title="Chilled House, Session 8",
                musicbrainz_id="4b05f421-21bb-4810-a1f0-53c40dd2952b",
            )
        ]

    mock_mb.search_metadata.side_effect = fake_search_metadata
    mock_mb.get_metadata.return_value = {
        "title": "My Way",
        "artist": "Calvin Harris",
        "album": "Chilled House, Session 8",
        "recording_id": "4b05f421-21bb-4810-a1f0-53c40dd2952b",
        "isrc": "GBARL1601007",
    }
    monkeypatch.setattr(enhancer, "_get_mb_plugin", lambda: mock_mb)

    track_input = EchosyncTrack(
        raw_title="00 - My Way",
        artist_name="Calvin Harris",
        album_title="Chilled House, Session 8",
    )

    res = enhancer.search_metadata_waterfall(track_input)
    assert len(captured_queries) == 1
    assert captured_queries[0] == "My Way", (
        f"Expected prefix '00 - ' to be sanitized to 'My Way', got '{captured_queries[0]}'"
    )
    assert res is not None


def test_diagnostic_musicbrainz_search_deprecates_artist_tracks(monkeypatch):
    """
    Test 5: MusicBrainzClient.search(type='track') must search recordings specifically
    and NEVER delegate to get_artist_tracks(query) which would leak artist top hits.
    """
    from plugins.EchoSync.musicbrainz.client import MusicBrainzClient

    client = MusicBrainzClient()
    mock_sdk = MagicMock()
    mock_sdk.config.get.return_value = ""
    client.sdk = mock_sdk

    artist_tracks_called = []
    monkeypatch.setattr(client, "get_artist_tracks", lambda a: artist_tracks_called.append(a))

    queries_run = []

    def fake_search_query(q, limit=10):
        queries_run.append(q)
        return []

    monkeypatch.setattr(client, "_search_metadata_query", fake_search_query)

    results = client.search("Calvin Harris", type="track", limit=10)

    assert len(artist_tracks_called) == 0, "MusicBrainzClient.search must never call get_artist_tracks"
    assert len(queries_run) == 1
    assert queries_run[0] == 'recording:"Calvin Harris"'
    assert results == []
