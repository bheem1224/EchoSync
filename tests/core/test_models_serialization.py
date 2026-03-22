from typing import Any, Dict

from core.models import SoulSyncTrack


def test_core_model_to_dict_includes_extended_metadata_fields():
    track = SoulSyncTrack(
        title='Serialize Me',
        artists=['Artist'],
        album='Album',
        duration_ms=123456,
        isrc='USRC10000001',
        total_discs=2,
        track_total=14,
        version='Live',
        is_compilation=True,
        quality_tags=['FLAC 24-bit'],
        sample_rate=96000,
        bit_depth=24,
        file_size=987654321,
        featured_artists=['Guest Artist'],
        fingerprint='abc123',
        fingerprint_confidence=0.99,
    )

    payload = track.to_dict()

    assert payload['duration_ms'] == 123456
    assert payload['isrc'] == 'USRC10000001'
    assert payload['total_discs'] == 2
    assert payload['track_total'] == 14
    assert payload['version'] == 'Live'
    assert payload['is_compilation'] is True
    assert payload['quality_tags'] == ['FLAC 24-bit']
    assert payload['sample_rate'] == 96000
    assert payload['bit_depth'] == 24
    assert payload['file_size'] == 987654321
    assert payload['featured_artists'] == ['Guest Artist']
    assert payload['fingerprint'] == 'abc123'
    assert payload['fingerprint_confidence'] == 0.99


def test_core_model_from_dict_hydrates_extended_metadata_fields():
    payload: Dict[str, Any] = {
        'title': 'Hydrate Me',
        'artists': ['Artist'],
        'album': 'Album',
        'duration_ms': 222000,
        'isrc': 'USRC10000002',
        'total_discs': 3,
        'track_total': 20,
        'version': 'Remaster',
        'is_compilation': False,
        'quality_tags': ['MP3 320kbps'],
        'sample_rate': 48000,
        'bit_depth': 16,
        'file_size': 12345,
        'featured_artists': ['Another Artist'],
        'fingerprint': 'xyz789',
        'fingerprint_confidence': 0.87,
    }

    track = SoulSyncTrack.from_dict(payload)

    assert track.duration_ms == 222000
    assert track.isrc == 'USRC10000002'
    assert track.total_discs == 3
    assert track.track_total == 20
    assert track.version == 'Remaster'
    assert track.is_compilation is False
    assert track.quality_tags == ['MP3 320kbps']
    assert track.sample_rate == 48000
    assert track.bit_depth == 16
    assert track.file_size == 12345
    assert track.featured_artists == ['Another Artist']
    assert track.fingerprint == 'xyz789'
    assert track.fingerprint_confidence == 0.87
