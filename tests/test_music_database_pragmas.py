import sqlite3
from database.music_database import MusicDatabase


def test_sqlite_pragmas_enable_wal_and_timeout(tmp_path):
    """The SQLAlchemy engine should configure WAL mode and busy_timeout via _sqlite_pragmas."""
    # create a temporary database file
    db_file = tmp_path / "test.db"
    # instantiate MusicDatabase with custom path
    mdb = MusicDatabase(database_path=str(db_file))
    # open a connection via SQLAlchemy engine so our pragma hook runs
    with mdb.engine.connect() as conn:
        # foreign keys should be on
        result = conn.exec_driver_sql("PRAGMA foreign_keys;")
        assert result.fetchone()[0] == 1

        # journal_mode should report WAL
        result = conn.exec_driver_sql("PRAGMA journal_mode;")
        mode = result.fetchone()[0]
        assert mode.lower() == "wal"

        # busy_timeout should be set to a value >= 5000 (returned as milliseconds)
        result = conn.exec_driver_sql("PRAGMA busy_timeout;")
        timeout_val = result.fetchone()[0]
        assert timeout_val >= 5000
