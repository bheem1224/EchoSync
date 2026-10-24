from pathlib import Path
from unittest.mock import MagicMock

import pytest

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
from database.working_database import (
    ReviewTask,
    WorkingBase,
    WorkingDatabase,
)
from web.routes.metadata_review import (
    ApproveReviewQueueRequest,
    _import_single_file,
    approve_review_queue_item,
)


@pytest.fixture
def review_test_env(tmp_path, monkeypatch):
    library_dir = tmp_path / "library"
    download_dir = tmp_path / "downloads"
    library_dir.mkdir(parents=True, exist_ok=True)
    download_dir.mkdir(parents=True, exist_ok=True)

    music_db_file = tmp_path / "music.db"
    working_db_file = tmp_path / "working.db"

    music_db = MusicDatabase(str(music_db_file))
    Base.metadata.create_all(music_db.engine)

    work_db = WorkingDatabase(str(working_db_file))
    WorkingBase.metadata.create_all(work_db.engine)

    def mock_config(key, default=None):
        if key in ("storage.library_dir", "library_dir"):
            return str(library_dir)
        if key in ("storage.download_dir", "download_dir"):
            return str(download_dir)
        if "dir" in key:
            return str(tmp_path)
        if key == "library_preferences":
            return (str(library_dir), "{Artist}/{Album}/{Track} - {Title}.{ext}")
        if key == "file_organization_pattern":
            return "{Artist}/{Album}/{Track} - {Title}.{ext}"
        return default

    monkeypatch.setattr("core.settings.config_manager.get", mock_config)
    monkeypatch.setattr(
        "core.path_formatter.get_library_preferences",
        lambda: (str(library_dir), "{Artist}/{Album}/{Track} - {Title}.{ext}"),
    )
    monkeypatch.setattr("core.path_formatter.get_reorganize_library_on_enhancement", lambda: True)

    monkeypatch.setattr("web.routes.metadata_review.get_database", lambda: music_db)
    monkeypatch.setattr("web.routes.metadata_review.get_working_database", lambda: work_db)
    monkeypatch.setattr("database.music_database.get_database", lambda *a, **kw: music_db)
    monkeypatch.setattr("database.working_database.get_working_database", lambda *a, **kw: work_db)

    # Mock metadata enhancer so tests do not attempt native tagging on dummy bytes
    mock_enhancer = MagicMock()
    mock_enhancer.tag_file.return_value = True
    mock_enhancer.tag_file_verified.return_value = True
    monkeypatch.setattr("web.routes.metadata_review.get_metadata_enhancer", lambda: mock_enhancer)

    # Synchronous job queue to execute background approval task immediately
    executed_jobs = []

    class FakeJobQueue:
        def register_job(self, name, func, interval_seconds=None):
            self.func = func

        def execute_job_now(self, name):
            self.func()
            executed_jobs.append(name)

        from contextlib import contextmanager

        @contextmanager
        def db_write_lease(self, task_name="", timeout=30.0):
            yield

    fake_job_queue = FakeJobQueue()
    import core.job_queue

    monkeypatch.setattr(core.job_queue, "job_queue", fake_job_queue)

    return {
        "music_db": music_db,
        "work_db": work_db,
        "library_dir": library_dir,
        "download_dir": download_dir,
        "executed_jobs": executed_jobs,
    }


