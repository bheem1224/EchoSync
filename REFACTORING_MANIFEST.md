# Refactoring Manifest: SoulSync v2.0 Hardening

## Overview
This manifest outlines the architectural refactoring required to stabilize SoulSync v2.0. The focus is on standardization, memory hygiene, decoupling, and test suite reconstruction.

## Phase 1: Provider Standardization
**Goal:** Ensure all providers are "dumb" translation layers adhering to the strict `Provider` interface.

| Priority | Component | File | Issue | Action |
| :--- | :--- | :--- | :--- | :--- |
| **High** | `SpotifyClient` | `providers/spotify/client.py` | Implements custom rate limiting and token management. | Move logic to `core/provider_base.py` or `core/request_manager.py`. |
| **High** | `SlskdProvider` | `providers/slskd/client.py` | Contains duplicated `_async_search` logic and download state management. | Standardize on `ProviderBase` methods; remove custom async loops if handled by `DownloadManager`. |
| **Med** | `PlexClient` | `providers/plex/client.py` | Uses `plexapi` directly without sufficient abstraction in some methods. | Ensure all returns are strictly `SoulSyncTrack` objects. |
| **Med** | `JellyfinClient` | `providers/jellyfin/client.py` | `DeprecationWarning: sdk.http_client is deprecated`. | Switch to `core.request_manager.RequestManager`. |
| **Med** | `TidalClient` | `providers/tidal/client.py` | `DeprecationWarning: HttpClient is deprecated`. | Switch to `core.request_manager.RequestManager`. |

## Phase 2: Database & Memory Hygiene
**Goal:** Optimize database interactions and prevent memory leaks.

| Priority | Component | File | Issue | Action |
| :--- | :--- | :--- | :--- | :--- |
| **P0** | `AutoImportService` | `services/auto_importer.py` | `_get_pending_review_files` loads all ignored tasks into a `set` in memory. | Refactor to use a generator or DB-side check (e.g., `EXISTS` query) during processing. |
| **High** | `LibraryManager` | `database/bulk_operations.py` | `bulk_import` iterates over large lists. | Verify usage of `yield` / generators in callers to avoid loading thousands of tracks into RAM before import. |
| **Med** | `SyncService` | `services/sync_service.py` | `_get_all_spotify_playlists` fetches all playlists from all accounts into a list. | Implement pagination/generators for playlist fetching. |

## Phase 3: Service Coupling & Flow
**Goal:** Decouple services and ensure a unified entry point for core logic.

| Priority | Component | File | Issue | Action |
| :--- | :--- | :--- | :--- | :--- |
| **High** | `MatchService` | `core/matching_engine/match_service.py` | Core engine logic hidden deep in `core`. | **Move to `services/match_service.py`**. Treat as a first-class Service. |
| **Med** | `SyncService` | `services/sync_service.py` | Directly instantiates `SpotifyClient` for multi-account support. | Use `ProviderRegistry` to get instances, even for specific accounts if possible, or abstract account handling. |
| **Med** | `MetadataEnhancer` | `services/metadata_enhancer.py` | Direct import of `mutagen` without abstraction layer. | (Low priority) Consider wrapping tagging logic if we support other taggers later. |

## Phase 4: Critical Logic Bugs (P0)
**Goal:** Fix critical logic flaws that cause data corruption or resource exhaustion.

| Priority | Component | File | Issue | Action |
| :--- | :--- | :--- | :--- | :--- |
| **P0** | `DownloadManager` | `services/download_manager.py` | **Missing Startup Library Check**: Does not verify if queued items already exist in the library on startup. | **Implement**: On startup, query `music_library.db` for existing tracks and purge them from the download queue. |
| **P0** | `DownloadManager` | `services/download_manager.py` | **Re-download Loop**: `queue_download` only checks active downloads, not the library. | **Implement**: In `queue_download`, check `music_library.db` (Tracks table) before accepting a download request. |
| **P0** | `AutoImportService` | `services/auto_importer.py` | Memory leak in `_get_pending_review_files`. | See Phase 2. |

## Phase 5: Test Suite Reboot
**Goal:** Rebuild the test suite to match v2.0 architecture.

### Deleted Tests (Obsolete/Broken)
The following files were deleted as part of the "Burn and Rebuild" phase:
- `tests/core/test_consensus.py`
- `tests/core/test_jellyfin_client.py`
- `tests/providers/test_slskd_provider.py`
- `tests/services/test_auto_importer.py`
- `tests/services/test_download_manager.py`
- `tests/services/test_metadata_enhancer.py`
- `tests/test_disabled_providers.py`
- `tests/test_match_service_e2e.py`
- `tests/test_matching_engine_main.py`
- `tests/test_settings.py`
- `tests/test_sync_e2e.py`
- `tests/core/test_web_scan_manager.py`
- `tests/core/test_wishlist_service.py`

### Critical Path Integration Tests (To Be Written)
1.  **Full Sync Flow**: E2E test simulating a sync request -> Provider Search -> Match -> Download Queue.
2.  **Database Bulk Import**: Test `LibraryManager.bulk_import` with 10k mock tracks to verify performance and batching.
3.  **Provider Auth Flow**: Test `SpotifyClient` and others with mock tokens to ensure rate limiting and refresh logic works via `ProviderBase`.
4.  **Download Lifecycle**: Test `DownloadManager` state transitions (Queued -> Searching -> Downloading -> Completed) with a mock `DownloaderProvider`.
5.  **Metadata Identification**: Test `MetadataEnhancer` with mock AcoustID/MusicBrainz responses.
