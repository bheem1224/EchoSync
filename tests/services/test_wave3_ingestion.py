"""Wave 3 unit tests for ingestion, watcher scope, reorganization, scan state, Gatekeeper EXDEV, and media priority."""

import errno
from pathlib import Path
from unittest.mock import MagicMock, patch

import echosync_core
import pytest

from core.io_gatekeeper import Gatekeeper
from core.media_scan_manager import MediaScanManager
from core.settings import config_manager
from database import _canonicalize_path
from database.music_database import (
    Album,
    Artist,
    Base,
    LocalMedia,
    MusicDatabase,
    Track,
    generate_nanoid,
)
from database.working_database import WorkingBase, WorkingDatabase
from services.auto_importer import AutoImportService
from services.library_reorganizer import LibraryReorganizerService
from services.library_watcher import (
    LibraryWatcherService,
    _process_new_file,
    is_path_suppressed,
    resolve_collision_safe_edition_path,
)
from services.media_manager import MediaManagerService


@pytest.fixture
def isolated_ingestion_env(tmp_path, monkeypatch):
    """Provide isolated tmp_path MusicDatabase, WorkingDatabase, library_dir, and download_dir."""
    library_dir = tmp_path / "library"
    download_dir = tmp_path / "downloads"
    library_dir.mkdir(parents=True, exist_ok=True)
    download_dir.mkdir(parents=True, exist_ok=True)

    music_db = MusicDatabase(str(tmp_path / "music.db"))
    Base.metadata.create_all(music_db.engine)

    working_db = WorkingDatabase(str(tmp_path / "working.db"))
    WorkingBase.metadata.create_all(working_db.engine)

    def mock_get(key, default=None):
        if key in ("storage.library_dir", "library_dir", "storage_locations.library"):
            return str(library_dir)
        if key in ("storage.download_dir", "download_dir", "storage.downloads_dir", "downloads_dir"):
            return str(download_dir)
        if key in (
            "auto_import.file_organization_pattern",
            "library_import.renaming_pattern",
            "metadata_enhancement.naming_template",
        ):
            return "{Artist}/{Album}/{Track} - {Title}.{ext}"
        if key == "metadata_enhancement":
            return {"enabled": True, "auto_import": True, "confidence_threshold": 90}
        return default

    monkeypatch.setattr(config_manager, "get", mock_get)
    monkeypatch.setattr(config_manager, "get_library_dir", lambda: library_dir)
    monkeypatch.setattr(config_manager, "get_downloads_dir", lambda: download_dir)
    monkeypatch.setattr("database.music_database.get_database", lambda *a, **kw: music_db)
    monkeypatch.setattr("database.get_database", lambda *a, **kw: music_db)
    monkeypatch.setattr("database.working_database.get_working_database", lambda *a, **kw: working_db)
    monkeypatch.setattr(
        "core.path_formatter.get_library_preferences",
        lambda: (str(library_dir), "{Artist}/{Album}/{Track} - {Title}.{ext}"),
    )

    yield {
        "music_db": music_db,
        "working_db": working_db,
        "library_dir": library_dir,
        "download_dir": download_dir,
    }

    music_db.dispose()
    working_db.dispose()


# ── Task 1: LibraryWatcherService Scope ───────────────────────────────────────


def test_library_watcher_watches_only_library_dir_never_downloads_dir(tmp_path, monkeypatch):
    """LibraryWatcherService must monitor ONLY library_dir, never download_dir."""
    library_dir = tmp_path / "library"
    downloads_dir = tmp_path / "downloads"

    monkeypatch.setattr(config_manager, "get_library_dir", lambda: library_dir)
    monkeypatch.setattr(config_manager, "get_downloads_dir", lambda: downloads_dir)

    scheduled = []
    mock_observer = MagicMock()
    mock_observer.schedule.side_effect = lambda handler, path, recursive=True: scheduled.append(
        (Path(path).resolve(), recursive)
    )
    monkeypatch.setattr("services.library_watcher.Observer", lambda: mock_observer)

    watcher = LibraryWatcherService()
    watcher.start()
    try:
        assert library_dir.exists()
        assert not downloads_dir.exists()
        assert scheduled == [(library_dir.resolve(), True)]
    finally:
        watcher.stop()


