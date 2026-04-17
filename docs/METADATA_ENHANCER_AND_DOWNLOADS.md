# Metadata Enhancer & Download Manager

**Current snapshot:** aligned with `services/metadata_enhancer.py`, `core/auto_importer.py`, and `services/download_manager.py` as of April 2026.

---

## Overview

The metadata pipeline consists of two independent entry points that feed into shared identification components:

1. **AutoImporter** (`core/auto_importer.py`) — Real-time file monitoring
   - Watches download/source folder for new audio files
   - Parses filenames, generates fingerprints, matches metadata
   - Auto-tags and organizes files into transfer folder
   - Runs on a configured interval via `job_queue`

2. **MetadataEnhancerService** (`services/metadata_enhancer.py`) — Retroactive batch enhancement
   - Scans local library for unidentified or incomplete tracks
   - Executes a 5-step identification pipeline
   - Populates missing metadata (MBID, ISRC, genres)
   - Runs on demand or via system jobs

3. **DownloadManager** (`services/download_manager.py`) — Download orchestration
   - Central control for download queue
   - Integrates with provider search (Slskd, etc.)
   - Uses matching engine to select best candidate
   - Polls for status and updates database

---

## Metadata Enhancement Pipeline

### Architecture

Both AutoImporter and MetadataEnhancerService use the same 5-step identification process:

```
Step 0/1: Read File Tags
    ↓ (has MBID in tags?)
Step 2: ISRC Fast-Path (if ISRC available)
    ↓ (has ISRC?)
Step 3: Stored Chromaprint (if fingerprint cached)
    ↓ (fingerprint exists?)
Step 4: Generate Chromaprint (compute new fingerprint)
    ↓ (generation succeeded?)
Step 5: Text Fallback (search by artist + title)
    ↓
Mark track with MBID or NOT_FOUND
```

### MetadataEnhancerService (Retroactive)

**Entry point:** `services/metadata_enhancer.py :: MetadataEnhancerService.enhance_library_metadata()`

Retroactive metadata enhancement for a library. Processes tracks in batches with per-session commits to keep memory flat.

#### Selection Criteria

MetadataEnhancerService selects tracks that need work:

1. **MBID identification** (primary)
   - `musicbrainz_id IS NULL` OR
   - `musicbrainz_id = "NOT_FOUND"` AND `enhancement_attempts < 5`
   - These tracks re-attempt up to 5 times to handle transient network failures

2. **Plugin metadata keys** (secondary)
   - Track has valid MBID but missing a key required by plugins
   - e.g., `register_metadata_requirements()` returns `['custom_key']`
   - Track is fast-pathed to plugin enrichment only

3. **Various Artists artist fix** (tertiary)
   - Track's artist is "Various Artist(s)" variant
   - File tags haven't been scanned yet
   - Extracts real performer from TPE1 tag before identification

#### Identification Steps

##### Step 0.5: Various Artists correction
If track artist is "Various Artist(s)", read the file's `ARTIST` tag and replace with the real performer (e.g., "Various Artist" → "Jane Doe").

##### Step 2: File tag lookup
Read ID3/Vorbis `musicbrainz_id` or `recording_id` from file. If found, skip fingerprinting.

##### Step 2.5: ISRC fast-path
If track has an ISRC (from file tag or database), use MusicBrainz's ISRC endpoint to resolve MBID directly. No fingerprinting needed.

##### Step 3: Cached chromaprint lookup
Check if this track's chromaprint is already stored in database from a previous run. If yes, resolve via AcoustID without re-reading audio file.

##### Step 4: Generate chromaprint
Generate fresh chromaprint from audio file. Then:
- **Step 4a (Chromaprint Cache Hit):** Check if identical chromaprint exists in DB
  - If sibling track has resolved MBID, reuse it (zero network calls)
  - Otherwise, query AcoustID with the chromaprint
- **Step 4b (New Chromaprint):** Store new chromaprint + AcoustID UUID in database

##### Step 5: Text fallback
If no MBID found after fingerprinting, search MusicBrainz by artist + title. Use `ExactSyncProfile` matching to select best result (≥85% confidence).

#### Post-Identification

After MBID is resolved:
1. Fetch full metadata from provider (album, genres, artist relationships)
2. Tag physical file with new MBID + ISRC
3. Apply `post_metadata_enrichment` hook
4. Commit to database

If identification failed:
- Increment `enhancement_attempts` counter
- Mark as `NOT_FOUND` (so it eventually expires after 5 retries)
- Does not block batch processing

### AutoImporter (Real-time)

**Entry point:** `core/auto_importer.py :: AutoImporter.scan_and_import()`

