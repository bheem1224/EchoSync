"""
Unit tests verifying the one-time schema initialization guard and singleton reuse
for ConfigDatabase.
"""

import logging
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from database.config_database import (
    ConfigDatabase,
    close_config_database,
    get_config_database,
    get_config_db,
)
from web.dependencies import get_config_db as web_get_config_db


@pytest.fixture
def temp_config_dir():
    tmp_dir = tempfile.mkdtemp(prefix="echosync_test_guard_")
    yield Path(tmp_dir)
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_one_time_schema_initialization_guard(temp_config_dir, caplog):
    """Verify schema migration runs strictly once and subsequent inits are guarded."""
    db_path = temp_config_dir / "config.db"

    # Reset class-level guards for this test path
    resolved_path = str(db_path.resolve())
    ConfigDatabase._initialized_paths.discard(resolved_path)

    with caplog.at_level(logging.DEBUG, logger="config_database"):
        db1 = ConfigDatabase(db_path=db_path)

        assert ConfigDatabase._schema_initialized is True
        assert ConfigDatabase._schema_verified is True
        assert resolved_path in ConfigDatabase._initialized_paths

        # Check debug message emitted
        debug_records = [
            r
            for r in caplog.records
            if "Config database schema ensured and legacy services migrated"
            in r.message
        ]
        assert len(debug_records) == 1
        assert debug_records[0].levelno == logging.DEBUG

        # Second instantiation on same path should skip migration checks
        caplog.clear()
        db2 = ConfigDatabase(db_path=db_path)
        assert db2 is not None

        # Verify no migration log emitted on second instantiation
        debug_records_second = [
            r
            for r in caplog.records
            if "Config database schema ensured and legacy services migrated"
            in r.message
        ]
        assert len(debug_records_second) == 0


def test_singleton_get_config_database(temp_config_dir):
    """Verify get_config_database and get_config_db return shared instances."""
    close_config_database()

    db1 = get_config_database()
    db2 = get_config_database()
    db3 = get_config_db()

    assert db1 is db2
    assert db2 is db3

    custom_path = temp_config_dir / "custom.db"
    c_db1 = get_config_database(db_path=custom_path)
    c_db2 = get_config_database(db_path=custom_path)
    c_db3 = get_config_db(db_path=custom_path)

    assert c_db1 is c_db2
    assert c_db2 is c_db3
    assert c_db1 is not db1


def test_fastapi_dependency_injection():
    """Verify get_config_db works as a FastAPI Depends provider."""
    app = FastAPI()

    @app.get("/test-dep")
    def test_endpoint(db: ConfigDatabase = Depends(web_get_config_db)):
        return {"instance_id": id(db)}

    client = TestClient(app)
    resp1 = client.get("/test-dep")
    resp2 = client.get("/test-dep")

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["instance_id"] == resp2.json()["instance_id"]
    assert resp1.json()["instance_id"] == id(get_config_database())
