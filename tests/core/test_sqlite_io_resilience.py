"""
Unit tests for SQLite I/O resilience and retry mechanisms under WAL lock contention
and disk I/O error conditions.
"""

import sqlite3
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.nexus_framework.plugin_SDK import PluginConfigSDK, _ConfigFacade
from database.config_database import ConfigDatabase, retry_sqlite_io


@pytest.fixture
def temp_db_path(tmp_path):
    db_file = tmp_path / "test_resilience_config.db"
    return str(db_file)


# =========================================================================
# 1. Standalone Decorator Tests
# =========================================================================


def test_retry_sqlite_io_succeeds_immediately():
    """Verify decorated function runs normally without failure."""
    calls = 0

    @retry_sqlite_io(max_retries=3, base_delay=0.01, max_delay=0.05)
    def simple_query():
        nonlocal calls
        calls += 1
        return "success"

    assert simple_query() == "success"
    assert calls == 1


@pytest.mark.parametrize(
    "error_message",
    [
        "disk I/O error",
        "database is locked",
        "database is busy",
        "sqlite3.OperationalError: disk i/o error on device",
    ],
)
def test_retry_sqlite_io_recovers_from_transient_errors(error_message):
    """Verify decorator retries on disk I/O, locked, and busy errors and succeeds."""
    calls = 0

    @retry_sqlite_io(max_retries=4, base_delay=0.01, max_delay=0.05)
    def flaky_query():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise sqlite3.OperationalError(error_message)
        return "recovered"

    result = flaky_query()
    assert result == "recovered"
    assert calls == 3


def test_retry_sqlite_io_raises_non_transient_immediately():
    """Verify non-transient SQLite OperationalErrors fail immediately without retry."""
    calls = 0

    @retry_sqlite_io(max_retries=4, base_delay=0.01, max_delay=0.05)
    def invalid_query():
        nonlocal calls
        calls += 1
        raise sqlite3.OperationalError("no such table: nonexistent_table")

    with pytest.raises(sqlite3.OperationalError) as exc_info:
        invalid_query()

    assert "no such table" in str(exc_info.value)
    assert calls == 1


def test_retry_sqlite_io_exhausts_retries():
    """Verify decorator raises the exception once max_retries is reached."""
    calls = 0

    @retry_sqlite_io(max_retries=3, base_delay=0.01, max_delay=0.05)
    def persistently_broken():
        nonlocal calls
        calls += 1
        raise sqlite3.OperationalError("disk I/O error")

    with pytest.raises(sqlite3.OperationalError) as exc_info:
        persistently_broken()

    assert "disk I/O error" in str(exc_info.value)
    assert calls == 3


# =========================================================================
# 2. ConfigDatabase Method Resilience Tests
# =========================================================================


def test_config_db_get_service_id_retries_transient_error(temp_db_path):
    """Verify get_service_id retries when encountering a transient disk I/O error."""
    db = ConfigDatabase(db_path=temp_db_path)
    db.register_service("spotify", "streaming", "Spotify Service", plugin_id=12345)

    original_get_conn = db._get_connection
    attempts = 0

    def mock_get_conn():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise sqlite3.OperationalError("disk I/O error")
        return original_get_conn()

    with patch.object(db, "_get_connection", side_effect=mock_get_conn):
        svc_id = db.get_service_id("spotify")
        assert svc_id is not None
        assert attempts == 2


def test_config_db_get_or_create_service_id_retries(temp_db_path):
    """Verify get_or_create_service_id retries transient disk I/O errors."""
    db = ConfigDatabase(db_path=temp_db_path)
    db.register_service("system", "core", "System core", plugin_id=0)

    original_get_conn = db._get_connection
    attempts = 0

    def mock_get_conn():
        nonlocal attempts
        attempts += 1
        if attempts <= 2:
            raise sqlite3.OperationalError("database is locked")
        return original_get_conn()

    with patch.object(db, "_get_connection", side_effect=mock_get_conn):
        svc_id = db.get_or_create_service_id("system")
        assert svc_id is not None
        assert attempts == 3


def test_config_db_get_service_credentials_retries(temp_db_path):
    """Verify get_service_credentials retries on transient errors."""
    db = ConfigDatabase(db_path=temp_db_path)
    db.register_service("spotify", "streaming", "Spotify Service", plugin_id=12345)
    db.set_service_config(12345, "client_id", "my_test_client_id")

    original_get_conn = db._get_connection
    attempts = 0

    def mock_get_conn():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise sqlite3.OperationalError("disk I/O error")
        return original_get_conn()

    with patch.object(db, "_get_connection", side_effect=mock_get_conn):
        creds = db.get_service_credentials("spotify")
        assert isinstance(creds, dict)
        assert creds.get("client_id") == "my_test_client_id"
        assert attempts >= 2


