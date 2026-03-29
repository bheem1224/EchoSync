# v2.4.0 Release Candidate - Architectural Compliance Audit

**Date:** March 29, 2025
**Auditor:** Jules (Principal Architect)
**Status:** ❌ FAIL (Violations Detected)

---

## Pillar 1: Provider-Agnostic Violations
**Status: ✅ PASS**

**Findings:**
A thorough scan of the `services/` directory (specifically targeting `metadata_enhancer.py`, `media_manager.py`, and `isrc_lookup_service.py`) revealed no hardcoded direct HTTP network requests.

* No instances of `requests.get()`, `httpx.get()`, or `urllib.request` were found bypassing the provider-agnostic system.
* The `isrc_lookup_service.py` correctly dispatches lookups dynamically via `ProviderRegistry.get_providers_with_capability(Capability.FETCH_METADATA)` and relies on the base `Provider` interface.

---

## Pillar 2: The Zero-Trust Plugin Sandbox
**Status: ❌ FAIL**

**Findings:**
The AST Scanner in `core/plugin_loader.py` is correctly configured to block `__import__` and `importlib` (as well as `os`, `subprocess`, `sqlite3`, and `sys`).

However, the CJK Language Pack plugin (`plugins/cjk_language_pack/`) is bypassing the core ecosystem's intended database flow:

* **Violation 1:** In `plugins/cjk_language_pack/__init__.py` (line 119) and `plugins/cjk_language_pack/plugin.py` (line 317), the plugin directly imports `TrackAlias`, `ArtistAlias`, and `get_database` from `database.music_database`.
* **Violation 2:** The plugin manually instantiates its own `db.session_scope()` block to write alias rows directly to the database. It is not using the ORM session provided by the `post_metadata_enrichment` hook payload, violating the Zero-Trust mandate that plugins must not directly alter core data structures.

---

## Pillar 3: Immutable URN Routing
**Status: ✅ PASS**

**Findings:**
The URN query stripper (`sync_id.split('?')[0]`) is strictly enforced:

* **Validation Decorators:** `database/working_database.py` correctly applies `@validates('sync_id')` to strip query parameters on all tracking tables (e.g., `User`, `UserTrackState`, `UserArtistRating`).
* **Bulk Operations:** `services/user_history_service.py` mathematically enforces the stripping before proceeding with the `_bulk_upsert_user_ratings` function (line 486).

---

## Pillar 4: Database Authority
**Status: ❌ FAIL**

**Findings:**
SQLAlchemy is still dynamically altering tables outside of the Alembic auto-migrator (`core/migrations.py`):

* **Violation 1:** In `core/database_update_worker.py` (line 57), there is a lingering call to `db.create_all()`. While the `create_all()` method itself has been gutted (it returns `pass` inside `database/music_database.py` and `database/working_database.py`), the invocation itself still exists and violates the strict `core/migrations.py` mandate.
* **Observation:** `core/migrations.py` contains raw `ALTER TABLE` execution logic (for the v2.2.0 `plex_id` rename). While functional, this pattern is flagged for review as v2.4.0+ mandates using Alembic environments for schema migrations.

---

## Pillar 5: General Stability & Bug Hunting (General Bug Hunt)
**Status: ⚠️ WARNING (Potential Issues Found)**

An aggressive scan of the new Copilot implementations surfaced the following runtime concerns:

1. **Fingerprint Deduplication (`services/library_hygiene.py`)**
   * **Ghost Track Deletion Risk:** In `_delete_track` (line 113), if the `os.remove(track.file_path)` call throws an `OSError`, the code swallows the exception (`pass`) and continues to `session.delete(track)`. This creates a race condition where the file still exists on disk but is deleted from the DB, creating true "ghost files" that will get re-imported on the next auto-scan, leading to an infinite loop of importing and deduplicating.
2. **ISRC Waterfall Engine (`services/isrc_lookup_service.py`)**
   * **Unhandled Edge Case:** The `_dispatch_isrc_via_providers` method catches general exceptions (`except Exception as exc:`) when a provider fails `provider.search_by_isrc(isrc)`. If `search_by_isrc` returns an unexpected type (like a raw dictionary instead of a `SoulSyncTrack` object), `_track_to_dict` will throw an `AttributeError` which will crash the entire waterfall, rather than failing gracefully and moving to the next provider.
3. **TrackAlias Persistence (`plugins/cjk_language_pack/__init__.py`)**
   * **Session Flush Issue:** In `_persist_track_aliases`, the plugin iterates over aliases and commits them manually. If a large batch of tracks is processed simultaneously, creating a new local database session for each track via the hook will severely exhaust the SQLite connection pool. This further underscores the need to fix the Pillar 2 violation.