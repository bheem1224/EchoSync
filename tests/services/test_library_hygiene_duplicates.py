import math
import os
import struct
import tempfile
import uuid
import wave
from pathlib import Path

from fastapi.testclient import TestClient

from database.music_database import (
    Artist,
    AudioFingerprint,
    LocalMedia,
    Track,
    get_database,
)
from services.library_hygiene import DuplicateHygieneService
from web.api_app import create_app

app = create_app(testing=True)


def create_dummy_wav(path: str, duration_sec: float = 1.0, freq: int = 440):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        num_frames = int(44100 * duration_sec)
        for i in range(num_frames):
            val = int(math.sin(2 * math.pi * freq * i / 44100) * 16000)
            wf.writeframes(struct.pack("<h", val))


def test_backfill_missing_fingerprints():
    music_db = get_database()
    suffix = uuid.uuid4().hex[:8]

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = str(Path(f.name).resolve())

    try:
        create_dummy_wav(wav_path, duration_sec=1.2, freq=440)
        media_id_val = f"bf_media_{suffix}"

        with music_db.session_scope() as session:
            artist = Artist(name=f"Backfill Artist {suffix}")
            session.add(artist)
            session.flush()

            track = Track(
                title=f"Backfill Track {suffix}",
                artist_id=artist.id,
                sync_id=f"bf_sync_{suffix}",
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

        hygiene = DuplicateHygieneService(music_db)
        backfilled = hygiene.backfill_missing_fingerprints()

        assert backfilled >= 1

        with music_db.session_scope() as session:
            fp = (
                session.query(AudioFingerprint)
                .filter(AudioFingerprint.media_id == media_id_val)
                .first()
            )
            assert fp is not None
            assert len(fp.chromaprint) > 0
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)


def test_relational_1_to_n_duplicates():
    music_db = get_database()
    suffix = uuid.uuid4().hex[:8]
    sync_id = f"rel_test_{suffix}"

    with music_db.session_scope() as session:
        artist = Artist(name=f"Relational Artist {suffix}")
        session.add(artist)
        session.flush()

        track = Track(
            title=f"Relational Song {suffix}",
            artist_id=artist.id,
            sync_id=sync_id,
        )
        session.add(track)
        session.flush()

        m_lossless = LocalMedia(
            track_id=track.id,
            file_path=f"/mock/library/{suffix}_best.flac",
            media_id=f"rel_best_{suffix}",
            file_format="flac",
            bitrate=1411,
            bit_depth=24,
            sample_rate=48000,
        )
        m_lossy = LocalMedia(
            track_id=track.id,
            file_path=f"/mock/library/{suffix}_worst.mp3",
            media_id=f"rel_worst_{suffix}",
            file_format="mp3",
            bitrate=320,
            bit_depth=16,
            sample_rate=44100,
        )
        session.add_all([m_lossless, m_lossy])
        session.commit()
        t_id = track.id

    hygiene = DuplicateHygieneService(music_db)
    dups = hygiene.find_duplicates()

    all_groups = dups["auto_resolve"] + dups["manual_review"]
    matched = [g for g in all_groups if g.get("sync_id") == sync_id]
    assert len(matched) == 1

    group = matched[0]
    assert group["type"] == "Duplicate Resolution"
    assert group["subtype"] == "relational_duplicate"
    assert group["track_id"] == t_id
    assert group["keep_media_id"] == f"rel_best_{suffix}"
    assert f"rel_worst_{suffix}" in group["delete_media_ids"]
    assert len(group["tracks"]) == 2


def test_acoustic_duplicates():
    music_db = get_database()
    suffix = uuid.uuid4().hex[:8]
    shared_chroma = f"AQAAA_acoustic_{suffix}"

    with music_db.session_scope() as session:
        artist = Artist(name=f"Acoustic Artist {suffix}")
        session.add(artist)
        session.flush()

        t1 = Track(
            title=f"Acoustic Song {suffix}",
            artist_id=artist.id,
            sync_id=f"ac_t1_{suffix}",
            duration=210,
        )
        t2 = Track(
            title=f"Acoustic Song (Deluxe) {suffix}",
            artist_id=artist.id,
            sync_id=f"ac_t2_{suffix}",
            duration=210,
        )
        session.add_all([t1, t2])
        session.flush()

        m1 = LocalMedia(
            track_id=t1.id,
            file_path=f"/mock/{suffix}_1.flac",
            media_id=f"ac_m1_{suffix}",
            file_format="flac",
            bitrate=1411,
            bit_depth=24,
            sample_rate=48000,
        )
        m2 = LocalMedia(
            track_id=t2.id,
            file_path=f"/mock/{suffix}_2.mp3",
            media_id=f"ac_m2_{suffix}",
            file_format="mp3",
            bitrate=320,
            bit_depth=16,
            sample_rate=44100,
        )
        session.add_all([m1, m2])
        session.flush()

        fp1 = AudioFingerprint(media_id=m1.media_id, chromaprint=shared_chroma)
        fp2 = AudioFingerprint(media_id=m2.media_id, chromaprint=shared_chroma)
        session.add_all([fp1, fp2])
        session.commit()
        t1_id = t1.id
        t2_id = t2.id

    hygiene = DuplicateHygieneService(music_db)
    dups = hygiene.find_duplicates()

    all_groups = dups["auto_resolve"] + dups["manual_review"]
    matched = [
        g
        for g in all_groups
        if g.get("keep_id") == t1_id or t1_id in g.get("delete_ids", [])
    ]
    assert len(matched) == 1

    group = matched[0]
    assert group["type"] == "Duplicate Resolution"
    assert group["subtype"] == "acoustic_duplicate"
    assert group["keep_id"] == t1_id
    assert t2_id in group["delete_ids"]
    assert len(group["tracks"]) == 2


