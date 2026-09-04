# Matching & Suggestion Engine Reference Manual

This technical specification details the complete mathematical scoring formulas, token-sort algorithms, confidence thresholds, vibe profiling vector distance models, recommendation pipelines, and automated lifecycle pruning rules used by EchoSync.

---

﻿# Matching Engine Reference

## Overview

SoulSync uses a hybrid matching engine with two main paths:

- `Tier 1`: weighted metadata matching via `WeightedMatchingEngine.calculate_match()`
- `Tier 2`: exact title + strict duration fallback via `WeightedMatchingEngine.calculate_title_duration_match()`

The matching engine is responsible for scoring candidate track pairs and returning a `MatchResult` containing:
- `confidence_score` (0-100)
- version/edition pass flags
- fuzzy text score
- duration score
- penalties, bonus values
- human-readable `reasoning`

---

## Code entry points

- `core/matching_engine/matching_engine.py`
  - `WeightedMatchingEngine.calculate_match()`
  - `WeightedMatchingEngine.calculate_title_duration_match()`
  - `_calculate_standard_match()` / `_calculate_fuzzy_text_match()`
- `core/matching_engine/scoring_profile.py`
  - `ExactSyncProfile`
  - `DownloadSearchProfile`
  - `LibraryImportProfile`
- `core/matching_engine/text_utils.py`
  - `normalize_text()`
  - `normalize_title()`
- `core/matching_engine/echo_sync_track.py`
  - `EchosyncTrack` data model
- `core/matching_engine/fingerprinting.py`
  - audio fingerprint comparisons used by the engine

---

## High-level workflow

### 1. Candidate discovery

The engine does not search the database itself. Candidate generation is handled by the playlist route and provider search infrastructure.

- `web/routes/playlists.py` performs Tier-1 and Tier-2 candidate queries
- search expansion and metadata normalization happen before the matching engine is invoked
- `WeightedMatchingEngine` receives pre-selected candidate tracks and scores them

### 2. Tier-1 matching

`calculate_match()` is the standard path. It executes the following flow:

1. ISRC fast-path
   - If both source and candidate have valid ISRCs and they match, return 100%
   - If both have valid ISRCs and they differ, return 0%
2. Fingerprint match
   - If both have fingerprints and they match, return a definitive high-confidence result
3. Version check
   - Reject hard on version mismatch (remix/live/original differences)
4. Edition check
   - Apply penalties for edition mismatch, but do not always reject
5. Fuzzy text matching
   - Compare title / artist / album with normalized fuzzy matching
6. Duration matching and bonus
   - Enforce tolerance and apply duration weighting
7. Quality bonus and plugin adjustments
   - Boost score or override duration tolerance via hooks

### 3. Tier-2 fallback

`calculate_title_duration_match()` is used when Tier-1 yields no viable candidates.

- exact normalized title match required
- duration must be within 2000ms by default
- artist is ignored
- returns 90-100% confidence when accepted
- still honors ISRC if available

---

## Scoring profiles

Profile definitions live in `core/matching_engine/scoring_profile.py`.

### Current profiles

- `ExactSyncProfile`
  - primary use: structured API metadata matching
  - metadata-heavy: title + artist + album + duration
  - no fingerprint weight
  - high threshold: `fuzzy_match_threshold = 0.90`
  - `min_confidence_to_accept = 85.0`

- `DownloadSearchProfile`
  - primary use: messy P2P/download searches
  - more tolerant text matching
  - `enforce_duration_match = True`
  - lower acceptance threshold: `70.0`

- `LibraryImportProfile`
  - primary use: local file identification / fingerprint-first matching
  - fingerprint weight is dominant
  - very lenient text expectations

### Configuration overrides

Weights and thresholds can be adjusted in `config/config.json` under `matching_profiles`.

---

## Normalization and text processing

Normalization lives in `core/matching_engine/text_utils.py`.

Key behaviors:
- Unicode normalization and accent removal
- feature-artist normalization (`feat`, `ft`, `featuring`, `x` → `&`)
- audio term stripping (`flac`, `320kbps`, `24bit`, etc.)
- title cleanup for OST/drama suffixes
- normalization hooks and skip hooks for plugins like CJK language pack

