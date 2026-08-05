import pytest
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

    def mock_get(key, default=None):
        if 'library_dir' in key or 'download_dir' in key:
            return str(tmp_path)
        return default
    monkeypatch.setattr(metadata_review.config_manager, 'get', mock_get)
    monkeypatch.setattr(metadata_review, 'get_working_database', lambda: mock_work_db)
    monkeypatch.setattr(metadata_review, 'get_metadata_enhancer', lambda: enhancer)

    app = _fake_app()
    with app.test_request_context('/api/review-queue'):
        response, status_code = metadata_review.get_review_queue()

    assert status_code == 200

    payload = response.get_json()
    assert len(payload['tasks']) == 1
    pass

    pass
    pass
    pass
    pass




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

    def mock_get(key, default=None):
        if 'library_dir' in key or 'download_dir' in key:
            return str(tmp_path)
        return default
    monkeypatch.setattr(metadata_review.config_manager, 'get', mock_get)
    monkeypatch.setattr(metadata_review, 'get_working_database', lambda: mock_work_db)
    monkeypatch.setattr(metadata_review, 'get_plugin_by_capability', fake_get_provider)
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
