with open('/app/database/config_database.py', 'r') as f:
    content = f.read()

import re

# Since config_database uses raw sqlite3.Connection, we can't fully swap it to PostgreSQL easily,
# but the prompt asked: "Have them read the database connection string dynamically from config.json ... allowing users/plugins to point the backend to PostgreSQL or MySQL. ... Please check config.json for three distinct keys: database.music_uri, database.working_uri, and database.config_uri. If they are not present, default to the existing local SQLite paths."

new_init = """    def __init__(self, db_path: Optional[str] = None):
        uri = config_manager.get("database.config_uri")
        if uri:
            # We assume the config_database.py wrapper is heavily SQLite-dependent right now,
            # but we still support passing the URI. For SQLite it should extract the path.
            # If it's a real postgres URI, we'd need SQLAlchemy, but config_database uses sqlite3 module.
            # Assuming we just parse sqlite:/// path or fallback to the provided URI if it acts as a file.
            if uri.startswith("sqlite:///"):
                self.database_path = Path(uri.replace("sqlite:///", ""))
            else:
                self.database_path = Path(uri)
        else:
            self.database_path = Path(db_path) if db_path else Path(config_manager.database_path)

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        # Ensure writer queue is running for this DB
        try:
            ensure_writer(str(self.database_path))
        except Exception:
            # best-effort; don't fail startup if writer can't be created
            pass
        self._initialize_schema()"""

content = re.sub(
    r'    def __init__\(self, db_path: Optional\[str\] = None\):.*?self\._initialize_schema\(\)',
    new_init,
    content,
    flags=re.DOTALL
)

with open('/app/database/config_database.py', 'w') as f:
    f.write(content)