`EchosyncTrack` uses this normalization during construction so the engine generally receives cleaned metadata.

---

## Hook integration

The matching engine exposes plugin extension points. The implementation is in `core/hook_manager.py`.

### Matching engine hooks

- `scoring_modifier`
  - used in `core/matching_engine/matching_engine.py`
  - can return:
    - `force_artist_score_to_100`
    - `duration_override`
    - `boost`
  - affects both standard matching and Tier-2 title-duration matching

- `pre_normalize_text`
  - used in `core/matching_engine/text_utils.py`
  - allows plugins to transliterate or pre-process raw metadata before normalization

- `pre_normalize_title`
  - used in `core/matching_engine/text_utils.py`
  - lets plugins capture context from titles before bracket stripping

### Search-side hooks

- `search_expansion`
  - used in `web/routes/playlists.py`
  - lets plugins add alternative query strings for candidate search

- `pre_provider_search`
  - available in provider search flow
  - useful for provider-specific query adjustments

### Example plugin implementation

See `plugins/cjk_language_pack/__init__.py` for a concrete example of:
- `pre_normalize_text`
- `pre_normalize_title`
- `scoring_modifier`
- `search_expansion`

---

## Implementation pointers

Use these code locations as your primary reference:

- `core/matching_engine/matching_engine.py`
  - `WeightedMatchingEngine`
  - `MatchResult`
- `core/matching_engine/scoring_profile.py`
  - profile classes and default weights
- `core/matching_engine/text_utils.py`
  - title/artist/album normalization
- `core/matching_engine/echo_sync_track.py`
  - source/candidate track schema
- `web/routes/playlists.py`
  - candidate selection
  - dynamic duration expansion
  - Tier-1 / Tier-2 invocation
- `core/hook_manager.py`
  - hook registration and filter pipeline

---

## Notes for developers

- The engine is intentionally separated from candidate discovery. Search logic lives in `web/routes/playlists.py` and provider-specific modules.
- `calculate_match()` is the main path for metadata scoring; `calculate_title_duration_match()` is the fallback path.
- If you change normalization rules, update `text_utils.py` and `EchosyncTrack` consistently.
- If you need to add a new extensibility point, register it in `core/hook_manager.py` and document it here.

---

## Troubleshooting pointers

- If a match is rejected unexpectedly, inspect `MatchResult.reasoning`
- If a title is normalized incorrectly, check `core/matching_engine/text_utils.py`
- If plugin-driven scoring changes are required, inspect `scoring_modifier` hook implementations
- If candidate search is too broad or too narrow, inspect `web/routes/playlists.py`

---

**Document version:** aligned to current implementation

---

# Suggestion Engine

**Current snapshot:** aligned with `core/suggestion_engine/` as of April 2026.

---

## Overview

The Suggestion Engine surfaces personalized music recommendations and manages the lifecycle of tracks in the user's library based on listening behavior and audio features.

**Core philosophy:**
- **Content-based filtering** — Match user's vibe signature (tempo, energy, valence, danceability, acousticness) against available tracks
- **Playback analytics** — Identify rarely-played, trending, and stale content
- **Lifecycle automation** — Automatically delete low-rated tracks or queue quality upgrades
- **Discovery** — Surface new tracks from similar artists based on recent listening history

---

## Architecture

### Components

The suggestion engine is split into 5 focused modules:

1. **Vibe Profiler** (`vibe_profiler.py`)
   - Calculates user's "vibe signature" from recent playback history
   - Uses Spotify/Echonest audio features (tempo, energy, valence, danceability, acousticness)
   - Computes Euclidean distance between user vibe and track features
   - Zero-weight features are treated as penalties (∞ distance)

2. **Discovery** (`discovery.py`)
   - Two entry points: `suggest_from_library()` and `discover_new_tracks()`
   - Surfaces rarely-played tracks from local library matching user vibe
   - Discovers new tracks from similar artists via ListenBrainz
   - Handles near-miss suggestions (alternate editions when duration exceeds tolerance)

