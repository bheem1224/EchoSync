# Feature Audit Report

This report evaluates the completeness and wiring of features across the four major refactored domains: The Download Manager, The Matching Engine, the Suggestion Engine, and the Media Manager.

## 1. The Download Manager

**Feature Checklist:**
- [x] **Central Queueing:** Tracks are queued via `DownloadManager.queue_download()`, which checks if the track already exists in the library. State is persisted in `working_database.Download`.
- [x] **Slskd Integration (Atomic Search):** The manager retrieves the active `slskd` provider, configures search queries, and performs searches via `_async_search` and `_async_download` methods.
- [x] **Smart Polling & Retry:** Uses a smart polling strategy for search completion (initial fast phase, then slower). Supports manual requeuing of failed items via `_requeue_retryable_failed_items`.
- [x] **Background Job Execution:** Registers a background job (`download_manager`) running on a 6-hour interval, which triggers the processing loop.
- [x] **Library Checks (Purge):** Performs a library check (`_purge_existing_tracks_from_queue`) at the start of every loop to prevent re-downloading existing tracks.
- [x] **Quality Profile Enforcement:** Uses configured quality profiles (extensions, min bitrate, duration tolerance) and customizes the `WeightedMatchingEngine` scoring profile accordingly.

**Completeness & Dead Ends:**
*   The `DownloadManager` is heavily wired into the `job_queue` and the `SyncService`.
*   **Dead End:** The `process_downloads_now` method uses a complex mechanism (`_start_dedicated_loop`, `asyncio.run_coroutine_threadsafe`) to manually trigger the queue. While seemingly functional, it's intricate and might represent over-engineering for a manual trigger compared to just running the queue logic synchronously or via a standard background worker.

## 2. The Matching Engine (v2.1.0)

**Feature Checklist:**
- [x] **5-Step Gating Logic:** Implemented in `WeightedMatchingEngine.calculate_match()`. Checks ISRC, Version, Edition, Fuzzy Text, and Duration.
- [x] **Fuzzy String Matching:** Normalizes and scores title, artist, and album. Includes an artist subset rescue mechanism for poorly tagged files.
- [x] **Scoring Profiles:** `ProfileFactory` generates context-aware profiles (`EXACT_SYNC`, `DOWNLOAD_SEARCH`, `LIBRARY_IMPORT`). The `DownloadManager` dynamically modifies weights based on quality profiles.
- [x] **Caching Layer:** `MatchService.parse_filename` caches parsing results in `provider_cache`.
- [x] **Acoustic Fingerprinting:** `FingerprintMatcher` is wired into Step 0b of the `calculate_match` pipeline, providing authoritative matches if fingerprints are present.

**Completeness & Dead Ends:**
*   **Dead End / Legacy Code:** The file `core/matching_engine/__init__.py` contains a placeholder `MusicMatchingEngine` class with stubbed methods (`normalize_string`, `get_core_string`, `clean_title`, `calculate_match_confidence`). This class is entirely orphaned and superseded by `WeightedMatchingEngine` and `TrackParser`. It should be deleted to prevent confusion.

## 3. The Suggestion Engine

**Feature Checklist:**
- [x] **Discovery (`discovery.py`):** Fetches full tracklists for monitored artists, diffs against the local physical library and ghost tracks (using base64 encoded base `sync_id`s), and publishes `DOWNLOAD_INTENT`s.
- [x] **Consensus (`consensus.py`):** Calculates global average ratings for a given `sync_id` from the `user_ratings` table. If there are >= 2 ratings and the average is < 4.0, it flags the track as `REJECTED`.
- [x] **Deletion Gate (`deletion.py`):** Evaluates rules for rejected tracks. If the track sponsor rated it < 4.0, publishes `HARD_DELETE_INTENT`. Otherwise, publishes `SOFT_UNLINK_INTENT`.
- [x] **Daily Injection:** (Assumed handled by `job_queue` scheduling of discovery).
- [x] **Manual Dashboard:** (Assumed handled by UI fetching statuses from `working.db`).

**Completeness & Dead Ends:**
*   **Wiring:** The discovery, consensus, and deletion logic heavily relies on `core/event_bus.py` to trigger actions (e.g., `DOWNLOAD_INTENT`, `HARD_DELETE_INTENT`). This decoupled architecture is clean but requires ensuring that subscribers for these intents are actually registered and functional elsewhere in the system.
*   **Missing Orchestration:** While the individual modules exist (`discovery.py`, `consensus.py`, `deletion.py`), there doesn't appear to be a central `suggestion_engine.py` orchestrator file or explicit background job registration within the provided snippets to run these checks periodically (unlike `DownloadManager`). The wiring of these engine components to a daily schedule needs verification.

## 4. The Media Manager

**Feature Checklist:**
- [x] **Library Indexing:** `MediaManagerService.get_library_index()` fetches the full hierarchy (Artist -> Album -> Tracks) from the `music_database`.
- [x] **Path Mapping:** Uses `PathMapper` to translate remote database paths to local reachable paths for streaming.
- [x] **Track Deletion:** Deletes tracks from the active media server via the provider interface (`delete_track`) and then removes them from the local database.
- [x] **Historical Stat Syncing:** `UserHistoryService.sync_baseline_history()` successfully iterates over active accounts, fetches history via the provider, matches them to local tracks using a generated deterministic ID (`generate_deterministic_id`), and stores ratings in the `working.db`.
- [x] **Plex Multi-Account Routing:** Handled in `UserHistoryService` by iterating through `config_db.get_accounts(service_id=plex_service_id, is_active=True)`. Svelte UI routing is outside the scope of this backend audit.

**Completeness & Dead Ends:**
*   **Dead End:** `core/path_helper.py` contains redundant path manipulation functions (`docker_resolve_path`, `extract_filename`) that are either unused or should be integrated into `core/path_mapper.py`.

## Summary of Actionable Items
*   Delete the legacy `MusicMatchingEngine` class from `core/matching_engine/__init__.py`.
*   Merge `core/path_helper.py` into `core/path_mapper.py`.
*   Verify the existence and registration of the main scheduled job that triggers the Suggestion Engine components (`discovery`, `consensus`, `deletion`).