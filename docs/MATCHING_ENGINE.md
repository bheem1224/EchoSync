# Matching Engine Reference

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