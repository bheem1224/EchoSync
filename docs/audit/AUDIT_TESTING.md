# Testing Audit Report

This report evaluates the testing coverage and quality of the SoulSync codebase, identifying stale tests and missing integration paths across the core refactored domains.

## 1. Stale Tests

**Issue:** Tests validating deprecated logic or old schemas that no longer align with the current architecture.

**Findings in `/tests/`:**
*   **Old Database Schemas:** Tests such as `test_refactored_database_scheme.py` likely need an overhaul to verify the strict separation between `music_database.py` (Physical Media) and `working_database.py` (Operational State, including `sync_id` URN strings for tracking). Ensure the assertions accurately reflect the new split tables and schemas.
*   **Hardcoded ±4s Math:** The matching engine has migrated to a robust `WeightedMatchingEngine` with configurable scoring profiles and percentage-based gating. Any test verifying raw integer duration differences (e.g., hardcoded ±4s) instead of using the new `calculate_match` confidence score must be updated to use the new profile thresholds (e.g., `duration_tolerance_ms`).
*   **Legacy Quality Profiles:** Tests assessing download selection should rely on the `quality_profiles` configuration injected into the `DownloadManager` rather than legacy monolithic `app_config` JSON blobs.

## 2. Missing Integration Tests

**Issue:** Critical paths in `services/` that lack end-to-end integration tests.

**Findings:**
*   **`services/download_manager.py`:** Lacks a comprehensive test covering the full lifecycle: queuing a track, the background loop processing it (mocking `slskd._async_search` and `_async_download`), and the subsequent state updates to `working_database.Download`.
*   **`services/media_manager.py`:** Needs tests to verify the integration of `PathMapper` for translating remote media server paths to local paths. Furthermore, the `delete_track` flow—where it coordinates deletion from the remote provider (`delete_track`) and the local database—requires an integration test to ensure transactional safety (or correct rollback/error handling).
*   **`services/user_history_service.py`:** Requires an end-to-end test verifying `sync_baseline_history()`. This should mock the `ProviderRegistry` to return multiple active Plex accounts, simulate the provider returning a list of `UserTrackInteraction`s, and verify that ratings are correctly stored in `working_database.UserRating` using the newly generated `sync_id`.

## 3. Actionable Fixes Checklist

**Checklist of exact test files that need to be deleted, updated, or created:**

- [ ] **Delete:** Any test explicitly relying on the deprecated `app_config` JSON blob for configuration, replacing them with tests that mock `database.config_database.ConfigDatabase`.
- [ ] **Delete:** Tests associated with the legacy `MusicMatchingEngine` class in `core/matching_engine/__init__.py`.
- [ ] **Update:** `tests/test_refactored_database_scheme.py` to assert the strict boundary between `music_library.db` and `working.db`.
- [ ] **Update:** Tests in `tests/test_matching_engine_isrc.py` (and any other matching engine tests) to use `WeightedMatchingEngine` and its 5-step gating logic instead of simple fuzzy string checks or raw duration math.
- [ ] **Create:** `tests/test_download_manager_integration.py` to cover the `queue_download` -> `process_loop` -> `_update_status` lifecycle.
- [ ] **Create:** `tests/test_media_manager_integration.py` to verify `PathMapper` integration and the full `delete_track` coordination.
- [ ] **Create:** `tests/test_user_history_service.py` to test the multi-account syncing logic and insertion into the `user_ratings` table using deterministic `sync_id`s.