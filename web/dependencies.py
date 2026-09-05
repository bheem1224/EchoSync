"""FastAPI dependencies for EchoSync web routes."""

from database.config_database import ConfigDatabase, get_config_database


def get_config_db() -> ConfigDatabase:
    """FastAPI Depends provider that returns the shared, thread-safe ConfigDatabase instance."""
    return get_config_database()
