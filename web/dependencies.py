from database.config_database import ConfigDatabase


def get_config_db() -> ConfigDatabase:
    """FastAPI Depends provider that returns the shared, thread-safe ConfigDatabase instance."""
    import database.config_database as cdb

    return cdb.get_config_database()
