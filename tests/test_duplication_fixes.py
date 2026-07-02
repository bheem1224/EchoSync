import os
from pathlib import Path
from core.matching_engine.echo_sync_track import EchosyncTrack, EchosyncMedia
from database.music_database import MusicDatabase, Track, LocalMedia, ExternalIdentifier, AudioFingerprint, Base
from database.bulk_operations import LibraryManager, _canonicalize_path
from plugins.EchoSync.local_server.database_cleanup import DatabaseCleanupJob


def _make_manager(tmpdir):
    db_path = os.path.join(tmpdir, "library.db")
    db = MusicDatabase(database_path=db_path)
    Base.metadata.create_all(db.engine)
    return db, LibraryManager(db.session_factory)


def test_path_canonicalization():
    # Test posix slashes, resolved path, trailing slash removal
    p1 = "c:\\foo\\bar\\..\\bar/"
    canon = _canonicalize_path(p1)
    # On Windows, path resolving converts to absolute and lowercase/uppercase is normalized depending on OS
    assert "/" in canon or "\\" in canon
    assert not canon.endswith("/")
    assert not canon.endswith("\\")

    # virtual paths remain untouched
    assert _canonicalize_path("virtual://something") == "virtual://something"


def test_duplicate_local_media_deduplicated_post_upsert(tmp_path):
    db, manager = _make_manager(str(tmp_path))

    # We will mock the physical file on disk using tmp_path so .resolve() succeeds
    test_file = tmp_path / "song.mp3"
    test_file.touch()
    path_str = str(test_file)

    # 1. Import local track with file path
    media1 = EchosyncMedia(file_path=path_str, file_size_bytes=1000)
    t1 = EchosyncTrack(
        raw_title="Deduplication Song",
        artist_name="Test Artist",
        album_title="Test Album",
        media=[media1]
    )
    manager.bulk_import([t1])

    # Verify 1 track and 1 local media row
    assert db.count_tracks() == 1
    assert db.count_files() == 1

    # 2. Import the track again via Plex (different path formatting/resolution)
    media2 = EchosyncMedia(file_path=path_str.replace("\\", "/"), file_size_bytes=1000)
    t2 = EchosyncTrack(
        raw_title="Deduplication Song",
        artist_name="Test Artist",
        album_title="Test Album",
        identifiers={"plex": "plex123"},
        media=[media2]
    )
    manager.bulk_import([t2])

    # The track and local media row should remain 1, but the track now has the Plex identifier!
    assert db.count_tracks() == 1
    assert db.count_files() == 1

    with db.session_scope() as session:
        track = session.query(Track).first()
        assert len(track.media_files) == 1
        assert len(track.external_identifiers) == 1
        assert track.external_identifiers[0].plugin_item_id == "plex123"


def test_virtual_placeholder_skipped_when_real_exists(tmp_path):
    db, manager = _make_manager(str(tmp_path))

    test_file = tmp_path / "song.mp3"
    test_file.touch()
    path_str = str(test_file)

    # 1. Import with real file path first
    media1 = EchosyncMedia(file_path=path_str, file_size_bytes=1000)
    t1 = EchosyncTrack(
        raw_title="Virtual Test Song",
        artist_name="Test Artist",
        album_title="Test Album",
        media=[media1]
    )
    manager.bulk_import([t1])

    # 2. Import with Plex identifier only (no media provided in this sync iteration)
    t2 = EchosyncTrack(
        raw_title="Virtual Test Song",
        artist_name="Test Artist",
        album_title="Test Album",
        identifiers={"plex": "plex_only"}
    )
    manager.bulk_import([t2])

    assert db.count_tracks() == 1
    assert db.count_files() == 1

    with db.session_scope() as session:
        media_rows = session.query(LocalMedia).all()
        assert len(media_rows) == 1
        assert not media_rows[0].file_path.startswith("virtual://")


