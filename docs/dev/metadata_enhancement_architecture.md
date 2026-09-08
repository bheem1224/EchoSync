# EchoSync Metadata Enhancement Architecture & Ingress Specification

## 1. Executive Summary & Problem Statement

Metadata enhancement in EchoSync is responsible for transforming raw audio files, loose downloaded tracks, and poorly tagged library items into canonical, structured, and verified library entities. The enhancement subsystem spans audio digital signal processing (Chromaprint / AcoustID), external metadata provider synchronization (MusicBrainz, Spotify), fuzzy text matching engines, database transaction pipelines across partitioned SQLite stores (`music_library.db` and `working.db`), and native Rust file tagging via `echosync_core`.

### The Problem of Pipeline Divergence
Historically, multiple independent entry points evolved across the codebase to trigger metadata enhancement:
1. The **Auto-Importer** ingestion daemon (`services/auto_importer.py`)
2. The **Retroactive Enhancer** system job (`core/task_manager/system_jobs.py` / `services/metadata_enhancer.py`)
3. The **Manual Review Queue** single-track lookup modal (`web/routes/metadata_review.py`)
4. The **Track Management & In-Library Editing** endpoints (`web/routes/manager.py`, `web/routes/tracks.py`)

Because each caller evolved custom fallback rules, different duration handling, disparate trust thresholds, and separate database persistence logic:
- Tracks identified through the UI review modal behaved differently than tracks ingested by the auto-importer.
- AcoustID candidate selection frequently selected remix recordings, live recordings, or compilation reissues instead of canonical studio releases (a failure mode where MusicBrainz Picard succeeds).
- Database columns such as `acoustid_id` were frequently left `NULL` despite successful fingerprint queries.

This document serves as the authoritative, unified architectural reference for all metadata enhancement pathways across EchoSync.

---

## 2. Ingress Pathways & Caller Analysis

