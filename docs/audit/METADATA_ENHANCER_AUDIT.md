# Retroactive Metadata Enhancer Audit Report

**Date:** `2024`
**Auditor:** Jules, Principal Systems Auditor
**Component:** `services/metadata_enhancer.py`
**Issue:** The Retroactive Metadata Enhancer consistently stalls at roughly 25% (750 songs) of a 3,000+ song library. Additionally, files previously tagged with Picard (containing MBID/ISRC) are not processed properly.

## Executive Summary

The background job for enhancing library metadata is stalling due to a combination of improper error handling within a batch transaction and flawed logic for tracks that are already tagged. This report details the root causes and outlines architectural recommendations to resolve the issues.

---

## 1. The Poison Pill (Error Handling & Batching)

### Finding

The `enhance_library_metadata` method processes tracks in batches of 100 (`batch_size=100`) within a `db.session_scope()`. However, the main processing loop (`for track in tracks_to_process:`) lacks a per-track `try/except` block.

If a single track encounters an error (e.g., an obscure Mutagen parsing error in `_tagging_read(local_path)` or a network timeout), the exception propagates unhandled. This causes the entire `db.session_scope()` to rollback, discarding any progress made on the other 99 tracks in the batch. The worker thread crashes, and because the tracks were never marked as processed (neither successfully nor as failed), the system infinitely retries the exact same batch on the next job execution. This is a classic "Poison Pill" scenario, which explains why processing consistently halts at track #751.

### Architectural Recommendation

**Implement Per-Track Error Handling:**
Wrap the processing logic for each track inside the `for track in tracks_to_process:` loop with a `try/except` block. If a track fails:
1. Catch the specific error (or fallback to `Exception`).
2. Log the error details for debugging.
3. Mark the track as `"NOT_FOUND"` (or a similar failure state).
4. Increment the `enhancement_attempts` counter in the track's `metadata_status` JSON blob.
5. Use `continue` to proceed to the next track, ensuring the successful tracks in the batch are committed to the database.

---

## 2. The 'Already Tagged' Logic Flaw

### Finding

In "Step 2 (Local File Parsing)" of `enhance_library_metadata`, the system reads the physical file tags to check for an existing `musicbrainz_id` (MBID) embedded by external tools like Picard.

If an MBID is found, the code updates the track (`track.musicbrainz_id = tag_mbid`), fires plugin hooks, and immediately calls `continue` to move to the next track.

```python
if tag_mbid:
    logger.info(f"Step 2 (Local Tags): Found MBID {tag_mbid} for {local_path.name}")
    track.musicbrainz_id = tag_mbid
    if tag_isrc and not track.isrc:
        track.isrc = tag_isrc
    track = hook_manager.apply_filters('post_metadata_enrichment', track)
    total_processed += 1
    continue  # Flawed: skips the rest of the pipeline
```

By calling `continue`, the pipeline prematurely exits for that track. It skips crucial subsequent steps like fetching missing artist metadata, downloading album artwork, and establishing database relationships (e.g., querying the API to complete the database record). While it bypasses the unnecessary AcoustID and text-search phases, it also skips the necessary metadata enrichment phase.

### Architectural Recommendation

**Refine the Fast-Path Logic:**
Do not `continue` immediately after finding an embedded MBID. Instead, the logic should skip the *identification* phases (Steps 3, 4, and 5) but proceed directly to the *API lookup* phase.

1. Set `new_musicbrainz_id = tag_mbid`.
2. Allow the code to fall through to the block where `if new_musicbrainz_id:` is handled.
3. This block should query the metadata provider (`metadata_provider.get_metadata(new_musicbrainz_id)`) to fetch the full metadata payload (including album art and relationships) and update the database accordingly.

---

## 3. Looping Behavior & Limits

### Finding

The overall method is wrapped in a loop capped at 500 iterations (`MAX_ITERATIONS = 500`). With a batch size of 100, this allows processing up to 50,000 tracks per job run, which is well above the 3,000 track library size.

The hard limit is correct and necessary to prevent runaway infinite loops in the event of systemic failures. However, because of the Poison Pill issue described in Section 1, the loop never successfully advances past the failing batch. Once the Poison Pill is handled properly, the loop will naturally progress through the entire library.

### Architectural Recommendation

No changes are needed to the `MAX_ITERATIONS` logic itself. Resolving the error handling inside the batch loop will allow the iterations to proceed as intended.

---

## Conclusion

To resolve the stalled metadata enhancement job:
1. Isolate track failures by introducing a robust `try/except` block per track.
2. Correct the bypass logic for pre-tagged files so they still receive full database enrichment via the metadata API.

Implementing these two changes will ensure the background job completes reliably, even when encountering malformed files, and correctly processes libraries previously tagged with Picard.
