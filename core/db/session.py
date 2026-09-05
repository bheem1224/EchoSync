import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker


@event.listens_for(Engine, "connect")
def set_sqlite_pragmas(dbapi_connection, connection_record):
    """
    Apply strict SQLite PRAGMA I/O tunings for low write amplification and high performance.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA synchronous = NORMAL;")
    cursor.execute("PRAGMA cache_size = -64000;")
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.close()


def get_engine(database_path: str = None) -> Engine:
    if not database_path:
        data_dir = os.getenv("ECHOSYNC_DATA_DIR", "data")
        database_path = str(Path(data_dir) / "music_library.db")

    engine_url = f"sqlite:///{database_path}"
    return create_engine(
        engine_url,
        future=True,
        echo=False,
        connect_args={"timeout": 5.0, "check_same_thread": False},
    )


def get_session_factory(engine: Engine = None) -> sessionmaker:
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