Monitors source folder and imports new files on a schedule. Similar to MetadataEnhancerService but simpler:
- One-shot per-file processing (no batching)
- Moves successful files to library folder
- Returns import statistics

Uses the same 5-step identification pipeline internally.

---

## Download Manager

**Entry point:** `services/download_manager.py :: DownloadManager`

Central orchestrator for music downloads. Manages the full lifecycle:

### Architecture

```
queue_download(track)
    ↓
_start_download_loop (async)
    ↓
_execute_waterfall_search_and_download
    ├─ For each download strategy:
    │   └─ _invoke_provider_search (with search_expansion hook)
    │       ├─ pre_provider_search hook
    │       └─ Provider search + matching
    └─ Best candidate → download
        ↓
    _poll_download_loop
        └─ Monitor progress, update DB
```

### Download Pipeline

1. **Queueing** — Track added to `downloads` table with `queued` status
2. **Strategy Selection** — Waterfall through quality tiers + search strategies
3. **Provider Search** — For each strategy, invoke provider with query variants
4. **Candidate Evaluation** — Match results against target track
5. **Download Execution** — Send best result to provider (Slskd)
6. **Status Monitoring** — Poll provider for completion
7. **Persistence** — Update database with status/path

### Search Expansion

When searching a provider, the download manager invokes `pre_provider_search` hook:

```python
query_or_queries = hook_manager.apply_filters(
    'pre_provider_search',
    query,
    strategy_name=strategy_name,
    artist_name=target_track.artist_name,
    title=target_track.title,
)
```

This allows plugins to:
- Expand a single query into multiple variants (e.g., CJK plugin returns both Hanzi and romanized versions)
- Return a list of query strings
- Deduplication is automatic

### Quality Profiles & Tier Filtering

Downloads respect user-configured quality preferences:

- Tier 1: User-preferred format (e.g., "FLAC")
- Tier 2: Acceptable alternative (e.g., "MP3 320")
- Tier 3: Fallback (e.g., "MP3 128")

Engine filters candidates by format before matching.

### Matching Engine Integration

Uses `PROFILE_DOWNLOAD_SEARCH`:
- More lenient text matching (handles messy filenames)
- Duration as "BS detector" (>5s off = likely wrong)
- `enforce_duration_match = True` — rejects outside tolerance before scoring

---

## Hooks

### Current hooks used

#### `register_metadata_requirements` (Metadata Enhancer)
**Location:** `services/metadata_enhancer.py` line 156

**Type:** Filter returning a list of strings

**Purpose:** Plugin declares which metadata keys it requires in `track.metadata_status`

**Return:** List of string keys (e.g., `['cjk_context', 'lyrics_fetched']`)

**Usage:**
```python
required_keys = hook_manager.apply_filters('register_metadata_requirements', [])
```

**Called:** Once per enhancement batch to determine which tracks need plugin enrichment

---

#### `post_metadata_enrichment` (Metadata Enhancer)
**Location:** `services/metadata_enhancer.py` lines 351, 421, 615

**Type:** Filter that transforms a Track object

**Purpose:** Plugin can modify track after MBID is identified and full metadata is fetched

**Input:** SQLAlchemy `Track` object (session-attached)

**Return:** Modified `Track` object (or same object if unchanged)

**Usage:**
```python
flag_modified(track, "metadata_status")
track = hook_manager.apply_filters('post_metadata_enrichment', track)
session.commit()
```

**Common use cases:**
- Add plugin-specific metadata (genres, lyrics, cover art links)
- Stamp `metadata_status` keys to mark completion
- Add relationships to other objects

**Important:** Hook receives a session-attached Track. If the hook returns a different object, it must be session-aware.

---

#### `pre_normalize_text` (Metadata Enhancer)
**Location:** `services/metadata_enhancer.py` line 735

**Type:** Filter transforming a query string

**Purpose:** Plugin transliterates or pre-processes search queries before sending to metadata provider

**Input:** Raw search query string (e.g., filename or normalized artist+title)

**Return:** Processed query string (or list of strings for expansion)

**Usage:**
```python
query = hook_manager.apply_filters('pre_normalize_text', raw_query)
```

**Example:** CJK plugin converts "望天涯" → ["望天涯", "wang tian ya"] for dual-script search

---

#### `pre_provider_search` (Download Manager)
**Location:** `services/download_manager.py` line 170

**Type:** Filter expanding a single query into variants

**Purpose:** Plugin adds alternative query strings before sending to download provider

**Input:** Query string + context
```python
query,
strategy_name=strategy_name,
artist_name=target_track.artist_name,
title=target_track.title,
```