3. **Consensus** (`consensus.py`)
   - Maps user ratings (0.5-5.0 stars) to deletion/upgrade lifecycle actions
   - Lifecycle decisions:
     - 0.5 stars → **DELETE** at month-end
     - 1.0 star → **UPGRADE** at week-end
     - 1.5-5.0 stars → **KEEP** (neutral opinion zone)

4. **Deletion** (`deletion.py`)
   - Executes staged deletion and quality upgrade actions
   - Supports admin overrides (`admin_exempt_deletion`, `admin_force_upgrade`)
   - Publishes lifecycle events to event bus

5. **Analytics** (`analytics.py`)
   - Aggregates playback history metrics
   - Provides server-wide trending IDs and stale track detection
   - No per-user filtering (global popularity veto)

---

## Workflows

### 1. Library Suggestion (Content-Based Filtering)

**Entry point:** `suggest_from_library(user_id, limit=50)`

**Flow:**
```
1. Calculate user's Vibe Signature
   ├─ Query working.db for last 30 days of plays
   ├─ Batch-fetch ExternalIdentifiers from music.db
   ├─ Batch-fetch TrackAudioFeatures from music.db
   └─ Compute weighted average of 5 audio features

2. Identify top artists in recent history
   ├─ Query user's PlaybackHistory for 30-day window
   └─ Extract unique artist names (apply score bonus)

3. Find rarely-played tracks
   ├─ Criteria: never played OR <3 scrobbles OR not played in 90 days
   ├─ Cross-reference all tracks with PlaybackHistory
   └─ Skip already-popular tracks

4. Score each rare track
   ├─ Compute vibe distance: Euclidean distance from user vibe
   ├─ Apply artist bonus: -0.15 distance if in recent top artists
   └─ Clamp negative distances to 0.0

5. Return top N tracks
   └─ Sorted by distance (lowest = best match)
```

**Characteristics:**
- No fingerprint matching — purely metadata + audio features
- Handles missing vibe signature gracefully (returns unscored tracks)
- Playlist-safe — never surfaces content user has recently heard
- Zero-weight audio features treated as penalties (avoid incomplete data)

---

### 2. New Track Discovery

**Entry point:** `discover_new_tracks(user_id)`

**Flow:**
```
1. Identify top 3 artists from user's 30-day history
   ├─ Query working.db PlaybackHistory
   ├─ Batch-fetch ExternalIdentifiers to map to Track objects
   └─ Aggregate play counts by artist

2. Fetch similar artists from ListenBrainz
   └─ Calls lb_provider.get_similar_artists(top_3_artists)

3. Diff against local MusicDatabase
   ├─ Check by musicbrainz_id (primary)
   ├─ Fallback: title + artist exact match
   └─ Only return tracks not in library

4. Return new track list
   └─ Plain dicts (no ORM objects) to prevent detached entity errors
```

**Characteristics:**
- Server-wide discovery (not personalized by vibe)
- External dependency: ListenBrainz provider must be available
- Idempotent — same artists always produce same results (no randomization)
- Result set tuned by library imports (new tracks disappear once imported)

---

### 3. Lifecycle Management (Delete/Upgrade)

**Entry point:** `process_lifecycle_actions()`

**Flow:**
```
1. Query staged lifecycle actions
   ├─ SELECT UserTrackState WHERE lifecycle_action IN [DELETE_MONTH_END, UPGRADE_WEEK_END]
   └─ Group by sync_id to aggregate user decisions

2. Check admin overrides
   ├─ admin_exempt_deletion = True → skip deletion
   └─ admin_force_upgrade = True → always queue upgrade

3. Evaluate time gates
   ├─ DELETE_MONTH_END: queued_at < 30 days ago
   └─ UPGRADE_WEEK_END: queued_at < 7 days ago

4. Execute action
   ├─ Deletion → MediaManagerService.delete_track()
   ├─ Upgrade → DuplicateHygieneService.queue_quality_upgrade()
   └─ Clear lifecycle state after completion

5. Publish events
   └─ HARD_DELETE_INTENT or QUALITY_UPGRADE_INTENT to event_bus
```

**Characteristics:**
- Batched per sync_id (multiple users can vote on same track)
- Time-gated to prevent accidental execution
- Admin control for library curation
- Idempotent — re-execution is safe

