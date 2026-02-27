from database.music_database import MusicDatabase
import sqlite3

if __name__ == '__main__':
    db = MusicDatabase()
    print('Resolved DB path:', db.database_path)
    conn = sqlite3.connect(str(db.database_path))
    c = conn.cursor()
    for tbl in ('artists','albums','tracks'):
        try:
            c.execute(f"SELECT COUNT(*) FROM {tbl}")
            print(f"{tbl}:", c.fetchone()[0])
        except Exception as e:
            print(f"{tbl}: error -", e)
    conn.close()
