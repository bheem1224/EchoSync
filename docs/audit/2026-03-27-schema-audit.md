# Schema Audit Report: SoulSync v2.4.0 (2026-03-27)

This document contains a comprehensive audit of the schema drift between the SQLAlchemy ORM models, actual SQLite databases, and data ingestion logic in preparation for shipping the Plugin Loader and CJK Language Pack.

## [Critical Disconnects]

### 1. `database/bulk_operations.py` (The `sync_id` Disconnect)
During bulk imports, `SoulSyncTrack` objects are converted to SQLAlchemy `Track` models in `LibraryManager._upsert_track`. However, the critical `sync_id` field is **never mapped**.
* **Creation path:** The `Track(...)` constructor does not receive the `sync_id` kwarg, even though the ORM strictly requires it.
* **Update path:** Existing tracks are not having their `sync_id` updated from `track_data.sync_id`.
* **Fallback Behavior:** In Alembic migration `4a0a9825ea5c`, there is a legacy fallback `UPDATE tracks SET sync_id = 'ss:track:legacy:' || CAST(id AS TEXT) WHERE sync_id IS NULL`. This indicates the system relies on the database row ID if missing. We must reject the track if `sync_id` is null or missing at the point of ingestion instead of allowing the database to assign a legacy fallback ID.

### 2. `database/music_database.py` (ORM vs. Alembic Alignment)
* The `Track` model correctly includes `sync_id` (String, unique, indexed) and `metadata_status` (JSON).
* The `Artist` model correctly includes `metadata_status` (JSON).
* `ParsedTrack` exists as a proper model.
* `acoustid_id` has been correctly removed from the `Track` model and exists exclusively in `AudioFingerprint`.
* **Critical Collision Risk:** Legacy raw SQL `ALTER TABLE` operations persist in the database initialization phase (`MusicDatabase._ensure_track_columns` and `MusicDatabase._ensure_external_identifier_columns`). Since we are strictly shifting to Alembic, these methods will collide and must be removed.

### 3. `database/working_database.py` (Cross-Database Relational Integrity)
* Relational integrity models that reference tracks (`UserRating`, `UserTrackState`, `Download`, `SuggestionStagingQueue`) are correctly using `sync_id` as their identifier.
* **Critical Collision Risk:** Similar to `music_database.py`, legacy raw SQL `ALTER TABLE` statements exist in `WorkingDatabase._ensure_user_track_state_columns`, `_ensure_user_rating_columns`, and `_ensure_media_server_playlist_columns`. These dynamic schema migration operations will collide with Alembic and must be removed.


## [Migration Status]

* **`774dea0fae22_drop_acoustid_id_from_tracks.py`:** Drops the `acoustid_id` column from the `tracks` table. However, it lacks a data migration step to safely move existing `acoustid_id` data from the `tracks` table over to the `audio_fingerprints` table prior to the column drop.
* **`4a0a9825ea5c_add_sync_id_to_tracks_and_parsed_tracks_.py`:** Adds the `sync_id` column to `tracks` and creates the `parsed_tracks` cache table.
* **`d2ee6f0a11f1_add_metadata_status_to_track_and_artist.py`:** Successfully adds the `metadata_status` column to both `artists` and `tracks`.


## [Surgical Action Plan]

**1. Fix `database/bulk_operations.py`**
* Modify `_upsert_track` (around lines 236-258) to explicitly pass and enforce `sync_id`:
```python
if not track_data.sync_id:
    logger.error(f"Rejecting track '{track_data.title}' due to missing sync_id")
    # Alternatively, raise an Exception or return (None, False) to reject entirely

# Update the creation path
track = Track(
    sync_id=track_data.sync_id,
    title=track_data.title,
    # ...
)

# In the update path
if track_data.sync_id is not None and track.sync_id != track_data.sync_id:
    track.sync_id = track_data.sync_id
```

**2. Fix `database/music_database.py`**
* Remove the implementation of `_ensure_track_columns(self)` and `_ensure_external_identifier_columns(self)`.
* Remove the calls to these methods in `create_all(self)`.

**3. Fix `database/working_database.py`**
* Remove the implementation of `_ensure_user_track_state_columns(self)`, `_ensure_user_rating_columns(self)`, and `_ensure_media_server_playlist_columns(self)`.
* Remove the calls to these methods in `create_all(self)`.

**4. Safely Migrate `acoustid_id` in Alembic**
* Modify migration `migrations/music/versions/774dea0fae22_drop_acoustid_id_from_tracks.py` to insert `acoustid_id` into `audio_fingerprints` before dropping it from `tracks`:
```python
# Before dropping `acoustid_id`, migrate data
op.execute('''
    INSERT INTO audio_fingerprints (track_id, fingerprint_hash, acoustid_id)
    SELECT id, 'legacy:migration:' || id, acoustid_id
    FROM tracks
    WHERE acoustid_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM audio_fingerprints WHERE track_id = tracks.id
      )
''')
# Then proceed with dropping the column
```