def test_library_watcher_disabled_when_library_dir_unconfigured(monkeypatch):
    """LibraryWatcherService stays disabled if library_dir is not configured."""
    monkeypatch.setattr(config_manager, "get_library_dir", lambda: None)
    mock_observer = MagicMock()
    monkeypatch.setattr("services.library_watcher.Observer", lambda: mock_observer)

    watcher = LibraryWatcherService()
    watcher.start()
    assert watcher._started is False
    mock_observer.schedule.assert_not_called()


# ── Task 2: AutoImportService & LibraryWatcherService no_autoflush & editions ─


def test_resolve_collision_safe_edition_path_with_unflushed_session(isolated_ingestion_env):
    """Collision-safe edition path checks disk + DB (even unflushed ORM rows) under no_autoflush."""
    music_db = isolated_ingestion_env["music_db"]
    library_dir = isolated_ingestion_env["library_dir"]
    base_dest = library_dir / "Artist" / "Album" / "04 - Title.flac"
    base_dest.parent.mkdir(parents=True, exist_ok=True)

    with music_db.session_factory() as session:
        artist = Artist(name="Artist", normalized_name="artist")
        album = Album(title="Album", normalized_title="album", artist=artist)
        session.add_all([artist, album])
        session.flush()

        track = Track(
            title="Title",
            normalized_title="title",
            track_number=4,
            artist_id=artist.id,
            album_id=album.id,
        )
        session.add(track)
        session.flush()

        # Add unflushed LocalMedia in session.new (not flushed to SQLite yet)
        unflushed_lm = LocalMedia(
            media_id=generate_nanoid(),
            track_id=track.id,
            file_path=_canonicalize_path(str(base_dest)),
            file_format="flac",
        )
        session.add(unflushed_lm)

        # Also leave a pending invalid Track with missing artist_id to verify autoflush does NOT trigger
        bad_pending = Track(title="Incomplete", normalized_title="incomplete", artist_id=None)  # type: ignore[arg-type]
        session.add(bad_pending)

        candidate = resolve_collision_safe_edition_path(
            base_dest,
            metadata={"file_format": "flac", "bit_depth": 24, "sample_rate": 96000},
            session=session,
        )
        assert candidate == library_dir / "Artist" / "Album" / "04 - Title [FLAC-24-96].flac"

        # If [FLAC-24-96] also exists on disk, counter suffix is appended
        candidate.write_bytes(b"existing 24-96")
        second = resolve_collision_safe_edition_path(
            base_dest,
            metadata={"file_format": "flac", "bit_depth": 24, "sample_rate": 96000},
            session=session,
        )
        assert second == library_dir / "Artist" / "Album" / "04 - Title [FLAC-24-96] (1).flac"
        session.rollback()


