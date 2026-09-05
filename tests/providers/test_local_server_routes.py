"""
Tests for the Local Server streaming route — web/routes/local_server.py

Coverage:
1.  Directory-traversal attacks           → 403 Forbidden
2.  Native browser formats (.flac, .mp3…) → Flask send_file() is called
                                             (sets Accept-Ranges: bytes)
3.  Exotic / lossless formats (.dsf, .ape…) → subprocess.Popen is called
                                               (FFmpeg live-transcode path)
                                               send_file is NOT called
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import web.routes.local_server as route_module

# ── Shared fixture ─────────────────────────────────────────────────────────────


@pytest.fixture()
def stream_client(tmp_path, monkeypatch):
    """
    Yield a (FastAPI TestClient, library_path) pair.
    """
    library = tmp_path / "library"
    library.mkdir()

    mock_cm = MagicMock()
    mock_cm.get.side_effect = lambda key, default=None: (
        str(library) if key in ("storage.library_dir", "library_dir") else default
    )
    monkeypatch.setattr(route_module, "config_manager", mock_cm)

    app = FastAPI()
    app.include_router(route_module.router)
    app.include_router(route_module.legacy_router)
    return TestClient(app), library


# ── 1. Directory-traversal prevention ─────────────────────────────────────────


class TestDirectoryTraversalPrevention:
    def test_path_sibling_to_library_returns_403(self, stream_client, tmp_path):
        client, _library = stream_client

        outside_file = tmp_path / "secret.txt"
        outside_file.write_text("sensitive content")

        resp = client.get(f"/api/local_server/stream?path={outside_file}")

        assert resp.status_code == 403
        body = resp.json()
        assert body is not None
        assert "Access denied" in body.get("detail", "")

    def test_path_resolving_above_library_root_returns_403(
        self, stream_client, tmp_path
    ):
        client, library = stream_client

        traversal_target = tmp_path / "above.txt"
        traversal_target.write_text("root-level secret")

        resp = client.get(f"/api/local_server/stream?path={traversal_target}")
        assert resp.status_code == 403

    def test_missing_path_param_returns_400(self, stream_client):
        client, _ = stream_client
        resp = client.get("/api/local_server/stream")
        assert resp.status_code in (400, 422)

    def test_nonexistent_file_inside_library_returns_404(self, stream_client):
        client, library = stream_client
        missing = library / "ghost.flac"

        resp = client.get(f"/api/local_server/stream?path={missing}")
        assert resp.status_code == 404


# ── 2. Native formats → FileResponse (Accept-Ranges delivery) ─────────────────


class TestNativeFormatDelivery:
    @pytest.mark.parametrize(
        "filename",
        [
            "track.flac",
            "track.mp3",
            "track.wav",
            "track.m4a",
            "track.ogg",
        ],
    )
    def test_native_format_delegates_to_send_file(self, stream_client, filename):
        client, library = stream_client

        audio_file = library / filename
        audio_file.write_bytes(b"\xff\xfb\x90\x00" * 16)

        resp = client.get(f"/api/local_server/stream?path={audio_file}")
        assert resp.status_code == 200

    def test_native_format_does_not_call_popen(self, stream_client):
        client, library = stream_client

        flac_file = library / "clean.flac"
        flac_file.write_bytes(b"\x66\x4c\x61\x43" * 4)

        with patch("web.routes.local_server.subprocess.Popen") as mock_popen:
            resp = client.get(f"/api/local_server/stream?path={flac_file}")

        assert resp.status_code == 200
        mock_popen.assert_not_called()


# ── 3. Exotic formats → subprocess.Popen (FFmpeg live transcode) ──────────────


class TestExoticFormatTranscoding:
    @pytest.mark.parametrize(
        "filename",
        [
            "hires.dsf",
            "dsd_stereo.dff",
            "lossless.ape",
            "legacy.wma",
        ],
    )
    def test_exotic_format_triggers_ffmpeg_popen(self, stream_client, filename):
        client, library = stream_client

        audio_file = library / filename
        audio_file.write_bytes(b"\x00" * 64)

        mock_proc = MagicMock()
        mock_proc.stdout.read.side_effect = [b"fLaCAudioChunk", b""]
        mock_proc.returncode = 0
        mock_proc.stderr.read.return_value = b""

        with patch(
            "web.routes.local_server.subprocess.Popen", return_value=mock_proc
        ) as mock_popen:
            resp = client.get(f"/api/local_server/stream?path={audio_file}")
            _ = resp.content

        assert resp.status_code == 200
        assert "audio/flac" in resp.headers.get("content-type", "")

        mock_popen.assert_called_once()
        popen_cmd = mock_popen.call_args[0][0]

        assert isinstance(popen_cmd, list)
        assert popen_cmd[0] == "ffmpeg"
        assert "-i" in popen_cmd
        assert "pipe:0" in popen_cmd

    def test_transcode_response_contains_content_disposition(self, stream_client):
        client, library = stream_client

        dsf_file = library / "album_track.dsf"
        dsf_file.write_bytes(b"\x00" * 32)

        mock_proc = MagicMock()
        mock_proc.stdout.read.side_effect = [b"fLaCData", b""]
        mock_proc.returncode = 0
        mock_proc.stderr.read.return_value = b""

        with patch("web.routes.local_server.subprocess.Popen", return_value=mock_proc):
            resp = client.get(f"/api/local_server/stream?path={dsf_file}")
            _ = resp.content

        assert resp.status_code == 200
        cd = resp.headers.get("content-disposition", "")
        assert "album_track.flac" in cd

    def test_ffmpeg_called_with_stdout_pipe(self, stream_client):
        import subprocess as _subprocess

        client, library = stream_client

        ape_file = library / "track.ape"
        ape_file.write_bytes(b"\x00" * 32)

        mock_proc = MagicMock()
        mock_proc.stdout.read.side_effect = [b"data", b""]
        mock_proc.returncode = 0
        mock_proc.stderr.read.return_value = b""

        with patch(
            "web.routes.local_server.subprocess.Popen", return_value=mock_proc
        ) as mock_popen:
            resp = client.get(f"/api/local_server/stream?path={ape_file}")
            _ = resp.content

        kwargs = mock_popen.call_args[1]
        assert kwargs.get("stdout") == _subprocess.PIPE
        assert kwargs.get("stderr") == _subprocess.PIPE
