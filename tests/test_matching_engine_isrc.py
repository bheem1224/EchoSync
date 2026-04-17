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