def test_auto_importer_collision_safe_edition_and_reparenting(isolated_ingestion_env, monkeypatch):
    """AutoImportService moves sibling editions to [FLAC-24-96] and re-parents under one Track."""
    music_db = isolated_ingestion_env["music_db"]
    library_dir = isolated_ingestion_env["library_dir"]
    download_dir = isolated_ingestion_env["download_dir"]

    # Seed existing 16-bit sibling edition in library + DB
    existing_lib_file = library_dir / "Daft Punk" / "Discovery" / "04 - Harder Better Faster Stronger.flac"
    existing_lib_file.parent.mkdir(parents=True, exist_ok=True)
    existing_lib_file.write_bytes(b"16bit_master_audio")

    with music_db.session_scope() as session:
        artist = Artist(name="Daft Punk", normalized_name="daft punk")
        album = Album(title="Discovery", normalized_title="discovery", artist=artist)
        session.add_all([artist, album])
        session.flush()

        canonical_track = Track(
            title="Harder Better Faster Stronger",
            normalized_title="harder better faster stronger",
            track_number=4,
            artist_id=artist.id,
            album_id=album.id,
            musicbrainz_id="mbid-hbfs-04",
            isrc="GBDUW0000059",
            duration=224000,
        )
        session.add(canonical_track)
        session.flush()

        lm_16 = LocalMedia(
            media_id=generate_nanoid(),
            track_id=canonical_track.id,
            file_path=_canonicalize_path(str(existing_lib_file)),
            file_format="flac",
            bit_depth=16,
            sample_rate=44100,
            bitrate=950,
        )
        session.add(lm_16)
        canonical_track_id = canonical_track.id

    # Incoming 24-bit/96kHz sibling edition in download_dir
    incoming_file = download_dir / "incoming_24_96.flac"
    incoming_file.write_bytes(b"24bit_96khz_master_audio_payload")

    monkeypatch.setattr(
        "echosync_core.extract_metadata",
        lambda p: {
            "codec": "flac",
            "bit_depth": 24,
            "sample_rate": 96000,
            "bitrate": 2800,
            "duration_ms": 224000,
        },
    )

    # Stop background watchdog on AutoImportService after init
    with patch.object(AutoImportService, "_start_watcher", lambda self: None):
        service = AutoImportService(library_root=library_dir)

    with (
        patch.object(service.enhancer, "tag_file_verified", return_value=True),
        patch.object(service.enhancer, "create_or_update_review_task", return_value=None),
    ):
        dest_path = service.finalize_import(
            incoming_file,
            {
                "title": "Harder Better Faster Stronger",
                "artist": "Daft Punk",
                "album": "Discovery",
                "track_number": 4,
                "musicbrainz_track_id": "mbid-hbfs-04",
                "isrc": "GBDUW0000059",
                "duration_ms": 224000,
            },
        )

    expected_dest = library_dir / "Daft Punk" / "Discovery" / "04 - Harder Better Faster Stronger [FLAC-24-96].flac"
    assert dest_path.resolve() == expected_dest.resolve()
    assert expected_dest.exists()
    assert existing_lib_file.exists()
    assert not incoming_file.exists()

    with music_db.session_scope() as session:
        tracks = session.query(Track).all()
        assert len(tracks) == 1
        assert tracks[0].id == canonical_track_id
        media_rows = session.query(LocalMedia).filter(LocalMedia.track_id == canonical_track_id).all()
        assert len(media_rows) == 2
        paths = {Path(m.file_path).name for m in media_rows}
        assert "04 - Harder Better Faster Stronger.flac" in paths
        assert "04 - Harder Better Faster Stronger [FLAC-24-96].flac" in paths


def test_library_watcher_deduplicates_and_reparents_by_mbid_and_isrc(isolated_ingestion_env, monkeypatch):
    """_process_new_file deduplicates and re-parents sibling editions under session.no_autoflush."""
    music_db = isolated_ingestion_env["music_db"]
    library_dir = isolated_ingestion_env["library_dir"]

    first_file = library_dir / "Artist" / "Album" / "04 - Title.flac"
    first_file.parent.mkdir(parents=True, exist_ok=True)
    first_file.write_bytes(b"A" * 70000)

    second_file = library_dir / "Artist" / "Album" / "04 - Title [FLAC-24-96].flac"
    second_file.write_bytes(b"B" * 70000)

    with music_db.session_scope() as session:
        artist = Artist(name="Artist", normalized_name="artist")
        album = Album(title="Album", normalized_title="album", artist=artist)
        session.add_all([artist, album])
        session.flush()

        canonical = Track(
            title="Title",
            normalized_title="title",
            track_number=4,
            artist_id=artist.id,
            album_id=album.id,
            musicbrainz_id="mbid-shared-track",
            isrc="USABC1234567",
            duration=180000,
        )
        session.add(canonical)
        session.flush()

        lm1 = LocalMedia(
            media_id=generate_nanoid(),
            track_id=canonical.id,
            file_path=_canonicalize_path(str(first_file)),
            file_format="flac",
            bit_depth=16,
            sample_rate=44100,
        )
        session.add(lm1)
        canonical_id = canonical.id

    # Second file has different artist alias so bulk_upsert_tracks alone would create a second Track
    monkeypatch.setattr(
        "services.library_watcher.echosync_core.extract_metadata",
        lambda p: {
            "title": "Title",
            "artist": "Artist feat. Guest",
            "album": "Album",
            "track_number": 4,
            "musicbrainz_track_id": "mbid-shared-track",
            "isrc": "USABC1234567",
            "codec": "flac",
            "bit_depth": 24,
            "sample_rate": 96000,
            "duration_ms": 180000,
        },
    )
    monkeypatch.setattr("services.library_watcher.event_bus.publish", lambda ev: None)

    _process_new_file(second_file)

    with music_db.session_scope() as session:
        all_tracks = session.query(Track).all()
        assert len(all_tracks) == 1
        assert all_tracks[0].id == canonical_id
        media_rows = session.query(LocalMedia).filter(LocalMedia.track_id == canonical_id).all()
        assert len(media_rows) == 2