def test_config_db_setting_aliases_and_retry(temp_db_path):
    """Verify get_setting and set_setting aliases work and survive transient errors."""
    db = ConfigDatabase(db_path=temp_db_path)

    # set_setting
    assert db.set_setting("storage.transient_test", "active_value") is True

    # get_setting
    val = db.get_setting("storage.transient_test")
    assert val == "active_value"

    # Simulate transient error during get_setting
    original_get_conn = db._get_connection
    attempts = 0

    def mock_get_conn():
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise sqlite3.OperationalError("database is busy")
        return original_get_conn()

    with patch.object(db, "_get_connection", side_effect=mock_get_conn):
        retrieved = db.get_setting("storage.transient_test")
        assert retrieved == "active_value"
        assert attempts == 2


# =========================================================================
# 3. PluginConfigSDK / _ConfigFacade Resilience Tests
# =========================================================================


def test_plugin_config_sdk_alias():
    """Verify PluginConfigSDK is an alias for _ConfigFacade."""
    assert PluginConfigSDK is _ConfigFacade


def test_plugin_config_sdk_get_survives_transient_error(temp_db_path):
    """Verify PluginConfigSDK.get retries transient errors and succeeds."""
    db = ConfigDatabase(db_path=temp_db_path)
    db.register_service("test_plugin", "provider", "Test Plugin", plugin_id=99999)
    db.set_service_config(99999, "api_key", "secret_key_123")

    facade = PluginConfigSDK("test_plugin")

    with patch("database.config_database.get_config_database", return_value=db):
        attempts = 0
        original_get_svc = db.get_service_config

        def mock_get_service_config(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise sqlite3.OperationalError("disk I/O error")
            return original_get_svc(*args, **kwargs)

        with patch.object(db, "get_service_config", side_effect=mock_get_service_config):
            val = facade.get("api_key")
            assert val == "secret_key_123"
            assert attempts == 2


def test_plugin_config_sdk_get_falls_back_to_default_on_persistent_error():
    """Verify PluginConfigSDK.get does not raise on persistent database failure, but returns default."""
    facade = PluginConfigSDK("test_broken_plugin")

    mock_db = MagicMock()
    mock_db.get_or_create_service_id.side_effect = sqlite3.OperationalError("disk I/O error")

    with patch("database.config_database.get_config_database", return_value=mock_db):
        val = facade.get("any_key", default="safe_default")
        assert val == "safe_default"


def test_plugin_config_sdk_set_survives_transient_error(temp_db_path):
    """Verify PluginConfigSDK.set retries transient errors."""
    db = ConfigDatabase(db_path=temp_db_path)
    db.register_service("test_plugin_set", "provider", "Test Plugin", plugin_id=88888)

    facade = PluginConfigSDK("test_plugin_set")

    with patch("database.config_database.get_config_database", return_value=db):
        attempts = 0
        original_set_svc = db.set_service_config

        def mock_set_service_config(*args, **kwargs):
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise sqlite3.OperationalError("database is locked")
            return original_set_svc(*args, **kwargs)

        with patch.object(db, "set_service_config", side_effect=mock_set_service_config):
            facade.set("theme", "dark")
            assert attempts == 2
            assert facade.get("theme") == "dark"


# =========================================================================
# 4. Real SQLite WAL Contention / Busy Timeout Test
# =========================================================================


def test_real_sqlite_wal_busy_timeout_and_retries(temp_db_path):
    """Simulate a concurrent writer holding an exclusive lock and verify that
    readers/writers handle contention properly via busy_timeout and retry.
    """
    db = ConfigDatabase(db_path=temp_db_path)
    db.register_service("system", "core", "System core", plugin_id=0)

    # Verify initial read works
    assert db.get_service_id("system") is not None

    # Hold a short transaction in another thread
    lock_released = threading.Event()
    thread_started = threading.Event()

    def locking_worker():
        conn = sqlite3.connect(temp_db_path, timeout=5.0)
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("BEGIN EXCLUSIVE")
        thread_started.set()
        # Hold lock for 0.15s then release
        time.sleep(0.15)
        conn.commit()
        conn.close()
        lock_released.set()

    t = threading.Thread(target=locking_worker)
    t.start()
    thread_started.wait()

    # Query during contention - should succeed via busy_timeout / retry
    svc_id = db.get_service_id("system")
    assert svc_id is not None

    t.join(timeout=2.0)
    assert lock_released.is_set()