def test_database_cleanup_job_deduplicates_and_reparents(tmp_path):
    db, manager = _make_manager(str(tmp_path))

    test_file = tmp_path / "song.mp3"
    test_file.touch()
    path_str = str(test_file)

    # Manually create duplicate LocalMedia rows (violating constraints, e.g. different casing or representation)
    with db.session_scope() as session:
        from database.music_database import Artist, Album
        artist = Artist(name="Test Artist", normalized_name="test artist")
        session.add(artist)
        session.flush()

        album = Album(title="Test Album", normalized_title="test album", artist_id=artist.id)
        session.add(album)
        session.flush()

        t = Track(title="Song", normalized_title="song", artist_id=artist.id, album_id=album.id, sync_id="sync123")
        session.add(t)
        session.flush()

        m1 = LocalMedia(track_id=t.id, media_id="m111", file_path=path_str, file_size_bytes=1000)
        m2 = LocalMedia(track_id=t.id, media_id="m222", file_path=path_str.upper(), file_size_bytes=1200)
        session.add_all([m1, m2])
        session.flush()

        # Add external identifier to the duplicate (m2)
        ext = ExternalIdentifier(media_id="m222", plugin_source="plex", plugin_item_id="plex456")
        # Add audio fingerprint to the duplicate (m2)
        fp = AudioFingerprint(media_id="m222", chromaprint="fingerprint123")
        session.add_all([ext, fp])
        session.commit()

    # Now run the DatabaseCleanupJob
    job = DatabaseCleanupJob()
    # Mock update_progress to prevent errors
    job.update_progress = lambda current, total, status="": None
    
    # We need to make sure we run inside the same database engine
    import plugins.EchoSync.local_server.database_cleanup as db_clean_module
    original_get_db = db_clean_module.get_database
    db_clean_module.get_database = lambda: db

    try:
        job.execute()
    finally:
        db_clean_module.get_database = original_get_db

    # Check results
    assert db.count_files() == 1
    with db.session_scope() as session:
        all_m = session.query(LocalMedia).all()
        assert len(all_m) == 1
        keeper = all_m[0]
        assert keeper.media_id == "m111"  # kept lowest id

        # The external identifier and fingerprint must have been reparented to keeper (m111)
        all_ext = session.query(ExternalIdentifier).all()
        assert len(all_ext) == 1
        assert all_ext[0].media_id == "m111"

        all_fp = session.query(AudioFingerprint).all()
        assert len(all_fp) == 1
        assert all_fp[0].media_id == "m111"


def test_statistics_queries_deduplicate_and_exclude_virtual(tmp_path):
    db, manager = _make_manager(str(tmp_path))

    with db.session_scope() as session:
        from database.music_database import Artist, Album
        artist = Artist(name="Test Artist", normalized_name="test artist")
        session.add(artist)
        session.flush()

        album = Album(title="Test Album", normalized_title="test album", artist_id=artist.id)
        session.add(album)
        session.flush()

        t = Track(title="Song", normalized_title="song", artist_id=artist.id, album_id=album.id, sync_id="sync123")
        session.add(t)
        session.flush()

        # 1. Real media file
        m1 = LocalMedia(track_id=t.id, media_id="m1", file_path="c:/path/to/song.mp3", file_size_bytes=10 * 1024 * 1024)
        # 2. Duplicate media file (pointing to same file path but different casing/slashes)
        m2 = LocalMedia(track_id=t.id, media_id="m2", file_path="C:/path/to/song.mp3", file_size_bytes=10 * 1024 * 1024)
        # 3. Virtual media file
        m3 = LocalMedia(track_id=t.id, media_id="m3", file_path="virtual://plex/123", file_size_bytes=5 * 1024 * 1024)

        session.add_all([m1, m2, m3])
        session.commit()

    # count_files should be 1
    assert db.count_files() == 1

    # get_total_storage_used should be 10MB
    assert db.get_total_storage_used() == 10 * 1024 * 1024


def test_album_artist_identifiers_ignored_in_external_identifiers(tmp_path):
    db, manager = _make_manager(str(tmp_path))

    test_file = tmp_path / "song.mp3"
    test_file.touch()
    path_str = str(test_file)

    # Ingest a track containing track MBID, plus album/artist identifiers in `identifiers` dictionary
    media1 = EchosyncMedia(file_path=path_str, file_size_bytes=1000)
    t1 = EchosyncTrack(
        raw_title="Scope Test Song",
        artist_name="Test Artist",
        album_title="Test Album",
        media=[media1],
        identifiers={
            "musicbrainz_id": "track-mbid-123",            # Should be accepted (track level)
            "plex": "plex-track-456",                      # Should be accepted (track level)
            "musicbrainz_release_id": "album-mbid-789",    # Should be ignored (album level)
            "musicbrainz_artistid": "artist-mbid-000",     # Should be ignored (artist level)
        }
    )
    manager.bulk_import([t1])

    # Verify that only the track level external identifiers were created
    with db.session_scope() as session:
        all_ext = session.query(ExternalIdentifier).all()
        # Should only have "musicbrainz_id" and "plex"
        sources = {ext.plugin_source for ext in all_ext}
        assert "musicbrainz_id" in sources
        assert "plex" in sources
        assert "musicbrainz_release_id" not in sources
        assert "musicbrainz_artistid" not in sources
        assert len(all_ext) == 2


