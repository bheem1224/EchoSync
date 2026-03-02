import os
import tempfile
from core.matching_engine.soul_sync_track import SoulSyncTrack
from database.music_database import MusicDatabase
from database.bulk_operations import LibraryManager


def _make_manager(tmpdir):
    db_path = os.path.join(tmpdir, "library.db")
    db = MusicDatabase(database_path=db_path)
    db.create_all()
    return db, LibraryManager(db.session_factory)


def test_import_with_duplicate_metadata_creates_separate_tracks(tmp_path):
    """Tracks that share metadata but have different provider ids should not merge."""
    db, manager = _make_manager(str(tmp_path))

    t1 = SoulSyncTrack(raw_title="Foo", artist_name="Artist", album_title="Album", identifiers={"plex": "100"})
    t2 = SoulSyncTrack(raw_title="Foo", artist_name="Artist", album_title="Album", identifiers={"plex": "200"})

    count = manager.bulk_import([t1, t2])
    assert count == 2, "Both tracks should be processed"
    assert db.count_tracks() == 2

    # verify each track has correct identifier
    with db.session_scope() as session:
        from database.music_database import Track, ExternalIdentifier
        tracks = session.query(Track).all()
        ids = []
        for tr in tracks:
            for ei in tr.external_identifiers:
                if ei.provider_source == 'plex':
                    ids.append(ei.provider_item_id)
        assert set(ids) == {"100", "200"}


def test_accented_artist_names_are_deduped(tmp_path):
    """Artist names differing only in accents should be merged on import."""
    db, manager = _make_manager(str(tmp_path))

    # Insert two artists manually with accent variants
    with db.session_scope() as session:
        from database.music_database import Artist
        a1 = Artist(name="Elley Duhé")
        a2 = Artist(name="Elley Duhe")
        session.add_all([a1, a2])
        session.flush()
        assert session.query(Artist).count() == 2

    # Import a track for the normalized name
    t = SoulSyncTrack(raw_title="Song", artist_name="Elley Duhé", album_title="Album",
                      identifiers={"plex": "300"})
    manager.bulk_import([t])

    # After import, the two artists should be merged into 1
    assert db.count_artists() == 1
    # artist name should be the first encountered
    with db.session_scope() as session:
        artist = session.query(Artist).first()
        assert normalize_text(artist.name) == normalize_text("Elley Duhé")


def test_cache_prepopulation_avoids_duplicates(tmp_path):
    """Re-importing existing artists should not create extra rows."""
    db, manager = _make_manager(str(tmp_path))

    t = SoulSyncTrack(raw_title="Song1", artist_name="Béla", album_title="A1", identifiers={"plex": "400"})
    manager.bulk_import([t])
    assert db.count_artists() == 1
    # import again with same artist spelled differently but normalizes same
    t2 = SoulSyncTrack(raw_title="Song2", artist_name="Bela", album_title="A2", identifiers={"plex": "401"})
    manager.bulk_import([t2])
    assert db.count_artists() == 1

# reuse normalize_text from text_utils
from core.matching_engine.text_utils import normalize_text
