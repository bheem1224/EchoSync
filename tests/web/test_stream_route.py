from unittest.mock import patch

from fastapi.testclient import TestClient

from web.api_app import create_app


def test_stream_route_by_int_and_base62_sync_id(tmp_path):
    # Create fake audio file
    fake_audio = tmp_path / "song.flac"
    fake_audio.write_bytes(b"fLaC" + b"\x00" * 1024)

    app = create_app()
    client = TestClient(app)

    with patch("web.routes.stream.media_manager.get_track_stream") as mock_get_stream:
        # 1. Test existing int track ID
        mock_get_stream.return_value = str(fake_audio)
        resp = client.get("/api/v1/stream/123")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("audio/flac")
        assert resp.content == fake_audio.read_bytes()

        # 2. Test Base62 / NanoID string ID
        mock_get_stream.return_value = str(fake_audio)
        resp2 = client.get("/api/v1/stream/wDtjGw4g")
        assert resp2.status_code == 200
        assert resp2.headers["content-type"].startswith("audio/flac")

        # 3. Test root alias /stream/{track_id}
        resp3 = client.get("/stream/wDtjGw4g")
        assert resp3.status_code == 200

        # 4. Test 404 for missing track
        mock_get_stream.return_value = None
        resp4 = client.get("/api/v1/stream/999999")
        assert resp4.status_code == 404
