import sqlite3

conn = sqlite3.connect("config/config.db")
c = conn.cursor()
print("Services:")
for r in c.execute("SELECT id, name, plugin_id, is_active FROM services").fetchall():
    print(r)

print("\nService Config:")
for r in c.execute(
    "SELECT service_id, config_key, config_value, is_sensitive FROM service_config"
).fetchall():
    print(r)

print("\nAccounts:")
for r in c.execute(
    "SELECT id, service_id, account_name, is_active, is_authenticated FROM accounts"
).fetchall():
    print(r)

print("\nAccount Tokens:")
for r in c.execute(
    "SELECT account_id, access_token IS NOT NULL, expires_at FROM account_tokens"
).fetchall():
    print(r)