**Return:** String or list of strings (deduplication automatic)

**Usage:**
```python
query_or_queries = hook_manager.apply_filters(
    'pre_provider_search',
    query,
    strategy_name=strategy_name,
    artist_name=getattr(target_track, 'artist_name', ""),
    title=getattr(target_track, 'title', ""),
)
queries = query_or_queries if isinstance(query_or_queries, list) else [query_or_queries]
```

**Short-circuit behavior:** If a high-confidence match (≥90%) is found on any variant, remaining variants are skipped.

---

## Download Strategy Skip Hooks

The download manager has **3 default search strategies** that are tried in waterfall order:

1. **artist+title** — Most specific, highest accuracy
2. **album+title** — Useful when artist has many versions
3. **title+strict-duration** — Broadest, with stricter duration tolerance

Each strategy is passed to the `pre_provider_search` hook, which allows plugins to skip strategies that don't apply to their metadata.

### Skip mechanism

Plugins implement skip behavior by returning an **empty list `[]`** from the `pre_provider_search` hook when a strategy should not be used:

```python
def _on_pre_provider_search(query, strategy_name="", **context):
    # Skip a strategy by returning empty list
    if strategy_name == "album+title" and some_condition(query):
        logger.debug(f"Skipping {strategy_name} for this query")
        return []  # <-- Empty list = skip this strategy
    
    # Otherwise, return expanded queries as normal
    return [query] or list_of_variants
```

**Flow:**
```
For each strategy (artist+title, album+title, title+...):
    expanded = pre_provider_search(query, strategy_name=..., ...)
    if not expanded:  # Empty list or falsy
        continue     # Skip to next strategy
    search_provider(expanded)
```

### Example: CJK Strategy Skipping

The CJK Language Pack skips the `album+title` strategy for CJK queries because P2P servers rarely tag CJK tracks by album name:

```python
def _on_pre_provider_search(query, strategy_name="", **kwargs):
    _probe = query if isinstance(query, str) else " ".join(str(q) for q in (query or []))
    
    # Skip album+title for CJK to avoid wasting HTTP requests
    if strategy_name == "album+title" and _has_cjk(_probe):
        logger.debug("Pruning album+title strategy for CJK query %r", query)
        return []  # <-- Skip this strategy
    
    # For other strategies, expand normally
    if _has_cjk(query):
        return _expand_query(query, ...)
    
    return query  # No expansion needed
```

**Benefit:** Avoids wasted network calls on strategies that never work for CJK metadata.

### Plugin skip patterns

#### Skip based on metadata characteristics
```python
def _on_pre_provider_search(query, strategy_name="", artist_name="", title="", **context):
    # Skip strategies that don't apply to this metadata
    if strategy_name == "album+title" and not album_has_value:
        return []
    if strategy_name == "artist+broad+filter" and artist_is_various:
        return []
    return query or []  # Return expanded or delegate
```

#### Skip based on provider capabilities
```python
def _on_pre_provider_search(query, **context):
    provider = context.get('provider')  # If available in context
    strategy = context.get('strategy_name')
    
    # Skip strategies not supported by this provider
    if provider == 'slskd' and strategy == 'title+strict-duration':
        return []  # Slskd doesn't support strict filters
    
    return query
```

#### Skip and substitute
```python
def _on_pre_provider_search(query, strategy_name="", **context):
    if strategy_name == "artist+title":
        # Skip default artist+title, return custom variant instead
        return [f"custom_prefix {query}"]  # Still returns a list
    
    return query
```

### Default strategy names

When registering your skip logic, use these exact strategy names:

| Strategy | Name | Use case |
| --- | --- | --- |
| Artist + Title | `artist+title` | Most specific, primary strategy |
| Album + Title | `album+title` | Fallback when artist is ambiguous |
| Title + Strict Duration | `title+strict-duration` | Broadest search with tighter duration gate |
| Artist + Broad + Filter | `artist+broad+filter` | Power-user fallback: artist-only search + client-side filename filter |

---

### Future hooks (not yet implemented)

Candidates for future enhancements:

#### `pre_identification_check` (proposed)
**Purpose:** Plugin can pre-screen tracks before entering identification pipeline

**Input:** `EchosyncTrack` object or file path

**Return:** Boolean (True = proceed with identification, False = skip)

**Use case:** Skip identified-as-spam tracks or demo versions

---

#### `post_provider_search` (proposed)
**Purpose:** Plugin can re-filter or re-rank search results before matching

**Input:** List of candidate tracks + target track

**Return:** Filtered/reordered list

**Use case:** Downrank results from certain sources or upgrade results matching user preferences

---

