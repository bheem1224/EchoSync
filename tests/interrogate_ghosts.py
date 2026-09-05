import os
import sqlite3
import sys
from collections import defaultdict


def main():
    db_path = r"\\KARNA\Docker\SoulSync\data\music_library.db"

    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        # Try a fallback if run locally
        fallback = os.path.join("data", "music_library.db")
        if os.path.exists(fallback):
            db_path = fallback
            print(f"Using fallback: {db_path}", file=sys.stderr)
        else:
            sys.exit(1)

    print(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM tracks")
    total_tracks = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM albums")
    total_albums = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM artists")
    total_artists = cur.fetchone()[0]

    cur.execute("SELECT file_path, file_size_bytes FROM local_media")
    rows = cur.fetchall()
    conn.close()

    total_rows = len(rows)
    print(f"Total rows in local_media: {total_rows}")
    print(f"Total rows in tracks:      {total_tracks}")
    print(f"Total rows in albums:      {total_albums}")
    print(f"Total rows in artists:     {total_artists}")

    # 1. Virtual Count
    virtual_count = sum(1 for path, _ in rows if path and path.startswith("virtual://"))
    print(f"Virtual count (paths starting with virtual://): {virtual_count}")

    # 2. Exact Duplicates
    path_counts = defaultdict(int)
    for path, _ in rows:
        if path:
            path_counts[path] += 1

    duplicate_paths = {path: count for path, count in path_counts.items() if count > 1}
    total_duplicates = sum(count - 1 for count in duplicate_paths.values())
    print(
        f"Duplicate file_path rows: {total_duplicates} (distinct paths duplicated: {len(duplicate_paths)})"
    )

    # 3. Extension Breakdown
    extension_counts = defaultdict(int)
    for path, _ in rows:
        if path:
            if path.startswith("virtual://"):
                ext = "[virtual]"
            else:
                _, ext = os.path.splitext(path.lower())
                if not ext:
                    ext = "[no_extension]"
            extension_counts[ext] += 1

    print("\nExtension Breakdown:")
    for ext, count in sorted(
        extension_counts.items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  {ext}: {count}")

    # Calculate sizes
    total_size = sum(sz for _, sz in rows if sz)
    library_size = sum(
        sz for path, sz in rows if path and path.startswith("/data/library/") and sz
    )
    ghost_size = sum(
        sz for path, sz in rows if path and path.startswith("/data/music/") and sz
    )
    other_size = total_size - library_size - ghost_size

    print("\nSize Breakdown:")
    print(
        f"  Total size in local_media:        {total_size / (1024**3):.2f} GB ({total_size} bytes)"
    )
    print(
        f"  Expected library size (/data/lib): {library_size / (1024**3):.2f} GB ({library_size} bytes)"
    )
    print(
        f"  Ghost paths size (/data/music):    {ghost_size / (1024**3):.2f} GB ({ghost_size} bytes)"
    )
    print(
        f"  Other paths size:                  {other_size / (1024**3):.2f} GB ({other_size} bytes)"
    )

    # 4. Path Anomaly Check
    # Expected folder is /data/library/
    expected_prefix = "/data/library/"
    anomalies = []
    null_zero_sizes = 0

    for path, size in rows:
        if size is None or size == 0:
            null_zero_sizes += 1

        if not path:
            anomalies.append((path, size, "NULL/Empty path"))
            continue

        if path.startswith("virtual://"):
            continue

        is_anomaly = False
        reason = ""

        # Check folder prefix
        if not path.startswith(expected_prefix):
            is_anomaly = True
            reason = f"Not in expected folder '{expected_prefix}'"
        # Check size
        elif size is None or size == 0:
            is_anomaly = True
            reason = "Size is NULL or 0"

        if is_anomaly:
            anomalies.append((path, size, reason))

    print(f"\nFiles with NULL or 0 size: {null_zero_sizes}")
    print(f"Path Anomalies Found: {len(anomalies)}")
    print("5 Examples of anomalous/weird/bloat paths:")
    for i, (path, size, reason) in enumerate(anomalies[:5]):
        print(f"  Example {i + 1}:")
        print(f"    Path:   {path}")
        print(f"    Size:   {size} bytes")
        print(f"    Reason: {reason}")


if __name__ == "__main__":
    main()