```
                                  INGRESS PATHWAYS
                                         │
     ┌───────────────────┬───────────────┴───────────────┬───────────────────┐
     │                   │                               │                   │
┌────▼─────────────┐┌────▼─────────────┐   ┌─────────────▼─────┐   ┌─────────▼─────────┐
│  Auto-Importer   ││ Retroactive Job  │   │ Manual Review UI  │   │ Manager / Tracks  │
│(services/        ││(task_manager/    │   │(web/routes/       │   │(web/routes/       │
│ auto_importer.py)││ system_jobs.py)  │   │ metadata_review)  │   │ manager, tracks)  │
└────┬─────────────┘└────┬─────────────┘   └─────────────┬─────┘   └─────────┬─────────┘
     │                   │                               │                   │
     │ Batch Grouping    │ Priority Queue (1-7)          │ Single Task ID    │ Single Track ID
     │ Directory Caching │ Chunking (50 tracks)          │ User Interactive  │ Admin Re-tag
     ▼                   ▼                               ▼                   ▼
┌──────────────────────────────────────────────────────────────────────────────────────┐
│                            services/metadata_enhancer.py                             │
│       identify_file()  /  identify_batch()  /  enhance_library_metadata()            │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.1 Ingress Pathway 1: Auto-Importer Service (`services/auto_importer.py`)

- **Primary Entry Points**:
  - `AutoImportService.scan_and_process()`: Periodic directory scanner or event-triggered ingestion run.
  - `AutoImportService.process_batch(files: list[Path])`: Core ingestion processor.
  - `AutoImportService._retry_aged_review_tasks()`: Retries pending review tasks older than 24 hours.
- **Invocation Pattern**:
  ```python
  # Batch-level grouping by parent directory for album-cache optimization
  batch_results = self.enhancer.identify_batch(dir_files_str)
  # Or single-file fallback
  metadata, confidence = self.enhancer.identify_file(path)
  ```
- **Execution Pipeline**:
  1. **System Lock & Concurrency**:
     - Acquires non-blocking `_scan_lock`.
     - Acquires blocking distributed `library_lock` with a 60-second timeout via `core.system_lock.acquire_library_lock("auto_import_batch")`.
  2. **I/O Safety Guardrails**:
     - Skips files with size `<= 64 KB` (prevents processing corrupted/partial audio).
     - Skips files with modification timestamp `<= 15 seconds` (cool-off window to prevent reading in-flight downloads).
     - Per-file deduplication lock (`_processing_lock`) and recently completed cache (`_recently_completed`).
  3. **Album-Aware Directory Grouping**:
     - Files are grouped by parent directory (`by_dir.setdefault(str(file_path.parent), []).append(file_path)`).
     - Passed to `RetroactiveEnhancer.identify_batch()`, which initializes an `album_cache` to reuse MusicBrainz release metadata across siblings in the same directory, reducing external network traffic by up to $(N-1)/N$.
  4. **Decision Gating**:
     - Read config: `metadata_enhancement.auto_import` (bool) and `metadata_enhancement.confidence_threshold` (default `0.90`).
     - If `metadata is not None` AND `confidence >= confidence_threshold` AND `auto_import == True`:
       - Invokes `self.finalize_import(file_path, metadata)`.
     - Otherwise:
       - Calls `self.enhancer.create_or_update_review_task(file_path, reason, match_data=metadata)` to stage the item into `working.db` (`ReviewTask`).
  5. **Finalization & Relocation**:
     - `finalize_import()` enforces mandatory fields (`title`, `artist`).
     - Calls `RetroactiveEnhancer.tag_file_verified(file_path, metadata)` to physically write and verify tags on disk.
     - Calculates destination path via `core.path_formatter.build_destination_path()` based on user pattern (e.g. `{Artist}/{Album}/{Title}{ext}`).
     - Enforces "Keep Both" duplicate naming (`{stem} ({counter}){ext}`) if destination exists.
     - Executes move through `Gatekeeper.authorize_and_execute()` wrapped in `suppress_path` to avoid triggering `library_watcher`.
     - Prunes empty source parent directories up to `download_dir`.
     - Updates review task status to `approved`.

---

### 2.2 Ingress Pathway 2: Retroactive Library Job (`core/task_manager/system_jobs.py`)

- **Primary Entry Points**:
  - `system_jobs.py` -> `_worker()` -> `RetroactiveEnhancer.enhance_library_metadata()`
  - `web/routes/system.py` -> `POST /api/v1/core/system/enhance/trigger` (manual invocation)
- **Invocation Pattern**:
  ```python
  enhancer = RetroactiveEnhancer()
  # Phase 1: Native Rust DSP audio fingerprinting pre-pass
  enhancer.backfill_missing_fingerprints(batch_size=50, progress_callback=update_progress)
  # Phase 2: Metadata enhancement with local cache resolution
  enhancer.enhance_library_metadata(batch_size=batch_size, check_all_files=check_all_files, limit=limit, force_refresh=force_refresh)
  ```
- **Execution Pipeline**:
  1. **Multiprocessing Worker**:
     - Dispatched as a dedicated daemon process (`multiprocessing.Process`) tracked by `ProcessOwner(OwnerType.SYSTEM_JOB)`.
  2. **Phase 1: Native Pre-pass (`backfill_missing_fingerprints`)**:
     - Scans `LocalMedia` joined with `Track` where `AudioFingerprint` is missing.
     - Computes Chromaprint fingerprints and exact audio durations using `FingerprintGenerator.generate_with_duration()`.
     - Atomically commits `AudioFingerprint` rows to prevent redundant audio decoding in Phase 2.
     - Emits `event_bus.publish("job_progress", ...)`.
  3. **Phase 2: Priority-Ranked Batch Selection**:
     - Queries `music_library.db` in short-lived sessions via `TrackRepository.get_tracks_for_enhancement()` with a strict 7-tier priority order:
       - **Priority 1**: `Artist.name` is NULL or starts with `"unknown"`
       - **Priority 2**: `Album.title` is NULL or starts with `"unknown"`
       - **Priority 3**: `Track.title` is NULL or starts with `"unknown"`
       - **Priority 4**: `Artist.name` starts with `"various artist"` and compilation performer unassigned
       - **Priority 5**: `Track.musicbrainz_id` is NULL
       - **Priority 6**: `Track.musicbrainz_id == "NOT_FOUND"` (with attempts `< 5`)
       - **Priority 7**: Other tracks needing filter requirement completion
  4. **Chunking & Bucket Separation (`CHUNK_SIZE = 50`)**:
     - Domain tracks (`EchosyncTrack`) are partitioned into three buckets:
       - `bucket_trust`: MBID already present on disk; all required tags exist.
       - `bucket_target`: MBID present; missing required tags.
       - `bucket_heavy`: No MBID; requires AcoustID and text waterfall discovery.
  5. **Resolution & Tag Writeback**:
     - Evaluates local Chromaprint cache (`resolve_canonical_from_chromaprint`).
     - Calls AcoustID `resolve_fingerprint_details`.
     - Invokes `select_best_acoustid_recording`.
     - Falls back to `search_metadata_waterfall`.
     - Writes physical tags to every associated media file via `tag_file_verified()`.
     - Resolves artist and album relationships in `TrackRepository.resolve_artists_and_albums()`.
     - Updates `metadata_status`, sets `enhanced = True`, and updates `AudioFingerprint.acoustid_id`.
     - Invokes hook filter `post_metadata_enrichment`.

---

### 2.3 Ingress Pathway 3: Manual Review Queue (`web/routes/metadata_review.py`)

- **Primary Entry Points**:
  - `POST /api/v1/review/{task_id}/lookup/acoustid` (`lookup_review_queue_item_acoustid`)
  - `POST /api/v1/review/{task_id}/lookup/musicbrainz` (`lookup_review_queue_item_musicbrainz`)
  - `POST /api/v1/review/{task_id}/lookup/isrc` (`lookup_review_queue_item_isrc`)
  - `POST /api/v1/review/{task_id}/approve` (`approve_review_queue_item`)
- **Invocation Pattern**:
  ```python
  # Step 1: Generate Chromaprint + duration
  fingerprint, duration = FingerprintGenerator.generate_with_duration(str(file_path))
  # Step 2: Query AcoustID plugin
  details = fingerprint_provider.resolve_fingerprint_details(fingerprint, duration_int)
  # Step 3: Candidate selection & fallback
  best_meta, best_mbid, _ = select_best_acoustid_recording(...)
  ```
- **Execution Pipeline**:
  1. **Immediate Fingerprint Stamping**:
     - Generates fingerprint and duration in a single pass.
     - Hydrates `EchosyncTrack` and **immediately saves `track_obj.fingerprint` into `task.track_data`** before making any outbound network requests. This guarantees that unindexed tracks have fingerprints stored in `working.db` for user-initiated AcoustID submission.
  2. **AcoustID Resolution**:
     - Calls `fingerprint_provider.resolve_fingerprint_details(fingerprint, duration_int)`.
     - Extracts `acoustid_id`, `mbids`, and `score`.
  3. **Candidate Selection & Divergence Fallback**:
     - Runs `select_best_acoustid_recording(candidate_mbids=mbids, file_duration_ms=file_dur_ms, ...)`.
     - **Critical Divergence**: If `select_best_acoustid_recording` returns no candidate (e.g. all candidates exceed the ±2000ms duration window or fail the trust gate), the route executes:
       ```python
       elif mbids:
           track_obj.musicbrainz_id = mbids[0]
           fetched = metadata_provider.get_metadata(mbids[0])
           # Unconditionally adopts mbids[0]!
       ```
  4. **Approval & Entity Promotion**:
     - When approved via `POST /{task_id}/approve`:
       - Dispatches a background job via `core.job_queue`.
       - Calls `tag_file_verified(file_path, metadata_to_tag)`.
       - Relocates file via `Gatekeeper` safe move.
       - Invokes `_import_single_file()`, which updates or inserts `Track`, `LocalMedia`, `Artist`, `Album`, `TrackArtist`, and `AudioFingerprint(media_id, chromaprint, acoustid_id)` in `music_library.db`.
       - Emits `event_bus.publish(EventType.TRACK_IMPORTED, ...)`.

---

### 2.4 Ingress Pathway 4: In-Library Track Management (`web/routes/manager.py` & `web/routes/tracks.py`)

- **Primary Entry Points**:
  - `POST /api/v1/core/manager/track/{track_id}/fetch_metadata` (`fetch_metadata`)
  - `PATCH /api/tracks/{sync_id}` (`patch_canonical_track`)
- **Execution Pipeline**:
  1. **On-Demand Library Fetch (`fetch_metadata`)**:
     - Loads `Track` from `music_library.db`.
     - Invokes `MetadataEnhancerService.identify_file(Path(track.file_path))`.
     - Stalls direct database mutation; instead creates or updates a `ReviewTask` in `working.db` with `detected_metadata`.
     - Returns the serialized task to the frontend so the user can review suggestions before disk write.
  2. **Logical Metadata Patching (`patch_canonical_track`)**:
     - Handles `PATCH /api/tracks/{sync_id}`.
     - Explicitly **rejects physical file properties** (`_PHYSICAL_FIELDS` = `file_path`, `duration`, `bitrate`, `channels`, etc.) with HTTP 400.
     - Allows logical updates to `title`, `track_number`, `disc_number`, `musicbrainz_id`, `isrc`, and `global_rating`.
     - Commits changes directly to `Track` in `music_library.db`.

---

## 3. The Cascading 5-Stage Decision Tree

Every file processed through the identification engine (`identify_file` or `enhance_library_metadata`) traverses a strict cascading waterfall:

```
[Audio File Ingestion]
        │
        ▼
