import pytest
from pathlib import Path
from core.path_security import resolve_safe_path, validate_zip_entry, PathTraversalError

def test_resolve_safe_path_valid(tmp_path):
    base_dir = tmp_path / "sandbox"
    base_dir.mkdir()
    
    # Valid relative subpath
    target = resolve_safe_path(base_dir, "manifest.json")
    assert target == base_dir.resolve() / "manifest.json"
    
    # Valid nested subpath
    target_nested = resolve_safe_path(base_dir, "sub/dir/config.json")
    assert target_nested == base_dir.resolve() / "sub" / "dir" / "config.json"

def test_resolve_safe_path_traversal_blocked(tmp_path):
    base_dir = tmp_path / "sandbox"
    base_dir.mkdir()
    
    # Escape attempt via ../
    with pytest.raises(PathTraversalError):
        resolve_safe_path(base_dir, "../outside.txt")
        
    # Deep escape attempt
    with pytest.raises(PathTraversalError):
        resolve_safe_path(base_dir, "sub/../../outside.txt")

def test_validate_zip_entry_zip_slip_blocked(tmp_path):
    base_dir = tmp_path / "sandbox"
    base_dir.mkdir()
    
    # Valid zip entry
    valid_path = validate_zip_entry(base_dir, "assets/logo.png")
    assert valid_path == base_dir.resolve() / "assets" / "logo.png"
    
    # Zip Slip attack entry
    with pytest.raises(PathTraversalError):
        validate_zip_entry(base_dir, "../../evil.sh")

def test_resolve_safe_path_symlink_escape(tmp_path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    outside_file = tmp_path / "outside_secret.txt"
    outside_file.write_text("secret")

    symlink_path = sandbox / "symlink_to_outside.txt"
    try:
        symlink_path.symlink_to(outside_file)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not supported in this environment")

    # Accessing the symlink inside the sandbox should resolve to outside_file and fail containment
    with pytest.raises(PathTraversalError):
        resolve_safe_path(sandbox, "symlink_to_outside.txt")

def test_resolve_safe_path_multi_root(tmp_path):
    root1 = tmp_path / "library"
    root2 = tmp_path / "downloads"
    root1.mkdir()
    root2.mkdir()

    file1 = root1 / "track1.flac"
    file1.touch()
    file2 = root2 / "track2.flac"
    file2.touch()

    # Both roots should be allowed
    assert resolve_safe_path([root1, root2], str(file1)) == file1.resolve()
    assert resolve_safe_path([root1, root2], str(file2)) == file2.resolve()

    # Outside file should be blocked
    outside = tmp_path / "secret.flac"
    outside.touch()
    with pytest.raises(PathTraversalError):
        resolve_safe_path([root1, root2], str(outside))


