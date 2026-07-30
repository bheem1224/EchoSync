import pytest
import os
from pathlib import Path
from core.io_gatekeeper import Gatekeeper, SecurityViolationError


def test_gatekeeper_uri_resolution(tmp_path):
    lib_dir = tmp_path / "library"
    lib_dir.mkdir()
    (lib_dir / "test.flac").touch()

    gatekeeper = Gatekeeper(allowed_roots=[tmp_path])
    resolved = gatekeeper.resolve_uri(f"echosync://library/test.flac")
    assert resolved.name == "test.flac"


def test_gatekeeper_path_traversal_blocked(tmp_path):
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()

    secret_dir = tmp_path / "secret"
    secret_dir.mkdir()
    secret_file = secret_dir / "passwords.txt"
    secret_file.touch()

    gatekeeper = Gatekeeper(allowed_roots=[allowed_dir])

    # Traversal attempt
    traversal_path = allowed_dir / "../secret/passwords.txt"

    with pytest.raises(SecurityViolationError) as excinfo:
        gatekeeper.validate_path(traversal_path)

    assert "traverses outside authorized storage roots" in str(excinfo.value)


def test_gatekeeper_authorize_and_execute(tmp_path):
    target_dir = tmp_path / "media"
    target_dir.mkdir()
    (target_dir / "track1.mp3").touch()
    (target_dir / "track2.flac").touch()

    gatekeeper = Gatekeeper(allowed_roots=[tmp_path])

    received_batches = []
    def telemetry_callback(batch):
        received_batches.extend(batch)

    manifest = {
        "operation": "batch_process",
        "target_uri": str(target_dir),
        "callback": telemetry_callback,
        "batch_interval_ms": 10,
    }

    result = gatekeeper.authorize_and_execute(manifest)
    assert result["success"] is True
    assert len(result["validated_paths"]) == 1
    assert result["validated_paths"][0] == target_dir.as_posix()
