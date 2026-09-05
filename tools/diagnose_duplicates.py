#!/usr/bin/env python3
"""
Diagnostic script to quantify duplicate LocalMedia rows in the music database.

Usage:
    python tools/diagnose_duplicates.py [path/to/music_library.db]

If no path is given it defaults to data/music_library.db.
"""

import os
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path


def main():
    db_path = sys.argv[1] if len(sys.argv) > 1 else "data/music_library.db"
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print("=== EchoSync Library Diagnostic ===")
    print(f"Database: {os.path.abspath(db_path)}")
    print()

    # --- 1. Basic counts ---
    cur.execute("SELECT COUNT(*) FROM tracks")
    total_tracks = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM local_media")
    total_media = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM albums")
    total_albums = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM artists")
    total_artists = cur.fetchone()[0]

    print("[Counts]")
    print(f"  Tracks:       {total_tracks}")
    print(f"  LocalMedia:   {total_media}")
    print(f"  Albums:       {total_albums}")
    print(f"  Artists:       {total_artists}")
    print()

    # --- 2. Distinct file paths vs total ---
    cur.execute(
        "SELECT COUNT(DISTINCT file_path) FROM local_media WHERE file_path IS NOT NULL AND file_path != ''"
    )
    distinct_paths = cur.fetchone()[0]
    print("[File Path Analysis]")
    print(f"  Total LocalMedia rows:    {total_media}")
    print(f"  Distinct file_path values: {distinct_paths}")
    print(f"  Duplicate path rows:       {total_media - distinct_paths}")
    print()

    # --- 3. Virtual vs real media ---
    cur.execute("SELECT COUNT(*) FROM local_media WHERE file_path LIKE 'virtual://%'")
    virtual_count = cur.fetchone()[0]
    cur.execute(
        "SELECT COUNT(*) FROM local_media WHERE file_path IS NULL OR file_path = ''"
    )
    null_count = cur.fetchone()[0]
    real_count = total_media - virtual_count - null_count
    print("[Media Types]")
    print(f"  Real file paths:   {real_count}")
    print(f"  Virtual paths:     {virtual_count}")
    print(f"  NULL/empty paths:  {null_count}")
    print()

    # --- 4. Tracks with multiple LocalMedia rows ---
    cur.execute("""
        SELECT track_id, COUNT(*) as cnt
        FROM local_media
        GROUP BY track_id
        HAVING cnt > 1
    """)
    multi_media_tracks = cur.fetchall()
    print("[Tracks with Multiple LocalMedia Rows]")
    print(f"  Tracks with >1 media row: {len(multi_media_tracks)}")
    if multi_media_tracks:
        # Show top 10 worst offenders
        multi_media_tracks.sort(key=lambda x: x[1], reverse=True)
        print("  Top offenders (track_id, media_count):")
        for track_id, cnt in multi_media_tracks[:10]:
            cur.execute(
                """
                SELECT t.title, a.name
                FROM tracks t
                JOIN artists a ON t.artist_id = a.id
                WHERE t.id = ?
            """,
                (track_id,),
            )
            row = cur.fetchone()
            name = f"'{row[0]}' by '{row[1]}'" if row else f"track_id={track_id}"
            print(f"    {name}: {cnt} media rows")

            # Show the paths
            cur.execute(
                "SELECT file_path, file_size_bytes FROM local_media WHERE track_id = ?",
                (track_id,),
            )
            for fp, sz in cur.fetchall():
                sz_str = f"{sz / (1024 * 1024):.1f} MB" if sz else "NULL"
                print(f"      -> {fp}  ({sz_str})")
    print()

    # --- 5. Storage analysis ---
    cur.execute("SELECT COALESCE(SUM(file_size_bytes), 0) FROM local_media")
    total_storage_raw = cur.fetchone()[0]

    cur.execute("""
        SELECT COALESCE(SUM(file_size_bytes), 0)
        FROM local_media
        WHERE file_path NOT LIKE 'virtual://%'
          AND file_path IS NOT NULL
          AND file_path != ''
    """)
    total_storage_real = cur.fetchone()[0]

    # Deduplicated: take MAX file_size_bytes per distinct file_path
    cur.execute("""
        SELECT COALESCE(SUM(best_size), 0)
        FROM (
            SELECT MAX(file_size_bytes) as best_size
            FROM local_media
            WHERE file_path NOT LIKE 'virtual://%'
              AND file_path IS NOT NULL
              AND file_path != ''
            GROUP BY file_path
        )
    """)
    total_storage_deduped = cur.fetchone()[0]

    def fmt_gb(b):
        return f"{b / (1024**3):.1f} GB"

    print("[Storage Analysis]")
    print(f"  Raw SUM(file_size_bytes):                {fmt_gb(total_storage_raw)}")
    print(f"  Excluding virtual paths:                 {fmt_gb(total_storage_real)}")
    print(f"  Deduplicated (distinct file_path only):  {fmt_gb(total_storage_deduped)}")
    print(
        f"  Inflation from duplicates:               {fmt_gb(total_storage_raw - total_storage_deduped)}"
    )
    print()

    # --- 6. File count analysis ---
    cur.execute("""
        SELECT COUNT(*)
        FROM (
            SELECT file_path
            FROM local_media
            WHERE file_path NOT LIKE 'virtual://%'
              AND file_path IS NOT NULL
              AND file_path != ''
            GROUP BY file_path
        )
    """)
    deduped_file_count = cur.fetchone()[0]
    print("[File Count Analysis]")
    print(f"  count_files() would report:  {total_media}")
    print(f"  Real, deduplicated files:    {deduped_file_count}")
    print(f"  Phantom file rows:           {total_media - deduped_file_count}")
    print()

    # --- 7. Path prefix analysis (to detect Plex vs local path divergence) ---
    cur.execute("""
        SELECT file_path FROM local_media
        WHERE file_path IS NOT NULL
          AND file_path != ''
          AND file_path NOT LIKE 'virtual://%'
        LIMIT 5000
    """)
    all_paths = [r[0] for r in cur.fetchall()]
    prefix_counts = defaultdict(int)
    for p in all_paths:
        # Take the first 3 path components
        parts = Path(p).parts[:3]
        prefix = "/".join(parts) if parts else p
        prefix_counts[prefix] += 1

    print("[Path Prefix Distribution (top 10)]")
    for prefix, cnt in sorted(prefix_counts.items(), key=lambda x: -x[1])[:10]:
        print(f"  {prefix}: {cnt} files")
    print()

    # --- 8. Tracks with NO media files ---
    cur.execute("""
        SELECT COUNT(*) FROM tracks t
        WHERE NOT EXISTS (SELECT 1 FROM local_media lm WHERE lm.track_id = t.id)
    """)
    orphan_tracks = cur.fetchone()[0]
    print("[Orphan Analysis]")
    print(f"  Tracks with zero LocalMedia rows: {orphan_tracks}")

    # Albums with no tracks
    cur.execute("""
        SELECT COUNT(*) FROM albums a
        WHERE NOT EXISTS (SELECT 1 FROM tracks t WHERE t.album_id = a.id)
    """)
    orphan_albums = cur.fetchone()[0]
    print(f"  Albums with zero Tracks:          {orphan_albums}")

    # Artists with no tracks
    cur.execute("""
        SELECT COUNT(*) FROM artists a
        WHERE NOT EXISTS (SELECT 1 FROM tracks t WHERE t.artist_id = a.id)
    """)
    orphan_artists = cur.fetchone()[0]
    print(f"  Artists with zero Tracks:          {orphan_artists}")
    print()

    # --- Summary ---
    print("=== SUMMARY ===")
    print(f"Your UI shows {total_media} files using {fmt_gb(total_storage_raw)}.")
    print(
        f"After deduplication, the real numbers are {deduped_file_count} files using {fmt_gb(total_storage_deduped)}."
    )
    print(
        f"That's {total_media - deduped_file_count} phantom file rows inflating storage by {fmt_gb(total_storage_raw - total_storage_deduped)}."
    )

    conn.close()


if __name__ == "__main__":
    main()