[Stage 1: Native Tag & Audio DSP Extraction]
  - Fast Header Read: echosync_core.extract_metadata()
  - Embedded MBID Check ─────────────────────────────► [Pass Trust Gate?] ──YES──► [Return MBID (0.99)]
        │ (No embedded MBID)                                  │ NO
        ▼                                                     ▼
  - PCM Waveform Decoding: generate_with_duration()    [Stage Divergence Queue]
  - Multi-channel Guard (>2 channels skip)
        │
        ▼
[Stage 2: Local Chromaprint Cache Lookup]
  - Check in-memory _local_chromaprint_cache
  - Query music_library.db (Track + AudioFingerprint) ──► [Pass Trust Gate?] ──YES──► [Return Cached (0.95)]
        │ (Cache Miss)                                        │ NO
        ▼                                                     ▼
[Stage 3: AcoustID Resolution & Candidate Scoring]     [Stage Divergence Queue]
  - POST https://api.acoustid.org/v2/lookup
  - Extract acoustid_id & candidate MBIDs
  - select_best_acoustid_recording()
    ├── Duration Delta <= 2000ms
    ├── verify_title_trust_gate(min_similarity=0.60)
    └── Returns Best Candidate ───────────────────────► [Match Found?] ────────YES──► [Return AcoustID (0.95)]
        │ (No AcoustID Match)
        ▼
