"""Wave 2 unit tests: SQLite schema, pre-migration backups, quarantine vs NOT_FOUND, Rayon Chromaprint batch & cache."""

from __future__ import annotations

import math
import sqlite3
import struct
import wave
from pathlib import Path

import echosync_core
from alembic import command
from alembic.config import Config

from core.db.migrations import snapshot_sqlite_before_migration
from core.metadata.cache import ChromaprintCache
from core.settings import config_manager
from database.config_database import ConfigDatabase, close_config_database
from database.music_database import (
    Album,
    Artist,
    AudioFingerprint,
    Base,
    LocalMedia,
    MusicDatabase,
    Track,
    close_database,
)


def _write_multi_tone_wav(
    path: Path, freq_sequence: list[float], duration_s: float = 14.0, sample_rate: int = 44100
) -> None:
    total_frames = int(duration_s * sample_rate)
    step_frames = max(1, total_frames // len(freq_sequence))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        frames = bytearray()
        for i in range(total_frames):
            freq = freq_sequence[min(i // step_frames, len(freq_sequence) - 1)]
            val = int(14000 * math.sin(2.0 * math.pi * freq * i / sample_rate))
            frames.extend(struct.pack("<h", val))
        wf.writeframes(bytes(frames))


def test_snapshot_sqlite_before_migration_creates_bak_for_non_empty_db(tmp_path):
    assert snapshot_sqlite_before_migration(":memory:") is None
    assert snapshot_sqlite_before_migration(tmp_path / "missing.db") is None

    empty_db = tmp_path / "empty.db"
    empty_db.write_bytes(b"")
    assert snapshot_sqlite_before_migration(empty_db) is None

    live_db = tmp_path / "music_library.db"
    conn = sqlite3.connect(live_db)
    conn.execute("CREATE TABLE demo (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO demo (name) VALUES ('sample')")
    conn.commit()
    conn.close()

    backup = snapshot_sqlite_before_migration(live_db)
    assert backup == Path(f"{live_db}.bak")
    assert backup.exists()
    assert backup.read_bytes() == live_db.read_bytes()


def test_music_alembic_wave2_migration_indexes_quarantine_and_without_rowid(tmp_path, monkeypatch):
    close_database()
    repo_root = Path(__file__).resolve().parents[2]
    music_ini = repo_root / "database" / "migrations" / "music" / "alembic.ini"
    db_path = tmp_path / "music_upgrade.db"
    monkeypatch.setattr(
        config_manager,
        "get",
        lambda key, default=None: f"sqlite:///{db_path.as_posix()}" if key == "database.music_uri" else default,
    )

    # Bootstrap schema via ORM Base.metadata.create_all, stamp at head, and downgrade to pre-Wave2 revision
    mdb = MusicDatabase(database_path=str(db_path))
    Base.metadata.create_all(mdb.engine)
    mdb.engine.dispose()
    close_database()

    cfg = Config(str(music_ini))
    cfg.attributes["configure_logger"] = False
    cfg.set_main_option("script_location", str(music_ini.parent))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.as_posix()}")

    command.stamp(cfg, "head")
    command.downgrade(cfg, "f3a4b5c6d7e8")

    # Seed a legacy NOT_FOUND track & pre-Wave2 rowid-backed track_artists table
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("DROP TABLE IF EXISTS track_artists")
    conn.execute(
        """
        CREATE TABLE track_artists (
            id INTEGER PRIMARY KEY,
            track_id INTEGER NOT NULL,
            artist_id INTEGER NOT NULL,
            role VARCHAR DEFAULT 'primary',
            position INTEGER DEFAULT 0
        )
        """
    )
    conn.execute("INSERT INTO artists (id, name, normalized_name) VALUES (1, 'Artist One', 'artist one')")
    conn.execute(
        "INSERT INTO tracks (id, title, normalized_title, artist_id, musicbrainz_id, sync_id) "
        "VALUES (10, 'Legacy Track', 'legacy track', 1, 'NOT_FOUND', 'sync-legacy-10')"
    )
    conn.execute(
        "INSERT INTO track_artists (id, track_id, artist_id, role, position) VALUES (1, 10, 1, 'primary', 0)"
    )
    conn.commit()
    conn.close()

    # Take backup then upgrade to head (g1a2b3c4d5e6)
    bak = snapshot_sqlite_before_migration(db_path)
    assert bak is not None and bak.exists()
    command.upgrade(cfg, "head")

    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT musicbrainz_id, verification_tier, version_type, enhancement_attempts FROM tracks WHERE id = 10"
    ).fetchone()
    assert row == (None, "quarantined", "original", 0)

    # Partial index on unverified tracks & LocalMedia.duration_ms index
    idx_rows = dict(conn.execute("SELECT name, sql FROM sqlite_master WHERE type='index'").fetchall())
    assert "ix_tracks_unverified" in idx_rows
    assert "verification_tier = 'unverified'" in (idx_rows["ix_tracks_unverified"] or "")
    assert "ix_local_media_duration_ms" in idx_rows

    local_media_cols = {r[1] for r in conn.execute("PRAGMA table_info(local_media)").fetchall()}
    assert "duration_ms" in local_media_cols

    # Junction tables are WITHOUT ROWID (no implicit rowid column)
    ta_sql = conn.execute("SELECT sql FROM sqlite_master WHERE name='track_artists'").fetchone()[0]
    aa_sql = conn.execute("SELECT sql FROM sqlite_master WHERE name='album_artists'").fetchone()[0]
    assert "WITHOUT ROWID" in ta_sql.upper()
    assert "WITHOUT ROWID" in aa_sql.upper()

    for tbl in ("track_artists", "album_artists"):
        try:
            conn.execute(f"SELECT rowid FROM {tbl}")
            raise AssertionError(f"Expected {tbl} to be WITHOUT ROWID")
        except sqlite3.OperationalError:
            pass

    # No AUTOINCREMENT sqlite_sequence table created on Wave 2 migrated schema
    seq_tbl = conn.execute("SELECT name FROM sqlite_master WHERE name='sqlite_sequence'").fetchone()
    assert seq_tbl is None
    conn.close()


def test_config_db_wave2_schema_without_rowid_and_seeded_roles(tmp_path):
    close_config_database()
    db_path = tmp_path / "config_wave2.db"
    cdb = ConfigDatabase(db_path=str(db_path))

    try:
        roles = {r["name"]: r for r in cdb.list_roles()}
        assert "admin" in roles and "member" in roles
        assert roles["admin"]["permissions"] == ["*"]
        assert "service:library:read" in roles["member"]["permissions"]

        with cdb._get_connection() as conn:
            for tbl in ("user_role_assignments", "user_managed_accounts"):
                sql_def = conn.execute(
                    "SELECT sql FROM sqlite_master WHERE name = ?", (tbl,)
                ).fetchone()[0]
                assert "WITHOUT ROWID" in sql_def.upper()
                try:
                    conn.execute(f"SELECT rowid FROM {tbl}")
                    raise AssertionError(f"{tbl} should not have rowid")
                except sqlite3.OperationalError:
                    pass

            svc_cols = {r[1] for r in conn.execute("PRAGMA table_info(services)").fetchall()}
            assert "granted_scopes" in svc_cols
    finally:
        close_config_database()


def test_track_is_verified_property_quarantine_invariance():
    quarantined = Track(title="Q", artist_id=1, verification_tier="quarantined", musicbrainz_id="mbid-1")
    legacy_sentinel = Track(title="S", artist_id=1, verification_tier="unverified", musicbrainz_id="NOT_FOUND")
    verified = Track(title="V", artist_id=1, verification_tier="acoustid_verified", musicbrainz_id="mbid-2")
    manual = Track(title="M", artist_id=1, verification_tier="manual_locked")

    assert quarantined.is_verified is False
    assert legacy_sentinel.is_verified is False
    assert verified.is_verified is True
    assert manual.is_verified is True


def test_rust_batch_chromaprint_and_local_cache_lookup(tmp_path, monkeypatch):
    close_database()
    wav_a = tmp_path / "melody_a.wav"
    wav_a_peer = tmp_path / "melody_a_peer.wav"
    wav_b = tmp_path / "melody_b.wav"
    seq_a = [261.63, 329.63, 392.00, 523.25, 293.66, 369.99, 440.00, 587.33, 329.63, 440.00, 523.25, 659.25]
    seq_a_peer = [261.63, 329.63, 392.00, 523.25, 293.66, 369.99, 440.00, 587.33, 329.63, 440.00, 523.25, 698.46]
    seq_b = [466.16, 311.13, 415.30, 277.18, 554.37, 349.23, 246.94, 493.88, 369.99, 233.08, 415.30, 311.13]
    _write_multi_tone_wav(wav_a, seq_a)
    _write_multi_tone_wav(wav_a_peer, seq_a_peer)
    _write_multi_tone_wav(wav_b, seq_b)

    fp_a, _ = echosync_core.fingerprint_audio(str(wav_a), trim_silence=False)
    fp_a_peer, _ = echosync_core.fingerprint_audio(str(wav_a_peer), trim_silence=False)
    fp_b, _ = echosync_core.fingerprint_audio(str(wav_b), trim_silence=False)
    assert fp_a and fp_a_peer and fp_b
    assert fp_a != fp_a_peer
    assert echosync_core.compare_chromaprints(fp_a, fp_a_peer) >= 0.85
    assert echosync_core.compare_chromaprints(fp_a, fp_b) < 0.85

    # Direct Rust Rayon parallel batch helpers
    matches = echosync_core.batch_compare_chromaprints(
        fp_a,
        [("peer-other", fp_b), ("peer-same", fp_a)],
        min_similarity=0.85,
    )
    assert len(matches) >= 1
    assert matches[0][0] == "peer-same"
    assert matches[0][1] == 1.0

    best = echosync_core.find_best_chromaprint_match(
        fp_a,
        [("peer-other", fp_b), ("peer-same", fp_a)],
        min_similarity=0.85,
    )
    assert best == ("peer-same", 1.0)

    # Seed isolated MusicDatabase and verify ChromaprintCache.check_local
    db_path = tmp_path / "music_cache.db"
    monkeypatch.setattr(
        config_manager,
        "get",
        lambda key, default=None: f"sqlite:///{db_path.as_posix()}" if key == "database.music_uri" else default,
    )
    music_db = MusicDatabase(database_path=str(db_path))
    Base.metadata.create_all(music_db.engine)

    import database.music_database as music_db_mod

    monkeypatch.setattr(music_db_mod, "get_database", lambda db_path=None: music_db)

    try:
        with music_db.session_scope() as session:
            artist = Artist(name="Synth Artist", normalized_name="synth artist")
            session.add(artist)
            session.flush()
            album = Album(title="Synth Album", normalized_title="synth album", artist_id=artist.id)
            session.add(album)
            session.flush()

            verified_track = Track(
                title="Verified Tone",
                normalized_title="verified tone",
                artist_id=artist.id,
                album_id=album.id,
                duration=14_000,
                musicbrainz_id="mbid-verified-tone",
                verification_tier="acoustid_verified",
                sync_id="sync-verified-tone",
            )
            quarantined_track = Track(
                title="Quarantined Tone",
                normalized_title="quarantined tone",
                artist_id=artist.id,
                album_id=album.id,
                duration=14_000,
                musicbrainz_id="mbid-quarantined-tone",
                verification_tier="quarantined",
                sync_id="sync-quarantined-tone",
            )
            session.add_all([verified_track, quarantined_track])
            session.flush()

            m_ok = LocalMedia(
                media_id="medok001",
                track_id=verified_track.id,
                file_path=str(wav_a),
                file_format="wav",
                duration_ms=14_000,
            )
            m_q = LocalMedia(
                media_id="medqr002",
                track_id=quarantined_track.id,
                file_path=str(wav_b),
                file_format="wav",
                duration_ms=14_000,
            )
            session.add_all([m_ok, m_q])
            session.flush()

            session.add_all(
                [
                    AudioFingerprint(media_id="medok001", chromaprint=fp_a, acoustid_id="ac-ok-1"),
                    AudioFingerprint(media_id="medqr002", chromaprint=fp_b, acoustid_id="ac-qr-2"),
                ]
            )

        cache = ChromaprintCache()
        # Hamming similarity peer lookup (non-identical fp_a_peer matches stored fp_a)
        hit = cache.check_local(fp_a_peer, duration_ms=14_000, sync_id="different-sync-id", similarity_threshold=0.85)
        assert hit is not None
        assert hit["musicbrainz_id"] == "mbid-verified-tone"
        assert hit["similarity_score"] >= 0.85

        # Quarantined peer must never satisfy ChromaprintCache.check_local
        quarantined_miss = cache.check_local(fp_b, duration_ms=14_000, sync_id="different-sync-id", similarity_threshold=0.85)
        assert quarantined_miss is None
    finally:
        close_database()
