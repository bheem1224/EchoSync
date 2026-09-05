import os
import sqlite3


def inspect_db(db_path):
    print(f"inspecting: {db_path} ({os.path.getsize(db_path)} bytes)")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [r[0] for r in cur.fetchall()]
        print(f"  tables: {tables}")
        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                count = cur.fetchone()[0]
                print(f"    {t}: {count} rows")
            except Exception as e:
                print(f"    {t}: error: {e}")
        conn.close()
    except Exception as e:
        print(f"  error connecting: {e}")
    print()


def main():
    # search for .db files in workspace
    for root, dirs, files in os.walk("."):
        if ".git" in root or ".venv" in root:
            continue
        for f in files:
            if f.endswith(".db"):
                inspect_db(os.path.join(root, f))


if __name__ == "__main__":
    main()