def test_metadata_duplicates():
    music_db = get_database()
    suffix = uuid.uuid4().hex[:8]

    with music_db.session_scope() as session:
        artist = Artist(name=f"Capital Cities {suffix}")
        session.add(artist)
        session.flush()

        t1 = Track(
            title=f"Safe and Sound {suffix}",
            artist_id=artist.id,
            sync_id=f"meta_t1_{suffix}",
            duration=193,
        )
        t2 = Track(
            title=f"Safe and Sound {suffix}",
            artist_id=artist.id,
            sync_id=f"meta_t2_{suffix}",
            duration=193,
        )
        session.add_all([t1, t2])
        session.flush()

        m1 = LocalMedia(
            track_id=t1.id,
            file_path=f"/mock/{suffix}_flac.flac",
            media_id=f"meta_m1_{suffix}",
            file_format="flac",
            bitrate=1411,
            bit_depth=16,
            sample_rate=44100,
        )
        m2 = LocalMedia(
            track_id=t2.id,
            file_path=f"/mock/{suffix}_mp3.mp3",
            media_id=f"meta_m2_{suffix}",
            file_format="mp3",
            bitrate=320,
            bit_depth=16,
            sample_rate=44100,
        )
        session.add_all([m1, m2])
        session.commit()
        t1_id = t1.id
        t2_id = t2.id

    hygiene = DuplicateHygieneService(music_db)
    dups = hygiene.find_duplicates()

    all_groups = dups["auto_resolve"] + dups["manual_review"]
    matched = [
        g
        for g in all_groups
        if g.get("keep_id") == t1_id or t1_id in g.get("delete_ids", [])
    ]
    assert len(matched) == 1

    group = matched[0]
    assert group["type"] == "Duplicate Resolution"
    assert group["subtype"] == "metadata_duplicate"
    assert group["keep_id"] == t1_id
    assert t2_id in group["delete_ids"]
    assert len(group["tracks"]) == 2


def test_manager_duplicates_api_endpoint():
    client = TestClient(app)
    response = client.get("/api/v1/system/manager/duplicates")
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert isinstance(data.get("duplicates"), list)


def test_backfill_progress_reporting():
    from core.event_bus import event_bus

    music_db = get_database()
    suffix = uuid.uuid4().hex[:8]

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = str(Path(f.name).resolve())

    progress_events = []

    def on_progress(payload):
        if payload.get("job_name") == "duplicate_scan_job":
            progress_events.append(payload)

    event_bus.subscribe("job_progress", on_progress)

    callback_calls = []

    def my_callback(curr, tot, msg):
        callback_calls.append((curr, tot, msg))

    try:
        create_dummy_wav(wav_path, duration_sec=1.0, freq=440)
        media_id_val = f"bf_prog_{suffix}"

        with music_db.session_scope() as session:
            artist = Artist(name=f"Progress Artist {suffix}")
            session.add(artist)
            session.flush()

            track = Track(
                title=f"Progress Track {suffix}",
                artist_id=artist.id,
                sync_id=f"bf_sync_prog_{suffix}",
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

        hygiene = DuplicateHygieneService(music_db)
        hygiene.backfill_missing_fingerprints(
            batch_size=1, progress_callback=my_callback
        )

        assert len(callback_calls) >= 1
        import time

        time.sleep(0.3)
        assert any(e.get("current", 0) >= 1 for e in progress_events)
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)


