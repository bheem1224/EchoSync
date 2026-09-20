#!/usr/bin/env python
"""
tools/patch_cjk_plugin_ids.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
One-off remediation script: repair corrupt ``plugin_id`` values on
``artist_aliases`` rows that were written by the CJK Language Pack plugin.

Root Cause
----------
``_resolve_plugin_id_int()`` in ``core/nexus_framework/plugin_SDK.py`` called
``get_service_id()`` on the config database, which returns the autoincrement
primary key (``services.id``) rather than the deterministic CRC32 stored in
the ``services.plugin_id`` column.  When the CJK plugin happened to be row 575
in the ``services`` table, every alias written via ``sdk.aliases.upsert``
stamped ``plugin_id = 575`` — violating the architectural invariant that
``plugin_id`` must be:

    ``zlib.crc32(<canonical_plugin_name>.lower().encode("utf-8")) & 0xFFFFFFFF``

Fix Applied
-----------
``_resolve_plugin_id_int`` now queries ``services.plugin_id`` directly
(PR already merged).  This script repairs pre-existing corrupt rows in the
``artist_aliases`` table.

Canonical Plugin Namespace
--------------------------
    ``EchoSync.cjk_language_pack``
    (as declared in ``plugins/EchoSync/cjk_language_pack/plugin.py:L54``)

Usage
-----
    uv run tools/patch_cjk_plugin_ids.py [--dry-run] [--db PATH]

Options
-------
    --dry-run   Report how many rows would be updated without committing.
    --db PATH   Override the default music database path resolved from config.
"""

from __future__ import annotations

import argparse
import sys
import zlib
from pathlib import Path

# ── Canonical plugin identifier ──────────────────────────────────────────────
# This MUST match PLUGIN_NAMESPACE in plugins/EchoSync/cjk_language_pack/plugin.py.
# compute_plugin_crc32() lowercases before hashing — so we use the lower-cased form.
CANONICAL_NAMESPACE = "echosync.cjk_language_pack"
CORRUPT_PLUGIN_ID = 575  # The autoincrement PK that was mistakenly used

CORRECT_PLUGIN_ID: int = zlib.crc32(CANONICAL_NAMESPACE.encode("utf-8")) & 0xFFFFFFFF
ALIAS_TYPE = "cjk_variant"


def _resolve_db_path() -> Path:
    """Resolve the music database path from EchoSync's config layer."""
    try:
        # Prefer the project's own resolution logic.
        from database.music_database import get_database

        db = get_database()
        # Most EchoSync DB objects expose _db_path or a similar attribute.
        for attr in ("_db_path", "db_path", "path"):
            candidate = getattr(db, attr, None)
            if candidate:
                return Path(candidate)
    except Exception:
        pass

    try:
        from core.settings import config_manager

        path_val = config_manager.get("database.path") or config_manager.get("db_path")
        if path_val:
            return Path(path_val)
    except Exception:
        pass

    # Absolute last resort: well-known default location.
    return Path("data") / "echosync.db"


def run(db_path: Path, dry_run: bool) -> None:
    import sqlite3

    if not db_path.exists():
        print(f"[ERROR] Database not found at: {db_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Database       : {db_path}")
    print(f"Corrupt ID     : {CORRUPT_PLUGIN_ID}")
    print(f"Correct CRC32  : {CORRECT_PLUGIN_ID}  (namespace={CANONICAL_NAMESPACE!r})")
    print(f"Alias type     : {ALIAS_TYPE!r}")
    print(f"Dry-run        : {dry_run}")
    print()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()

        # ── 1. Count rows that need patching ─────────────────────────────────
        cursor.execute(
            "SELECT COUNT(*) AS n FROM artist_aliases WHERE plugin_id = ? AND alias_type = ?",
            (CORRUPT_PLUGIN_ID, ALIAS_TYPE),
        )
        affected: int = cursor.fetchone()["n"]
        print(f"Rows with plugin_id={CORRUPT_PLUGIN_ID} and alias_type={ALIAS_TYPE!r}: {affected}")

        if affected == 0:
            print("[OK] No corrupt rows found — nothing to do.")
            return

        # ── 2. Safety check: ensure the correct CRC32 is NOT already in use ──
        cursor.execute(
            "SELECT COUNT(*) AS n FROM artist_aliases WHERE plugin_id = ? AND alias_type = ?",
            (CORRECT_PLUGIN_ID, ALIAS_TYPE),
        )
        already_correct: int = cursor.fetchone()["n"]
        if already_correct:
            print(
                f"[WARN] {already_correct} rows already have the correct plugin_id={CORRECT_PLUGIN_ID}. "
                "The UPDATE below may create temporary duplicates — they will be deduplicated by the "
                "unique index on (artist_id, name, alias_type, plugin_id) if one exists."
            )

        if dry_run:
            print(f"\n[DRY-RUN] Would update {affected} row(s). No changes committed.")
            return

        # ── 3. Apply the patch ────────────────────────────────────────────────
        cursor.execute(
            "UPDATE artist_aliases SET plugin_id = ? WHERE plugin_id = ? AND alias_type = ?",
            (CORRECT_PLUGIN_ID, CORRUPT_PLUGIN_ID, ALIAS_TYPE),
        )
        updated = cursor.rowcount
        conn.commit()

        print(f"\n[OK] Updated {updated} row(s): plugin_id {CORRUPT_PLUGIN_ID} → {CORRECT_PLUGIN_ID}.")

        # ── 4. Verify ─────────────────────────────────────────────────────────
        cursor.execute(
            "SELECT COUNT(*) AS n FROM artist_aliases WHERE plugin_id = ? AND alias_type = ?",
            (CORRUPT_PLUGIN_ID, ALIAS_TYPE),
        )
        remaining: int = cursor.fetchone()["n"]
        if remaining == 0:
            print("[VERIFY] No rows remain with the corrupt plugin_id. ✓")
        else:
            print(f"[WARN] {remaining} row(s) still have plugin_id={CORRUPT_PLUGIN_ID} — investigate manually.")

    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Repair corrupt CJK plugin_id values in artist_aliases.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Report affected rows without modifying the database.",
    )
    parser.add_argument(
        "--db",
        metavar="PATH",
        default=None,
        help="Explicit path to the EchoSync music database (SQLite). "
        "If omitted, the path is resolved from the project config.",
    )
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else _resolve_db_path()
    run(db_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