[Stage 4: ISRC Waterfall Resolution]
  - File tags / DB have ISRC
  - dispatch_isrc_lookup(isrc) ───────────────────────► [ISRC Hit?] ───────────YES──► [Return ISRC (0.92)]
        │ (No ISRC or Resolution Failed)
        ▼
[Stage 5: Text Fallback Search & Lucene Query]
  - Clean comparison fields: normalize_track_comparison_fields()
  - MusicBrainz Lucene Search: /recording?query=...
  - WeightedMatchingEngine(PROFILE_EXACT_SYNC)
  - Verify Trust Gate & Score >= 85.0% ───────────────► [Match Found?] ────────YES──► [Return Text (0.85)]
        │ (No MB Match)
        ▼
  - Spotify Search Fallback + ISRC Resolution ────────► [Spotify Hit?] ────────YES──► [Return Spotify (0.85)]
        │ (All Stages Failed)
        ▼
[Queue for Manual Review (confidence: 0.0)]
```

### Stage 1: Audio DSP Extraction (`generate_with_duration` vs `extract_metadata`)
- **Native Header Extraction (`echosync_core.extract_metadata`)**:
  - Parses ID3v2, Vorbis Comments, MP4 atoms, and FLAC headers without decoding audio frames.
  - Returns `title`, `artist`, `album`, `isrc`, `track_number`, `duration_ms`, `mbid`.
  - **Embedded MBID Fast-Path**: If the file already contains an embedded MusicBrainz Recording ID, queries MusicBrainz immediately. If the candidate title passes `verify_title_trust_gate`, identification short-circuits with confidence **0.99**.
- **Acoustic Fingerprint Generation (`FingerprintGenerator.generate_with_duration`)**:
  - Probes channel count via `echosync_core`. If channels $> 2$ (e.g. 5.1 surround sound), fingerprinting is aborted to prevent C-library memory faults in `fpcalc`.
  - Attempts native Rust DSP extraction (`echosync_core.fingerprint_audio(trim_silence=True)`).
  - Falls back to `acoustid.fingerprint_file(file_path)` via `fpcalc`.
  - Returns tuple: `(chromaprint_string, duration_seconds)`.

### Stage 2: Local Chromaprint Cache Lookup (`resolve_canonical_from_chromaprint`)
- Prevents external API calls when an identical audio file is already cataloged.
- Lookup flow:
  1. Checks in-memory dictionary `self._local_chromaprint_cache[chromaprint]`.
  2. Queries `music_library.db`:
     ```sql
     SELECT t.*, a.name, alb.title
     FROM tracks t
     JOIN local_media lm ON lm.track_id = t.id
     JOIN audio_fingerprints af ON af.media_id = lm.media_id
     WHERE af.chromaprint = :chromaprint
       AND t.musicbrainz_id IS NOT NULL
       AND t.musicbrainz_id NOT IN ('', 'NOT_FOUND')
     LIMIT 1;
     ```
  3. Verifies candidate title with `verify_title_trust_gate()`.
  4. On hit: returns metadata with confidence **0.95**.

### Stage 3: AcoustID Resolution & MBID Recording Selection
- Invokes AcoustID plugin HTTP client (`POST https://api.acoustid.org/v2/lookup`):
  ```json
  {
    "client": "<api_key>",
    "meta": "recordingids",
    "fingerprint": "<chromaprint>",
    "duration": "<duration_int>"
  }
  ```
