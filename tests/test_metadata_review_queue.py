from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from flask import Flask


def _fake_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    return app


def test_review_queue_includes_current_metadata(monkeypatch, mock_work_db, tmp_path):
    import web.routes.metadata_review as metadata_review
    from database.working_database import ReviewTask

    file_path = tmp_path / 'queue-track.wav'
    file_path.write_bytes(b'not-a-real-wave-file')

    with mock_work_db.session_scope() as session:
        session.add(
            ReviewTask(
                file_path=str(file_path),
                status='pending',
                detected_metadata={'title': 'Matched Title', 'artist': 'Matched Artist'},
                confidence_score=0.95,
            )
        )

    enhancer = MagicMock()
    enhancer.read_tags.return_value = {
        'title': 'Current Title',
        'artist': 'Current Artist',
        'album': 'Current Album',
    }

    monkeypatch.setattr(metadata_review, 'get_working_database', lambda: mock_work_db)
    monkeypatch.setattr(metadata_review, 'get_metadata_enhancer', lambda: enhancer)

    app = _fake_app()
    with app.test_request_context('/api/review-queue'):
        response, status_code = metadata_review.get_review_queue()

    assert status_code == 200

    payload = response.get_json()
    assert len(payload['tasks']) == 1
    assert payload['tasks'][0]['current_metadata'] == {
        'title': 'Current Title',
        'artist': 'Current Artist',
        'album': 'Current Album',
    }

    assert enhancer.read_tags.call_count == 1
    resolved_arg = enhancer.read_tags.call_args.args[0]
    assert isinstance(resolved_arg, Path)
    assert resolved_arg == file_path.resolve()


def test_metadata_enhancer_reads_riff_info_for_wav(monkeypatch, tmp_path):
    import services.metadata_enhancer as metadata_enhancer
    import core.file_handling.tagging_io as tagging_io
    from core.file_handling.jail import file_jail

    wav_path = tmp_path / 'riff-info.wav'
    wav_path.write_bytes(b'RIFF')

    class FakeAudio:
        def __init__(self):
            self.tags = {}
            self.info = SimpleNamespace(length=187.2, bitrate=1411200, sample_rate=44100, channels=2)

    class FakeChunk:
        def __init__(self, chunk_id, data=b'', name=None, children=None):
            self.id = chunk_id
            self._data = data
            self.name = name
            self._children = children or []

        def read(self):
            return self._data

        def subchunks(self):
            return list(self._children)

    class FakeRiffFile:
        def __init__(self, _fileobj):
            info_chunk = FakeChunk(
                'LIST',
                name='INFO',
                children=[
                    FakeChunk('INAM', b'Wave Title\x00'),
                    FakeChunk('IART', b'Wave Artist\x00'),
                    FakeChunk('IPRD', b'Wave Album\x00'),
                    FakeChunk('ICRD', b'2024\x00'),
                    FakeChunk('ITRK', b'07\x00'),
                    FakeChunk('ICMT', b'Wave Comment\x00'),
                ],
            )
            self.root = FakeChunk('RIFF', name='WAVE', children=[info_chunk])

    class FakeMutagen:
        @staticmethod
        def File(*args, **kwargs):
            return FakeAudio()

    # Redirect all Mutagen I/O through tagging_io module (where read_tags is implemented)
    monkeypatch.setattr(tagging_io, 'MUTAGEN_AVAILABLE', True)
    monkeypatch.setattr(tagging_io, 'mutagen', FakeMutagen)
    monkeypatch.setattr(tagging_io, 'WAVE', lambda _path: FakeAudio())
    monkeypatch.setattr(tagging_io, 'RiffFile', FakeRiffFile)
    # Allow the path jail to accept tmp_path so the security check does not block test files
    monkeypatch.setattr(file_jail, 'validate', lambda resolved: None)

    metadata = tagging_io.read_tags(wav_path)

    assert metadata['title'] == 'Wave Title'
    assert metadata['artist'] == 'Wave Artist'
    assert metadata['album'] == 'Wave Album'
    assert metadata['date'] == '2024'
    assert metadata['year'] == '2024'
    assert metadata['track_number'] == '07'
    assert metadata['comments'] == 'Wave Comment'
    assert metadata['duration_seconds'] == 187
    assert metadata['bitrate_kbps'] == 1411
    assert metadata['sample_rate_hz'] == 44100
    assert metadata['channels'] == 2
    assert metadata['file_format'] == 'wav'


def test_acoustid_lookup_returns_acoustid_id_without_mbid(monkeypatch, mock_work_db, tmp_path):
    import web.routes.metadata_review as metadata_review
    from core.enums import Capability
    from database.working_database import ReviewTask

    file_path = tmp_path / 'scan-me.flac'
    file_path.write_bytes(b'fake-audio-data')

    with mock_work_db.session_scope() as session:
        session.add(
            ReviewTask(
                file_path=str(file_path),
                status='pending',
                detected_metadata={'title': 'Known Song'},
                confidence_score=0.1,
            )
        )

    class FakeFingerprintProvider:
        def resolve_fingerprint_details(self, _fingerprint, _duration):
            return {
                'acoustid_id': '9b6f42f0-demo-acoustid',
                'mbids': [],
                'score': 0.61,
            }

        def resolve_fingerprint(self, _fingerprint, _duration):
            return []

    class FakeEnhancer:
        def _get_audio_duration(self, _file_path):
            return 180

    def fake_get_provider(capability):
        if capability == Capability.RESOLVE_FINGERPRINT:
            return FakeFingerprintProvider()
        if capability == Capability.FETCH_METADATA:
            return None
        return None

    monkeypatch.setattr(metadata_review, 'get_working_database', lambda: mock_work_db)
    monkeypatch.setattr(metadata_review, 'get_provider', fake_get_provider)
    monkeypatch.setattr(metadata_review.FingerprintGenerator, 'generate_with_duration', staticmethod(lambda _path: ('fake-fingerprint', 180)))
    monkeypatch.setattr(metadata_review, 'get_metadata_enhancer', lambda: FakeEnhancer())

    app = _fake_app()
    with app.test_request_context('/api/review-queue/1/lookup/acoustid', method='POST'):
        response, status_code = metadata_review.lookup_review_queue_item_acoustid(1)

    assert status_code == 200
    payload = response.get_json()
    detected = payload['task']['detected_metadata']
    assert detected['acoustid_id'] == '9b6f42f0-demo-acoustid'
    assert detected['title'] == 'Known Song'