def test_approval_path_collision_does_not_crash(review_test_env):
    """
    Test A: Approval with relocated path collision does NOT crash with
    sqlite3.IntegrityError: UNIQUE constraint failed: local_media.file_path.

    Verifies that when a target file path is already allocated to an existing
    LocalMedia row in the database, the approval pipeline automatically disambiguates
    the target path (e.g. appends counter '(1)') instead of crashing on the unique constraint.
    """
    music_db = review_test_env["music_db"]
    work_db = review_test_env["work_db"]
    library_dir = review_test_env["library_dir"]
    download_dir = review_test_env["download_dir"]

    # 1. Seed canonical track and media already occupying the target library path
    canon_file = library_dir / "Adele" / "21" / "01 - Rolling in the Deep.flac"
    canon_file.parent.mkdir(parents=True, exist_ok=True)
    canon_file.write_bytes(b"master_audio_1_distinct_stream")

    mid_canon = f"mid_{generate_nanoid(8)}"
    with music_db.session_scope() as session:
        artist = Artist(name="Adele", normalized_name="adele")
        album = Album(title="21", normalized_title="21", artist=artist)
        session.add_all([artist, album])
        session.flush()

        canon_track = Track(
            title="Rolling in the Deep",
            normalized_title="rolling in the deep",
            edition=None,
            track_number=1,
            artist_id=artist.id,
            album_id=album.id,
            duration=228000,
        )
        session.add(canon_track)
        session.flush()

        lm_canon = LocalMedia(
            media_id=mid_canon,
            track_id=canon_track.id,
            file_path=_canonicalize_path(str(canon_file)),
            file_size_bytes=canon_file.stat().st_size,
            file_format="flac",
        )
        session.add(lm_canon)
        session.commit()

    # 2. Incoming distinct audio file in download_dir
    incoming_file = download_dir / "incoming_audio.flac"
    incoming_file.write_bytes(b"master_audio_2_distinct_stream_different_length")

    mid_incoming = f"mid_{generate_nanoid(8)}"
    # Pre-index incoming file in music_db as unorganized download under staging track
    with music_db.session_scope() as session:
        staging_track = Track(
            title="Rolling in the Deep (Staging)",
            normalized_title="rolling in the deep staging",
            artist_id=artist.id,
            album_id=album.id,
            track_number=1,
        )
        session.add(staging_track)
        session.flush()

        lm_incoming = LocalMedia(
            media_id=mid_incoming,
            track_id=staging_track.id,
            file_path=_canonicalize_path(str(incoming_file)),
            file_size_bytes=incoming_file.stat().st_size,
            file_format="flac",
        )
        session.add(lm_incoming)
        session.commit()

    # Create ReviewTask in working_db
    with work_db.session_scope() as session:
        task = ReviewTask(
            file_path=str(incoming_file),
            media_id=mid_incoming,
            status="pending",
            confidence_score=0.92,
            track_data={
                "artist": "Adele",
                "album": "21",
                "title": "Rolling in the Deep",
                "track_number": 1,
                "edition": None,
                "media_id": mid_incoming,
            },
        )
        session.add(task)
        session.commit()
        task_id = task.id

    # 3. Approve review item pointing to the same metadata
    payload = ApproveReviewQueueRequest(
        metadata={
            "artist": "Adele",
            "album": "21",
            "title": "Rolling in the Deep",
            "track_number": 1,
            "edition": None,
            "media_id": mid_incoming,
        }
    )

    # Must NOT raise sqlite3.IntegrityError
    res = approve_review_queue_item(task_id, payload)
    assert res["success"] is True

    # 4. Verify that:
    # - Original canonical file remains untouched
    assert canon_file.exists()
    assert canon_file.read_bytes() == b"master_audio_1_distinct_stream"

    # - Incoming file was disambiguated to (1)
    disambiguated_file = library_dir / "Adele" / "21" / "01 - Rolling in the Deep (1).flac"
    assert disambiguated_file.exists()
    assert disambiguated_file.read_bytes() == b"master_audio_2_distinct_stream_different_length"

    # - Both LocalMedia rows exist in music_db with distinct paths without collision
    with music_db.session_scope() as session:
        all_lm = session.query(LocalMedia).all()
        assert len(all_lm) == 2
        paths = {lm.file_path for lm in all_lm}
        assert _canonicalize_path(str(canon_file)) in paths
        assert _canonicalize_path(str(disambiguated_file)) in paths


