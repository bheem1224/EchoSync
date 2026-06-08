import os
import sqlite3
from pathlib import Path

root = Path("C:\\Users\\bheem\\Nextcloud2\\VS-Code-Projects\\EchoSync")
for dirpath, _, filenames in os.walk(root):
    for f in filenames:
        if f.endswith(".db"):
            fp = Path(dirpath) / f
            size = fp.stat().st_size
            try:
                conn = sqlite3.connect(fp)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tracks'")
                has_tracks = cursor.fetchone() is not None
                if has_tracks:
                    cursor.execute("SELECT count(*) FROM tracks")
                    count = cursor.fetchone()[0]
                    print(f"DB: {fp} | Size: {size} bytes | Tracks Table Row Count: {count}")
                else:
                    print(f"DB: {fp} | Size: {size} bytes | No tracks table")
                conn.close()
            except Exception as e:
                print(f"DB: {fp} | Size: {size} bytes | Error: {e}")
