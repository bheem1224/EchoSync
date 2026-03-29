"""
Tests for MediaManagerService.deduce_path_mapping — services/media_manager.py

The method performs a backwards-walk through path components to find the
divergence point between a local (container) path and a remote (media-server)
path, then returns the two directory prefixes as a tuple and persists them.

Coverage:
  Case A  — paths sharing a common file/directory suffix  → (local_prefix, remote_prefix)
  Case B  — paths with no common filename segment         → None
  Edge    — empty / None inputs                           → None

Note on platform scope:
  The parametrized "Case A" tests use POSIX-style absolute paths (/app/…,
  /mnt/…).  They are skipped on Windows because Python's pathlib.Path.parts
  represents the root differently on that platform ('\\' vs '/'), which changes
  the exact string the function produces for the prefix.  These tests are
  designed to run in a POSIX environment (CI / Docker).  The "Case B" and edge
  tests do not depend on path representation and run everywhere.
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

from services.media_manager import MediaManagerService


# ── Fixture ────────────────────────────────────────────────────────────────────

@pytest.fixture()
def media_manager(monkeypatch, mock_db):
    """
    Construct a MediaManagerService in isolation:
      - Patches get_database() so no real database file is needed.
      - Patches event_bus.subscribe so test runs don't accumulate real handlers.
    """
    monkeypatch.setattr("services.media_manager.get_database", lambda: mock_db)
    monkeypatch.setattr("services.media_manager.event_bus.subscribe",
                        lambda *args, **kwargs: None)
    return MediaManagerService()


# ── Case A: successful divergence point extraction (POSIX only) ────────────────

@pytest.mark.skipif(sys.platform == "win32",
                    reason="POSIX absolute-path test; run in CI / Docker")
class TestDeducePathMappingCaseA:
    """
    The algorithm steps backward through matching path components.
    The last non-matching component pair marks the divergence; everything
    to the left of that point becomes the returned prefix pair.

    Example:
      local    = /app/music/Artist/Song.flac
      remote   = /mnt/storage/media/music/Artist/Song.flac
      common tail: Song.flac  Artist  music   (3 components match)
      divergence:  "app"  vs  "media"
      ⟹  local_prefix  = /app
          remote_prefix = /mnt/storage/media
    """

    @pytest.mark.parametrize("local_path, provider_path, expected_local, expected_remote", [
        (
            # Standard Docker-volume layout: /app/… mapped to /mnt/storage/…
            "/app/music/Artist/Song.flac",
            "/mnt/storage/media/music/Artist/Song.flac",
            "/app",
            "/mnt/storage/media",
        ),
        (
            # NFS share: /data/ vs /shares/nfs/library/
            "/data/music/Rock/Band/track.mp3",
            "/shares/nfs/library/music/Rock/Band/track.mp3",
            "/data",
            "/shares/nfs/library",
        ),
        (
            # Single-level divergence: only the root segment differs
            "/local/Song.flac",
            "/remote/Song.flac",
            "/local",
            "/remote",
        ),
    ])
    def test_returns_divergence_prefixes(
        self,
        media_manager,
        local_path,
        provider_path,
        expected_local,
        expected_remote,
    ):
        """
        deduce_path_mapping must return the pair of prefixes at the exact
        point where the two path trees diverge.

        The DB persistence side-effect is suppressed by returning None from
        get_active_media_server() so the test stays pure and deterministic.
        """
        with patch("services.media_manager.config_manager") as mock_cm:
            mock_cm.get_active_media_server.return_value = None   # skip DB write

            result = media_manager.deduce_path_mapping(local_path, provider_path)

        assert result is not None, (
            f"Expected a mapping tuple, got None for "
            f"local='{local_path}' provider='{provider_path}'"
        )

        local_prefix, remote_prefix = result
        assert local_prefix == expected_local
        assert remote_prefix == expected_remote

    def test_result_is_a_two_tuple(self, media_manager):
        """Return value must be a two-element tuple, not a list or dict."""
        with patch("services.media_manager.config_manager") as mock_cm:
            mock_cm.get_active_media_server.return_value = None
            result = media_manager.deduce_path_mapping(
                "/app/music/track.flac",
                "/mnt/data/music/track.flac",
            )

        assert isinstance(result, tuple)
        assert len(result) == 2


# ── Case B: no common filename → None (platform-neutral) ──────────────────────

class TestDeducePathMappingCaseB:
    """
    When the last path component (filename) differs between the two paths,
    there is no meaningful divergence point and the method must return None.
    """

    def test_completely_different_filenames_returns_none(self, media_manager):
        """
        Paths whose filenames do not match cannot produce a valid mapping.
        The algorithm detects this on the very first backwards-comparison step
        and returns None immediately via the 'no common suffix' guard.
        """
        with patch("services.media_manager.config_manager") as mock_cm:
            mock_cm.get_active_media_server.return_value = None

            result = media_manager.deduce_path_mapping(
                "/data/files/song.flac",
                "/totally/different/path/audio.mp3",
            )

        assert result is None

    def test_same_directories_different_filenames_returns_none(self, media_manager):
        """
        Even if the directory structure is identical, a different filename
        means the algorithm cannot safely infer a mapping.
        """
        with patch("services.media_manager.config_manager") as mock_cm:
            mock_cm.get_active_media_server.return_value = None

            result = media_manager.deduce_path_mapping(
                "/music/Artist/Album/track_01.flac",
                "/music/Artist/Album/track_02.flac",
            )

        # 'track_01.flac' != 'track_02.flac' → no overlap found
        assert result is None


# ── Edge cases: empty / None inputs ───────────────────────────────────────────

class TestDeducePathMappingEdgeCases:

    @pytest.mark.parametrize("local, remote", [
        ("", "/mnt/storage/media/track.flac"),
        ("/app/music/track.flac", ""),
        ("", ""),
    ])
    def test_empty_inputs_return_none(self, media_manager, local, remote):
        """The early-return guard must catch any empty path argument."""
        with patch("services.media_manager.config_manager") as mock_cm:
            mock_cm.get_active_media_server.return_value = None

            assert media_manager.deduce_path_mapping(local, remote) is None

    @pytest.mark.skipif(sys.platform == "win32",
                        reason="POSIX absolute-path test; run in CI / Docker")
    def test_successful_mapping_is_persisted_to_config_db(self, media_manager):
        """
        When a valid mapping is deduced AND an active media server is configured,
        the result must be written to the config database exactly once via
        set_service_config().
        """
        mock_config_db = MagicMock()
        mock_config_db.get_or_create_service_id.return_value = 42
        mock_config_db.get_service_config.return_value = None   # no existing mappings

        with patch("services.media_manager.config_manager") as mock_cm, \
             patch("database.config_database.get_config_database", return_value=mock_config_db):

            mock_cm.get_active_media_server.return_value = "plex"

            result = media_manager.deduce_path_mapping(
                "/app/music/Artist/Song.flac",
                "/mnt/storage/media/music/Artist/Song.flac",
            )

        assert result is not None
        # set_service_config must be called with the 'path_mappings' key
        mock_config_db.set_service_config.assert_called_once()
        call_args = mock_config_db.set_service_config.call_args
        assert call_args[0][1] == "path_mappings"    # second positional arg is the key

    @pytest.mark.skipif(sys.platform == "win32",
                        reason="POSIX absolute-path test; run in CI / Docker")
    def test_duplicate_mapping_is_not_added_twice(self, media_manager):
        """
        If the deduced mapping already exists in the DB, set_service_config
        must NOT be called again (idempotent persistence).
        """
        import json

        local_prefix = "/app"
        remote_prefix = "/mnt/storage/media"
        existing = [{"local": local_prefix, "remote": remote_prefix}]

        mock_config_db = MagicMock()
        mock_config_db.get_or_create_service_id.return_value = 42
        mock_config_db.get_service_config.return_value = json.dumps(existing)

        with patch("services.media_manager.config_manager") as mock_cm, \
             patch("database.config_database.get_config_database", return_value=mock_config_db):

            mock_cm.get_active_media_server.return_value = "plex"

            media_manager.deduce_path_mapping(
                "/app/music/Artist/Song.flac",
                "/mnt/storage/media/music/Artist/Song.flac",
            )

        mock_config_db.set_service_config.assert_not_called()