def test_approval_path_collision_brand_new_file_does_not_crash(review_test_env):
    """
    Test A (unindexed variant): A completely new file arriving from downloads
    (never pre-indexed in music.db) whose metadata points to an existing file in the library.
    Verifies that the approval pipeline checks disk and DB allocations, disambiguates the path,
    and inserts the new record without crashing.
    """
    music_db = review_test_env["music_db"]
    work_db = review_test_env["work_db"]
    library_dir = review_test_env["library_dir"]
    download_dir = review_test_env["download_dir"]

    # 1. Seed canonical track in music_db
    canon_file = library_dir / "Coldplay" / "Parachutes" / "01 - Don't Panic.flac"
    canon_file.parent.mkdir(parents=True, exist_ok=True)
    canon_file.write_bytes(b"coldplay_canonical_dont_panic")

    with music_db.session_scope() as session:
        artist = Artist(name="Coldplay", normalized_name="coldplay")
        album = Album(title="Parachutes", normalized_title="parachutes", artist=artist)
        session.add_all([artist, album])
        session.flush()

        canon_track = Track(
            title="Don't Panic",
            normalized_title="dont panic",
            edition=None,
            track_number=1,
            artist_id=artist.id,
            album_id=album.id,
            duration=137000,
        )
        session.add(canon_track)
        session.flush()

        lm_canon = LocalMedia(
            media_id=f"mid_{generate_nanoid(8)}",
            track_id=canon_track.id,
            file_path=_canonicalize_path(str(canon_file)),
            file_size_bytes=canon_file.stat().st_size,
            file_format="flac",
        )
        session.add(lm_canon)
        session.commit()

    # 2. Brand new incoming file in download_dir (NOT in music.db)
    incoming_file = download_dir / "new_dont_panic.flac"
    incoming_file.write_bytes(b"coldplay_alternate_master_dont_panic")

    with work_db.session_scope() as session:
        task = ReviewTask(
            file_path=str(incoming_file),
            status="pending",
            confidence_score=0.90,
            track_data={
                "artist": "Coldplay",
                "album": "Parachutes",
                "title": "Don't Panic",
                "track_number": 1,
            },
        )
        session.add(task)
        session.commit()
        task_id = task.id

    payload = ApproveReviewQueueRequest(
        metadata={
            "artist": "Coldplay",
            "album": "Parachutes",
            "title": "Don't Panic",
            "track_number": 1,
        }
    )

    res = approve_review_queue_item(task_id, payload)
    assert res["success"] is True

    # Disambiguated file exists
    disambiguated_file = library_dir / "Coldplay" / "Parachutes" / "01 - Don't Panic (1).flac"
    assert disambiguated_file.exists()

    with music_db.session_scope() as session:
        all_lm = session.query(LocalMedia).all()
        assert len(all_lm) == 2
        paths = {lm.file_path for lm in all_lm}
        assert _canonicalize_path(str(canon_file)) in paths
        assert _canonicalize_path(str(disambiguated_file)) in paths


def test_stripping_edition_reconsolidates_track_and_prunes_orphan(review_test_env):
    """
    Test B: Stripping an edition merges LocalMedia into the primary canonical Track
    and prunes the leftover orphaned Track.

    Verifies that when a track previously had an edition tag (e.g. "Remix") creating
    a separate Track row, stripping that edition causes the LocalMedia to re-link to
    the preexisting canonical Track row in the album, deleting the orphaned Track.
    """
    music_db = review_test_env["music_db"]
    work_db = review_test_env["work_db"]
    library_dir = review_test_env["library_dir"]

    # 1. Seed canonical track ("Lights", edition=None) and variant track ("Lights", edition="Remix")
    f_canon = library_dir / "Ellie Goulding" / "Lights" / "01 - Lights.flac"
    f_canon.parent.mkdir(parents=True, exist_ok=True)
    f_canon.write_bytes(b"lights_canonical_audio")

    f_remix = library_dir / "Ellie Goulding" / "Lights" / "01 - Lights (Remix).flac"
    f_remix.write_bytes(b"lights_remix_audio")

    mid_canon = f"mid_{generate_nanoid(8)}"
    mid_remix = f"mid_{generate_nanoid(8)}"

    with music_db.session_scope() as session:
        artist = Artist(name="Ellie Goulding", normalized_name="ellie goulding")
        album = Album(title="Lights", normalized_title="lights", artist=artist)
        session.add_all([artist, album])
        session.flush()

        canon_track = Track(
            title="Lights",
            normalized_title="lights",
            edition=None,
            track_number=1,
            artist_id=artist.id,
            album_id=album.id,
            duration=210000,
        )
        remix_track = Track(
            title="Lights",
            normalized_title="lights",
            edition="Remix",
            track_number=1,
            artist_id=artist.id,
            album_id=album.id,
            duration=240000,
        )
        session.add_all([canon_track, remix_track])
        session.flush()

        lm_canon = LocalMedia(
            media_id=mid_canon,
            track_id=canon_track.id,
            file_path=_canonicalize_path(str(f_canon)),
            file_size_bytes=f_canon.stat().st_size,
            file_format="flac",
        )
        lm_remix = LocalMedia(
            media_id=mid_remix,
            track_id=remix_track.id,
            file_path=_canonicalize_path(str(f_remix)),
            file_size_bytes=f_remix.stat().st_size,
            file_format="flac",
        )
        session.add_all([lm_canon, lm_remix])
        session.commit()

        canon_track_id = canon_track.id
        remix_track_id = remix_track.id
        album_id = album.id

    # 2. Stage ReviewTask for f_remix stripping the edition to None/empty
    with work_db.session_scope() as session:
        task = ReviewTask(
            file_path=str(f_remix),
            media_id=mid_remix,
            status="pending",
            confidence_score=0.95,
            track_data={
                "artist": "Ellie Goulding",
                "album": "Lights",
                "title": "Lights",
                "track_number": 1,
                "edition": "Remix",
                "media_id": mid_remix,
            },
        )
        session.add(task)
        session.commit()
        task_id = task.id

    # 3. Approve review task with edition stripped
    payload = ApproveReviewQueueRequest(
        metadata={
            "artist": "Ellie Goulding",
            "album": "Lights",
            "title": "Lights",
            "track_number": 1,
            "edition": None,
            "media_id": mid_remix,
        }
    )

    res = approve_review_queue_item(task_id, payload)
    assert res["success"] is True

    # 4. Assertions:
    with music_db.session_scope() as session:
        # Exactly 1 Track exists under the album
        album_tracks = session.query(Track).filter(Track.album_id == album_id).all()
        assert len(album_tracks) == 1
        surviving_track = album_tracks[0]
        assert surviving_track.id == canon_track_id
        assert surviving_track.title == "Lights"
        assert surviving_track.edition is None

        # Orphaned remix_track was completely pruned from database
        assert session.get(Track, remix_track_id) is None

        # Both LocalMedia records are now attached to surviving canonical track
        media_records = session.query(LocalMedia).filter(LocalMedia.track_id == canon_track_id).all()
        assert len(media_records) == 2
        m_ids = {m.media_id for m in media_records}
        assert mid_canon in m_ids
        assert mid_remix in m_ids


