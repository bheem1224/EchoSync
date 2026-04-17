# Release Candidate Audit Report (v2.1.0 RC)

## Pillar 1: Async State & Promise Handling (Svelte UI)

**Status**: ⚠️ Minor Issues Found (Read-only documentation)

I have audited the Svelte UI components in the `webui/src/` directory for async/state safety.
*   **`webui/src/components/DownloadQueueViewer.svelte`**:
    *   **Missing try/catch in loops**: The `searchSelected()` and `deleteSelected()` functions loop over selected IDs and perform `await apiClient.post`/`.delete` inside the loop. The `try/catch` block wraps the *entire* loop rather than the individual items. If one API call fails midway through, the loop throws an exception, halts entirely, and skips processing the remaining selected items. These calls should be wrapped in individual `try/catch` blocks within the loop.
*   **`webui/src/components/MetadataReviewModal.svelte`**:
    *   **Debounce/Save Checks**: It does not use automatic debounce timeouts for typing, relying instead on manual button clicks or Enter key (`saveDraft`), which sets a `savingDraft` boolean lock. This handles unmounts safely since there are no background timers that could resolve after the component is destroyed.
    *   The async `saveDraft` and `approveAndImport` methods correctly use finally blocks to reset locking booleans (`savingDraft = false; approving = false;`).
*   **`webui/src/components/ReviewQueue.svelte`**:
    *   No issues found. Async functions like `loadQueue()` are cleanly wrapped in try/catch and use `finally` to clear `loading` state correctly.
*   *Note: Per instruction boundaries, I have not modified any Svelte UI code. These must be addressed by the frontend maintainer.*

## Pillar 2: Concurrency & Thread Leaks (Backend)

**Status**: ✅ Fixed

*   **`providers/plex/client.py` and `providers/spotify/client.py`**:
    *   Reviewed and confirmed there are no rogue `while True` loops or unmanaged thread spawns. They safely use HTTP polling and Spotipy features.
*   **`core/job_queue.py`**:
    *   The `JobQueue` locks and background workers are tightly managed. The `_finalize_job_after_run` logic ensures transient/manual jobs are pruned properly without memory leaks.
*   **`web/routes/metadata_review.py` (AcoustID Background Submission)**:
    *   **Bug found**: The `POST /api/review-queue/<id>/approve` endpoint was previously processing the file tagging and database ingestion synchronously, blocking the main Flask HTTP thread.
    *   **Fix Applied**: Refactored the `POST /approve` endpoint to instantiate a background task (`_process_approval_background`) and submit it to the `job_queue` using `interval_seconds=None` (one-off job). The API now immediately returns `HTTP 202 Accepted` with a status of `"approved_queued"`, completely removing the block from the main thread.

## Pillar 3: Stream Safety & Resource Leaks

**Status**: ✅ Fixed

*   **`web/routes/metadata_review.py` (Stream Endpoint)**:
    *   **Bug found**: The requested `GET /api/review-queue/<id>/stream` endpoint was completely missing, meaning the UI had no backend implementation to stream from.
    *   **Fix Applied**: Implemented the `GET /api/review-queue/<int:task_id>/stream` endpoint. It correctly extracts the physical file path from the database, validates its existence, and utilizes Flask's native `send_file(path, conditional=True)` function. This guarantees proper file descriptor handling and native `Accept-Ranges: bytes` support without any custom generator leaks.

## Pillar 4: Schema vs. Payload Alignment

**Status**: ✅ Fixed

*   **Payload Alignment**:
    *   `EchosyncTrack` and the payloads handled in `metadata_review.py` naturally extract `isrc` and `acoustid_id`.
    *   **Bug found**: `acoustid_id` was missing entirely from the `Track` schema in `database/music_database.py`. The matching engine relies on this for accurate identification, but it was previously only tracked in `AudioFingerprint` or lost during bulk operations if the track itself needed direct linkage.
    *   **Fix Applied**:
        1. Added `acoustid_id: Mapped[Optional[str]] = mapped_column(String)` to the `Track` ORM model.
        2. Updated the `_ensure_track_columns` startup pragma script to dynamically execute `ALTER TABLE tracks ADD COLUMN acoustid_id TEXT` on boot for existing SQLite instances.
        3. Updated `LibraryManager._upsert_track` in `database/bulk_operations.py` to persist incoming `isrc` and `acoustid_id` data onto the `Track` model during both insert and sparse update operations, ensuring alignment with the payload.