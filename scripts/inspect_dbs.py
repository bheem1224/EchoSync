import glob
import sqlite3

for path in glob.glob("**/*.db", recursive=True):
    print("Found db:", path)
    try:
        conn = sqlite3.connect(path)
        tables = [
            r[0]
            for r in conn.cursor()
            .execute("SELECT name FROM sqlite_master WHERE type='table'")
            .fetchall()
        ]
        print("  Tables:", tables)
        if "services" in tables:
            for r in (
                conn.cursor()
                .execute(
                    "SELECT plugin_id, service_name, provider_id, enabled FROM services"
                )
                .fetchall()
            ):
                print("    service:", r)
    except Exception as e:
        print("  Error:", e)