def test_multiple_editions_attach_as_siblings_under_single_track(review_test_env):
    """
    Test C: Multiple file editions (e.g. 16-bit vs 24-bit FLAC) attach cleanly
    as siblings under a single Track entity with distinct paths.
    """
    music_db = review_test_env["music_db"]
    work_db = review_test_env["work_db"]
    library_dir = review_test_env["library_dir"]
    download_dir = review_test_env["download_dir"]

    # 1. Seed Track with 16-bit FLAC
    f_16bit = library_dir / "Adele" / "21" / "01 - Rolling in the Deep.flac"
    f_16bit.parent.mkdir(parents=True, exist_ok=True)
    f_16bit.write_bytes(b"audio_content_16bit_flac")

    mid_16bit = f"mid_{generate_nanoid(8)}"
    with music_db.session_scope() as session:
        artist = Artist(name="Adele", normalized_name="adele")
        album = Album(title="21", normalized_title="21", artist=artist)
        session.add_all([artist, album])
        session.flush()

        track = Track(
            title="Rolling in the Deep",
            normalized_title="rolling in the deep",
            edition=None,
            track_number=1,
            artist_id=artist.id,
            album_id=album.id,
            duration=228000,
        )
        session.add(track)
        session.flush()

        lm_16 = LocalMedia(
            media_id=mid_16bit,
            track_id=track.id,
            file_path=_canonicalize_path(str(f_16bit)),
            file_size_bytes=f_16bit.stat().st_size,
            file_format="flac",
            bit_depth=16,
            sample_rate=44100,
        )
        session.add(lm_16)
        session.commit()
        track_id = track.id
        album_id = album.id

    # 2. Incoming 24-bit / 96kHz FLAC file in download_dir
    f_24bit = download_dir / "24bit_download.flac"
    f_24bit.write_bytes(b"audio_content_24bit_flac_distinct")

    mid_24bit = f"mid_{generate_nanoid(8)}"
    with music_db.session_scope() as session:
        staging_track_24 = Track(
            title="Rolling in the Deep (24bit)",
            normalized_title="rolling in the deep 24bit",
            artist_id=artist.id,
            album_id=album.id,
            track_number=1,
        )
        session.add(staging_track_24)
        session.flush()

        lm_24 = LocalMedia(
            media_id=mid_24bit,
            track_id=staging_track_24.id,
            file_path=_canonicalize_path(str(f_24bit)),
            file_size_bytes=f_24bit.stat().st_size,
            file_format="flac",
            bit_depth=24,
            sample_rate=96000,
        )
        session.add(lm_24)
        session.commit()

    with work_db.session_scope() as session:
        task = ReviewTask(
            file_path=str(f_24bit),
            media_id=mid_24bit,
            status="pending",
            confidence_score=0.98,
            track_data={
                "artist": "Adele",
                "album": "21",
                "title": "Rolling in the Deep",
                "track_number": 1,
                "edition": None,
                "bit_depth": 24,
                "sample_rate": 96000,
                "media_id": mid_24bit,
            },
        )
        session.add(task)
        session.commit()
        task_id = task.id

    # 3. Approve review task
    payload = ApproveReviewQueueRequest(
        metadata={
            "artist": "Adele",
            "album": "21",
            "title": "Rolling in the Deep",
            "track_number": 1,
            "edition": None,
            "bit_depth": 24,
            "sample_rate": 96000,
            "media_id": mid_24bit,
        }
    )

    res = approve_review_queue_item(task_id, payload)
    assert res["success"] is True

    # 4. Verify assertions:
    with music_db.session_scope() as session:
        # Exactly 1 Track exists in the album
        tracks = session.query(Track).filter(Track.album_id == album_id).all()
        assert len(tracks) == 1
        assert tracks[0].id == track_id

        # Both LocalMedia attach cleanly under track_id
        media_files = session.query(LocalMedia).filter(LocalMedia.track_id == track_id).all()
        assert len(media_files) == 2

        # Distinct paths
        paths = [m.file_path for m in media_files]
        assert len(set(paths)) == 2

        # One path should have the high-res quality tag "[24-96]" or disambiguated "(1)"
        assert any("[24-96]" in p or "(1)" in p for p in paths)

        # Both files physically exist on disk
        for p in paths:
            assert Path(p).exists()