# ── Task 3: LibraryReorganizerService per-track commits & suppress_path ───────


def test_library_reorganizer_suppresses_src_and_dst_and_commits_per_track(isolated_ingestion_env, monkeypatch):
    """LibraryReorganizerService suppresses both src/dst paths and commits each track independently."""
    music_db = isolated_ingestion_env["music_db"]
    library_dir = isolated_ingestion_env["library_dir"]

    file_a = library_dir / "unsorted" / "song_a.flac"
    file_b = library_dir / "unsorted" / "song_b.flac"
    file_a.parent.mkdir(parents=True, exist_ok=True)
    file_a.write_bytes(b"audio_a_bytes")
    file_b.write_bytes(b"audio_b_bytes")

    with music_db.session_scope() as session:
        artist = Artist(name="Reorg Artist", normalized_name="reorg artist")
        album = Album(title="Reorg Album", normalized_title="reorg album", artist=artist)
        session.add_all([artist, album])
        session.flush()

        t_a = Track(title="Song A", normalized_title="song a", track_number=1, artist_id=artist.id, album_id=album.id)
        t_b = Track(title="Song B", normalized_title="song b", track_number=2, artist_id=artist.id, album_id=album.id)
        session.add_all([t_a, t_b])
        session.flush()

        m_a = LocalMedia(media_id="reorg-a", track_id=t_a.id, file_path=str(file_a), file_format="flac")
        m_b = LocalMedia(media_id="reorg-b", track_id=t_b.id, file_path=str(file_b), file_format="flac")
        session.add_all([m_a, m_b])
        track_a_id, track_b_id = t_a.id, t_b.id

    monkeypatch.setattr(
        "services.library_reorganizer.get_library_preferences",
        lambda: (str(library_dir), "{Artist}/{Album}/{Track} - {Title}.{ext}"),
    )
    monkeypatch.setattr("services.library_reorganizer.get_prefer_canonical_studio_album", lambda: False)

    suppression_checks = []
    orig_execute = Gatekeeper.authorize_and_execute

    def spy_execute(manifest):
        src = manifest.get("src")
        dst = manifest.get("dst")
        suppression_checks.append((src, dst, is_path_suppressed(src), is_path_suppressed(dst)))
        if src and "song_b.flac" in src:
            raise OSError("Simulated failure on Track B")
        return orig_execute(manifest)

    monkeypatch.setattr(Gatekeeper, "authorize_and_execute", spy_execute)

    reorganizer = LibraryReorganizerService()
    reorganizer.library_root = library_dir
    reorganizer.reorganize_library(track_ids=[track_a_id, track_b_id])

    # Both src and dst were suppressed at Gatekeeper move time, then released afterward
    assert len(suppression_checks) == 2
    for src, dst, src_sup, dst_sup in suppression_checks:
        assert src_sup is True
        assert dst_sup is True
        assert is_path_suppressed(src) is False
        assert is_path_suppressed(dst) is False

    expected_a = library_dir / "Reorg Artist" / "Reorg Album" / "01 - Song A.flac"
    assert expected_a.exists()
    assert not file_a.exists()
    assert file_b.exists()

    # Track A was committed despite Track B failing
    with music_db.session_scope() as session:
        db_m_a = session.query(LocalMedia).filter_by(media_id="reorg-a").one()
        db_m_b = session.query(LocalMedia).filter_by(media_id="reorg-b").one()
        assert Path(db_m_a.file_path).resolve() == expected_a.resolve()
        assert Path(db_m_b.file_path).resolve() == file_b.resolve()


