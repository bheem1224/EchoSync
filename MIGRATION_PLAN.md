"""
ARCHITECTURAL MIGRATION PLAN
============================

FROM: Provider-centric (each provider owns data)
TO: Data-centric (canonical Track model, single database)

CURRENT STATE (Before Migration):
- Spotify/Tidal/Plex each have their own data models
- Providers may store data independently
- Conversion happens at boundaries
- Multiple sources of truth

TARGET STATE (After Migration):
- Single Track model (core/models.py) 
- Single database (music_database)
- Providers create/enrich tracks through database
- Progressive enrichment model

MIGRATION STEPS:
===============

PHASE 1: Foundation (DONE)
---------------------------
✅ Create core/models.py with canonical Track model
✅ Update core/plugin_system.py with new architecture
   - Add TRACK_FIELDS registry
   - Update PluginType enum (PLAYLIST_PROVIDER, LIBRARY_PROVIDER, etc.)
   - Add provides_fields/consumes_fields to PluginDeclaration
   - Add requires_auth flag

PHASE 2: Database Schema (TODO)
-------------------------------
[ ] Add canonical_tracks table to music_database.py
    - track_id (UUID, primary key)
    - JSON fields for all Track attributes
    - Indexes on: track_id, isrc, musicbrainz_recording_id, acoustid
    - Full-text search on title, artists
    
[ ] Add migration utilities:
    - migrate_existing_tracks() - convert current tracks to canonical model
    - rebuild_provider_refs() - extract provider references from existing data
    - calculate_confidence_scores() - score existing tracks

PHASE 3: Provider Adapter Layer (TODO)
-------------------------------------
[ ] Create core/provider_adapter.py
    - Base class for all provider adapters
    - Methods: create_stub(), enrich_track(), attach_ref()
    - Enforces: all operations go through music_database
    
[ ] Update each provider to use adapter:
    - spotify_client.py → SpotifyAdapter
    - tidal_client.py → TidalAdapter
    - plex_client.py → PlexAdapter
    - jellyfin_client.py → JellyfinAdapter
    - navidrome_client.py → NavidromeAdapter
    - soulseek_client.py → SoulseekAdapter
    - listenbrainz_client.py → ListenBrainzAdapter

PHASE 4: Database Update (TODO)
------------------------------
[ ] Add Track CRUD operations to music_database.py:
    - create_track(Track) → track_id
    - get_track(track_id) → Track
    - find_tracks(**filters) → List[Track]
    - update_track(track_id, **fields) → bool
    - enrich_track(track_id, **fields) → Track
    - attach_provider_ref(track_id, provider, ref) → Track
    
[ ] Add search/matching operations:
    - find_by_isrc(isrc) → Optional[Track]
    - find_by_musicbrainz_id(mbid) → Optional[Track]
    - find_by_acoustid(acoustid) → Optional[Track]
    - fuzzy_match(title, artists, album) → List[Track]

PHASE 5: Provider Migration (TODO)
---------------------------------
For EACH provider (Spotify, Tidal, Plex, Jellyfin, Navidrome, Soulseek):

[ ] Step 1: Add adapter initialization
    - Remove internal data storage
    - Initialize with music_database reference
    - Declare provides_fields/consumes_fields

[ ] Step 2: Convert data operations
    - get_playlist() → creates Track stubs, returns track_ids
    - get_track_info() → enriches existing Track with fields
    - search() → creates Track stubs for results
    - download() → updates download_status, attaches file_path

[ ] Step 3: Update tests
    - Mock music_database instead of provider
    - Test Track creation/enrichment
    - Verify provider_refs are attached correctly

PHASE 6: Migration Script (TODO)
-------------------------------
[ ] Create migration.py script:
    ```python
    def migrate_to_canonical_model():
        # 1. Create canonical_tracks table
        # 2. Export existing tracks from old schema
        # 3. Convert to Track model
        # 4. Import into canonical_tracks
        # 5. Rebuild provider_refs from old data
        # 6. Calculate initial confidence_scores
        # 7. Verify migration (count checks, spot checks)
        # 8. Backup old tables
    ```

PHASE 7: Testing & Validation (TODO)
-----------------------------------
[ ] Update all existing tests to use Track model
[ ] Add integration tests for Track lifecycle:
    - Create stub from Spotify
    - Enrich with MusicBrainz
    - Find via Soulseek
    - Download via slskd
    - Verify file matches
[ ] Performance testing:
    - 10k track import
    - 1k track fuzzy matching
    - Provider ref lookups

PHASE 8: Cleanup (TODO)
----------------------
[ ] Remove old provider-specific models
[ ] Remove duplicate database tables
[ ] Update documentation
[ ] Remove compatibility layers

COMPATIBILITY NOTES:
==================
- PluginDeclaration keeps legacy 'provides'/'consumes' fields during transition
- Old capability flags (METADATA_CAPABILITIES) remain until all providers migrated
- Database keeps old schema until migration verified

ROLLBACK PLAN:
=============
- Keep old database schema until Phase 8
- Feature flag: USE_CANONICAL_MODEL (default: False during migration)
- Each provider can be rolled back independently
- Full rollback: revert to old schema, disable adapters

TESTING STRATEGY:
================
1. Unit tests: Track model operations
2. Integration tests: End-to-end workflows with Track
3. Migration tests: Old data → new model conversion
4. Performance tests: Database queries with canonical schema
5. Regression tests: Ensure existing features still work

RISK MITIGATION:
===============
- Backup database before each phase
- Incremental migration (one provider at a time)
- Feature flags for gradual rollout
- Monitoring: track operation latency, error rates
- Rollback triggers: >5% error rate increase, >2x latency increase
"""