def test_import_single_file_true_duplicate_merges_and_prunes(review_test_env):
    """
    Test Case A in _import_single_file:
    When an incoming file has an identical byte size (or chromaprint) to an already
    indexed file at the target path, _import_single_file merges the redundant LocalMedia
    into conflicting_lm and prunes any empty orphaned track entity.
    """
    music_db = review_test_env["music_db"]
    library_dir = review_test_env["library_dir"]
    download_dir = review_test_env["download_dir"]

    # Canonical file
    f_canon = library_dir / "Artist" / "Album" / "01 - Song.flac"
    f_canon.parent.mkdir(parents=True, exist_ok=True)
    f_canon.write_bytes(b"exact_identical_audio_bytes")

    # Duplicate file in staging
    f_dup = download_dir / "exact_dup.flac"
    f_dup.write_bytes(b"exact_identical_audio_bytes")

    mid_canon = f"mid_{generate_nanoid(8)}"
    mid_dup = f"mid_{generate_nanoid(8)}"

    with music_db.session_scope() as session:
        artist = Artist(name="Artist", normalized_name="artist")
        album = Album(title="Album", normalized_title="album", artist=artist)
        session.add_all([artist, album])
        session.flush()

        t_canon = Track(
            title="Song",
            normalized_title="song",
            artist_id=artist.id,
            album_id=album.id,
            track_number=1,
        )
        t_temp = Track(
            title="Song Temp",
            normalized_title="song temp",
            artist_id=artist.id,
            album_id=album.id,
            track_number=1,
        )
        session.add_all([t_canon, t_temp])
        session.flush()

        lm_canon = LocalMedia(
            media_id=mid_canon,
            track_id=t_canon.id,
            file_path=_canonicalize_path(str(f_canon)),
            file_size_bytes=f_canon.stat().st_size,
            file_format="flac",
        )
        lm_dup = LocalMedia(
            media_id=mid_dup,
            track_id=t_temp.id,
            file_path=_canonicalize_path(str(f_dup)),
            file_size_bytes=f_dup.stat().st_size,
            file_format="flac",
        )
        session.add_all([lm_canon, lm_dup])
        session.commit()

        temp_track_id = t_temp.id
        canon_track_id = t_canon.id

    metadata = {
        "artist": "Artist",
        "album": "Album",
        "title": "Song",
        "track_number": 1,
        "media_id": mid_dup,
    }

    # Attempt importing f_dup targeting f_canon's path
    res = _import_single_file(
        f_canon,
        metadata,
        old_file_path=f_dup,
        media_id=mid_dup,
    )
    assert res == 1

    with music_db.session_scope() as session:
        # lm_dup should have been deleted (merged into lm_canon)
        remaining_lm = session.query(LocalMedia).all()
        assert len(remaining_lm) == 1
        assert remaining_lm[0].media_id == mid_canon

        # Temporary orphaned track should have been pruned
        assert session.get(Track, temp_track_id) is None
        assert session.get(Track, canon_track_id) is not None
