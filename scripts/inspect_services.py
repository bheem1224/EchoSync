import sqlite3

conn = sqlite3.connect("config/config.db")
c = conn.cursor()
cols = [r[1] for r in c.execute("PRAGMA table_info(services)").fetchall()]
print("Services columns:", cols)
rows = c.execute("SELECT * FROM services").fetchall()
for r in rows:
    print(dict(zip(cols, r)))