def test_phase3_remaster_and_live_false_positives():
    music_db = get_database()
    suffix = uuid.uuid4().hex[:8]

    with music_db.session_scope() as session:
        artist = Artist(name=f"Eagles {suffix}")
        session.add(artist)
        session.flush()

        # Track 1: Studio track
        t_studio1 = Track(
            title=f"Hotel California {suffix}",
            artist_id=artist.id,
            sync_id=f"studio1_{suffix}",
            edition=None,
            duration=390,
        )
        # Track 2: Studio duplicate (lower quality)
        t_studio2 = Track(
            title=f"Hotel California {suffix}",
            artist_id=artist.id,
            sync_id=f"studio2_{suffix}",
            edition=None,
            duration=390,
        )
        # Track 3: Live version
        t_live = Track(
            title=f"Hotel California (Live) {suffix}",
            artist_id=artist.id,
            sync_id=f"live_{suffix}",
            edition="Live",
            duration=430,
        )
        # Track 4: Acoustic version
        t_acoustic = Track(
            title=f"Hotel California {suffix}",
            artist_id=artist.id,
            sync_id=f"acoustic_{suffix}",
            edition="Acoustic",
            duration=380,
        )
        session.add_all([t_studio1, t_studio2, t_live, t_acoustic])
        session.flush()

        m_s1 = LocalMedia(
            track_id=t_studio1.id,
            file_path=f"/mock/{suffix}_s1.flac",
            media_id=f"m_s1_{suffix}",
            file_format="flac",
            bitrate=1411,
        )
        m_s2 = LocalMedia(
            track_id=t_studio2.id,
            file_path=f"/mock/{suffix}_s2.mp3",
            media_id=f"m_s2_{suffix}",
            file_format="mp3",
            bitrate=256,
        )
        m_live = LocalMedia(
            track_id=t_live.id,
            file_path=f"/mock/{suffix}_live.flac",
            media_id=f"m_live_{suffix}",
            file_format="flac",
            bitrate=1411,
        )
        m_ac = LocalMedia(
            track_id=t_acoustic.id,
            file_path=f"/mock/{suffix}_ac.flac",
            media_id=f"m_ac_{suffix}",
            file_format="flac",
            bitrate=1411,
        )
        session.add_all([m_s1, m_s2, m_live, m_ac])
        session.commit()

        s1_id = t_studio1.id
        s2_id = t_studio2.id
        live_id = t_live.id
        ac_id = t_acoustic.id

    hygiene = DuplicateHygieneService(music_db)
    dups = hygiene.find_duplicates(backfill=False)
    all_groups = dups["auto_resolve"] + dups["manual_review"]

    # Studio 1 and Studio 2 should be matched together
    studio_group = next((g for g in all_groups if g.get("keep_id") == s1_id), None)
    assert studio_group is not None
    assert s2_id in studio_group["delete_ids"]

    # Live and Acoustic tracks MUST NOT be in delete_ids of the studio group!
    assert live_id not in studio_group["delete_ids"]
    assert ac_id not in studio_group["delete_ids"]

    # Live track and Acoustic track must NOT be staged for auto-deletion anywhere
    auto_delete_ids = [
        tid for g in dups["auto_resolve"] for tid in g.get("delete_ids", [])
    ]
    assert live_id not in auto_delete_ids
    assert ac_id not in auto_delete_ids


def test_phase3_differing_acoustic_fingerprints_manual_review():
    music_db = get_database()
    suffix = uuid.uuid4().hex[:8]

    with music_db.session_scope() as session:
        artist = Artist(name=f"Different Takes {suffix}")
        session.add(artist)
        session.flush()

        t1 = Track(
            title=f"Same Title {suffix}",
            artist_id=artist.id,
            sync_id=f"diff_t1_{suffix}",
            duration=200,
        )
        t2 = Track(
            title=f"Same Title {suffix}",
            artist_id=artist.id,
            sync_id=f"diff_t2_{suffix}",
            duration=200,
        )
        session.add_all([t1, t2])
        session.flush()

        m1 = LocalMedia(
            track_id=t1.id,
            file_path=f"/mock/{suffix}_take1.flac",
            media_id=f"m_take1_{suffix}",
            file_format="flac",
            bitrate=1411,
        )
        m2 = LocalMedia(
            track_id=t2.id,
            file_path=f"/mock/{suffix}_take2.flac",
            media_id=f"m_take2_{suffix}",
            file_format="flac",
            bitrate=1411,
        )
        session.add_all([m1, m2])
        session.flush()

        # Different acoustic fingerprints!
        fp1 = AudioFingerprint(
            media_id=m1.media_id, chromaprint=f"CHROMA_TAKE_A_{suffix}"
        )
        fp2 = AudioFingerprint(
            media_id=m2.media_id, chromaprint=f"CHROMA_TAKE_B_{suffix}"
        )
        session.add_all([fp1, fp2])
        session.commit()

        t1_id = t1.id
        t2_id = t2.id

    hygiene = DuplicateHygieneService(music_db)
    dups = hygiene.find_duplicates(backfill=False)

    # Must NOT be in auto_resolve!
    auto_delete_ids = [
        tid for g in dups["auto_resolve"] for tid in g.get("delete_ids", [])
    ]
    assert t1_id not in auto_delete_ids
    assert t2_id not in auto_delete_ids

    # Must be in manual_review with requires_manual_review = True
    manual_match = [
        g for g in dups["manual_review"] if g.get("keep_id") in (t1_id, t2_id)
    ]
    assert len(manual_match) == 1
    assert manual_match[0]["requires_manual_review"] is True
    assert manual_match[0]["confidence_score"] <= 50.0
