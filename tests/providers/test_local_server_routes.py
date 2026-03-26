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

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from flask import Flask, Response

import web.routes.local_server as route_module


# ── Shared fixture ─────────────────────────────────────────────────────────────

@pytest.fixture()
def stream_client(tmp_path, monkeypatch):
    """
    Yield a (Flask test client, library_path) pair.

    The temp library directory is registered as the return value of
    config_manager.get_library_dir() so every test gets an isolated sandbox
    that maps exactly to the route's security boundary.
    """
    library = tmp_path / "library"
    library.mkdir()

    mock_cm = MagicMock()
    mock_cm.get_library_dir.return_value = library
    monkeypatch.setattr(route_module, "config_manager", mock_cm)

    app = Flask(__name__)
    app.register_blueprint(route_module.bp)
    return app.test_client(), library


# ── 1. Directory-traversal prevention ─────────────────────────────────────────

class TestDirectoryTraversalPrevention:

    def test_path_sibling_to_library_returns_403(self, stream_client, tmp_path):
        """
        A file that exists on disk but lives OUTSIDE the library root must be
        rejected with 403.  The route resolves the full path before the check,
        so no ../ tricks can work.
        """
        client, _library = stream_client

        outside_file = tmp_path / "secret.txt"
        outside_file.write_text("sensitive content")

        resp = client.get(f"/api/local_server/stream?path={outside_file}")

        assert resp.status_code == 403
        body = resp.get_json()
        assert body is not None
        assert "Access denied" in body["error"]

    def test_path_resolving_above_library_root_returns_403(self, stream_client, tmp_path):
        """
        A direct absolute path to a file above the library root (simulating
        what ../../etc/passwd resolves to) must be rejected.
        """
        client, library = stream_client

        # File that exists but is the PARENT directory of the library root
        traversal_target = tmp_path / "above.txt"
        traversal_target.write_text("root-level secret")

        # The route resolves the query-param path with Path().resolve().
        # Passing the absolute resolved path directly is equivalent to a
        # successful ../ traversal from inside the library.
        resp = client.get(f"/api/local_server/stream?path={traversal_target}")

        assert resp.status_code == 403

    def test_missing_path_param_returns_400(self, stream_client):
        """A request with no `path` query parameter must return 400."""
        client, _ = stream_client
        resp = client.get("/api/local_server/stream")
        assert resp.status_code == 400

    def test_nonexistent_file_inside_library_returns_404(self, stream_client):
        """A path inside the library that doesn't exist on disk must return 404."""
        client, library = stream_client
        missing = library / "ghost.flac"   # never created on disk

        resp = client.get(f"/api/local_server/stream?path={missing}")
        assert resp.status_code == 404


# ── 2. Native formats → send_file (Accept-Ranges delivery) ────────────────────

class TestNativeFormatDelivery:

    @pytest.mark.parametrize("filename", [
        "track.flac",
        "track.mp3",
        "track.wav",
        "track.m4a",
        "track.ogg",
    ])
    def test_native_format_delegates_to_send_file(self, stream_client, filename):
        """
        For every native browser-playable format the route must call
        Flask's send_file() with conditional=True (which sets the
        Accept-Ranges: bytes header and enables browser range requests).
        """
        client, library = stream_client

        audio_file = library / filename
        audio_file.write_bytes(b"\xff\xfb\x90\x00" * 16)   # plausible audio bytes

        # send_file must return a real Response so the test client can
        # handle the return value from the view function.
        sentinel = Response("ok", status=200, mimetype="audio/mpeg")

        with patch("web.routes.local_server.send_file", return_value=sentinel) as mock_sf:
            resp = client.get(f"/api/local_server/stream?path={audio_file}")

        assert resp.status_code == 200

        mock_sf.assert_called_once()

        # First positional argument must be the resolved file path.
        called_with_path = mock_sf.call_args[0][0]
        assert Path(called_with_path).resolve() == audio_file.resolve()

        # conditional=True is the Accept-Ranges prerequisite.
        assert mock_sf.call_args.kwargs.get("conditional") is True

    def test_native_format_does_not_call_popen(self, stream_client):
        """send_file path must never touch subprocess.Popen."""
        client, library = stream_client

        flac_file = library / "clean.flac"
        flac_file.write_bytes(b"\x66\x4c\x61\x43" * 4)    # fLaC magic bytes

        sentinel = Response("ok", status=200, mimetype="audio/flac")

        with patch("web.routes.local_server.send_file", return_value=sentinel), \
             patch("web.routes.local_server.subprocess.Popen") as mock_popen:
            client.get(f"/api/local_server/stream?path={flac_file}")

        mock_popen.assert_not_called()


