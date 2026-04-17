from core.matching_engine.echo_sync_track import EchosyncTrack


def test_matching_engine_from_dict_hydrates_duration_ms_and_isrc_from_identifiers():
    payload = {
        'raw_title': 'Track Name',
        'artist_name': 'Artist Name',
        'album_title': 'Album Name',
        'duration_ms': 201000,
        'identifiers': {
            'spotify': 'spotify-track-id',
            'isrc': 'USRC10000003',
        },
    }

    track = EchosyncTrack.from_dict(payload)

    assert track.duration == 201000
    assert track.isrc == 'USRC10000003'


def test_matching_engine_to_dict_includes_version_and_is_compilation():
    track = EchosyncTrack(
        raw_title='Track Name',
        artist_name='Artist Name',
        album_title='Album Name',
        version='Extended Mix',
        is_compilation=True,
    )

    payload = track.to_dict()

    assert payload['version'] == 'Extended Mix'
    assert payload['is_compilation'] is True
