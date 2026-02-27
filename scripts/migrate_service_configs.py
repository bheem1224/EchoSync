#!/usr/bin/env python3
"""Migrate service_config entries from music_database to encrypted config.db (config_database).
Usage: python scripts/migrate_service_configs.py spotify
"""
import sys
from database.music_database import get_database as get_music_db
from sdk.storage_service import get_storage_service

def migrate(service_name: str):
    mdb = get_music_db()
    storage = get_storage_service()
    with mdb._get_connection() as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM services WHERE name = ?", (service_name,))
        row = c.fetchone()
        if not row:
            print(f"Service {service_name} not found in music database")
            return
        service_id = row[0]
        c.execute("SELECT config_key, config_value, is_sensitive FROM service_config WHERE service_id = ?", (service_id,))
        rows = c.fetchall()
        if not rows:
            print(f"No config entries found for {service_name}")
            return
        migrated = 0
        for r in rows:
            key = r[0]
            value = r[1]
            is_sensitive = bool(r[2])
            ok = storage.set_service_config(service_name, key, value, is_sensitive=is_sensitive)
            if ok:
                migrated += 1
        print(f"Migrated {migrated} entries for {service_name} into config.db")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/migrate_service_configs.py <service_name>")
        sys.exit(1)
    migrate(sys.argv[1])
