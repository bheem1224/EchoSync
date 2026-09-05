"""
Unit tests for directory pruning utilities (core/utils/file_utils.py).
"""

from pathlib import Path

from core.utils.file_utils import (
    prune_empty_directories_tree,
    prune_empty_parent_directories,
)


def test_prune_empty_directory_tree(tmp_path: Path):
    """Verifies ascending deletion deletes empty artist/album hierarchy and halts at designated root."""
    root_dir = tmp_path / "downloads"
    root_dir.mkdir(parents=True)

    artist_dir = root_dir / "Linkin Park"
    album_dir = artist_dir / "Hybrid Theory"
    album_dir.mkdir(parents=True)

    test_file = album_dir / "track.mp3"
    # Simulate track was relocated/deleted
    test_file_path = str(test_file)

    pruned = prune_empty_parent_directories(test_file_path, stop_at_roots={root_dir})

    # album_dir and artist_dir should be pruned (2 directories)
    assert pruned == 2
    assert not album_dir.exists()
    assert not artist_dir.exists()
    # root_dir must remain intact
    assert root_dir.exists()


def test_prune_directory_with_junk_artifacts(tmp_path: Path):
    """Verifies junk artifacts (.DS_Store, Thumbs.db, etc.) are unlinked and the directory is pruned."""
    root_dir = tmp_path / "library"
    root_dir.mkdir(parents=True)

    album_dir = root_dir / "Artist" / "Album"
    album_dir.mkdir(parents=True)

    # Populate junk artifacts
    (album_dir / ".DS_Store").write_bytes(b"dummy ds_store")
    (album_dir / "Thumbs.db").write_bytes(b"dummy thumbs")
    (album_dir / "desktop.ini").write_bytes(b"dummy desktop.ini")

    pruned = prune_empty_parent_directories(album_dir, stop_at_roots={root_dir})

    assert pruned == 2
    assert not album_dir.exists()
    assert not (root_dir / "Artist").exists()
    assert root_dir.exists()


def test_prune_halts_on_populated_directory(tmp_path: Path):
    """Verifies directories with valid audio files or other content remain untouched."""
    root_dir = tmp_path / "downloads"
    root_dir.mkdir(parents=True)

    artist_dir = root_dir / "The Weeknd"
    album_dir = artist_dir / "After Hours"
    album_dir.mkdir(parents=True)

    # One file is moved, but another remains
    moved_file = album_dir / "01 - Blinding Lights.flac"
    remaining_file = album_dir / "02 - In Your Eyes.flac"
    remaining_file.write_bytes(b"audio data")

    pruned = prune_empty_parent_directories(moved_file, stop_at_roots={root_dir})

    # Nothing should be pruned since album_dir still contains remaining_file
    assert pruned == 0
    assert album_dir.exists()
    assert artist_dir.exists()
    assert remaining_file.exists()


def test_prune_never_deletes_root_boundary(tmp_path: Path):
    """Verifies /data/downloads and /data/library roots are never deleted even when empty."""
    library_root = tmp_path / "data" / "library"
    downloads_root = tmp_path / "data" / "downloads"
    library_root.mkdir(parents=True)
    downloads_root.mkdir(parents=True)

    # Calling directly on the root directory with itself in stop_at_roots
    pruned_lib = prune_empty_parent_directories(
        library_root, stop_at_roots={library_root, downloads_root}
    )
    pruned_dl = prune_empty_parent_directories(
        downloads_root, stop_at_roots={library_root, downloads_root}
    )

    assert pruned_lib == 0
    assert pruned_dl == 0
    assert library_root.exists()
    assert downloads_root.exists()


def test_prune_empty_directories_tree(tmp_path: Path):
    """Verifies bottom-up traversal cleans all nested empty/junk folders across the entire tree."""
    lib_root = tmp_path / "music_library"
    lib_root.mkdir(parents=True)

    # Folder 1: Empty nested folders
    empty_artist = lib_root / "EmptyArtist" / "EmptyAlbum"
    empty_artist.mkdir(parents=True)

    # Folder 2: Folder with only .DS_Store
    ds_artist = lib_root / "DSArtist" / "DSAlbum"
    ds_artist.mkdir(parents=True)
    (ds_artist / ".DS_Store").write_bytes(b"ds store")

    # Folder 3: Populated folder
    pop_artist = lib_root / "PopArtist" / "PopAlbum"
    pop_artist.mkdir(parents=True)
    (pop_artist / "song.flac").write_bytes(b"music")

    pruned = prune_empty_directories_tree(lib_root)

    # Should prune EmptyAlbum, EmptyArtist, DSAlbum, DSArtist (4 total)
    assert pruned == 4
    assert not (lib_root / "EmptyArtist").exists()
    assert not (lib_root / "DSArtist").exists()
    assert (lib_root / "PopArtist" / "PopAlbum" / "song.flac").exists()
    assert lib_root.exists()