---

### 4. Near-Miss Suggestion

**Entry point:** `recommend_near_miss(user_id, music_db_track_id, context=None)`

**When called:**
- Playlist sync loop detects `MatchResult.is_near_miss == True`
- Text match was near-perfect (title ≥0.95, artist ≥0.95) but duration exceeded strict tolerance
- Indicates alternate edition (Radio Edit, Single Mix, Club Version, etc.)

**Result:**
- Inserted into `SuggestionStagingQueue` with reason `near_miss_alternate_edition`
- Surfaced in UI for user manual review
- Not a hard match — score remains 0.0 in engine

---

## Configuration

### Runtime Settings

Located in `config.json` under `manager` section:

```json
{
  "manager": {
    "auto_delete": false,
    "auto_upgrade": false,
    "upgrade_quality_profile_id": null
  }
}
```

| Setting | Type | Default | Purpose |
| --- | --- | --- | --- |
| `auto_delete` | bool | `false` | Auto-execute staged deletions at month-end |
| `auto_upgrade` | bool | `false` | Auto-execute staged upgrades at week-end |
| `upgrade_quality_profile_id` | string or null | `null` | Which quality tier to upgrade toward (e.g., "high-bitrate") |

### Job Registration

Suggestion engine has three scheduled jobs:

1. **Daily Playlist Generation**
   - Job name: `suggestion_engine_daily_playlists`
   - Interval: 86400 seconds (24 hours)
   - Runs: `discover_new_tracks()` for top 5 artists, then generates daily mixes
   - File: `core/system_jobs.py`

2. **Lifecycle Processing** (proposed)
   - Job name: `suggestion_engine_lifecycle`
   - Interval: 3600 seconds (1 hour)
   - Runs: `process_lifecycle_actions()`
   - Only executes if `auto_delete` or `auto_upgrade` is enabled

3. **Playback Analytics** (proposed)
   - Job name: `suggestion_engine_analytics`
   - Interval: 21600 seconds (6 hours)
   - Runs: `PlaybackAnalytics.get_trending_provider_ids()` and `get_stale_provider_ids()`
   - Caches aggregated playback metrics for rapid query

---

## Customization & Extensibility

### Current State

The Suggestion Engine currently **does not expose hooks**. All scoring logic is embedded in the modules.

### How to Customize

#### 1. Vibe Signature Calculation

To change how user vibes are calculated, modify `vibe_profiler.py`:

**Current weights (equal):**
```python
features_accumulator = {
    'tempo': 0.0,
    'energy': 0.0,
    'valence': 0.0,
    'danceability': 0.0,
    'acousticness': 0.0
}
```

**Customization e.g., weight valence higher:**
```python
weights = {
    'tempo': 1.0,
    'energy': 1.0,
    'valence': 2.0,        # Higher weight
    'danceability': 1.0,
    'acousticness': 1.0
}
for feature, weight in weights.items():
    features_accumulator[feature] += raw_features[feature] * count * weight
```

#### 2. Rare Track Definition

To change what "rarely played" means, modify `discovery.py`:

**Current definition:**
```python
is_rarely_played = False
if not provider_ids:
    is_rarely_played = True  # Never played
elif p_data['total_plays'] < 3:
    is_rarely_played = True  # <3 all-time scrobbles
elif p_data['last_played'] < ninety_days_ago:
    is_rarely_played = True  # Not played in 90 days
```

**Example: stricter threshold (fewer recommendations)**
```python
# Only return tracks with <1 scrobble in last 6 months
if not provider_ids or (
    p_data['total_plays'] < 1
    and p_data['last_played'] < six_months_ago
):
    is_rarely_played = True
```

#### 3. Vibe Distance Metric

To use a different distance algorithm, replace `calculate_vibe_distance()` in `vibe_profiler.py`:

**Current: Euclidean distance with tempo normalization**
```python
distance_squared = (
    (norm_t_tempo - norm_f_tempo) ** 2 +
    (t_energy - f_energy) ** 2 +
    (t_valence - f_valence) ** 2 +
    (t_dance - f_dance) ** 2 +
    (t_acoustic - f_acoustic) ** 2
)
return math.sqrt(distance_squared)
```