- Evaluates candidate MBIDs via `select_best_acoustid_recording()`:
  - Fetches detailed recording info via `metadata_provider.get_metadata(mbid)`.
  - Validates title against baseline using `verify_title_trust_gate(min_similarity=0.60)`.
  - Calculates duration delta: `delta = abs(file_duration_ms - recording_duration_ms)`.
  - Accepts the candidate with the lowest delta where `delta <= 2000ms`.
  - On hit: stamps `acoustid_id` and returns metadata with confidence **0.95**.

### Stage 4: ISRC Waterfall Resolution
- If the track contains an ISRC code from tags or database:
  - Invokes `services.isrc_lookup_service.dispatch_isrc_lookup(isrc)`.
  - Queries MusicBrainz by ISRC (`/recording?query=isrc:<ISRC>`).
  - Falls back to Spotify API by ISRC (`track:isrc:<ISRC>`).
  - On hit: returns canonical metadata with confidence **0.92**.

### Stage 5: Text Fallback Search & Weighted Matching Engine
- Executes when fingerprinting and ISRC yield no matches.
- Cleans and normalizes strings:
  - Strips leading track numbers (`01 - `, `00. `) via regex.
  - Normalizes artist/title noise (`normalize_track_comparison_fields()`).
- MusicBrainz Lucene Search:
  - Queries `MusicBrainzClient.search_metadata(track, limit=10)`.
- Scored via `WeightedMatchingEngine(PROFILE_EXACT_SYNC)`:
  - Token-level similarity, Levenshtein distance, and duration weighting.
  - Threshold: requires score $\ge 85.0\%$.
  - Trust gate check: `verify_title_trust_gate()`.
- Secondary Fallback:
  - Queries Spotify Search API (`track:<title> artist:<artist>`).
  - Evaluates match with `WeightedMatchingEngine`.
  - If matched and Spotify track has an ISRC, redispatches to `dispatch_isrc_lookup` to obtain MusicBrainz IDs.

---

## 4. Pipeline Differences & Divergence Matrix

The four primary callers share core utility functions but diverge in critical operational behaviors:

| Operational Dimension | Auto-Importer (`auto_importer.py`) | Retroactive Enhancer (`metadata_enhancer.py`) | Review Queue UI (`metadata_review.py`) | Track Patch Route (`tracks.py`) |
| :--- | :--- | :--- | :--- | :--- |
| **Execution Context** | Background worker thread / lock | Multiprocessing daemon child | Synchronous HTTP + background task | Synchronous HTTP |
| **Batch Optimization** | Groups by parent dir; uses `identify_batch` + `album_cache` | Chunks 50 tracks; uses `_local_chromaprint_cache` | Single file only (`task_id`); no directory cache | Single track only (`sync_id`) |
| **Duration Source** | Header `duration_ms` or DSP `dur_sec` | Header, existing DB duration, or DSP `dur_sec` | DSP `dur_sec` with audio helper fallback | Unmodified (rejects physical fields) |
| **Trust Gate Enforcement** | Strict (`verify_title_trust_gate`) | Strict (`verify_title_trust_gate`) | Partial: strict in helper, **unconditional `mbids[0]` fallback** | None (user direct edit) |
| **Rejection Handling** | Creates `ReviewTask` in `working.db` | Staged to `SuggestionStagingQueue` (`working.db`) | Returns 200 with fingerprint for submission | HTTP 400 Bad Request |
| **Physical Tag Writing** | Direct via `tag_file_verified` | Direct via `tag_file_verified` | Direct via `tag_file_verified` | **None** (logical DB fields only) |
| **File Relocation** | Automated to library path pattern | None (in-place tagging only) | Automated to library path pattern | None |
| **Event Emitted** | None (relies on watcher or review) | `job_progress` | `TRACK_IMPORTED` | None |

---

## 5. Architectural Flaws & Root-Cause Analysis

### 5.1 Flaw 1: The "Remix Drift" & Canonical Misidentification (Picard vs. EchoSync)

#### The Symptom
When matching well-known studio tracks (e.g. Calvin Harris - "My Way" or Daft Punk - "Get Lucky"), EchoSync frequently assigns the track to a remix recording, karaoke version, or late compilation release, whereas MusicBrainz Picard reliably resolves the canonical studio album.

#### The Root Causes

