import sqlite3
import os

db_path = "data/working.db"
if not os.path.exists(db_path):
    print(f"{db_path} does not exist")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(downloads)")
    columns = cursor.fetchall()
    print("Columns in 'downloads' table:")
    for col in columns:
        print(col)
    conn.close()
