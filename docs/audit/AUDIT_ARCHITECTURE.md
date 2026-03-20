# AUDIT_ARCHITECTURE.md (Redundancy & Strictness)

## 🚨 V2.1.0 CRITICAL BLOCKERS

- [ ] **Unmerged Legacy File:** `core/path_helper.py` still exists alongside `core/path_mapper.py`. The `extract_filename` and `docker_resolve_path` functions must be integrated into `core/path_mapper.py` or deleted if unused.
- [ ] **Interface Non-Compliance (`PlaylistProvider`):** The `remove_tracks_from_playlist` method in `providers/tidal/client.py` is not implemented (returns False and logs a warning). It must throw a `NotImplementedError` or implement proper write-mode playlist manipulation.
- [ ] **Tight Coupling in `sync_service.py`:** The `_find_track_in_media_server` method uses hardcoded "dummy track" hacks (`JellyfinTrackFromDB`, `NavidromeTrackFromDB`) for specific providers. This violates the `ProviderBase` abstraction. Providers must have a standardized way to construct tracks from DB hits.

## Warnings / Tech Debt

- [ ] **Consolidation Candidate (`core/`):** Several micro-files (`core/enums.py`, `core/network_utils.py`, `core/security.py`) are highly fragmented. Consider consolidating related small models or enums to reduce import overhead and directory clutter.
- [ ] **Dead Code:** Check `core/watchlist_scanner.py` and `core/personalized_playlists.py` for raw SQL query patterns that could be migrated to SQLAlchemy ORM models for better maintainability and to match the rest of the application.
