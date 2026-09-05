from core.settings import config_manager


def check_indexes():
    db_path = config_manager.database_path
    import sqlite3

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA journal_mode = WAL")
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM quality_profiles")
        print(f"Quality profiles: {c.fetchall()}")
        c.execute("SELECT * FROM services")
        print("Services query succeeded.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    check_indexes()
