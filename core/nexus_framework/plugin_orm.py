import re
from sqlalchemy.orm import declarative_base, declared_attr

def get_plugin_base(plugin_id: str):
    """
    Factory function to generate a SQLAlchemy declarative base class for a specific plugin.
    Automatically scopes all table names to prevent collisions with core tables or other plugins.
    """
    # Sanitize plugin ID to be safe for table names
    safe_plugin_id = re.sub(r'[^a-zA-Z0-9_]', '_', plugin_id).lower()

    class PluginBaseModel:
        @declared_attr
        def __tablename__(cls):
            # If the user defined a __tablename__, use it but prefix it.
            # Otherwise, use the class name but prefix it.
            base_name = getattr(cls, '_tablename', cls.__name__.lower())

            # Avoid double prefixing if the class inherits from another plugin class
            prefix = f"plugin_{safe_plugin_id}_"
            if base_name.startswith(prefix):
                return base_name

            return f"{prefix}{base_name}"

    return declarative_base(cls=PluginBaseModel)


def copy_table_data(session_factory, dest_model, source_plugin_id: str, source_table_name: str) -> bool:
    """
    Copies all data from another plugin's table into the destination model's table.
    Crucial for data migration when a user switches between Stable and Beta plugin channels.

    Args:
        session_factory: A callable that returns an active SQLAlchemy Session.
        dest_model: The SQLAlchemy model class representing the destination table.
        source_plugin_id: The ID of the plugin from which to copy (e.g., 'musicbrainz').
        source_table_name: The base table name as defined in the source plugin's model (e.g., 'cache').

    Returns:
        bool: True if the operation succeeded or was cleanly skipped, False on severe error.
    """
    import logging
    logger = logging.getLogger("plugin_orm")
    
    # 1. Strict Validation to prevent SQL injection
    if not re.match(r'^[a-zA-Z0-9_]+$', source_plugin_id):
        logger.error(f"Invalid source_plugin_id: {source_plugin_id}")
        return False
        
    if not re.match(r'^[a-zA-Z0-9_]+$', source_table_name):
        logger.error(f"Invalid source_table_name: {source_table_name}")
        return False

    # 2. Dynamic Table Name Construction
    dest_table = dest_model.__tablename__
    safe_source_id = source_plugin_id.lower()
    source_table_full = f"plugin_{safe_source_id}_{source_table_name}"
    
    if not re.match(r'^[a-zA-Z0-9_]+$', dest_table) or not re.match(r'^[a-zA-Z0-9_]+$', source_table_full):
        logger.error(f"Invalid SQL identifier in table migration: dest='{dest_table}', source='{source_table_full}'")
        return False

    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError

    with session_factory() as session:
        try:
            # 3. Check if source table exists and has data before attempting copy
            # We use a simple select limit 1 to see if it exists
            session.execute(text(f'SELECT 1 FROM "{source_table_full}" LIMIT 1'))
            
            # 4. Check if destination table is already populated (idempotency)
            # If the dest table already has rows, we shouldn't blindly append, 
            # as that could cause constraint violations. For a clean migration, 
            # we assume the dest table should be empty.
            dest_count = session.execute(text(f'SELECT count(*) FROM "{dest_table}"')).scalar()
            if dest_count > 0:
                logger.info(f"Destination table {dest_table} already contains data. Skipping copy from {source_table_full}.")
                return True

            # 5. Execute the copy
            # Note: We assume the schemas are identical (which they should be for stable -> beta).
            logger.info(f"Copying data from {source_table_full} to {dest_table}...")
            query = f'INSERT INTO "{dest_table}" SELECT * FROM "{source_table_full}"'
            result = session.execute(text(query))
            session.commit()
            
            logger.info(f"Successfully copied {result.rowcount} rows from {source_table_full} to {dest_table}.")
            return True
            
        except OperationalError as e:
            # Common case: User never installed the stable version, so the table doesn't exist.
            if "no such table" in str(e).lower():
                logger.info(f"Source table {source_table_full} does not exist. Skipping copy.")
                return True
            logger.error(f"Operational error during table copy: {e}")
            session.rollback()
            return False
        except Exception as e:
            logger.error(f"Failed to copy table data: {e}", exc_info=True)
            session.rollback()
            return False