```
                     ECHOSYNC CANDIDATE RESOLUTION (FLAWED)
                     
AcoustID Response ──► [meta="recordingids"] ──► List of MBIDs: [Remix_MBID, Original_MBID]
                                                      │
              ┌───────────────────────────────────────┴───────────────────────────────────────┐
              ▼                                                                               ▼
     Remix_MBID Evaluation                                                           Original_MBID Evaluation
  ├── Duration: 219s (Delta: 0ms)                                                 ├── Duration: 218s (Delta: 1000ms)
  ├── Trust Gate: SequenceMatcher("My Way (Club Mix)", "My Way") = 0.62 (>= 0.60) ├── Trust Gate: SequenceMatcher("My Way", "My Way") = 1.0
  └── Delta (0ms) < Current Best (inf)                                            └── Delta (1000ms) > Current Best (0ms)
              │                                                                               │
              ▼                                                                               ▼
     *** SELECTED ***                                                                     [REJECTED]
              │
              ▼
   GET /recording/{Remix_MBID}
   releases = data.get("releases")
   release = releases[0]  <── Blindly picks first release (often "Ultra EDM Comp 2017")
```

1. **AcoustID Query Scope (`meta=recordingids`)**:
   - In `plugins/EchoSync/acoustid/client.py`, EchoSync queries AcoustID with `meta="recordingids"`.
   - AcoustID returns a list of recording IDs linked to the fingerprint. These IDs are **unsorted and unweighted**; they include re-releases, remixes with identical musical stems, karaoke tracks, and bootlegs.
   - *Contrast with Picard*: Picard requests `meta="recordings releasegroups releases tracks compress"`. Picard evaluates the full release group hierarchy directly from the response.
2. **MusicBrainz `releases[0]` Blind Selection**:
   - In `plugins/EchoSync/musicbrainz/client.py` (`get_metadata()`):
     ```python
     releases = data.get("releases") or []
     if releases:
         release = releases[0] or {}
         result["album"] = release.get("title") or ""
         result["release_id"] = release.get("id") or ""
         result["date"] = release.get("date") or ""
     ```
   - MusicBrainz API `/ws/2/recording/{mbid}?inc=releases` does **not** sort releases chronologically or by status. The first entry (`releases[0]`) is frequently a budget compilation, promotional single, or regional reissue.
3. **Flawed Duration Delta Minimization (`select_best_acoustid_recording`)**:
   - `select_best_acoustid_recording` ranks candidates solely by `delta = abs(file_dur_ms - mb_dur_ms)`.
   - If a remix or radio edit happens to have a duration closer to the physical file by a few milliseconds (often due to encoder padding or differing lead-in silence), EchoSync selects the remix over the canonical studio release.
4. **Lenient Trust Gate Ratio (`min_similarity = 0.60`)**:
   - `verify_title_trust_gate` uses `difflib.SequenceMatcher.ratio() >= 0.60`.
   - Titles such as `"Song (Club Mix)"` or `"Song (Remix)"` have high token and character overlap with `"Song"`, easily exceeding 0.60.
5. **Lack of Album Cluster Voting**:
   - Picard clusters all tracks in a directory into an album group and matches them collectively against potential MusicBrainz releases. If 9 out of 10 tracks match the tracklist of a specific studio album, Picard binds all 10 tracks to that album.
   - EchoSync processes tracks in isolation without cluster voting.

---

### 5.2 Flaw 2: The `acoustid_id` NULL Phenomenon

#### The Symptom
The `audio_fingerprints` table in `music_library.db` contains records where `chromaprint` is populated, but `acoustid_id` remains `NULL`.

#### The Root Causes
1. **Legacy Method Signature Truncation**:
   - Early implementations used `fingerprint_provider.resolve_fingerprint()`, which only returned `list[str]` (MBIDs). The AcoustID track UUID returned by AcoustID's API was discarded.
2. **Null Duration Guard Bypass**:
   - AcoustID v2 API requires `duration`. In older flows, if `track.duration` was `NULL` in the database, `identify_file` and `enhance_library_metadata` passed `duration = None` or `duration = 0`.
   - `AcoustIDProvider.resolve_fingerprint_details` explicitly aborts lookup if `duration <= 0`:
     ```python
     if duration_int <= 0:
         logger.warning("Aborting AcoustID lookup: Invalid track duration (0s)")
         return {"acoustid_id": None, "mbids": [], "score": None}
     ```
3. **Asymmetric Database Writeback**:
   - In earlier iterations of `enhance_library_metadata`, when a track was resolved from the local chromaprint cache or text waterfall, `AudioFingerprint` records were either skipped or updated without setting `acoustid_id`.
   - Resolution: `FingerprintGenerator.generate_with_duration()` must always be used to extract duration directly from the audio stream if missing from database records.

