# API Usage Audit for SoulSync v2.4.0

## Executive Summary

To achieve the 30% reduction in external API usage for v2.4.0, our audit has identified significant inefficiencies, primarily revolving around the classic "N+1 Query Problem" and severe underutilization of existing caching infrastructure.

**Top 3 Biggest API Offenders:**
1. **MusicBrainz (`get_metadata`, `search_metadata`)**: Heavily abused during the bulk import pipeline. A 12-track album will trigger 12 separate `search_metadata` and `get_metadata` calls because files are processed individually. The strict 1 request/sec limit makes this a massive bottleneck and rate-limit liability.
2. **AcoustID (`resolve_fingerprint_details`)**: Fired per-track during local library enhancement. Like MusicBrainz, it suffers from the N+1 problem during bulk imports, making redundant lookups for tracks that belong to the same album.
3. **Underutilization of `core.caching.ProviderCache`**: Despite having a robust, database-backed caching layer (`@provider_cache`) with TTL support, *none* of the core external metadata providers (MusicBrainz, AcoustID) are actually decorated with or utilizing this cache for their most expensive lookup operations.

---

## Detailed Findings

### 1. The N+1 Query Problem: Bulk Import Pipeline

**The Offender:** `services/auto_importer.py` & `services/metadata_enhancer.py` (via MusicBrainz/AcoustID Providers)

**The Trigger:** Per-track processing during directory scans.

**Location:**
* `services/auto_importer.py` - Lines 150-200 (`process_batch` iterates over files one by one and calls `identify_file`).
* `services/metadata_enhancer.py` - Lines 275-370 (`identify_file` performs isolated lookups).

**The Redundancy Risk:**
When `auto_importer.py` scans a directory containing a 12-track album, it passes each file individually to `metadata_enhancer.py:identify_file`.
For *every single file*, the system:
1. Generates an AcoustID fingerprint and calls `AcoustID.resolve_fingerprint`.
2. Takes the resulting MBID and calls `MusicBrainz.get_metadata`.
3. If that fails, it falls back to `MusicBrainz.search_metadata` using the filename, and then `MusicBrainz.get_metadata` on the best match.

There is no context sharing. If 12 tracks belong to the same album or artist, we query MusicBrainz 12 to 24 separate times for data that is largely identical (Album name, Release Year, Artist info). This loop easily bursts past the strict MusicBrainz 1 request/second limit.

**Architectural Recommendation:**
* **Implement Batch Processing:** Modify `auto_importer.py` to group files by directory (assuming directories represent albums) before passing them to the enhancer.
* **Pre-fetch and Cache Album Context:** If the first track in a directory identifies an MBID belonging to a specific Release/Album, fetch the *entire* Release metadata once and cache it in memory for the duration of the batch run to evaluate the remaining 11 tracks against.

---

### 2. Missing Provider Caching

**The Offender:** `providers/musicbrainz/client.py` & `providers/acoustid/client.py`

**The Trigger:** Standard API method invocations.

**Location:**
* `core/caching/provider_cache.py` (The unused infrastructure)
* `providers/musicbrainz/client.py` - Line 153 (`search_metadata`) and Line 226 (`get_metadata`)
* `providers/acoustid/client.py` - Line 89 (`resolve_fingerprint_details`)

**The Redundancy Risk:**
The system possesses a robust `ProviderCache` in `core/caching/provider_cache.py` featuring a `@provider_cache` decorator and database persistence (`music_library.db`). However, a codebase scan reveals this decorator is entirely absent from the `musicbrainz` and `acoustid` provider clients. Static metadata (like Album or Artist details fetched by MBID) is being requested over the network repeatedly, even if it was fetched 10 minutes ago.

**Architectural Recommendation:**
* **Apply Decorators:** Immediately decorate `MusicBrainz.get_metadata`, `MusicBrainz.search_metadata`, and `AcoustID.resolve_fingerprint` with `@provider_cache(ttl_seconds=...)`.
* **Optimize TTLs:** Static entity data (Artist info, Album tracks) rarely changes. Set aggressive TTLs for these endpoints (e.g., 7-30 days / `604800` to `2592000` seconds). Search query results can have shorter TTLs (e.g., 24 hours).

---

### 3. Spotify Custom Caching Architecture

**The Offender:** `providers/spotify/client.py` & `providers/spotify/cache_manager.py`

**The Trigger:** Playlist synchronization and track retrieval.

**Location:**
* `providers/spotify/cache_manager.py` (Entire file)
* `providers/spotify/client.py` - Line 674 (`get_playlist_tracks`)

**The Redundancy Risk:**
Unlike MusicBrainz, Spotify is utilizing caching, but it is using a bespoke, isolated cache manager (`SpotifyCacheManager`) specifically for playlists (`prv_spotify_playlists` table), bypassing the generic `core.caching` layer. While this is effective for playlist synchronization, standard individual track or artist lookups (`get_track`, `get_artist`) in the Spotify client are *not* cached, leading to redundant calls when users browse the UI or during matching fallbacks.

**Architectural Recommendation:**
* **Consolidate Caching:** While the specialized playlist sync cache can remain, apply the standard `@provider_cache` to `Spotify.get_track`, `Spotify.get_artist`, and `Spotify.get_album` to prevent redundant network calls for individual entity lookups.
