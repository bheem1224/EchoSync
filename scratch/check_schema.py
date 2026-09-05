import os
import sqlite3
from pathlib import Path

# Try to find the config.db
# Based on core/migrations.py and run_api.py, it should be in the data dir or .gemini/antigravity/...
# But let's check the ECHOSYNC_DATA_DIR env or default to data/

data_dir = os.getenv("ECHOSYNC_DATA_DIR", "data")
db_path = Path(data_dir) / "config.db"

if not db_path.exists():
    # Fallback to the path mentioned in the error if possible, but let's try to be smart
    # Actually, the user says SoulSync is at c:\Users\bheem\VScode-Projects\SoulSync
    db_path = Path(r"c:\Users\bheem\VScode-Projects\SoulSync\config\config.db")

if not db_path.exists():
    print(f"DB not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='services'"
    )
    row = cursor.fetchone()
    if row:
        print(row[0])
    else:
        print("Table 'services' not found")
    conn.close()
