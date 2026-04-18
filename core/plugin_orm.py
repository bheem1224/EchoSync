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
