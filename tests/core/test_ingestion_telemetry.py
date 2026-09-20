"""
Tests for mtime and inode telemetry extraction and persistence across the ingestion pipeline,
repository layer, and incremental library scanner.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.database.repositories.track_repo import TrackRepository
from core.db.echo_sync_track import EchosyncMedia, EchosyncTrack
from core.orchestrator.ingestion import _parse_telemetry_dict
from database.music_database import Base, LocalMedia


@pytest.fixture
def memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_parse_telemetry_dict_extracts_mtime_and_inode_flat():
    """Verify that _parse_telemetry_dict extracts flat mtime and inode fields from FFI dict."""
    raw_dict = {
        "title": "Starlight",
        "artist_name": "Muse",
        "album_title": "Black Holes and Revelations",
        "file_path": "/music/Muse/Starlight.flac",
        "file_format": "flac",
        "bitrate": 1000,
        "sample_rate": 44100,
        "bit_depth": 16,
        "channels": 2,
        "file_size_bytes": 35000000,
        "mtime": 1726840000.5,
        "inode": 987654321,
    }

    track = _parse_telemetry_dict(raw_dict)
    assert track is not None
    assert len(track.media) == 1

    media = track.media[0]
    assert media.file_path == "/music/Muse/Starlight.flac"
    assert media.mtime == 1726840000.5
    assert media.inode == 987654321
    assert media.file_format == "flac"


def test_parse_telemetry_dict_structured_media_preserves_telemetry():
    """Verify that structured 2-model media dictionaries preserve mtime and inode."""
    raw_dict = {
        "raw_title": "Knights of Cydonia",
        "artist_name": "Muse",
        "album_title": "Black Holes and Revelations",
        "media": [
            {
                "file_path": "/music/Muse/Knights.flac",
                "file_format": "flac",
                "bitrate": 1050,
                "sample_rate": 44100,
                "bit_depth": 16,
                "channels": 2,
                "file_size_bytes": 45000000,
                "mtime": 1726850000.123,
                "inode": 123456789,
            }
        ],
    }

    track = _parse_telemetry_dict(raw_dict)
    assert track is not None
    assert len(track.media) == 1

    media = track.media[0]
    assert media.file_path == "/music/Muse/Knights.flac"
    assert media.mtime == 1726850000.123
    assert media.inode == 123456789


def test_track_repo_bulk_upsert_persists_and_updates_telemetry(memory_db):
    """Verify that bulk_upsert_tracks inserts and on conflict updates mtime and inode."""
    repo = TrackRepository(memory_db)

    # 1. Initial Insert
    track1 = EchosyncTrack(
        raw_title="Time",
        artist_name="Pink Floyd",
        album_title="The Dark Side of the Moon",
        duration=425000,
        media=[
            EchosyncMedia(
                file_path="/music/Pink Floyd/Time.flac",
                file_format="flac",
                bitrate=950,
                mtime=1700000000.0,
                inode=55555,
            )
        ],
    )

    affected = repo.bulk_upsert_tracks([track1])
    memory_db.commit()
    assert affected >= 1

    saved_media = memory_db.query(LocalMedia).first()
    assert saved_media is not None
    assert saved_media.mtime == 1700000000.0
    assert saved_media.inode == 55555

    # 2. Rescan with updated mtime and inode (e.g. retagged / modified on disk)
    track1_updated = EchosyncTrack(
        raw_title="Time",
        artist_name="Pink Floyd",
        album_title="The Dark Side of the Moon",
        duration=425000,
        media=[
            EchosyncMedia(
                file_path="/music/Pink Floyd/Time.flac",
                file_format="flac",
                bitrate=950,
                mtime=1700005000.0,
                inode=66666,
            )
        ],
    )

    repo.bulk_upsert_tracks([track1_updated])
    memory_db.commit()

    memory_db.expire_all()
    updated_media = memory_db.query(LocalMedia).first()
    assert updated_media is not None
    assert updated_media.mtime == 1700005000.0
    assert updated_media.inode == 66666


def test_legacy_flat_fallback_persists_telemetry(memory_db):
    """Verify legacy track objects with flat file_path, mtime, inode are preserved."""
    repo = TrackRepository(memory_db)

    legacy_raw = {
        "title": "Money",
        "artist_name": "Pink Floyd",
        "album_title": "The Dark Side of the Moon",
        "file_path": "/music/Pink Floyd/Money.flac",
        "mtime": 1710000000.0,
        "inode": 77777,
    }
    legacy_track = _parse_telemetry_dict(legacy_raw)
    assert legacy_track is not None

    repo.bulk_upsert_tracks([legacy_track])
    memory_db.commit()

    saved_media = memory_db.query(LocalMedia).first()
    assert saved_media is not None
    assert saved_media.mtime == 1710000000.0
    assert saved_media.inode == 77777
