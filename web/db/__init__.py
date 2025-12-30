"""Database wrapper modules for web package.

These wrappers ensure clean separation between the web API layer and the
core database implementations. This design provides:
- Easier debugging (you know if error is in wrapper or actual DB)
- Modular codebase (plugins can extend via wrappers)
- Clear interface contracts
- Single point of adaptation
"""

from web.db.music_database import MusicDatabaseWrapper, get_music_database
from web.db.config_db import ConfigDatabaseWrapper, get_config_database

__all__ = [
    'MusicDatabaseWrapper',
    'ConfigDatabaseWrapper',
    'get_music_database',
    'get_config_database',
]