def test_unicode_nfc_normalization(tmp_path):
    db, manager = _make_manager(str(tmp_path))

    # NFC (Café) vs NFD (Cafe + combining acute accent)
    title_nfc = "Caf\u00e9"
    title_nfd = "Cafe\u0301"

    # Create temporary file with NFD casing/path naming
    test_file = tmp_path / f"song_{title_nfd}.mp3"
    test_file.touch()
    path_nfd = str(test_file)

    media1 = EchosyncMedia(file_path=path_nfd, file_size_bytes=1000)
    t1 = EchosyncTrack(
        raw_title=title_nfd,
        artist_name="Artist " + title_nfd,
        album_title="Album " + title_nfd,
        media=[media1]
    )

    # Ingest the NFD track
    manager.bulk_import([t1])

    # 1. Assert stored title, artist, album and paths are NFC normalized
    with db.session_scope() as session:
        track = session.query(Track).first()
        assert track.title == title_nfc
        assert track.artist.name == "Artist " + title_nfc
        assert track.album.title == "Album " + title_nfc
        
        # Path should be NFC normalized
        media_row = session.query(LocalMedia).first()
        assert title_nfc in media_row.file_path
        assert title_nfd not in media_row.file_path

    # 2. Ingest again using NFC raw values to verify it matches case-insensitively and unicode-insensitively
    path_nfc = path_nfd.replace(title_nfd, title_nfc)
    media2 = EchosyncMedia(file_path=path_nfc, file_size_bytes=1000)
    t2 = EchosyncTrack(
        raw_title=title_nfc,
        artist_name="Artist " + title_nfc,
        album_title="Album " + title_nfc,
        media=[media2]
    )
    manager.bulk_import([t2])

    # Should still only be 1 track and 1 LocalMedia in the DB
    assert db.count_tracks() == 1
    assert db.count_files() == 1


def test_cjk_hooks_bypassed_during_ingestion():
    from plugins.EchoSync.cjk_language_pack import _on_pre_normalize_text
    
    # 1. Normal context: should perform Traditional -> Simplified CJK normalization
    res_normal = _on_pre_normalize_text("長風謠")
    assert res_normal == "长风谣"
    
    # 2. Simulated bulk_operations context: should bypass and return unmutated Traditional Chinese
    # We compile a wrapper function with a custom filename containing "bulk_operations" to mock the call stack.
    code_str = """
def run_in_bulk_operations(func, arg):
    return func(arg)
"""
    globs = {}
    exec(compile(code_str, "C:/some/path/to/bulk_operations.py", "exec"), globs)
    run_in_bulk_operations = globs["run_in_bulk_operations"]
    
    res_ingestion = run_in_bulk_operations(_on_pre_normalize_text, "長風謠")
    assert res_ingestion == "長風謠"


def test_decorate_mode_safely_decorates_identifiers(tmp_path):
    db, manager = _make_manager(str(tmp_path))

    # 1. Normal import of a track with its local media file
    media1 = EchosyncMedia(file_path="/data/library/artist/album/song.mp3", file_size_bytes=1000)
    t1 = EchosyncTrack(
        raw_title="Song Title",
        artist_name="Artist Name",
        album_title="Album Title",
        media=[media1],
        identifiers={"plex": "plex_id_111"}
    )
    manager.bulk_import([t1])

    from database.bulk_operations import _canonicalize_path
    expected_path = _canonicalize_path("/data/library/artist/album/song.mp3")

    assert db.count_tracks() == 1
    assert db.count_files() == 1

    with db.session_scope() as session:
        lm = session.query(LocalMedia).first()
        assert lm.file_path == expected_path
        assert len(lm.external_identifiers) == 1
        assert lm.external_identifiers[0].plugin_source == "plex"
        assert lm.external_identifiers[0].plugin_item_id == "plex_id_111"

    # 2. Re-import in Decorate Mode (identifiers_only=True) with a different media path and new identifiers
    media_remote = EchosyncMedia(file_path="spotify://track/456", file_size_bytes=1000)
    t2 = EchosyncTrack(
        raw_title="Song Title",
        artist_name="Artist Name",
        album_title="Album Title",
        media=[media_remote],
        identifiers={"plex": "plex_id_111", "spotify": "spotify_id_999"}
    )
    
    # We call bulk_import with identifiers_only=True
    # To pass identifiers_only=True to bulk_import:
    # Let's check bulk_import's signature. Does it take identifiers_only?
    # Yes: bulk_import(self, tracks: List[EchosyncTrack], delete_orphans: bool = False, identifiers_only: bool = False)
    manager.bulk_import([t2], identifiers_only=True)

    # 3. Assertions
    # Count of files must still be exactly 1 (no new media row created for spotify://track/456)
    assert db.count_tracks() == 1
    assert db.count_files() == 1

    with db.session_scope() as session:
        lm = session.query(LocalMedia).first()
        assert lm.file_path == expected_path # Still pointing to local
        
        # Should have both plex and spotify identifiers attached to it!
        sources = {eid.plugin_source: eid.plugin_item_id for eid in lm.external_identifiers}
        assert sources == {"plex": "plex_id_111", "spotify": "spotify_id_999"}




