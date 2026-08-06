from typing import Any, Dict
from core.db.echo_sync_track import EchosyncTrack, EchosyncMedia


def test_core_model_to_dict_includes_extended_metadata_fields():
    track = EchosyncTrack(
        raw_title='Serialize Me',
        artist_name='Artist',
        album_title='Album',
        duration=123456,
        isrc='USRC10000001',
        version='Live',
        is_compilation=True,
        quality_tags=['FLAC 24-bit'],
        media=[
            EchosyncMedia(
                file_path='/path/to/file.flac',
                file_format='FLAC',
                sample_rate=96000,
                bit_depth=24,
                file_size_bytes=987654321,
            )
        ],
        fingerprint='abc123',
    )

    payload = track.to_dict()

    assert payload['duration_ms'] == 123456
    assert payload['isrc'] == 'USRC10000001'
    assert payload['version'] == 'Live'
    assert payload['is_compilation'] is True
    assert payload['quality_tags'] == ['FLAC 24-bit']
    assert payload['media'][0]['sample_rate'] == 96000
    assert payload['media'][0]['bit_depth'] == 24
    assert payload['media'][0]['file_size_bytes'] == 987654321
    assert payload['fingerprint'] == 'abc123'


def test_core_model_from_dict_hydrates_extended_metadata_fields():
    payload: Dict[str, Any] = {
        'raw_title': 'Hydrate Me',
        'artist': 'Artist',
        'album_title': 'Album',
        'duration_ms': 222000,
        'isrc': 'USRC10000002',
        'version': 'Remaster',
        'is_compilation': False,
        'quality_tags': ['MP3 320kbps'],
        'media': [{
            'file_path': '/path/to/file.mp3',
            'file_format': 'MP3',
            'sample_rate': 48000,
            'bit_depth': 16,
            'file_size_bytes': 12345,
        }],
        'fingerprint': 'xyz789',
    }

    track = EchosyncTrack.from_dict(payload)

    assert track.duration == 222000
    assert track.isrc == 'USRC10000002'
    assert track.version == 'Remaster'
    assert track.is_compilation is False
    assert track.quality_tags == ['MP3 320kbps']
    assert track.media[0].sample_rate == 48000
    assert track.media[0].bit_depth == 16
    assert track.media[0].file_size_bytes == 12345
    assert track.fingerprint == 'xyz789'
