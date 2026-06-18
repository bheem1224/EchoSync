import sqlite3
import os

db_path = 'data/music_library.db'

print(f"Using db: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute('DROP TABLE IF EXISTS local_media')
    
    # Check if media_id was added
    try:
        cur.execute('ALTER TABLE audio_fingerprints DROP COLUMN media_id')
    except Exception as e:
        print(f'could not drop column media_id from audio_fingerprints: {e}')
        
    try:
        cur.execute('ALTER TABLE external_identifiers DROP COLUMN media_id')
    except Exception as e:
        print(f'could not drop column media_id from external_identifiers: {e}')
    
    # Reset alembic
    cur.execute("UPDATE alembic_version SET version_num = 'eaf4b5d2df68'")
    conn.commit()
    conn.close()
    print('DB cleaned up for retry')
except Exception as e:
    print(f"Error: {e}")
