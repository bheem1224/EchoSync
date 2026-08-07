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
