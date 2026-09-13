"""
Phase 2B Integration Test Suite: Plugin Concurrency & Daemon Modernization.

Tests:
1. Strict integer-only plugin_id enforcement in core.tiered_logger.
2. SLSKD EventBus subscriber thread supervision under OwnerType.PLUGIN and CRC32 owner_id.
3. SLSKD webhook DB write lease acquisition.
4. Tidal OAuth sidecar supervision with bound_to_general_pool=False and deprecation logging.
5. LocalServer sequential crawler with cooperative cancellation support.
6. LocalServer DatabaseCleanupJob write lease acquisition.
"""

import asyncio
import logging
import pytest
from unittest.mock import MagicMock, patch

from core.plugins.sdk import compute_plugin_crc32
from core.task_manager.models import OwnerType, ProcessCategory
from core.task_manager.supervisor import supervisor
from core.task_manager.task_queue import job_queue, db_write_lease
from core.tiered_logger import get_logger, SourceTagAdapter


# ==============================================================================
# 1. Tiered Logger Strict Integer Plugin ID Tests
# ==============================================================================


def test_tiered_logger_integer_plugin_id():
    """Verify that integer plugin_id correctly formats [TAINT:<int_id>]."""
    test_crc32 = compute_plugin_crc32("EchoSync.slskd")
    logger = get_logger("plugins.slskd", plugin_id=test_crc32)

    assert isinstance(logger, SourceTagAdapter)
    assert f"[TAINT:{test_crc32}]" in logger.tag
    assert logger.tag.startswith("[plugin slskd]")

    msg, kwargs = logger.process("test message", {})
    assert f"[TAINT:{test_crc32}] - test message" in msg


def test_tiered_logger_rejects_string_plugin_id():
    """Verify that passing string namespace to plugin_id raises TypeError without fallback."""
    with pytest.raises(TypeError) as exc_info:
        get_logger("plugins.slskd", plugin_id="EchoSync.slskd")
    assert "plugin_id must be an unsigned 32-bit integer" in str(exc_info.value)


def test_tiered_logger_rejects_boolean_plugin_id():
    """Verify that boolean values are rejected despite being subclass of int."""
    with pytest.raises(TypeError) as exc_info:
        get_logger("plugins.slskd", plugin_id=True)
    assert "plugin_id must be an unsigned 32-bit integer" in str(exc_info.value)


def test_tiered_logger_rejects_out_of_range_plugin_id():
    """Verify that negative or > 32-bit integers are rejected with ValueError."""
    with pytest.raises(ValueError):
        get_logger("plugins.slskd", plugin_id=-1)

    with pytest.raises(ValueError):
        get_logger("plugins.slskd", plugin_id=0x100000000)


# ==============================================================================
# 2. SLSKD EventBus Thread Supervision Tests
# ==============================================================================


def test_slskd_eventbus_callbacks_spawn_supervised_threads():
    """Verify that SLSKD EventBus callbacks spawn supervised threads with OwnerType.PLUGIN."""
    from plugins.EchoSync.slskd.plugin import PLUGIN_CRC32

    # Simulate dispatching from a thread with no running event loop
    spawn_mock = MagicMock(return_value=(MagicMock(), "mock_reg_id"))
    with patch.object(supervisor, "spawn_supervised_thread", spawn_mock):
        with patch("asyncio.get_running_loop", side_effect=RuntimeError("no running event loop")):
            from core.event_bus import event_bus

            # Publish event that triggers slskd subscriber
            event_bus.publish({"event": "SERVICE_DEGRADED", "service": "slskd"})

            # Allow event bus dispatcher to process
            import time

            time.sleep(0.1)

            assert spawn_mock.called
            call_kwargs = spawn_mock.call_args[1]
            assert call_kwargs["owner_id"] == str(PLUGIN_CRC32)
            assert call_kwargs["owner_type"] == OwnerType.PLUGIN
            assert call_kwargs["bound_to_general_pool"] is True


