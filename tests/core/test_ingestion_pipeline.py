from core.database.repositories.track_repo import bulk_upsert_tracks
from core.db.echo_sync_track import EchosyncMedia, EchosyncTrack
from core.orchestrator.ingestion import IngestionOrchestrator
from database.music_database import Track, get_database


def test_echosync_track_model():
    track = EchosyncTrack(
        raw_title="Testing Phase 4",
        artist_name="Audiophile Engineer",
        album_title="Rust Ingestion",
        media=[
            EchosyncMedia(
                file_path="/media/library/test.flac",
                file_format="FLAC",
                sample_rate=96000,
                bit_depth=24,
            )
        ],
    )
    assert track.title == "Testing Phase 4"
    assert track.artist_name == "Audiophile Engineer"
    assert track.media[0].sample_rate == 96000
    assert track.media[0].file_path == "/media/library/test.flac"


def test_bulk_upsert_tracks_sqlalchemy2():
    db = get_database()
    from database.music_database import Base

    Base.metadata.drop_all(db.engine)
    Base.metadata.create_all(db.engine)

    session = db.get_session()
    try:
        t1 = EchosyncTrack(
            sync_id="test_sync_001",
            raw_title="Track One",
            artist_name="Artist A",
            album_title="Album A",
            duration=210000,
            media=[
                EchosyncMedia(
                    file_path="/media/test1.flac",
                    file_format="FLAC",
                    bitrate=1411000,
                    sample_rate=44100,
                    bit_depth=16,
                )
            ],
        )
        t2 = EchosyncTrack(
            sync_id="test_sync_002",
            raw_title="Track Two",
            artist_name="Artist B",
            album_title="Album B",
            duration=180000,
            media=[
                EchosyncMedia(
                    file_path="/media/test2.m4a",
                    file_format="ALAC",
                )
            ],
        )

        rows = bulk_upsert_tracks(session, [t1, t2])
        session.commit()
        assert rows > 0

        # Verify initial insert
        db_track = session.query(Track).filter_by(sync_id="test_sync_001").first()
        assert db_track is not None
        assert db_track.title == "Track One"

        # Test UPSERT conflict update: overwrite technical fields, COALESCE metadata
        t1_updated = EchosyncTrack(
            sync_id="test_sync_001",
            raw_title="Track One (Remastered)",
            artist_name="Artist A",
            album_title="Album A",
            duration=215000,
            media=[
                EchosyncMedia(
                    file_path="/media/test1.flac",
                    file_format="FLAC",
                )
            ],
        )
        bulk_upsert_tracks(session, [t1_updated])
        session.commit()
        session.expire_all()

        re_loaded = session.query(Track).filter_by(sync_id="test_sync_001").first()
        assert re_loaded.duration == 215000
    finally:
        session.close()


def test_ingestion_orchestration():
    db = get_database()

    orchestrator = IngestionOrchestrator(batch_size=5)
    cb = orchestrator.create_telemetry_callback()

    raw_batch = [
        {
            "sync_id": f"batch_sync_{i}",
            "title": f"Batch Track {i}",
            "artist": "Batch Artist",
            "duration_ms": 200000 + i,
            "codec": "FLAC",
            "file_path": f"/media/batch_{i}.flac",
        }
        for i in range(12)
    ]

    cb(raw_batch)
    cb.flush()

    session = db.get_session()
    try:
        count = session.query(Track).filter(Track.sync_id.like("batch_sync_%")).count()
        assert count == 12
    finally:
        session.close()