**Alternative: Manhattan distance (taxicab metric)**
```python
return (
    abs(norm_t_tempo - norm_f_tempo) +
    abs(t_energy - f_energy) +
    abs(t_valence - f_valence) +
    abs(t_dance - f_dance) +
    abs(t_acoustic - f_acoustic)
)
```

**Alternative: Cosine similarity**
```python
def cosine_distance(target_vibe, track_features):
    # Treat as vectors, compute dot product / magnitudes
    # Return 1 - similarity (lower = better match)
```

#### 4. Lifecycle Thresholds

To change when deletion/upgrade is triggered, modify `consensus.py`:

**Current mapping:**
```python
if avg_score <= 1.0:
    return {"status": "DELETE_CANDIDATE", ...}
elif avg_score <= 2.0:
    return {"status": "UPGRADE_CANDIDATE", ...}
```

**Example: lower deletion threshold (require 0.5 stars, not 1.0)**
```python
if avg_score < 1.0:  # Strictly 0.5 stars only
    return {"status": "DELETE_CANDIDATE", ...}
elif avg_score <= 1.5:  # Raise upgrade threshold
    return {"status": "UPGRADE_CANDIDATE", ...}
```

#### 5. Artist Bonus Logic

To change how recent artists influence suggestions, modify `discovery.py`:

**Current:**
```python
if t.artist and t.artist.name.lower() in recent_artists_set:
    distance -= 0.15  # Fixed bonus
```

**Example: variable bonus based on play count**
```python
artist_plays = recent_artists_counts.get(t.artist.name.lower(), 0)
artist_bonus = min(0.5, artist_plays * 0.01)  # Scale with popularity
distance -= artist_bonus
```

---

### Future Hook Opportunities

If you need plugin-level customization without editing core code, these hooks could be added:

#### `suggest_from_library_filters` (proposed)
**Purpose:** Plugin can exclude tracks from suggestions based on custom logic

**Input:** Track object + user_id + vibe_signature
**Return:** Boolean (True = include, False = exclude)

**Use case:** Custom genre filters, blacklist specific artists, enforce language preferences

```python
def _on_suggest_filters(track, user_id, vibe_signature):
    # Exclude tracks from blacklisted artists
    if track.artist.name in user_blacklist:
        return False
    # Exclude non-English tracks for English-only user
    if user_language == 'en' and track.language != 'en':
        return False
    return True

hook_manager.add_filter('suggest_from_library_filters', _on_suggest_filters)
```

#### `vibe_score_adjustment` (proposed)
**Purpose:** Plugin can boost/reduce vibe scores based on custom heuristics

**Input:** Track + calculated distance + user context
**Return:** Modified distance

**Use case:** Genre matching, mood-based boosting, temporal relevance (seasonal music)

```python
def _on_vibe_boost(track, distance, user_context):
    # Seasonal boost: heavy metal in winter, pop in summer
    if is_winter and track.genre == 'Metal':
        return distance * 0.8  # Lower distance = better match
    # Temporal relevance: boost recently-added tracks
    days_since_added = (now - track.date_added).days
    if days_since_added < 30:
        return distance * 0.9
    return distance

hook_manager.add_filter('vibe_score_adjustment', _on_vibe_boost)
```

#### `lifecycle_decision` (proposed)
**Purpose:** Plugin can override lifecycle consensus for a track

**Input:** Track + consensus decision + user_ids who voted
**Return:** Modified decision dict (or original if no change)

**Use case:** Protect favorite artists from deletion, force upgrade high-profile tracks

```python
def _on_lifecycle_override(track, decision, user_ids):
    # Protect "favorite artists" from deletion
    if track.artist.name in FAVORITE_ARTISTS:
        return {"status": "KEEP", "action": "KEEP_AND_FEED_PREFERENCE_MODEL"}
    # Always upgrade tracks with >10 users voting keep
    if len(user_ids) > 10 and decision['status'] != 'DELETE_CANDIDATE':
        decision['action'] = 'UPGRADE_WEEK_END'
    return decision

hook_manager.add_filter('lifecycle_decision', _on_lifecycle_override)
```