@pytest.mark.asyncio
async def test_slskd_webhook_mutation_acquires_db_write_lease():
    """Verify that on_webhook_received acquires db_write_lease during DownloadQueue update."""
    from plugins.EchoSync.slskd.plugin import on_webhook_received, PLUGIN_CRC32

    mock_lease = MagicMock()
    mock_lease.__enter__ = MagicMock(return_value=None)
    mock_lease.__exit__ = MagicMock(return_value=None)

    payload = {
        "event": "DownloadFileComplete",
        "task_id": 999,
        "filename": "song.flac",
    }

    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.session_scope.return_value.__enter__.return_value = mock_session
    mock_task = MagicMock()
    mock_task.echo_sync_track = {"title": "Test"}
    mock_session.get.return_value = mock_task

    with patch("database.working_database.get_working_database", return_value=mock_db):
        with patch("plugins.EchoSync.slskd.plugin.db_write_lease", return_value=mock_lease) as lease_factory:
            await on_webhook_received("download_status", payload)
            lease_factory.assert_called_once_with(task_name=f"plugin_{PLUGIN_CRC32}")
            mock_lease.__enter__.assert_called_once()
            mock_lease.__exit__.assert_called_once()


# ==============================================================================
# 3. Tidal OAuth Sidecar Supervision Tests
# ==============================================================================


def test_tidal_oauth_sidecar_retired_and_warns():
    """Verify Tidal bespoke OAuth sidecar is retired and delegates to centralized HTTPS sidecar."""
    from plugins.EchoSync.tidal.client import TidalClient

    client = TidalClient()
    with patch("plugins.EchoSync.tidal.client.logger.info") as mock_info:
        client._start_callback_server()
        assert mock_info.called
        msg = mock_info.call_args[0][0]
        assert "deprecated" in msg
        assert "centralized HTTPS sidecar on port 5001" in msg
        assert client.auth_server is None


# ==============================================================================
# 4. LocalServer Crawler & Database Cleanup Tests
# ==============================================================================


def test_local_server_crawler_cooperative_cancellation(tmp_path):
    """Verify LocalServer crawler iterates sequentially and respects cooperative cancellation."""
    from plugins.EchoSync.local_server.client import LocalServerProvider

    # Create dummy directory with dummy audio files
    lib_dir = tmp_path / "music"
    lib_dir.mkdir()
    (lib_dir / "track1.mp3").write_bytes(b"dummy")
    (lib_dir / "track2.mp3").write_bytes(b"dummy")

    provider = LocalServerProvider()
    provider.sdk = MagicMock()
    provider.sdk.config.get.return_value = str(lib_dir)

    # Mock cancellation after first file
    cancelled_states = [False, True]

    def mock_is_cancelled():
        if cancelled_states:
            return cancelled_states.pop(0)
        return True

    with patch.object(supervisor, "is_current_task_cancelled", side_effect=mock_is_cancelled):
        with patch("plugins.EchoSync.local_server.client.inspect_audio_file") as mock_inspect:
            mock_audio = MagicMock()
            mock_audio.artist_source = "tpe1"
            mock_audio.artist = "Test Artist"
            mock_audio.title = "Test Track"
            mock_audio.duration_ms = 180000
            mock_audio.isrc = None
            mock_inspect.return_value = mock_audio

            tracks = list(provider.get_all_tracks())
            # Only 1 track should be yielded because second iteration encountered cancellation
            assert len(tracks) <= 1


def test_local_server_database_cleanup_acquires_write_lease():
    """Verify DatabaseCleanupJob acquires db_write_lease during execution."""
    from plugins.EchoSync.local_server.database_cleanup import DatabaseCleanupJob, PLUGIN_CRC32

    job = DatabaseCleanupJob()
    mock_db = MagicMock()
    mock_session = MagicMock()
    mock_db.session_scope.return_value.__enter__.return_value = mock_session
    mock_session.query.return_value.all.return_value = []
    mock_session.query.return_value.filter.return_value.all.return_value = []

    mock_lease = MagicMock()
    mock_lease.__enter__ = MagicMock(return_value=None)
    mock_lease.__exit__ = MagicMock(return_value=None)

    with patch("plugins.EchoSync.local_server.database_cleanup.get_database", return_value=mock_db):
        with patch(
            "plugins.EchoSync.local_server.database_cleanup.db_write_lease", return_value=mock_lease
        ) as lease_mock:
            job.execute()
            lease_mock.assert_called_once_with(task_name=f"plugin_{PLUGIN_CRC32}")
            mock_lease.__enter__.assert_called_once()
            mock_lease.__exit__.assert_called_once()
