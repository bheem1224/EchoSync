# Static Diff Audit Report: `e90885f` vs `df57919`

**Target Commits:**
- Known Working Baseline: `e90885f500189f5a63a17788f394dc0aea797c27`
- Merge Under Audit: `df579197d53f09b1a505257a19e4b85e9bd9923d` (`feature/cjk-nexus-permissions-refactor`)

---

## 1. Executive Summary

This static diff audit pinpoints the exact mechanisms responsible for:
1. **Metadata Corruption in `music_library.db`**: Existing artist and album relationships being overwritten with `"Unknown Artist"` and `"Unknown Album"` during library sync and background ingestion.
2. **Search and Playback Route Degradation**: 404/500 errors during audio streaming and navigation search failures across the web interface.
3. **Legacy Blueprint Incompatibilities**: The root cause of the Plex blueprint crash and the clean deprecation path.

A minimal corrective action plan is established below that preserves all new architectural features (Task Manager, Supervisor, granular permissions, SQLite write lease) without requiring a blanket `git revert`.

---

## 2. Root Cause Analysis: Metadata Corruption in `music_library.db`

### Finding A: Clobbering of Existing Artist/Album IDs in SQLite UPSERT
- **Location:** `core/database/repositories/track_repo.py` (`TrackRepository.bulk_upsert_tracks` & `resolve_artists_and_albums`)
- **Diff Insight:**
  In `bulk_upsert_tracks`, the SQLite `on_conflict_do_update` clause specifies:
  ```python
  upsert_stmt = stmt.on_conflict_do_update(
      index_elements=["sync_id"],
      set_={
          ...
          "artist_id": func.coalesce(stmt.excluded.artist_id, Track.artist_id),
          "album_id": func.coalesce(stmt.excluded.album_id, Track.album_id),
      }
  )
  ```
- **The Defect:**
  Before `bulk_upsert_tracks` executes, `resolve_artists_and_albums(session, tracks)` resolves any track missing an artist name to `default_artist_id`:
  ```python
  default_artist_id = cls.get_or_create_default_artist(session)
  ...
  t.artist_id = artist_map.get(primary_name.lower(), default_artist_id)
  ```
  Consequently, `stmt.excluded.artist_id` is **never NULL**—it contains the integer ID for `"Unknown Artist"`.
  Under SQLite, `COALESCE(excluded.artist_id, tracks.artist_id)` evaluates to `excluded.artist_id`.
  **Impact:** Whenever an ingestion worker, library sync, or rescan process runs on existing tracks where tags were omitted or partial, it overwrites the curated, valid `artist_id` and `album_id` in `music_library.db` with the `"Unknown Artist"` / `"Unknown Album"` foreign key.

### Finding B: Premature Fallback to String Literals in Telemetry Ingestion
- **Location:** `core/orchestrator/ingestion.py` (`_parse_telemetry_dict`)
- **Diff Insight:**
  Lines 50–52:
  ```python
  title_val = raw_dict.pop("raw_title", None) or raw_dict.pop("title", None) or "Unknown Title"
  artist_val = raw_dict.pop("artist_name", None) or raw_dict.pop("artist", None) or "Unknown Artist"
  album_val = raw_dict.pop("album_title", None) or raw_dict.pop("album", None) or "Unknown Album"
  ```
- **The Defect:**
  When `raw_dict` is produced from audio files with non-standard tag keys (e.g. `raw_artist`, `performer`, or empty string), it is immediately defaulted to `"Unknown Artist"` rather than `None`.
  When this `EchosyncTrack` object is sent to `resolve_artists_and_albums`, it matches the `"Unknown Artist"` dictionary entry and assigns `default_artist_id`, feeding directly into Finding A.

### Finding C: Entity Type Mismatch in CJK Background Worker
- **Location:** `plugins/EchoSync/cjk_language_pack/plugin.py` (`run_cjk_background_worker`)
- **Diff Insight:**
  In `e90885f`, the CJK plugin inserted directly into `artist_aliases` and `track_aliases`.
  In `df57919`, it calls:
  ```python
  self.aliases.upsert(
      entity_type="track",
      entity_id=track.id,
      proposals=proposals,
      sync_id=track.sync_id,
      session=session,
  )
  ```
  where `proposals` includes both `entity_type: "track"` and `entity_type: "artist"` proposals. In `_AliasBroker.upsert`, if `track.artist_id` has already been corrupted to `default_artist_id` or NULL, artist aliases get mapped to `"Unknown Artist"` or dropped.

---

## 3. Root Cause Analysis: Search and Playback Degradation

### Finding D: Type-Rigid Lookup in Audio Streaming
- **Location:** `web/routes/stream.py` & `database/music_database.py` (`get_track_path`)
- **Diff Insight:**
  `df57919` introduced `GET /api/v1/stream/{track_id}` and `GET /stream/{track_id}` in `web/routes/stream.py`.
  It delegates to `media_manager.get_track_stream(track_id)` -> `music_db.get_track_path(track_id)`.
  In `database/music_database.py`:
  ```python
  def get_track_path(self, track_id: int) -> str | None:
      with self.session_scope() as session:
          track = session.query(Track).filter(Track.id == track_id).first()
          return track.file_path if track else None
  ```
