import sqlite3
import os

db_paths = [
    "data/music.db",
    "data/working.db",
    "data/config.db",
    "database/music_database.db",
    "database/working_database.db",
    "database/config_database.db",
    "music.db",
    "working.db",
    "config.db"
]

# Walk workspace to find any .db files
for root, dirs, files in os.walk("."):
    for file in files:
        if file.endswith(".db"):
            db_paths.append(os.path.join(root, file))

db_paths = list(set([os.path.abspath(p) for p in db_paths if os.path.exists(p)]))

print(f"Found databases: {db_paths}")

for path in db_paths:
    try:
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            if table.startswith("_alembic_tmp_"):
                print(f"Dropping temporary table {table} in {path}")
                cursor.execute(f"DROP TABLE IF EXISTS {table};")
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error checking/cleaning {path}: {e}")
