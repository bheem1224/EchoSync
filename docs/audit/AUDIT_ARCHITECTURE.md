# Architecture Audit Report

This report evaluates the structural boundaries and architectural adherence of the SoulSync codebase, focusing on the recent Media Manager, Suggestion Engine, and v2.1.0 Matching Engine refactors.

## 1. Boundary Violations: `providers/`

**Rule:** Providers must be "dumb". They handle their own API auth, pagination, rate-limiting, and mapping to `SoulSyncTrack` or `UserTrackInteraction`. They must not contain matching logic, duration math, or business logic.

**Findings:**
*   **`slskd/client.py`:**
    *   **Violation:** The `_process_search_responses` method includes mathematical size gating for FLAC files (`approx_bytes_per_second < 70000`) to reduce fake/transcoded files. This crosses the line into business logic/quality filtering.
    *   **Violation:** The `_parse_filename_metadata` method contains complex regex-based heuristic parsing of filenames to extract bit depth, sample rate, track number, artist, title, and album. This logic belongs in `core/matching_engine/track_parser.py`, not the provider.
*   **`spotify/client.py`:**
    *   **Adherence:** Generally adheres well. It focuses heavily on OAuth, caching, and mapping API responses to `SoulSyncTrack`. No obvious business logic or duration math observed.

## 2. Orchestration: `services/`

**Rule:** Services orchestrate between `providers/` and `core/` without hardcoding logic.

**Findings:**
*   **`match_service.py`:** Properly delegates to `WeightedMatchingEngine`, `TrackParser`, and caching mechanisms. It orchestrates the flow cleanly based on `MatchContext`.
*   **`media_manager.py`:** Cleanly orchestrates between `config_manager`, `ProviderRegistry`, `PathMapper`, and `music_database`. It avoids hardcoding provider specifics.
*   **`download_manager.py`:** Acts as the central orchestrator. It pulls the active provider via `ProviderRegistry`, generates search strategies using `text_utils`, delegates matching to `WeightedMatchingEngine`, and uses the provider purely for execution (`search`, `download`, `get_download_status`). It adheres well to the "Central Control" design principle.
*   **`sync_service.py`:** Uses `MatchService` and `download_manager`. However, it contains some provider-specific branching in `_find_track_in_media_server` (e.g., `if server_type == "jellyfin": ... class JellyfinTrackFromDB:`). This indicates a slight leak of provider specifics into the orchestration layer, though it attempts to abstract it.
*   **`user_history_service.py`:** Cleanly orchestrates between config DB (for accounts), `ProviderRegistry` (to fetch history), `working_database` (to store ratings), and `generate_deterministic_id`.

## 3. Consolidation Opportunities: `core/` & `database/`

**Rule:** Identify files that are too small or closely related and should be collapsed based on domain logic.

**Findings:**
*   **`core/path_helper.py` & `core/path_mapper.py`:** Both exist and handle path manipulations. They should be consolidated into a single `path_mapper.py` file to unify path handling logic.
*   **`database/` directory:**
    *   `database/__init__.py`, `database/music_database.py`, `database/working_database.py`, `database/config_database.py` (assumed based on memory), `database/engine.py`, `database/bulk_operations.py`. The split between `music_database.py` (Physical Media) and `working_database.py` (Operational State) is a deliberate architectural choice (as per memory) and should be maintained. However, smaller utility files like `engine.py` could potentially be merged into their respective domain files if they only contain a few helper functions.

## 4. Provider Swappability

**Rule:** All providers must strictly adhere to the base interfaces defined in `core/provider_base.py` or `core/user_history.py`. No tight couplings.

**Findings:**
*   Providers self-declare capabilities via `ProviderCapabilities`.
*   The use of `ProviderRegistry.create_instance` in services (`sync_service.py`, `media_manager.py`, `user_history_service.py`, `download_manager.py`) ensures that services interact with interfaces rather than concrete implementations.
*   **Caveat in `sync_service.py`:** The `_find_track_in_media_server` method creates dummy track objects based on the `server_type` string ("jellyfin", "navidrome", "plex"). This suggests the provider base interface for media servers might lack a standardized way to construct or represent tracks from local database hits, forcing the service to tightly couple to the specific provider types to satisfy the downstream `update_playlist` method.