---

## 6. Data Mutations, Tagging & Hook Lifecycle

### 6.1 Database Mutations Matrix

Enhancement operations touch multiple tables across two database files:

```
[Incoming Metadata]
         │
         ├───────────────────────────────────────────────────────┐
         ▼                                                       ▼
   [music_library.db]                                       [working.db]
   ├── tracks                                               ├── review_tasks
   │   ├── title, normalized_title                          │   ├── status ('pending', 'approved')
   │   ├── artist_id, album_id                              │   ├── confidence_score
   │   ├── musicbrainz_id, isrc                             │   ├── detected_metadata (JSON)
   │   └── metadata_status (JSON)                           │   └── track_data (JSON)
   ├── local_media                                          │
   │   └── file_path (relocation updates)                   └── suggestion_staging_queue
   ├── albums                                                   ├── sync_id
   │   ├── title, normalized_title                              ├── reason ('METADATA_DIVERGENCE')
   │   ├── artist_id, mb_release_id                             └── context_data (JSON)
   │   └── release_date                                         
   ├── artists                                              
   │   ├── name, normalized_name                            
   │   └── musicbrainz_id                                   
   ├── track_artists (multi-artist associations)            
   └── audio_fingerprints                                   
       ├── media_id                                         
       ├── chromaprint                                      
       └── acoustid_id                                      
```

#### Detailed Table Mutation Specifications:
1. **`tracks`**:
   - `title`: Updated with display title or canonical title.
   - `normalized_title`: Computed via `normalize_title()`.
   - `musicbrainz_id`: Assigned MBID recording UUID or stamped `"NOT_FOUND"`.
   - `isrc`: Updated with standard 12-character ISRC code.
   - `metadata_status`: JSON dictionary updated with:
     - `enhanced`: `True`
     - `enhancement_attempts`: Incremented counter
     - `compilation_performer_resolved`: Flag for various artists
     - Required plugin keys (e.g. `cjk_restored`)
2. **`audio_fingerprints`**:
   - `chromaprint`: Raw base64-like Chromaprint string.
   - `acoustid_id`: AcoustID track UUID (e.g. `848149e9-798b-4ea7-90c7-2c9e7e725068`).
   - `media_id`: Foreign key referencing `local_media.media_id`.
3. **`review_tasks` (`working.db`)**:
   - `status`: Transitions between `"pending"` and `"approved"`.
   - `confidence_score`: Float between `0.0` and `1.0`.
   - `detected_metadata`: Serialized payload of matched fields.
   - `track_data`: Domain representation including embedded Chromaprint.

---

### 6.2 Physical File Tagging Lifecycle (`services/metadata_enhancer.py`)

Physical file modification enforces a zero-trust write-and-verify roundtrip:

```
[Metadata Dictionary]
         │
         ▼
build_native_tag_payload()
  ├── TITLE = display_title (e.g. "Song (Acoustic Version)")
  ├── TSOT (Sort Title) = canonical raw title ("Song")
  ├── TIT3 / SUBTITLE / VERSION = edition string ("Acoustic Version")
  ├── ARTIST, ALBUM, ALBUMARTIST
  ├── MUSICBRAINZ_TRACKID, MUSICBRAINZ_ALBUMID
  └── ACOUSTID_ID, ISRC, DATE, TRACKNUMBER, DISCNUMBER
         │
         ▼
File Permissions Escalation
  ├── File chmod: current_mode | 0o664
  └── Directory chmod: parent_mode | 0o775
         │
         ▼
Native Rust FFI Write (echosync_core)
  └── echosync_core.write_metadata(file_path, tags_to_write)  [via lofty crate]
         │
         ▼
Readback Verification (Immediate)
  └── verified_tags = echosync_core.extract_metadata(file_path)
         │
         ├── Verified Title / Artist Match? ──YES──► Tagging Successful
         └── Mismatch / Extraction Failed?  ──NO───► Raise MetadataWriteVerificationError
```

---

### 6.3 Event Bus & Hook Manager Subsystems

#### Hook Manager Filter Hooks (`core/hook_manager.py`)
1. **`register_metadata_requirements`**:
   - Signature: `(requirements: list[str]) -> list[str]`
   - Invoked during batch selection in `get_tracks_for_enhancement()` and `enhance_library_metadata()`.
   - Plugins (such as `cjk_language_pack`) append required keys (e.g. `"cjk_restored"`). Tracks lacking these keys in `metadata_status` are flagged for re-enhancement even if previously marked `enhanced: true`.