# ── Task 4: MediaScanManager._execute_scan try...finally state reset ──────────


@pytest.mark.parametrize(
    "client_factory,trigger_side_effect",
    [
        (lambda: (None, None), None),
        (lambda: (MagicMock(), None), None),  # early return when server_type missing
        (lambda: (_ for _ in ()).throw(RuntimeError("registry error")), None),
        (lambda: (MagicMock(trigger_library_scan=MagicMock(return_value=False)), "plex"), None),
        (
            lambda: (
                MagicMock(trigger_library_scan=MagicMock(side_effect=RuntimeError("network error"))),
                "plex",
            ),
            None,
        ),
    ],
)
def test_media_scan_manager_always_resets_scan_in_progress(client_factory, trigger_side_effect):
    """_execute_scan must reset _scan_in_progress to False on all early returns and exceptions."""
    mgr = MediaScanManager(delay_seconds=60)
    try:
        with patch.object(mgr, "_get_active_media_client", side_effect=client_factory):
            mgr._execute_scan()
        assert mgr._scan_in_progress is False
        assert mgr.get_status()["scan_in_progress"] is False
    finally:
        mgr.shutdown()


# ── Task 5: Gatekeeper Cross-Volume EXDEV Fallback ────────────────────────────


def test_gatekeeper_exdev_fallback_copies_verifies_and_deletes_source(tmp_path, monkeypatch):
    """On EXDEV, Gatekeeper copies to staging temp, verifies size+hash, promotes, and deletes src."""
    src_dir = tmp_path / "vol_a"
    dst_dir = tmp_path / "vol_b"
    src_dir.mkdir()
    dst_dir.mkdir()

    src_file = src_dir / "track.flac"
    payload = b"fLaC_valid_test_payload_" * 500
    src_file.write_bytes(payload)
    dst_file = dst_dir / "nested" / "01 - Track.flac"

    gk = Gatekeeper(allowed_roots=[tmp_path])

    copy_calls = []
    delete_calls = []
    orig_copy = echosync_core.copy_file
    orig_delete = echosync_core.delete_file

    def exdev_move(s, d):
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    def tracked_copy(s, d):
        copy_calls.append((s, d))
        return orig_copy(s, d)

    def tracked_delete(p):
        delete_calls.append(p)
        return orig_delete(p)

    monkeypatch.setattr(echosync_core, "safe_move_file", exdev_move)
    monkeypatch.setattr(echosync_core, "copy_file", tracked_copy)
    monkeypatch.setattr(echosync_core, "delete_file", tracked_delete)

    res = gk.authorize_and_execute({"operation": "safe_move", "src": str(src_file), "dst": str(dst_file)})
    assert res["success"] is True
    assert dst_file.exists()
    assert dst_file.read_bytes() == payload
    assert not src_file.exists()
    assert len(copy_calls) == 1
    assert ".tmp" in copy_calls[0][1]
    assert delete_calls == [src_file.as_posix()]
    assert not list(dst_file.parent.glob("*.tmp"))


