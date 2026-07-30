import pytest
import os
from pathlib import Path
import echosync_core
from core.io_gatekeeper import Gatekeeper, SecurityViolationError


def test_native_file_operations(tmp_path):
    src_dir = tmp_path / "src"
    dst_dir = tmp_path / "dst"
    src_dir.mkdir()
    dst_dir.mkdir()

    file_a = src_dir / "file_a.txt"
    file_a.write_text("hello audiophile world")

    file_b = dst_dir / "file_b.txt"

    # Test copy
    bytes_copied = echosync_core.copy_file(str(file_a), str(file_b))
    assert bytes_copied > 0
    assert file_b.exists()

    # Test move
    file_c = dst_dir / "file_c.txt"
    echosync_core.safe_move_file(str(file_a), str(file_c))
    assert not file_a.exists()
    assert file_c.exists()

    # Test delete
    echosync_core.delete_file(str(file_c))
    assert not file_c.exists()


def test_gatekeeper_phase3_manifests(tmp_path):
    lib_dir = tmp_path / "library"
    dl_dir = tmp_path / "downloads"
    lib_dir.mkdir()
    dl_dir.mkdir()

    src_file = dl_dir / "incoming.flac"
    src_file.write_bytes(b"dummy flac bytes")

    gatekeeper = Gatekeeper(allowed_roots=[tmp_path])

    # 1. safe_move via Gatekeeper
    move_manifest = {
        "operation": "safe_move",
        "target_uri": str(src_file),
        "destination_uri": str(lib_dir / "final.flac"),
    }
    res = gatekeeper.authorize_and_execute(move_manifest)
    assert res["success"] is True
    assert not src_file.exists()
    assert (lib_dir / "final.flac").exists()

    # 2. copy_file via Gatekeeper
    copy_manifest = {
        "operation": "copy_file",
        "target_uri": str(lib_dir / "final.flac"),
        "destination_uri": str(dl_dir / "copied.flac"),
    }
    res_copy = gatekeeper.authorize_and_execute(copy_manifest)
    assert res_copy["success"] is True
    assert (dl_dir / "copied.flac").exists()

    # 3. delete_file via Gatekeeper
    del_manifest = {
        "operation": "delete_file",
        "target_uri": str(dl_dir / "copied.flac"),
    }
    res_del = gatekeeper.authorize_and_execute(del_manifest)
    assert res_del["success"] is True
    assert not (dl_dir / "copied.flac").exists()