2. **`post_metadata_enrichment`**:
   - Signature: `(track: Track) -> Track`
   - Executed immediately before committing enhanced tracks in `enhance_library_metadata()`.
   - Allows plugins to restore localized CJK titles, map aliases, and stamp custom processing metadata.

#### Event Bus Publications (`core/event_bus.py`)
1. **`TRACK_IMPORTED`**:
   - Published by: `AutoImportService.finalize_import()` and `web/routes/metadata_review.py` (`approve_review_queue_item`).
   - Consumers: `DownloadManager._on_track_imported()` (cancels duplicate active downloads), `DeduplicationService._on_track_imported()`, `AutoImportService._on_track_imported()` (evicts pending review tasks).
2. **`job_progress`**:
   - Published by: `RetroactiveEnhancer.backfill_missing_fingerprints()`.
   - Payload: `{"job_name": "retroactive_metadata_enhancement", "phase": "fingerprinting", "current": int, "total": int, "percentage": float}`.

---

## 7. Rate Limiting, RequestManager & Caching Architecture

External API integration must strictly respect upstream provider terms of service to prevent IP bans.

### 7.1 Centralized HTTP Client (`core/request_manager.py`)
- All external HTTP calls must pass through `RequestManager`.
- **Rate Limiting Engine**:
  - `GlobalRateLimiter.wait_for_url(url, requests_per_second)` enforces token-bucket pacing across threads.
  - **AcoustID**: Configured for **1.0 request/second** (`self.http.rate = RateLimitConfig(requests_per_second=1.0)`).
  - **MusicBrainz**: Configured for **1.0 request/second** with required custom User-Agent header:
    ```
    User-Agent: Echosync/0.1.0 ( https://github.com/echosync/echosync )
    ```
- **Retry & Backoff Logic (`RetryConfig`)**:
  - Max retries: 4 attempts.
  - Base backoff: 1.5 seconds; Max backoff: 15.0 seconds; Jitter: ±20%.
  - Honors `Retry-After` HTTP headers on status 429 (Too Many Requests) and 503 (Service Unavailable).

### 7.2 Multi-Tier Caching Architecture

| Cache Layer | Storage Mechanism | TTL | Key Structure | Content |
| :--- | :--- | :--- | :--- | :--- |
| **Directory Album Cache** | In-memory `dict` in `identify_batch` | Per batch run | `release_id` (MusicBrainz) | Full tracklist, disc/track numbers, artwork URL |
| **Local Chromaprint Cache** | In-memory `_local_chromaprint_cache` | Service lifecycle | Raw Chromaprint string | Canonical metadata dict + `musicbrainz_id` |
| **Plugin Query Cache** | SQLite `parsed_tracks` table | 30 days (`2592000s`) | SHA256 / method signature | Full JSON response of AcoustID and MB queries |
| **Database Fingerprint Store**| `audio_fingerprints` table | Persistent | `media_id` / `chromaprint` | `chromaprint`, `acoustid_id` |

---

## 8. Architectural Remediation Roadmap

To resolve the remix drift and ensure production parity with MusicBrainz Picard, future refactoring should implement the following enhancements:

1. **Picard-Style Release Group Scoring**:
   - In `MusicBrainzClient.get_metadata()`, replace `releases[0]` with an intelligent release selector:
     - Filter releases by `status == "Official"` (penalize `"Bootleg"` or `"Promotion"`).
     - Score release types: `Album` (+50) > `EP` (+30) > `Single` (+20) > `Compilation` (-40).
     - Sort candidate releases by `date` ascending to select the original debut release.
2. **Directory-Level Album Cluster Voting**:
   - Aggregate all AcoustID responses across files in the same directory.
   - Count candidate `release_group_id` occurrences.
   - If $>70\%$ of tracks in a directory belong to a common release group, force all tracks to bind to releases within that group.
3. **Expanded AcoustID Metadata Query**:
   - Change `payload["meta"]` in `AcoustIDProvider` from `"recordingids"` to `"recordings releasegroups releases tracks"`.
   - Parse release groups directly from AcoustID to eliminate intermediate roundtrip queries.
4. **Tightened Trust Gate Ratio**:
   - Increase `min_similarity` in `verify_title_trust_gate` from `0.60` to `0.80`.
   - Add a penalty rule for mismatched version strings (e.g. reject if candidate contains `"Remix"` but baseline does not).
5. **Unified Metadata Pipeline Engine**:
   - Deprecate individual route-level lookup logic in `web/routes/metadata_review.py`.
   - Route all single-track lookups through a unified `MetadataEnhancer.identify_track()` method to guarantee identical behavior across all four entry points.
