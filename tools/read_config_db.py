import sqlite3


def main():
    conn = sqlite3.connect("config/config.db")
    cur = conn.cursor()

    # List tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cur.fetchall()]
    for t in tables:
        print(f"Table: {t}")
        cur.execute(f"PRAGMA table_info({t});")
        cols = [c[1] for c in cur.fetchall()]
        print(f"  Columns: {cols}")
        try:
            cur.execute(f"SELECT * FROM {t} LIMIT 20;")
            rows = cur.fetchall()
            for r in rows:
                print(f"    {r}")
        except Exception as e:
            print(f"    error: {e}")
        print()
    conn.close()


if __name__ == "__main__":
    main()
