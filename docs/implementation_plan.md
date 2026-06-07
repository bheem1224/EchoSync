- If `local_success` is True, run `DatabaseUpdateWorker` with `identifiers_only=True`.
       - If `local_success` is False, run `DatabaseUpdateWorker` with `identifiers_only=False` (fallback to let Plex/Jellyfin populate the library).

## Verification Plan
### Automated Tests
- Run database update unit tests to ensure `bulk_import` respects the `identifiers_only` flag.

### Manual Verification
- Ask the user to run the database update and verify that `local_server` populates the library, and Plex tracks don't overwrite local metadata but successfully link their IDs.

### 3. SyncID & CJK Integration
**v2.3.0 Behavior:**
- `sync_id` was NOT a physical database column. It was a dynamically generated string property on the `SoulSyncTrack` model in `core/matching_engine/soul_sync_track.py`.
- It used the format: `ss:track:meta:{base64(artist|title)}?dur=...&isrc=...&ext=...`.
- It was crucial for linking physical `Track` objects (which might have duplicate files or move around) to `working_db.db` records (`UserTrackState`, `Download`, `UserRating`) deterministically. CJK romanization didn't exist natively but was hinted at in the matching engine.

**New Plugin Behavior (Current & Broken):**
- The new CJK plugin appears to rely heavily on `sync_id` to map romanized text back to original tracks.
- **Issue**: Because `sync_id` was stripped or ignored in the new database ingest factories, the plugins cannot reliably map external data to internal records.

### 4. Local Server Folder Scanning & Missing Metadata
**v2.3.0 Behavior:**
- The Local Server (`providers/local_server/client.py`) crawled the directory using `os.walk` and read tags using `LocalFileHandler.read_tags` (backed by `mutagen`).
- **Critical Flaw in v2.3.0**: The `get_library_tracks()` method explicitly *ignored* most tags! It only extracted `title`, `artist`, `duration_ms`, and `isrc`, passing those to `create_soul_sync_track`. Tags like `album`, `mbid`, `bitrate`, `sample_rate`, and `file_format` were discarded during the initial database import.

**New Plugin Behavior:**
- If the new Local Server plugin copied this logic, it explains why you see "pretty much all metadata is missing" after a database update, even though Picard wrote it to the file.

### 5. Retroactive Metadata Enhancer
**v2.3.0 Behavior:**
- Ran purely as an independent, on-demand service. 
- It worked around the Local Server's missing metadata flaw by querying the database for tracks where `musicbrainz_id IS NULL`, opening the physical file *again* via `mutagen`, and updating the database if it found `mbid`/`isrc`. If local tags were missing, it generated an AcoustID fingerprint and queried the MusicBrainz API.

**New Plugin Behavior (Current & Broken):**
- Was hardcoded into `system_jobs.py` to trigger automatically after *every* successful database update.
- **Issue**: Caused massive unintended API spam, throttling, and timeouts as it attempted to fingerprint and lookup 13,000+ tracks immediately after ingest.

### 6. Download Manager
**v2.3.0 Behavior:**
- Used a centralized `DownloadManager` that queued tracks, ran a waterfall search across configured providers (usually Slskd), passed candidates through the `WeightedMatchingEngine` (scoring >= 90), and dispatched `_async_download()`.

**New Plugin Behavior (Current & Broken):**
- **Issue**: Decoupling Slskd into a generic plugin broke the strict signature (`username`, `filename`, `size`) expected by the legacy Download Manager loop.

---

## Proposed Implementation Plan

### Step 1: Fix Database Update Flow & Decouple `identifiers_only`
- Modify `DatabaseUpdateWorker` and `system_jobs.py` to enforce a strict 2-step process dynamically:
  1. **Primary Pass**: Check if `Local Server` plugin is installed. If yes, run a full DB update using it. If no, select the highest priority remote media server (Plex/Jellyfin) to run the full DB update.
  2. **Secondary Pass**: Run all remaining remote media servers in `identifiers_only` mode to map their `ratingKey`s/IDs to the existing tracks.
- Ensure the ingest logic automatically prunes `ExternalIdentifiers` that are no longer returned by the remote servers.

### Step 2: Fix Local Server Metadata Extraction
- Modify the `LocalServerProvider` plugin's `get_library_tracks` method so that it passes ALL available metadata (album, mbid, bitrate, file_format, sample_rate, acoustid_id, release_year) to `create_soul_sync_track`. This eliminates the missing metadata bug out-of-the-box without relying on the enhancer.

### Step 3: Restore `sync_id` Availability
- Modify the `Track` model or the ingestion factory (`SoulSyncTrack.from_dict()`) to ensure `sync_id` is always deterministically calculated and attached to the runtime track objects.
- Evaluate adding a dedicated `sync_id` column to the `tracks` table if the CJK and Suggestion Engine plugins require fast SQL lookups on it, rather than runtime generation.

### Step 4: Stabilize Metadata Enhancer
- Keep the `RetroactiveEnhancer` completely decoupled from the automated DB update loop (already partially fixed in `system_jobs.py`).
- Ensure the enhancer strictly prioritizes local file metadata before resorting to AcoustID/MusicBrainz network calls.

### Step 5: Align Download Manager with Plugins
- Update `services/download_manager.py` to support the new `PluginProvider` abstract interface.
- Ensure the parameters passed to the `Slskd` plugin's download method are correctly mapped from the `WeightedMatchingEngine` candidate identifiers.