#### `on_download_complete` (proposed)
**Purpose:** Plugin hook fires when a download finishes

**Input:** Download ID, local path, metadata

**Return:** None (informational only)

**Use case:** Trigger cover art fetch, lyrics indexing, library organization

---

#### `on_identification_failed` (proposed)
**Purpose:** Plugin can attempt custom identification if standard pipeline fails

**Input:** File path, failed attempts metadata

**Return:** Metadata dict or None

**Use case:** Custom fingerprint matching, OCR-based identification, user-playlist heuristics

---

### Strategy Skip Hooks (Query Expansion Pattern)

Rather than explicit "skip" hooks, skip logic is implemented through the `pre_provider_search` hook pattern:

**Return empty list `[]`** from `pre_provider_search` to skip a strategy entirely (no variants generated).

This allows plugins to:
- Conditionally disable strategies based on query content (e.g., CJK plugin skips `album+title`)
- Avoid wasted provider requests on strategies that won't work for certain metadata
- Implement smart fallback logic based on track characteristics

See the "Download Strategy Skip Hooks" section above for detailed examples and the CJK plugin implementation.

---

### Other Skip Mechanisms (Fingerprinting & Network)

#### Skip fingerprinting
**Status:** Not implemented as a hook

**Rationale:** Fingerprinting is optional but important for accuracy. Better to make it configurable per-profile than to disable via hook.

**Alternative:** Set `fingerprint_weight = 0.0` in profile to de-prioritize fingerprints.

---

#### `skip_network_detection`
**Status:** Manual override via `_NETWORK_DISABLED` flag

**Location:** `services/metadata_enhancer.py` line 40

**Rationale:** Network operations can be disabled globally for testing, but plugin control would be less safe.

**Current mechanism:** Set `_NETWORK_DISABLED = True` to bypass all AcoustID/MusicBrainz calls. Only file tags and chromaprint cache are used.

---

## Code locations reference

### Core identification
- `services/metadata_enhancer.py` — Main retroactive pipeline
- `core/auto_importer.py` — Real-time file monitoring
- `core/matching_engine/matching_engine.py` — Matching logic

### Profile and configuration
- `core/matching_engine/scoring_profile.py` — `PROFILE_EXACT_SYNC`, `PROFILE_DOWNLOAD_SEARCH`
- `config/config.json` — `auto_import`, `matching_profiles` sections

### Download infrastructure
- `services/download_manager.py` — Central download orchestrator
- `database/working_database.py` — `Download` table schema
- `core/provider.py` — Provider registry and base class

### Database schema
- `database/music_database.py` — `Track`, `Artist`, `Album`, `AudioFingerprint` tables
- `database/working_database.py` — `ReviewTask`, `Download` tables

---

## Extending the pipeline

### Adding a metadata requirement

1. In your plugin's `setup()` function, register your requirement key:
```python
def _on_register_metadata_requirements(keys: list) -> list:
    return keys + ['my_custom_metadata']

hook_manager.add_filter('register_metadata_requirements', _on_register_metadata_requirements)
```

2. In `post_metadata_enrichment`, check and populate your key:
```python
def _on_post_metadata_enrichment(track):
    status = track.metadata_status or {}
    if status.get('my_custom_metadata') is None:
        # ... fetch/compute metadata ...
        status['my_custom_metadata'] = result
        track.metadata_status = status
    return track

hook_manager.add_filter('post_metadata_enrichment', _on_post_metadata_enrichment)
```

3. MetadataEnhancerService will automatically re-select tracks until your key is populated.

### Custom search expansion

In your plugin, expand search queries for downloads:

```python
def _on_pre_provider_search(query: str, **context) -> list:
    # context = { strategy_name, artist_name, title }
    variants = [query]
    if context.get('artist_name'):
        # Add variants...
        variants.append(f"{context['artist_name']} {context['title']}")
    return variants

hook_manager.add_filter('pre_provider_search', _on_pre_provider_search)
```

---

## Implementation notes

- **Batch processing:** MetadataEnhancerService commits after each track to avoid bloating memory on large libraries
- **Error resilience:** Unhandled exceptions in per-track processing are caught and logged; batch continues
- **Session safety:** `flag_modified()` must be called before `hook_manager.apply_filters()` to ensure hooks operate on session-tracked objects
- **Deduplication:** `pre_provider_search` results are order-preserving deduplicated via `dict.fromkeys()`
- **Short-circuit:** Download manager stops iterating variants once a perfect match (≥90%) is found
- **Re-attempts:** Failed identification tracks are retried up to 5 times via `enhancement_attempts` counter

---

**Document version:** aligned to current implementation