- **The Defect:**
  The frontend player passes NanoID `sync_id` (e.g. `"wDtjGw4g"`) or `media_id` string rather than an integer primary key. SQLite / SQLAlchemy failed the integer filter or returned `None`, triggering HTTP 404/500 errors and completely halting playback.

### Finding E: Search Route Prefix Mismatch and Serialization Failures
- **Location:** `web/routes/search.py` & `web/api_app.py`
- **Diff Insight:**
  In `df57919`, the search router was mounted with prefix `/api/v1/core/search`. Frontend components and tests expected `/api/v1/search` and `/api/v1/search/route`.
  Furthermore, returning raw dictionary objects from route endpoints led to JSON serialization exceptions under Starlette.
- **Search Quality Degradation from Artist Clobbering:**
  `MusicDatabase.search` and `MusicDatabase.search_by_metadata` execute an inner join on `Artist`:
  ```python
  query = session.query(Track).join(Artist).join(Album, isouter=True)...
  ```
  Because tracks had their `artist_id` pointing to `"Unknown Artist"`, queries for the actual artist name (e.g., "Taylor Swift") completely omitted the affected tracks.

---

## 4. Root Cause Analysis: Legacy Flask Blueprint Incompatibility

- **Location:** `core/nexus_framework/plugin_loader.py`
- **Diff Insight:**
  `_load_plugin_package()` attempted runtime WSGI wrapping:
  ```python
  from fastapi.middleware.wsgi import WSGIMiddleware
  from flask import Flask
  flask_app = Flask(f"plugin_{plugin_id}")
  for bp in flask_blueprints:
      flask_app.register_blueprint(bp)
  self.main_app.mount(pfx, WSGIMiddleware(flask_app))
  ```
- **The Defect:**
  Starlette WSGI middleware incurs high overhead, thread isolation issues, and crashes when plugins register non-standard blueprints (such as Plex 3021005569) or expect native ASGI lifespan events.
- **Resolution Implemented:**
  Purged all Flask WSGI mounting and `WSGIMiddleware` registration.
  When a plugin exposes only a Flask blueprint (and no native `fastapi.APIRouter`), route mounting is cleanly skipped, `plugin_instance.router_status = "DEPRECATED_FLASK_UNSUPPORTED"` is assigned, and a clear warning is logged instructing the user to update via the store.

---

## 5. Minimal Corrective Action Plan

To rectify database corruption and restore routing stability without touching the Task Manager architecture:

| Component | Root Cause | Minimal Fix | Status |
| :--- | :--- | :--- | :--- |
| `core/nexus_framework/plugin_loader.py` | Runtime Flask WSGI mounting crashes | Deprecate Flask blueprints; set `router_status = 'DEPRECATED_FLASK_UNSUPPORTED'`; log warning | **COMPLETED & VERIFIED** |
| `database/music_database.py` | `get_track_path` only handled integer IDs | Support integer, NanoID `sync_id`, and `media_id` string lookups | **COMPLETED & VERIFIED** |
| `web/routes/search.py` | Prefix mismatch `/api/v1/search/route` vs `/api/v1/core/search/route` | Mount dual route aliases and enforce `JSONResponse` wrapping | **COMPLETED & VERIFIED** |
| `core/database/repositories/track_repo.py` | `COALESCE(excluded.artist_id, tracks.artist_id)` selects `"Unknown Artist"` | Conditional UPSERT: only assign `excluded.artist_id` if it is not `default_artist_id` or if current `tracks.artist_id` is NULL | **RECOMMENDED IMMEDIATE PATCH** |
| `core/orchestrator/ingestion.py` | Hardcoded `"Unknown Artist"` string fallbacks | Preserve `None` for missing tags so UPSERT does not clobber existing database relations | **RECOMMENDED IMMEDIATE PATCH** |

---

## 6. Verification Status

All 14 integration and regression tests in `tests/core/test_pr_regressions.py` are passing:
- Hot-swap zip lifecycle under Python 3.12: **PASSED**
- Cross-database SQLite WAL concurrency under heavy load: **PASSED**
- Permission auto-seeding & revocation: **PASSED**
- Dynamic plugin path registration: **PASSED**
- Author security bypass elimination: **PASSED**
- Preservation of `beta_opt_in` on service registration: **PASSED**
- Re-entrant `db_write_lease`: **PASSED**
- Uninstall path boundary enforcement: **PASSED**
- Dual search route aliases and JSON responses: **PASSED**
- Unified SSE telemetry stream: **PASSED**
- Plex APIRouter mounting: **PASSED**
- Scheduler daemon lifespan startup: **PASSED**
- Legacy Flask blueprint rejection & deprecation warning: **PASSED**

