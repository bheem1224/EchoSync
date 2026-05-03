import sqlite3
import os

db_path = "data/working.db"
if not os.path.exists(db_path):
    print(f"{db_path} does not exist")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(downloads)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if "soul_sync_track" in columns and "echo_sync_track" not in columns:
        print("Renaming 'soul_sync_track' to 'echo_sync_track'...")
        try:
            cursor.execute("ALTER TABLE downloads RENAME COLUMN soul_sync_track TO echo_sync_track")
            conn.commit()
            print("Successfully renamed column.")
        except Exception as e:
            print(f"Error renaming column: {e}")
    elif "echo_sync_track" in columns:
        print("'echo_sync_track' already exists.")
    else:
        print("Neither 'soul_sync_track' nor 'echo_sync_track' found.")
    
    conn.close()
