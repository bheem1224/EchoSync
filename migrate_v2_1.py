#!/usr/bin/env python3

"""
Migration script for v2.1.0

This script safely adds the missing `isrc` column to the `tracks` table
in the `music_library.db` database without dropping existing user data.
"""

import os
import sqlite3
from pathlib import Path
from core.tiered_logger import get_logger

logger = get_logger("migrate_v2_1")

def run_migration():
    data_dir = os.getenv("SOULSYNC_DATA_DIR")
    if data_dir:
        db_path = Path(data_dir) / "music_library.db"
    else:
        db_path = Path("data") / "music_library.db"

    if not db_path.exists():
        logger.info(f"Database file {db_path} does not exist. No migration needed.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if the column already exists
        cursor.execute("PRAGMA table_info('tracks')")
        columns = [info[1] for info in cursor.fetchall()]

        if 'isrc' not in columns:
            logger.info("Adding 'isrc' column to 'tracks' table...")
            cursor.execute("ALTER TABLE tracks ADD COLUMN isrc VARCHAR")
            conn.commit()
            logger.info("Successfully added 'isrc' column.")
        else:
            logger.info("'isrc' column already exists in 'tracks' table.")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    run_migration()
