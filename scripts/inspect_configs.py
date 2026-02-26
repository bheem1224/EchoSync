#!/usr/bin/env python3
import json
from sdk.storage_service import get_storage_service
from database.music_database import get_database

storage = get_storage_service()
mdb = get_database()

print('StorageService (config.db) entries:')
for key in ('client_id','client_secret','redirect_uri'):
    try:
        v = storage.get_service_config('spotify', key)
    except Exception as e:
        v = f'ERROR: {e}'
    print(f'  {key}: {v}')

print('\nMusic DB (service_config) entries:')
with mdb._get_connection() as conn:
    c = conn.cursor()
    c.execute('SELECT id FROM services WHERE name = ?', ('spotify',))
    row = c.fetchone()
    if not row:
        print('  No spotify service registered in music DB')
    else:
        sid = row[0]
        c.execute('SELECT config_key, config_value, is_sensitive FROM service_config WHERE service_id = ?', (sid,))
        rows = c.fetchall()
        if not rows:
            print('  No config entries for spotify in music DB')
        else:
            for r in rows:
                print(f'  {r[0]} = {r[1]} (sensitive={bool(r[2])})')

print('\nConfig JSON (config/config.json) preview:')
import os, json
cfg_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'config.json')
try:
    with open(cfg_path, 'r') as f:
        data = json.load(f)
    print(json.dumps(data.get('spotify', {}), indent=2))
except Exception as e:
    print(f'  Could not read config.json: {e}')
