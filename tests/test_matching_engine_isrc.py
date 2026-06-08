from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.echo_sync_track import EchosyncTrack
from core.matching_engine.scoring_profile import PROFILE_DOWNLOAD_SEARCH


def make_track(isrc=None, **kwargs):
    tr = EchosyncTrack(raw_title=kwargs.get('raw_title','T'), artist_name=kwargs.get('artist_name','A'), album_title=kwargs.get('album_title','B'))
    tr.duration = kwargs.get('duration', 180000)
    if isrc is not None:
        tr.isrc = isrc
    return tr


def test_isrc_validity():
    engine = WeightedMatchingEngine(PROFILE_DOWNLOAD_SEARCH)
    assert engine.is_valid_isrc('USRC17607839')
    assert not engine.is_valid_isrc('foo')
    assert not engine.is_valid_isrc('')


def test_isrc_mismatch_auto_fail():
    engine = WeightedMatchingEngine(PROFILE_DOWNLOAD_SEARCH)
    src = make_track(isrc='USRC17607839')
    cand = make_track(isrc='USRC17607840')
    res = engine.calculate_match(src, cand)
    assert res.confidence_score == 0.0
    assert 'ISRC mismatch' in res.reasoning


def test_isrc_match_instant():
    engine = WeightedMatchingEngine(PROFILE_DOWNLOAD_SEARCH)
    src = make_track(isrc='USRC17607839')
    cand = make_track(isrc='USRC17607839')
    res = engine.calculate_match(src, cand)
    assert res.confidence_score == 100.0
    assert 'ISRC match' in res.reasoning


def test_missing_isrc_ignored():
    engine = WeightedMatchingEngine(PROFILE_DOWNLOAD_SEARCH)
    src = make_track()  # no isrc
    cand = make_track()  # no isrc
    res = engine.calculate_match(src, cand)
    # should be >0 because fuzzy/default logic will score
    assert res.confidence_score > 0


def test_echosync_track_isrc_validation_valid():
    track = EchosyncTrack(raw_title="Title", artist_name="Artist", album_title="Album", isrc="US-RC1-76-07839")
    assert track.isrc == "USRC17607839"


def test_echosync_track_isrc_validation_invalid():
    track = EchosyncTrack(raw_title="Title", artist_name="Artist", album_title="Album", isrc="TamilKey.com")
    assert track.isrc is None


def test_bulk_operations_isrc_healing(tmp_path):
    from database.music_database import MusicDatabase, Track
    from database.bulk_operations import LibraryManager
    import os
    
    db_path = os.path.join(tmp_path, "library.db")
    db = MusicDatabase(database_path=db_path)
    from database.music_database import Base
    Base.metadata.create_all(db.engine)
    manager = LibraryManager(db.session_factory)
    
    # 1. Create a track with an invalid ISRC in the database
    with db.session_scope() as session:
        from database.music_database import Artist
        artist = Artist(name="Test Artist")
        session.add(artist)
        session.flush()
        track = Track(title="Test Title", artist_id=artist.id, isrc="TamilKey.com")
        session.add(track)
        
    # Verify the database has the invalid ISRC initially
    with db.session_scope() as session:
        t = session.query(Track).first()
        assert t.isrc == "TamilKey.com"
        
    # 2. Run bulk import with a track_data that will cause upsert to trigger database validation
    t_data = EchosyncTrack(raw_title="Test Title", artist_name="Test Artist", album_title="")
    manager.bulk_import([t_data])
    
    # Verify the ISRC in the database has been healed/cleared to None
    with db.session_scope() as session:
        t = session.query(Track).first()
        assert t.isrc is None

