import math
import os
import struct
import tempfile
import wave
from pathlib import Path

from core.event_bus import event_bus
from database.music_database import (
    Artist,
    AudioFingerprint,
    LocalMedia,
    Track,
    get_database,
)
from database.working_database import SuggestionStagingQueue, get_working_database
from services.deduplicator import DeduplicationService
from services.media_manager import MediaManagerService


def create_dummy_wav(path: str, duration_sec: float = 1.0, freq: int = 440):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        num_frames = int(44100 * duration_sec)
        for i in range(num_frames):
            val = int(math.sin(2 * math.pi * freq * i / 44100) * 16000)
            wf.writeframes(struct.pack("<h", val))


def test_native_rust_fingerprinting():
    import echosync_core

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
    try:
        create_dummy_wav(wav_path, duration_sec=1.5, freq=440)
        fp, dur = echosync_core.fingerprint_audio(wav_path, trim_silence=True)
        assert isinstance(fp, str)
        assert len(fp) > 0
        assert round(dur, 1) == 1.5
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)


def test_audio_fingerprint_schema_duplicate_chromaprint():
    import uuid

    music_db = get_database()
    suffix = uuid.uuid4().hex[:8]
    with music_db.session_scope() as session:
        # Create artist, track, and two distinct local_media
        artist = Artist(name=f"Test Schema Artist {suffix}")
        session.add(artist)
        session.flush()

        track = Track(
            title=f"Duplicate FP Test Track {suffix}",
            artist_id=artist.id,
            sync_id=f"fp_test_sync_{suffix}",
        )
        session.add(track)
        session.flush()

        media1 = LocalMedia(
            track_id=track.id,
            file_path=f"/mock/path/m1_{suffix}.flac",
            media_id=f"test_m1_{suffix}",
            file_format="flac",
        )
        media2 = LocalMedia(
            track_id=track.id,
            file_path=f"/mock/path/m2_{suffix}.flac",
            media_id=f"test_m2_{suffix}",
            file_format="flac",
        )
        session.add_all([media1, media2])
        session.flush()

        # Insert same chromaprint on both distinct media rows
        shared_chromaprint = f"AQAAAAshared_hash_{suffix}"
        afp1 = AudioFingerprint(
            media_id=media1.media_id, chromaprint=shared_chromaprint
        )
        afp2 = AudioFingerprint(
            media_id=media2.media_id, chromaprint=shared_chromaprint
        )
        session.add_all([afp1, afp2])
        session.commit()

        # Verify both exist
        fps = (
            session.query(AudioFingerprint)
            .filter(AudioFingerprint.chromaprint == shared_chromaprint)
            .all()
        )
        assert len(fps) == 2


def test_relational_1_to_n_duplicate_detection_and_staging():
    import time
    import uuid

    music_db = get_database()
    working_db = get_working_database()
    media_mgr = MediaManagerService()
    dedup = DeduplicationService()

    unique_sync_id = f"rel_{uuid.uuid4().hex[:12]}"
    with music_db.session_scope() as session:
        artist = Artist(name=f"Relational Artist {uuid.uuid4().hex[:6]}")
        session.add(artist)
        session.flush()

        track = Track(
            title="1:N Resolution Song", artist_id=artist.id, sync_id=unique_sync_id
        )
        session.add(track)
        session.flush()

        # Media 1: FLAC (lossless, higher quality)
        m_winner = LocalMedia(
            track_id=track.id,
            file_path=f"/mock/library/{uuid.uuid4().hex[:8]}_winner.flac",
            media_id=f"win_{uuid.uuid4().hex[:4]}",
            file_format="flac",
            bitrate=1411,
            bit_depth=24,
            sample_rate=48000,
        )
        # Media 2: MP3 (lossy, lower quality)
        m_loser = LocalMedia(
            track_id=track.id,
            file_path=f"/mock/library/{uuid.uuid4().hex[:8]}_loser.mp3",
            media_id=f"lose_{uuid.uuid4().hex[:4]}",
            file_format="mp3",
            bitrate=320,
            bit_depth=16,
            sample_rate=44100,
        )
        session.add_all([m_winner, m_loser])
        session.commit()
        t_id = track.id
        win_id = m_winner.media_id
        lose_id = m_loser.media_id

    # Resolve relational duplicate
    payload = dedup.resolve_relational_duplicates(t_id)
    assert payload is not None
    assert payload["keep_media_id"] == win_id
    assert payload["delete_media_ids"] == [lose_id]
    assert payload["confidence_score"] == 100.0

    # Wait briefly for EventBus background dispatcher thread
    time.sleep(0.5)

    # Ensure staged into SuggestionStagingQueue
    with working_db.session_scope() as w_session:
        staged = (
            w_session.query(SuggestionStagingQueue)
            .filter(SuggestionStagingQueue.sync_id == unique_sync_id)
            .first()
        )
        assert staged is not None
        assert staged.intent_type == "HYGIENE_DUPLICATION"
        assert staged.context_data["keep_media_id"] == win_id
        assert staged.context_data["delete_media_ids"] == [lose_id]


def test_reactive_ingestion_interception():
    import time
    import uuid

    music_db = get_database()
    dedup = DeduplicationService()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = str(Path(f.name).resolve())

    try:
        create_dummy_wav(wav_path, duration_sec=1.0, freq=520)

        ingest_sync = f"ingest_{uuid.uuid4().hex[:10]}"
        media_id_val = f"m_{uuid.uuid4().hex[:6]}"

        # Pre-seed track & LocalMedia in DB
        with music_db.session_scope() as session:
            artist = Artist(name=f"Ingestion Artist {uuid.uuid4().hex[:6]}")
            session.add(artist)
            session.flush()

            track = Track(
                title="Ingestion Track", artist_id=artist.id, sync_id=ingest_sync
            )
            session.add(track)
            session.flush()

            media = LocalMedia(
                track_id=track.id,
                file_path=wav_path,
                media_id=media_id_val,
                file_format="wav",
                bitrate=1411,
            )
            session.add(media)
            session.commit()

        # Trigger reactive ingestion event
        event_payload = {
            "event": "TRACK_IMPORTED",
            "track": {
                "title": "Ingestion Track",
                "artist_name": "Ingestion Artist",
                "file_path": wav_path,
            },
        }
        event_bus.publish(event_payload)

        # Allow event loop a moment to process
        time.sleep(0.5)

        # Verify AudioFingerprint was generated & stored
        with music_db.session_scope() as session:
            fp_record = (
                session.query(AudioFingerprint)
                .filter(AudioFingerprint.media_id == media_id_val)
                .first()
            )
            assert fp_record is not None
            assert len(fp_record.chromaprint) > 0

    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)