#### `discover_new_tracks_filter` (proposed)
**Purpose:** Plugin can filter/rerank discovered tracks before returning

**Input:** List of discovered track dicts + user_id
**Return:** Filtered/reordered list

**Use case:** Prioritize certain sources, filter by language/era, boost own releases

```python
def _on_discover_filter(tracks, user_id):
    # Only return tracks from "main" releases (not remixes or bootlegs)
    filtered = [t for t in tracks if 'remix' not in t.get('title', '').lower()]
    # Prioritize classical if user listens to lots of classical
    classical_ratio = user_genre_distribution('classical')
    if classical_ratio > 0.5:
        classical_first = [t for t in filtered if t.get('genre') == 'Classical']
        return classical_first + [t for t in filtered if t.get('genre') != 'Classical']
    return filtered

hook_manager.add_filter('discover_new_tracks_filter', _on_discover_filter)
```

---

## Implementation Notes

### Batch Efficiency
- **No N+1 queries:** Vibe profiler uses batch `in_()` queries for ExternalIdentifiers and TrackAudioFeatures
- **Zero additional DB calls:** Feature aggregation happens in Python after batch fetch
- **Careful session scoping:** Cross-database queries (working.db ↔ music.db) carefully scope sessions to avoid transaction conflicts

### Near-Miss Idempotency
- `recommend_near_miss()` uses UNIQUE constraint on `(user_id, music_db_track_id, reason)`
- Duplicate suggestions are silently ignored (IntegrityError caught)
- Safe to call multiple times from playlist sync loop

### Lifecycle Staging
- User ratings are consensus-checked via `calculate_consensus()`
- Decision is *staged* in UserTrackState as `lifecycle_action`
- Execution is gated by time (`lifecycle_queued_at` < cutoff) and admin flags
- Idempotent: same staged action executed multiple times has no side effects

### Audio Feature Constraints
- Features are expected to be in `[0.0, 1.0]` range (except tempo)
- Missing or invalid features treated as infinite distance (excluded from suggestions)
- Vibe signature requires ≥1 track with complete feature vector

---

## Code Locations

### Core suggestion engine
- `core/suggestion_engine/vibe_profiler.py` — Vibe calculation and distance metrics
- `core/suggestion_engine/discovery.py` — Library suggestions and new track discovery
- `core/suggestion_engine/consensus.py` — Lifecycle consensus mapping
- `core/suggestion_engine/deletion.py` — Delete/upgrade execution
- `core/suggestion_engine/analytics.py` — Playback history aggregation

### Integration points
- `core/system_jobs.py` — Daily playlist generation job registration
- `web/routes/manager.py` — Admin lifecycle action endpoints
- `services/state_listener.py` — Listens to rating changes and triggers consensus
- `services/library_hygiene.py` — Uses analytics for duplicate detection
- `web/routes/playlists.py` — Calls `recommend_near_miss()` for near-misses

### Database schema
- `database/working_database.py` — `UserTrackState`, `UserRating`, `PlaybackHistory`, `SuggestionStagingQueue` tables
- `database/music_database.py` — `Track`, `Artist`, `TrackAudioFeatures`, `ExternalIdentifier` tables

---

## Troubleshooting

**Suggestions are empty**
- Check if user has recent playback history (≥30 days)
- Verify TrackAudioFeatures are populated in music.db
- Inspect `vibe_profiler.calculate_user_vibe()` return value (logs "No recent playback" if missing)

**Lifecycle actions not executing**
- Verify `auto_delete` or `auto_upgrade` is enabled in config
- Check `lifecycle_queued_at` timestamps (must be >7 or >30 days old)
- Review admin override flags on UserTrackState rows

**Discovery returns no results**
- ListenBrainz provider must be available and registered
- Top 3 artists must exist in local library (ExternalIdentifiers must be linked)
- Run `discover_new_tracks()` manually with logging to trace failures

**Vibe distance always infinite**
- Check if TrackAudioFeatures records exist for matched sync_ids
- Verify audio features have non-NULL values for all 5 dimensions
- If missing, they're excluded from suggestions (not an error, expected behavior)

---

**Document version:** aligned to current implementation