def test_gatekeeper_exdev_size_mismatch_preserves_source_and_cleans_temp(tmp_path, monkeypatch):
    """If cross-volume copy produces truncated bytes, source stays intact and temp file is removed."""
    src_file = tmp_path / "src.flac"
    dst_file = tmp_path / "dst" / "final.flac"
    src_file.write_bytes(b"FULL_AUDIO_STREAM_DATA_1234567890")

    gk = Gatekeeper(allowed_roots=[tmp_path])

    monkeypatch.setattr(
        echosync_core,
        "safe_move_file",
        lambda s, d: (_ for _ in ()).throw(OSError(errno.EXDEV, "Invalid cross-device link")),
    )

    def truncated_copy(s, d):
        Path(d).write_bytes(b"SHORT")
        return 5

    monkeypatch.setattr(echosync_core, "copy_file", truncated_copy)

    with pytest.raises(OSError, match="size mismatch"):
        gk.authorize_and_execute({"operation": "safe_move", "src": str(src_file), "dst": str(dst_file)})

    assert src_file.exists()
    assert src_file.read_bytes() == b"FULL_AUDIO_STREAM_DATA_1234567890"
    assert not dst_file.exists()
    assert not list(dst_file.parent.glob("*.tmp"))


# ── Task 6: MediaManagerService Lossless Priority Alignment ───────────────────


def test_media_manager_lossless_priority_aligned_with_get_best_media(isolated_ingestion_env):
    """MediaManagerService orders and streams media using (is_lossless, bitrate, sample_rate, bit_depth)."""
    music_db = isolated_ingestion_env["music_db"]
    library_dir = isolated_ingestion_env["library_dir"]

    mp3_file = library_dir / "track_320.mp3"
    flac_cd_file = library_dir / "track_16_44.flac"
    flac_hi_file = library_dir / "track_24_96.flac"
    mp3_file.write_bytes(b"mp3")
    flac_cd_file.write_bytes(b"flac16")
    flac_hi_file.write_bytes(b"flac24")

    with music_db.session_scope() as session:
        artist = Artist(name="Audiophile", normalized_name="audiophile")
        session.add(artist)
        session.flush()

        track = Track(
            title="Reference Track",
            normalized_title="reference track",
            artist_id=artist.id,
            sync_id="sync_audiophile_1",
        )
        session.add(track)
        session.flush()

        # Deliberately give MP3 higher numeric bitrate than low-bitrate FLAC tag to verify is_lossless dominates
        m_mp3 = LocalMedia(
            track_id=track.id,
            media_id="m_mp3",
            file_path=str(mp3_file),
            file_format="mp3",
            bitrate=320,
            sample_rate=44100,
            bit_depth=16,
        )
        m_flac_cd = LocalMedia(
            track_id=track.id,
            media_id="m_flac_cd",
            file_path=str(flac_cd_file),
            file_format="flac",
            bitrate=250,
            sample_rate=44100,
            bit_depth=16,
        )
        m_flac_hi = LocalMedia(
            track_id=track.id,
            media_id="m_flac_hi",
            file_path=str(flac_hi_file),
            file_format="flac",
            bitrate=250,
            sample_rate=96000,
            bit_depth=24,
        )
        session.add_all([m_mp3, m_flac_cd, m_flac_hi])
        session.flush()

        best_from_track = track.get_best_media()
        best_from_service = MediaManagerService.get_best_media(track)
        ordered = MediaManagerService.order_media_files(list(track.media_files))

        assert best_from_track is not None
        assert best_from_service is not None
        assert best_from_service.media_id == best_from_track.media_id == "m_flac_hi"
        assert [m.media_id for m in ordered] == ["m_flac_hi", "m_flac_cd", "m_mp3"]

    svc = MediaManagerService(db=music_db)
    # 1. Best lossless hi-res file is streamed first
    assert Path(svc.get_track_stream("sync_audiophile_1")).resolve() == flac_hi_file.resolve()

    # 2. If hi-res file is missing on disk, falls back to CD FLAC (still before 320 MP3)
    flac_hi_file.unlink()
    assert Path(svc.get_track_stream("sync_audiophile_1")).resolve() == flac_cd_file.resolve()

    # 3. If both FLAC files are missing, falls back to MP3
    flac_cd_file.unlink()
    assert Path(svc.get_track_stream("sync_audiophile_1")).resolve() == mp3_file.resolve()
