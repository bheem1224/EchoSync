"""Unit tests for on-demand verbose file logging, third-party suppression,
and structured MusicBrainz logging.
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from core.tiered_logger import (
    VERBOSE,
    disable_verbose_file_logging,
    enable_verbose_file_logging,
    get_logger,
    is_verbose_file_logging_enabled,
    setup_logging,
)
from web.api_app import create_app


def test_third_party_stream_loggers_suppressed():
    """Third-party stream loggers are clamped to WARNING."""
    setup_logging(level="INFO")

    for noisy_logger in ("sse_starlette", "sse_starlette.sse", "uvicorn.access", "urllib3", "httpx"):
        logger = logging.getLogger(noisy_logger)
        assert logger.level == logging.WARNING, (
            f"Logger {noisy_logger} level was {logger.level}, expected WARNING ({logging.WARNING})"
        )


def test_on_demand_verbose_file_logging_lifecycle(tmp_path: Path):
    """Ensure verbose file handler is strictly on-demand: not created or open until enabled, and cleanly closed when disabled."""
    # 1. Setup normal logging in tmp_path
    setup_logging(level="INFO", log_dir=str(tmp_path))
    disable_verbose_file_logging()

    verbose_file = tmp_path / "echosync-verbose.log"
    assert not is_verbose_file_logging_enabled()
    assert not verbose_file.exists()

    # Log a level 5 (VERBOSE) message while disabled
    test_logger = get_logger("test.lifecycle")
    test_logger.log(VERBOSE, "This message should NOT be written to disk when disabled")
    assert not verbose_file.exists()

    # 2. Enable verbose file logging dynamically
    res = enable_verbose_file_logging(log_dir=tmp_path)
    assert res is True
    assert is_verbose_file_logging_enabled()
    assert verbose_file.exists()

    # 3. Log a level 5 message and verify write
    test_logger.log(VERBOSE, "UNIQUE_DIAGNOSTIC_PAYLOAD_12345")
    test_logger.verbose("CONVENIENCE_VERBOSE_MESSAGE_67890")

    content = verbose_file.read_text(encoding="utf-8")
    assert "UNIQUE_DIAGNOSTIC_PAYLOAD_12345" in content
    assert "CONVENIENCE_VERBOSE_MESSAGE_67890" in content

    # 4. Disable verbose file logging dynamically
    disable_verbose_file_logging()
    assert not is_verbose_file_logging_enabled()

    # 5. Log after disable - message should not be appended
    current_size = verbose_file.stat().st_size
    test_logger.log(VERBOSE, "AFTER_DISABLE_PAYLOAD_BLOCKED")
    assert verbose_file.stat().st_size == current_size


def test_musicbrainz_structured_vs_verbose_logging():
    """MusicBrainz get_metadata logs concise single-line under DEBUG and full raw dict under VERBOSE."""
    from plugins.EchoSync.musicbrainz.client import MusicBrainzClient

    client = MusicBrainzClient()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "rec-123",
        "title": "Livin' on a Prayer",
        "artist-credit": [{"name": "Bon Jovi", "joinphrase": ""}],
        "releases": [{"id": "rel-1", "title": "Slippery When Wet", "date": "1986-08-18"}],
        "length": 249000,
        "isrcs": ["USPR38600001"],
    }
    client.http.get = MagicMock(return_value=mock_resp)

    # Capture logs with a custom handler
    records = []

    class RecordHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    mb_logger = logging.getLogger("provider.musicbrainz")
    rec_handler = RecordHandler()
    rec_handler.setLevel(VERBOSE)
    mb_logger.addHandler(rec_handler)
    original_level = mb_logger.level
    mb_logger.setLevel(logging.DEBUG)  # Only DEBUG enabled, not VERBOSE (5)

    from core.caching.plugin_cache import get_cache
    get_cache().clear()

    try:
        # Run get_metadata with mb_logger at DEBUG level
        result = client.get_metadata("rec-123")
        assert result is not None
        assert result["title"] == "Livin' on a Prayer"

        # Check debug logs: should have concise summary, NOT raw json
        debug_msgs = [r.getMessage() for r in records if r.levelno == logging.DEBUG]
        concise = [m for m in debug_msgs if "resolved: 'Livin' on a Prayer' by 'Bon Jovi'" in m]
        assert len(concise) == 1
        assert "Raw MBID=rec-123 payload:" not in " ".join(debug_msgs)

        # Now enable VERBOSE (level 5) on mb_logger
        records.clear()
        get_cache().clear()
        mb_logger.setLevel(VERBOSE)
        client.get_metadata("rec-123")

        verbose_msgs = [r.getMessage() for r in records if r.levelno == VERBOSE]
        raw_payload_logs = [m for m in verbose_msgs if "Raw MBID=rec-123 payload:" in m]
        assert len(raw_payload_logs) == 1
        assert "USPR38600001" in raw_payload_logs[0]

    finally:
        mb_logger.removeHandler(rec_handler)
        mb_logger.setLevel(original_level)


def test_system_settings_verbose_logging_api_toggle(tmp_path: Path):
    """PATCH /api/v1/system/settings toggles on-demand verbose logging dynamically."""
    setup_logging(level="INFO", log_dir=str(tmp_path))
    disable_verbose_file_logging()

    app = create_app(testing=True)
    test_client = TestClient(app)

    assert not is_verbose_file_logging_enabled()

    # Enable via API
    resp = test_client.patch(
        "/api/v1/system/settings",
        json={"system.verbose_logging_enabled": True},
    )
    assert resp.status_code == 200
    assert is_verbose_file_logging_enabled()

    # Disable via API
    resp = test_client.patch(
        "/api/v1/system/settings",
        json={"system.verbose_logging_enabled": False},
    )
    assert resp.status_code == 200
    assert not is_verbose_file_logging_enabled()