# ── 3. Exotic formats → subprocess.Popen (FFmpeg live transcode) ──────────────

class TestExoticFormatTranscoding:

    @pytest.mark.parametrize("filename", [
        "hires.dsf",
        "dsd_stereo.dff",
        "lossless.ape",
        "legacy.wma",
    ])
    def test_exotic_format_triggers_ffmpeg_popen(self, stream_client, filename):
        """
        Exotic formats that browsers cannot decode (DSF, DFF, APE, WMA) must
        call subprocess.Popen to launch FFmpeg and stream a FLAC transcode.
        send_file must NOT be called (the frontend player stays lightweight).
        """
        client, library = stream_client

        audio_file = library / filename
        audio_file.write_bytes(b"\x00" * 64)    # opaque exotic-format bytes

        mock_proc = MagicMock()
        # Simulate FFmpeg yielding one data chunk then signalling EOF.
        mock_proc.stdout.read.side_effect = [b"fLaCAudioChunk", b""]
        mock_proc.returncode = 0
        mock_proc.stderr.read.return_value = b""

        with patch("web.routes.local_server.subprocess.Popen",
                   return_value=mock_proc) as mock_popen, \
             patch("web.routes.local_server.send_file") as mock_sf:

            resp = client.get(f"/api/local_server/stream?path={audio_file}")
            # Consuming resp.data iterates the stream_with_context generator,
            # which is when subprocess.Popen is actually called inside generate().
            _ = resp.data

        # ── Response assertions ──────────────────────────────────────────────
        assert resp.status_code == 200
        assert "audio/flac" in resp.content_type

        # ── FFmpeg invocation assertions ─────────────────────────────────────
        mock_popen.assert_called_once()

        popen_cmd = mock_popen.call_args[0][0]

        # Must be a list — never shell=True — to prevent command injection via
        # special characters in filenames (OWASP: Command Injection).
        assert isinstance(popen_cmd, list), (
            "subprocess.Popen must be called with a list argument, not a shell string"
        )
        assert popen_cmd[0] == "ffmpeg"

        # The escaped file path must appear somewhere in the command.
        assert str(audio_file.resolve()) in popen_cmd

        # ── No double-serving ────────────────────────────────────────────────
        mock_sf.assert_not_called()

    def test_transcode_response_contains_content_disposition(self, stream_client):
        """
        The transcoded FLAC stream must carry a Content-Disposition header so
        the browser knows the suggested filename even without Content-Length.
        """
        client, library = stream_client

        dsf_file = library / "album_track.dsf"
        dsf_file.write_bytes(b"\x00" * 32)

        mock_proc = MagicMock()
        mock_proc.stdout.read.side_effect = [b"fLaCData", b""]
        mock_proc.returncode = 0
        mock_proc.stderr.read.return_value = b""

        with patch("web.routes.local_server.subprocess.Popen", return_value=mock_proc):
            resp = client.get(f"/api/local_server/stream?path={dsf_file}")
            _ = resp.data

        assert resp.status_code == 200
        cd = resp.headers.get("Content-Disposition", "")
        # Must include the stem of the original file (with .flac substituted).
        assert "album_track.flac" in cd

    def test_ffmpeg_called_with_stdout_pipe(self, stream_client):
        """
        FFmpeg must be invoked with stdout=PIPE so its output can be streamed
        directly to the client without writing a temporary file to disk.
        """
        import subprocess as _subprocess

        client, library = stream_client

        ape_file = library / "track.ape"
        ape_file.write_bytes(b"\x00" * 32)

        mock_proc = MagicMock()
        mock_proc.stdout.read.side_effect = [b"data", b""]
        mock_proc.returncode = 0
        mock_proc.stderr.read.return_value = b""

        with patch("web.routes.local_server.subprocess.Popen",
                   return_value=mock_proc) as mock_popen:
            resp = client.get(f"/api/local_server/stream?path={ape_file}")
            _ = resp.data

        kwargs = mock_popen.call_args[1]
        assert kwargs.get("stdout") == _subprocess.PIPE
        assert kwargs.get("stderr") == _subprocess.PIPE
