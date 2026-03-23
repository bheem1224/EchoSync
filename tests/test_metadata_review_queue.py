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

    monkeypatch.setattr(metadata_enhancer, 'MUTAGEN_AVAILABLE', True)
    monkeypatch.setattr(metadata_enhancer.mutagen, 'File', lambda *args, **kwargs: FakeAudio())
    monkeypatch.setattr(metadata_enhancer, 'WAVE', lambda _path: FakeAudio())
    monkeypatch.setattr(metadata_enhancer, 'RiffFile', FakeRiffFile)

    metadata = metadata_enhancer.MetadataEnhancerService().read_tags(wav_path)

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
