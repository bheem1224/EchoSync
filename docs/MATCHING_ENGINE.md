# SoulSync Matching Engine - Complete Reference Guide

**Last Updated:** January 17, 2026  
**Version:** 2.0 (Tier-2 Fallback + Artist Subset Rescue + ISRC Instant Match)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [High-Level Architecture](#high-level-architecture)
3. [Matching Workflows](#matching-workflows)
   - [Tier-1: Full Artist+Title Search](#tier-1-full-artisttitle-search)
   - [Tier-2: Exact Title+Duration Fallback](#tier-2-exact-titleduration-fallback)
4. [Scoring Profile System](#scoring-profile-system)
5. [Core Matching Algorithm](#core-matching-algorithm)
   - [5-Step Gating Logic](#5-step-gating-logic)
   - [ISRC Instant Match](#isrc-instant-match)
   - [Artist Subset Rescue](#artist-subset-rescue)
6. [Text Normalization](#text-normalization)
7. [Duration Matching](#duration-matching)
8. [Version & Edition Handling](#version--edition-handling)
9. [Fallback Mechanisms](#fallback-mechanisms)
10. [Configuration & Weights](#configuration--weights)
11. [Implementation Details](#implementation-details)
12. [Troubleshooting](#troubleshooting)

---

## Executive Summary

The SoulSync Matching Engine is a **multi-tiered, weighted scoring system** designed to match music tracks across different services (Spotify, Tidal, Plex, Apple Music) with high accuracy despite metadata inconsistencies.

### Key Innovation: Tiered Candidate Retrieval

- **Tier-1:** Full database search using both artist+title patterns; results scored via complete 5-step algorithm
- **Tier-2:** Fallback when Tier-1 fails; retrieves exact title matches within ±2 seconds duration; scored with title+duration only (artist ignored)

### Confidence Scoring

- **90-100%:** ISRC match, exact title+duration (Tier-2), or high fuzzy score with favorable version/edition/duration
- **70-89%:** Fuzzy text match (title+artist+album weighted) with acceptable version/edition alignment
- **<70%:** Failed fuzzy match threshold, version/edition/duration mismatch, or no candidates

### Core Philosophy

1. **Precision over Recall:** Avoid false positives at cost of some false negatives
2. **Metadata-agnostic:** Handle missing/messy metadata gracefully
3. **Fallback Chain:** Try exact matches first, progressively relax criteria
4. **Rescue Mechanisms:** Artist subset tokenization, ISRC instant match, duration guard rails

---

## High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Playlist Analyze Endpoint                      │
│              web/routes/playlists.py :: analyze_playlists()      │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
            ┌───────▼───────┐      ┌───────▼───────┐
            │   TIER-1       │      │   TIER-2      │
            │  (if found)    │      │ (if T1 empty) │
            └───────┬────────┘      └───────┬───────┘
                    │                       │
      ┌─────────────▼─────────────┐         │
      │  SQL: artist+title search │         │
      │  (exact or fuzzy pattern) │         │
      └─────────────┬─────────────┘         │
                    │                       │
      ┌─────────────▼─────────────┐         │
      │ Candidates: 0-10 rows     │         │
      └─────────────┬─────────────┘         │
                    │                       │
                    │              ┌────────▼────────┐
                    │              │ SQL: title exact │
                    │              │  ±2s duration   │
                    │              └────────┬────────┘
                    │                       │
                    │              ┌────────▼────────┐
                    │              │ Candidates: 1-10│
                    │              └────────┬────────┘
                    │                       │
            ┌───────┴───────┬───────────────┘
            │               │
    ┌───────▼─────────┐ ┌──▼──────────────┐
    │  calculate_match │ │calculate_title_ │
    │ (5-step gating)  │ │duration_match   │
    └───────┬─────────┘ └──┬──────────────┘
            │               │
    ┌───────▼─────────────┴──────┐
    │  Best Match (highest score) │
    │  confidence_score: 0-100    │
    └────────────────────────────┘
```

### File Structure

```
core/matching_engine/
├── matching_engine.py          # WeightedMatchingEngine (main logic)
├── scoring_profile.py          # ScoringProfile + weights (ExactSyncProfile, etc)
├── text_utils.py              # normalize_title, normalize_artist, normalize_album
├── soul_sync_track.py         # SoulSyncTrack dataclass
├── fingerprinting.py          # FingerprintMatcher (ISRC, MusicBrainz)
└── __init__.py

web/routes/
└── playlists.py               # analyze_playlists endpoint (Tier-1 & Tier-2 calls)

providers/
├── plex/client.py             # PlexClient with _extract_version_suffix
├── spotify/client.py          # SpotifyClient
└── ...
```

---

## Matching Workflows

### Tier-1: Full Artist+Title Search

**When used:** First attempt for all tracks in playlist analysis  
**SQL Query:** Match both artist and title using exact or fuzzy patterns  
**Scoring:** Full 5-step gating algorithm

```sql
-- Simplified Tier-1 query
SELECT t.id, t.title, t.duration, a.name as artist_name, a.id as artist_id
FROM tracks t
JOIN artists a ON t.artist_id = a.id
WHERE (
    -- Exact artist+title match
    LOWER(a.name) = LOWER(:artist)
    AND LOWER(t.title) = LOWER(:title)
    )
    OR (
    -- Fuzzy artist match (contains artist name)
    LOWER(a.name) LIKE '%' || LOWER(:artist) || '%'
    AND LOWER(t.title) LIKE '%' || LOWER(:title) || '%'
    )
ORDER BY ABS(t.duration - :duration) ASC
LIMIT 10
```

**Expected outcome:** 0-10 candidates sorted by duration proximity

---

### Tier-2: Exact Title+Duration Fallback

**When used:** Only if Tier-1 returns 0 candidates  
**SQL Query:** Exact title match with strict duration tolerance (±2000ms)  
**Scoring:** Title+Duration only (artist ignored, confidence 90-100%)

```sql
-- Tier-2 query (artist ignored)
SELECT t.id, t.title, t.duration, a.name as artist_name, a.id as artist_id
FROM tracks t
JOIN artists a ON t.artist_id = a.id
WHERE (
    LOWER(t.title) = LOWER(:title_exact)
    OR LOWER(REPLACE(REPLACE(t.title, '''', ''), ''', ''))
        = LOWER(REPLACE(REPLACE(:title_exact, '''', ''), ''', ''))
    )
AND t.duration IS NOT NULL
AND t.duration BETWEEN :duration_min AND :duration_max
ORDER BY ABS(t.duration - :duration) ASC
LIMIT 10
```

**Key differences from Tier-1:**
- No artist matching (artist ignored in scoring)
- Exact title required (normalized for apostrophes)
- Strict duration: ±2000ms (2 seconds)
- Confidence: 90-100% (not full 5-step scoring)

**Use case:** Handles cases where:
- Artist metadata is unreliable or foreign (e.g., Plex metadata mismatch)
- Title is reliable and unique enough
- Duration differentiates duplicate titles

---

## Scoring Profile System

Scoring profiles define **weights and penalties** for different matching scenarios.

### Available Profiles

#### **ExactSyncProfile** (Tier-1 matching)
```
Used for: Structured API metadata (Spotify → Tidal/Plex)
Philosophy: High precision, avoid false positives

Weights (normalized within text_weight):
- Title:  35% (most important)
- Artist: 35% (equally important)
- Album:  10% (low - compilations have same track)

Other:
- Duration: 20%
- ISRC/Fingerprint: 0% (no global IDs in Tier-1)
- Quality Bonus: 5%

Penalties:
- Version mismatch: -50 (Remix vs Original = killer)
- Edition mismatch: -15 (deluxe vs standard)

Thresholds:
- Fuzzy match minimum: 90%
- Min confidence to accept: 85%
- Duration tolerance: 3000ms (3 seconds)
```

#### **DownloadSearchProfile** (future use)
```
Used for: P2P downloads with messy filenames (Slskd)
Philosophy: Tolerant, filename junk expected

Weights:
- Title:  40%
- Artist: 30%
- Album:  10%
- Duration: 20%

Penalties:
- Version mismatch: -50
- Edition mismatch: -10 (lower, format differences expected)
- Duration tolerance: 5000ms (5 seconds - allows for different masters)

Thresholds:
- Fuzzy match minimum: 75%
- Min confidence to accept: 70%
```

---

## Core Matching Algorithm

### 5-Step Gating Logic

The **WeightedMatchingEngine** implements a 5-step verification process (used in Tier-1):

#### **Step 0a: ISRC Instant Match** ⚡
```python
if source.isrc == candidate.isrc:
    return MatchResult(confidence_score=100.0, reasoning="ISRC match (instant 100%)")
```

**Why:** ISRC (International Standard Recording Code) uniquely identifies a recording. Perfect match = perfect confidence.

**Example:**
- Source ISRC: `UST1Z0700001`
- Candidate ISRC: `UST1Z0700001`
- → **Result: 100% match, skip all other steps**

---

#### **Step 0b: Fingerprint Matching** 🔍
```python
if source.fingerprint == candidate.fingerprint:
    return MatchResult(confidence_score=100.0, reasoning="Fingerprint match (audio identical)")
```

**Why:** Audio fingerprint (like Shazam) is nearly perfect for identifying same audio file.

**Note:** Currently not used in Tier-1 (no fingerprints available for API metadata), but infrastructure exists.

---

#### **Step 1: Version Check**
Detects remix vs original, live vs studio, etc.

**Logic:**
```python
def _check_version_match(source, candidate):
    # If both have no version info → PASS
    if not source.edition and not candidate.edition:
        return True, "Both have no version"
    
    # If either missing → PASS (no strong signal)
    if not source.edition or not candidate.edition:
        return True, "One side has no version"
    
    # Both have editions → check for match
    if source.edition.lower() == candidate.edition.lower():
        return True, f"Versions match: '{source.edition}'"
    
    # Check keyword overlap (e.g., both contain "remix")
    source_keywords = extract_version_keywords(source.edition)
    candidate_keywords = extract_version_keywords(candidate.edition)
    
    if overlap:
        return True, "Version keywords match"
    
    # If one is "remix" and other is "original" → FAIL
    if ('remix' in source) != ('remix' in candidate):
        return False, "One is remix, other is original"
    
    return False, "Different versions"
```

**Penalty:** If fails, apply **-50** to final score

**Examples:**
- ✅ "Wake Me Up (Original)" vs "Wake Me Up" → PASS (missing is forgiving)
- ✅ "Song (Remix)" vs "Song (Remix)" → PASS (exact match)
- ❌ "Song (Original)" vs "Song (Remix)" → FAIL (-50 penalty)

---

#### **Step 2: Edition/Track Check**
Detects deluxe vs standard, disc number mismatches, etc.

```python
def _check_edition_match(source, candidate):
    if source.disc_number and candidate.disc_number:
        if source.disc_number != candidate.disc_number:
            return False, f"Disc mismatch: {source.disc} vs {candidate.disc}"
    
    # No strong signal if disc numbers missing
    return True, "No edition info to compare"
```

**Penalty:** If fails, apply **-15** to final score

**Examples:**
- ✅ Disc 1 vs Disc 1 → PASS
- ❌ Disc 1 vs Disc 2 → FAIL (-15 penalty)

---

#### **Step 3: Fuzzy Text Matching** 📝
Compare title, artist, album using normalized fuzzy matching.

**Process:**
1. **Normalize each field:**
   - Lowercase
   - Remove accents (é → e)
   - Strip featured artists (feat. → removed)
   - Remove special characters
   
2. **Calculate fuzzy ratio** using `SequenceMatcher.ratio()` (0.0-1.0)

3. **Weighted average** of title, artist, album scores:
   ```
   weighted_score = (title_score * 0.6 + artist_score * 0.3 + album_score * 0.1) / weights_sum
   ```

4. **Gating:** If `weighted_score < fuzzy_threshold (0.90)` → **FAIL**

**Artist Subset Rescue:**
```python
# If fuzzy artist score is low, check for tokenized artist subset match
if artist_fuzzy_score < 0.8:
    is_subset = check_if_one_artist_list_subset_of_other()
    
    if is_subset and duration_within_2_seconds():
        artist_fuzzy_score = 1.0  # Promote to perfect match
```

**Why:** Handles cases like:
- Source: "Macklemore" vs Candidate: "Macklemore & Ryan Lewis"
- Tokenize into: ["macklemore"] vs ["macklemore", "ryan", "lewis"]
- "macklemore" ⊆ set → Valid subset match (and duration tight) → **1.0**

**Examples:**
```
✅ "Wake Me Up" vs "Wake Me Up" → 1.0
✅ "Stereo Hearts (feat. Adam Levine)" vs "Stereo Hearts" → 1.0 (feat stripped)
❌ "Wake Me Up" vs "Wake Me Down" → 0.3 (very different)
```

---

#### **Step 4: Duration Matching** ⏱️
Compare track duration with tolerance.

```python
def _calculate_duration_match(source, candidate):
    diff_ms = abs(source.duration - candidate.duration)
    tolerance_ms = 3000  # 3 seconds (from profile)
    
    if diff_ms <= tolerance_ms:
        # Score decreases as difference increases
        return 1.0 - (diff_ms / tolerance_ms) * 0.5  # Max 0.5 deduction
    else:
        return 0.0  # Outside tolerance = fail
```

**Score:**
- `0-1000ms diff`: 1.0 (perfect)
- `1000-2000ms diff`: 0.5 (acceptable)
- `2000-3000ms diff`: 0.25 (borderline)
- `>3000ms diff`: 0.0 (fail)

**Examples:**
- ✅ 240,000ms vs 240,500ms → 0.92 (500ms diff = acceptable)
- ✅ 240,000ms vs 242,500ms → 0.58 (2500ms diff = borderline)
- ❌ 240,000ms vs 243,500ms → 0.0 (3500ms > 3000ms tolerance)

---

#### **Step 5: Quality Tie-Breaker** 🎵
If candidate has quality metadata (e.g., bitrate tags), apply bonus.

```python
if candidate.quality_tags:
    confidence += 5.0  # 5% bonus
```

---

### Final Score Calculation

```
raw_score = (text_contribution + duration_contribution + quality_bonus) - penalties

normalized_score = (raw_score / max_possible_score) * 100

final_score = clamp(normalized_score, 0, 100)

RESULT:
  - if final_score >= 85%: ACCEPT
  - if 70% <= final_score < 85%: UNCERTAIN (log for review)
  - if final_score < 70%: REJECT
```

---

## ISRC Instant Match

**Definition:** ISRC (International Standard Recording Code) is a unique identifier for specific audio recordings.

**Format:** 12 characters, e.g., `UST1Z0700001`
- Country: 2 chars (US)
- Registrant: 3 chars (T1Z)
- Year: 2 digits (07)
- Sequential: 5 digits (00001)

**Integration:**

```python
# In matching_engine.py :: calculate_match()
if source.isrc and candidate.isrc:
    if source.isrc.strip().upper() == candidate.isrc.strip().upper():
        return MatchResult(confidence_score=100.0, reasoning="ISRC match")
```

**When to use:**
- ✅ Matching Spotify track (has ISRC) against database track (has ISRC from Spotify importer)
- ❌ Matching Plex track (no ISRC) against Spotify track
- ❌ Matching user-uploaded file

**Data sources:**
- Spotify API: always includes ISRC
- Tidal API: includes ISRC
- Plex API: does NOT include ISRC
- Local files: may have ISRC in metadata (rarely)

---

## Artist Subset Rescue

**Problem:** 
- Source: "Macklemore"
- Candidate: "Macklemore & Ryan Lewis"
- Fuzzy match: 0.45 (too low, fails Step 3)

**Solution:** Tokenize artists and check subset relationship.

**Algorithm:**

```python
def _tokenize_artists(artist_string: str) -> set:
    """Split 'Artist 1 & Artist 2 feat. Artist 3' into individual names"""
    tokens = re.split(r'\s*(?:&|feat\.|ft\.|featuring|with|and|,)\s*', artist_string)
    return {normalize(token) for token in tokens if token}

def _check_artist_subset_match(source, candidate):
    source_tokens = _tokenize_artists(source.artist_name)
    candidate_tokens = _tokenize_artists(candidate.artist_name)
    
    # Check if one is subset of other
    if source_tokens.issubset(candidate_tokens):
        # e.g., {macklemore} ⊆ {macklemore, ryan, lewis} → TRUE
        return True, 1.0, "Source artists are subset of candidate"
    
    elif candidate_tokens.issubset(source_tokens):
        return True, 1.0, "Candidate artists are subset of source"
    
    else:
        # Check partial overlap
        intersection = source_tokens & candidate_tokens
        if intersection:
            return False, 0.0, f"Partial overlap: {intersection}"
        else:
            return False, 0.0, "No artist overlap"
```

**Guard Rail:** Subset rescue only activates if:
1. Artist fuzzy score is low (`< 0.8`)
2. Is actually a subset match
3. **Duration is within 2 seconds** ← tight duration guard rail

**Why the guard rail?** Without it, "Macklemore" song at 3:00 could match "Macklemore & Ryan Lewis" at 2:00, which is wrong. The 2-second window prevents accidental cross-matching.

**Examples:**

```
Source: "Macklemore", 240000ms
Candidate: "Macklemore & Ryan Lewis", 240500ms

1. Fuzzy artist score: 0.45 < 0.8 → attempt rescue
2. Tokenize: {macklemore} vs {macklemore, ryan, lewis}
3. {macklemore} ⊆ {macklemore, ryan, lewis} → TRUE
4. Duration diff: 500ms < 2000ms → PASS guard rail
5. Result: Boost artist score to 1.0 → ACCEPT

---

Source: "Macklemore", 180000ms
Candidate: "Macklemore & Ryan Lewis", 240000ms

1. Fuzzy artist score: 0.45 < 0.8 → attempt rescue
2. Tokenize: {macklemore} vs {macklemore, ryan, lewis}
3. {macklemore} ⊆ {macklemore, ryan, lewis} → TRUE
4. Duration diff: 60000ms > 2000ms → FAIL guard rail
5. Result: No boost, fuzzy score remains 0.45 → REJECT
```

---

## Text Normalization

**Purpose:** Convert messy real-world strings into consistent format for comparison.

### normalize_title(title)

**Process:**
1. Lowercase: `"WAKE ME UP"` → `"wake me up"`
2. Remove accents: `"Café"` → `"cafe"`
3. Strip featured-artist markers:
   - `"Stereo Hearts (feat. Adam Levine)"` → `"Stereo Hearts"`
   - `"Song with Artist"` → `"Song"`
4. Remove special characters: `"Wake-Me-Up!"` → `"Wake Me Up"`
5. Collapse spaces: `"Wake  Me    Up"` → `"Wake Me Up"`

**Code:**
```python
def normalize_title(title):
    normalized = normalize_text(title)  # lowercase + remove accents + spaces
    
    # Remove parenthetical featured artist clauses
    normalized = re.sub(
        r"\s*[\(\[\{]\s*(feat\.?|featuring|with)\b[^\)\]\}]*[\)\]\}]",
        "",
        normalized,
        flags=re.IGNORECASE
    )
    
    # Remove trailing feat/with clauses
    normalized = re.sub(r"\s+(feat\.?|featuring|with)\b.*$", "", normalized, flags=re.IGNORECASE)
    
    # Keep only alphanumeric, spaces, hyphens, quotes, parens
    normalized = re.sub(r'[^\w\s\-\(\)\'\"]', '', normalized)
    
    return normalized.strip()
```

**Examples:**
```
normalize_title("WAKE ME UP!") → "wake me up"
normalize_title("Stereo Hearts (feat. Adam Levine)") → "stereo hearts"
normalize_title('"All the Things She Said" Music Video') → "all the things she said music video"
normalize_title("Café Français (Remix)") → "cafe francais remix"
```

### normalize_artist(artist)

**Process:**
1. Lowercase, remove accents, strip spaces (same as title)
2. Remove featured-artist markers: `"Macklemore feat. Ryan Lewis"` → `"Macklemore"`
3. Keep all artist names from delimited list: `"Artist 1 & Artist 2"` → `"artist 1 & artist 2"`

**Code:**
```python
def normalize_artist(artist):
    normalized = normalize_text(artist)  # lowercase + accents + spaces
    
    # Remove feat/ft markers and everything after
    normalized = re.sub(
        r'\s*(?:feat\.|featuring|ft\.?|with).*$',
        '',
        normalized,
        flags=re.IGNORECASE
    )
    
    return normalized.strip()
```

**Examples:**
```
normalize_artist("MACKLEMORE") → "macklemore"
normalize_artist("Macklemore & Ryan Lewis") → "macklemore & ryan lewis"
normalize_artist("Axwell & Ingrosso") → "axwell & ingrosso"
normalize_artist("Macklemore feat. Ryan Lewis") → "macklemore"
```

### normalize_album(album)

**Process:**
1. Lowercase, remove accents
2. Remove edition markers: deluxe, remaster, extended, etc.
3. Keep album name only

**Code:**
```python
def normalize_album(album):
    normalized = normalize_text(album)
    
    # Remove edition markers
    normalized = re.sub(
        r'\s*(?:deluxe|remaster|remastered|extended|edition)\s*edition\b',
        '',
        normalized,
        flags=re.IGNORECASE
    )
    
    return normalized.strip()
```

**Examples:**
```
normalize_album("True (Avicii by Avicii)") → "true avicii by avicii"
normalize_album("Album Deluxe Edition") → "album"
normalize_album("Café Français") → "cafe francais"
```

---

## Duration Matching

**Purpose:** Use audio duration as a tie-breaker and BS detector.

### Tier-1 Duration Matching (full scoring)

```python
def _calculate_duration_match(source, candidate):
    if not source.duration or not candidate.duration:
        return 1.0  # Missing = assume match
    
    diff_ms = abs(source.duration - candidate.duration)
    tolerance_ms = 3000  # 3 seconds
    
    if diff_ms <= tolerance_ms:
        # Score based on proximity
        return 1.0 - (diff_ms / tolerance_ms) * 0.5
    else:
        return 0.0  # Outside tolerance
```

**Tolerance Justification (±3000ms):**
- Different audio masters (CD vs Streaming) may have different fade-out lengths
- Encoding/transcoding can add/remove milliseconds
- 3 seconds is large enough to account for master differences, small enough to catch wrong tracks

**Examples:**
```
240000 vs 240500 → diff=500ms < 3000ms → score=0.917
240000 vs 241500 → diff=1500ms < 3000ms → score=0.708
240000 vs 243500 → diff=3500ms > 3000ms → score=0.0 (FAIL)
```

### Tier-2 Duration Matching (strict)

```python
def calculate_title_duration_match(source, candidate):
    if not source.duration or not candidate.duration:
        return 0.0  # Missing = cannot validate
    
    diff_ms = abs(source.duration - candidate.duration)
    tolerance_ms = 2000  # 2 seconds (stricter)
    
    if diff_ms > tolerance_ms:
        return MatchResult(confidence_score=0.0, reasoning="Duration outside tolerance")
    
    # Calculate confidence 90-100% based on proximity
    duration_score = 1.0 - (diff_ms / tolerance_ms) * 0.1
    confidence = 90.0 + (duration_score * 10.0)  # 90-100% range
    
    return MatchResult(confidence_score=confidence, ...)
```

**Tier-2 stricter tolerance (±2000ms):**
- Title is being used as the only identifier
- Duration must be tight to avoid false positives
- Prevents "Song at 3:00" from matching "Song at 2:00"

---

## Version & Edition Handling

### Version Keywords

**Definition:** Keywords that indicate remix, live, acoustic, etc.

```python
VERSION_KEYWORDS = {
    'remix', 'rmx', 'mix', 'edit',
    'extended', 'instrumental', 'acapella', 'bootleg',
    'cover', 'remaster', 'remastered',
    'original', 'club', 'radio', 'house', 'deep', 'progressive',
    'version', 'ver', 'alternative', 'alt', 'acoustic', 'live'
}
```

**Matching Logic:**
```python
# Check keyword overlap
source_keywords = {'remix', 'edit'}
candidate_keywords = {'remix', 'extended'}
overlap = source_keywords & candidate_keywords  # {'remix'}

if overlap:
    return True, "Version keywords match"
```

### Title Cleaning in Plex Client

**Problem:** Plex metadata includes parenthetical suffixes that should be extracted into `edition` field.

```
Title: "All the Things She Said" Music Video
→ Should become: title="All the Things She Said", edition="Music Video"

Title: Wake Me Up (Avicii by Avicii)
Album: True (Avicii by Avicii)
→ Should become: title="Wake Me Up", edition removed (matched album)
```

**Implementation:**

```python
def _extract_version_suffix(text: str) -> tuple[str, Optional[str]]:
    """Extract version suffix from text in parentheses or common edition suffixes."""
    
    import re
    
    # First check for common edition suffixes (case-insensitive)
    edition_patterns = [
        r'\s+(?:Music\s+Video|Official\s+Video|Video|Live\s+Version|Acoustic\s+Version|Remix|Remaster|Extended\s+Version)\s*$',
        r'\s*\(([^)]*)\)\s*$'  # Then try parentheses
    ]
    
    for pattern in edition_patterns:
        if pattern == r'\s*\(([^)]*)\)\s*$':
            match = re.search(pattern, text)
            if match:
                base = text[:match.start()].strip()
                version = match.group(1).strip()
                if base and version:
                    return base, version
        else:
            match = re.search(pattern, text)
            if match:
                base = text[:match.start()].strip()
                version = match.group(0).strip().lower()
                return base, version
    
    return text, None
```

**Examples:**
```
"Wake Me Up (Avicii by Avicii)"
→ ("Wake Me Up", "Avicii by Avicii")

"All the Things She Said Music Video"
→ ("All the Things She Said", "music video")

"Song Live Version"
→ ("Song", "live version")

"Normal Title"
→ ("Normal Title", None)
```

---

## Fallback Mechanisms

### Fallback Chain (Order of Operations)

1. **ISRC Instant Match** ✅
   - If ISRC exists and matches → 100% confidence, done

2. **Fingerprint Match** ✅
   - If audio fingerprint matches → 100% confidence, done

3. **Tier-1 Full Matching** ✅
   - Artist + Title SQL search
   - 5-step scoring algorithm
   - If best match ≥ 85% confidence → accept

4. **Tier-2 Exact Title+Duration** ✅
   - If Tier-1 found nothing
   - Exact title (normalized) + duration ±2000ms
   - 90-100% confidence range
   - Ignores artist

5. **Manual Review** ❓
   - If Tier-2 also fails
   - Log unmatched track for manual intervention
   - Don't create false matches

### Rescue Mechanisms (within Tier-1)

#### Artist Subset Rescue
- If fuzzy artist score `< 0.8`
- AND one artist list is subset of other
- AND duration within 2 seconds
- → Boost artist score to 1.0

#### Featured Artist Stripping
- Remove `(feat. Artist)` from titles before fuzzy match
- Example: "Stereo Hearts (feat. Adam Levine)" → "Stereo Hearts"

---

## Configuration & Weights

### Profile Configuration in config.json

```json
{
  "matching_profiles": {
    "exact_sync": {
      "text_weight": 0.80,
      "title_weight": 0.4375,
      "artist_weight": 0.4375,
      "album_weight": 0.125,
      "duration_weight": 0.20,
      "fingerprint_weight": 0.0,
      "quality_bonus": 0.05,
      "version_mismatch_penalty": 50.0,
      "edition_mismatch_penalty": 15.0,
      "duration_tolerance_ms": 3000,
      "fuzzy_match_threshold": 0.90,
      "min_confidence_to_accept": 85.0,
      "text_match_fallback": 0.92
    }
  }
}
```

### Modifying Weights

**To make matching more tolerant:**
```json
{
  "fuzzy_match_threshold": 0.80,  # Was 0.90 - relax text match requirement
  "duration_tolerance_ms": 4000,  # Was 3000 - allow 4 seconds variance
  "min_confidence_to_accept": 75.0  # Was 85 - accept lower confidence
}
```

**To make matching stricter:**
```json
{
  "fuzzy_match_threshold": 0.95,  # Was 0.90 - require higher text match
  "version_mismatch_penalty": 75.0,  # Was 50 - penalize version mismatches more
  "duration_tolerance_ms": 2000  # Was 3000 - allow only 2 seconds
}
```

---

## Implementation Details

### Core Files

#### `core/matching_engine/matching_engine.py` (648 lines)

**Main class:** `WeightedMatchingEngine`

**Key methods:**
```python
# Primary entry points
calculate_match(source, candidate) -> MatchResult
  # Full 5-step gating for Tier-1

calculate_title_duration_match(source, candidate) -> MatchResult
  # Tier-2 fallback: title + duration only

# Scoring methods (internal)
_calculate_standard_match(source, candidate) -> MatchResult
_calculate_fuzzy_text_match(source, candidate) -> float
_calculate_duration_match(source, candidate) -> float

# Verification methods
_check_version_match(source, candidate) -> (bool, str)
_check_edition_match(source, candidate) -> (bool, str)

# Fuzzy matching
_fuzzy_match(a, b) -> float
_normalize_string_for_comparison(s) -> str

# Artist subset rescue
_tokenize_artists(artist_string) -> set
_check_artist_subset_match(source, candidate) -> (bool, float, str)

# Version/edition parsing
_extract_version_keywords(version_str) -> set
```

#### `core/matching_engine/scoring_profile.py` (380 lines)

**Main classes:**
```python
ScoringWeights  # Dataclass with all weights/penalties
ScoringProfile  # Abstract base
ExactSyncProfile  # Concrete implementation
DownloadSearchProfile  # Concrete implementation
```

#### `core/matching_engine/text_utils.py` (337 lines)

**Functions:**
```python
normalize_text(text) -> str
  # Lowercase, accents, spaces

normalize_title(title) -> str
  # + strip featured artists

normalize_artist(artist) -> str
  # + keep all artist names

normalize_album(album) -> str
  # + remove edition markers

remove_accents(text) -> str
  # Unicode normalization
```

#### `web/routes/playlists.py` (491 lines)

**Main endpoint:** `analyze_playlists()`

**Key sections:**
```python
# Tier-1 query (lines ~130-160)
tier1_query = text("""
    SELECT t.id, t.title, t.duration, a.name as artist_name, a.id as artist_id
    FROM tracks t
    JOIN artists a ON t.artist_id = a.id
    WHERE (...)
    ORDER BY ABS(t.duration - :duration) ASC
    LIMIT 10
""")

# Tier-2 query (lines ~170-195)
tier2_query = text("""
    SELECT t.id, t.title, t.duration, a.name as artist_name, a.id as artist_id
    FROM tracks t
    JOIN artists a ON t.artist_id = a.id
    WHERE (
        LOWER(t.title) = LOWER(:title_exact)
        OR LOWER(REPLACE(REPLACE(t.title, '''', ''), ''', ''))
            = LOWER(REPLACE(REPLACE(:title_exact, '''', ''), ''', ''))
    )
    AND t.duration BETWEEN :duration_min AND :duration_max
    ORDER BY ABS(t.duration - :duration) ASC
    LIMIT 10
""")

# Scoring (lines ~220-240)
if tier2_mode:
    result = matching_engine.calculate_title_duration_match(source_track, candidate_track)
else:
    result = matching_engine.calculate_match(source_track, candidate_track)

# Accept if confidence >= threshold
if result.confidence_score >= profile.weights.min_confidence_to_accept:
    library_match = candidate_track.title
    best_score = result.confidence_score
```

#### `providers/plex/client.py` (616 lines)

**Key method:** `_extract_version_suffix()`

```python
def _extract_version_suffix(self, text: str) -> tuple[str, Optional[str]]:
    """Extract version suffix from text in parentheses or common edition suffixes."""
    import re
    
    edition_patterns = [
        r'\s+(?:Music\s+Video|Official\s+Video|Video|Live\s+Version|...)\s*$',
        r'\s*\(([^)]*)\)\s*$'
    ]
    
    for pattern in edition_patterns:
        match = re.search(pattern, text)
        if match:
            base = text[:match.start()].strip()
            version = ...
            return base, version
    
    return text, None
```

**Integration in `_convert_track_to_soulsync()`:**
```python
title_base, title_version = self._extract_version_suffix(title)
album_base, album_version = self._extract_version_suffix(album)

if title_version and album_version and title_version.lower() == album_version.lower():
    title = title_base  # Remove matching version suffix
```

---

## Troubleshooting

### Track Not Finding Match

**Symptom:** Tier-1 returns 0 candidates, Tier-2 also returns 0

**Diagnostics:**

1. **Check logs for Tier-1 activation:**
   ```
   DEBUG - Tier 1 found 0 candidates for 'Song Title' by 'Artist Name'. Attempting Tier 2...
   ```

2. **Check Tier-2 activation:**
   ```
   DEBUG - Tier 2 fallback activated for 'Song Title' by 'Artist Name'
   ```

3. **If Tier-2 returns 0:**
   ```
   DEBUG - Tier 2 found 0 candidates for exact title match 'Song Title'
   ```

**Common Causes:**

| Symptom | Cause | Fix |
|---------|-------|-----|
| Tier-1 returns 0, Tier-2 returns 0 | Title doesn't exist in DB | Verify database has track; check importer |
| Tier-1 returns candidates, best score <70% | Fuzzy match fails | Check title/artist normalization |
| Duration mismatch in logs | Master/edition difference | Increase `duration_tolerance_ms` |
| "Version mismatch" penalty applied | Remix vs Original detected | Verify correct track type |
| Artist subset rescue not triggering | Duration outside 2s guard rail | Check duration difference |

### Score Too Low

**Symptom:** Track matches but confidence < 70%, rejected

**Diagnostics:**

1. **Check score breakdown:**
   ```
   Text match: 0.92 × 0.80 = 73.6 points
   Duration match: 0.85 × 0.20 = 17 points
   Version penalty: -50
   FINAL SCORE: 40.6/100 ← TOO LOW
   ```

2. **Identify failing step:**
   - If `Version mismatch: Original vs Remix` → version_mismatch_penalty too high
   - If `Fuzzy text score 0.70 < 0.90` → fuzzy_match_threshold too high
   - If `Duration diff 4500ms > 3000ms` → duration_tolerance_ms too low

**Fixes:**

```python
# Option 1: Relax profile in config.json
{
  "fuzzy_match_threshold": 0.85,  # Was 0.90
  "duration_tolerance_ms": 4000,  # Was 3000
  "version_mismatch_penalty": 30.0  # Was 50
}

# Option 2: Check if wrong track is being compared
# → Verify SQL query is returning correct candidates
```

### False Positives (Wrong Match)

**Symptom:** Track matches but with incorrect title/artist

**Diagnostics:**

1. **Check confidence score:**
   - If ≥ 90%: Something is wrong with SQL/candidates
   - If 70-89%: Scoring is accepting too many fuzzy matches

2. **Check SQL candidates:**
   ```
   SELECT * FROM tracks WHERE artist LIKE '%..%' AND title LIKE '%..%'
   ```
   Are unrelated tracks being returned?

3. **Review scoring:**
   ```
   Text match: 0.65 (should be higher for correct match)
   FINAL: 82% confidence
   ```

**Fixes:**

```python
# Option 1: Increase fuzzy threshold
{
  "fuzzy_match_threshold": 0.95  # Was 0.90 - stricter
}

# Option 2: Reduce tolerance for Tier-2
{
  "duration_tolerance_ms": 1500  # Was 2000 for Tier-2 - stricter
}

# Option 3: Review SQL query - maybe LIKE pattern too broad
# Change:
#   LOWER(a.name) LIKE '%' || :artist || '%'
# To:
#   LOWER(a.name) LIKE :artist || '%'  # Match prefix only
```

### ISRC Not Matching

**Symptom:** Tracks have same ISRC but not matching

**Diagnostics:**

```python
# Check ISRC values
source.isrc = "UST1Z0700001"
candidate.isrc = "UST1Z0700001 "  # Note trailing space

# Solution: code strips and uppercases
if source.isrc.strip().upper() == candidate.isrc.strip().upper():
```

**Common issues:**
- Extra whitespace (fixed by `.strip()`)
- Case differences (fixed by `.upper()`)
- Different ISRC registrants (legitimate - different recordings)

---

## Future Improvements

### Planned Enhancements

1. **Acoustic Fingerprinting:** Implement Shazam-like fingerprinting for audio files
2. **MusicBrainz Integration:** Use MB RecordingID for additional matching confidence
3. **Feature Extraction:** Extract BPM, key, genre from audio for better scoring
4. **Learning Weights:** Use user feedback to auto-tune weights over time
5. **Diacritic Normalization in SQL:** Add precomputed `title_normalized` column for faster Tier-2
6. **Smarter Feat Stripping:** Handle international featured-artist markers (e.g., "ft" in different languages)

### Known Limitations

- **Plex metadata:** No ISRC, sometimes artist mismatches (different master sources)
- **User uploads:** Often missing metadata, no ISRC
- **Live recordings:** Duration varies between performances, hard to match
- **Compilations:** Same track appears on multiple albums, SQL ORDER BY duration helps but not perfect

---

## Quick Reference

### Key Constants

```python
TIER1_CANDIDATE_LIMIT = 10        # Max SQL results
TIER2_CANDIDATE_LIMIT = 10
TIER2_DURATION_TOLERANCE = 2000   # milliseconds (2 seconds)
TIER1_DURATION_TOLERANCE = 3000   # milliseconds (3 seconds)
ARTIST_SUBSET_GUARD_RAIL = 2000   # milliseconds (2 seconds)
ARTIST_FUZZY_THRESHOLD = 0.80     # 80% fuzzy match required to attempt subset rescue
MIN_CONFIDENCE_TIER1 = 85.0        # Percent
MIN_CONFIDENCE_TIER2 = 90.0        # Percent
ISRC_INSTANT_MATCH = 100.0         # Percent (highest confidence)
```

### Scoring Ranges

- **90-100%:** Excellent match (ISRC, exact title+duration, or excellent fuzzy + good duration)
- **80-89%:** Good match (high fuzzy score, favorable version/edition/duration)
- **70-79%:** Acceptable match (decent fuzzy score, no penalties)
- **<70%:** Reject (failed fuzzy threshold or too many penalties)

### Debug Logging

Enable via environment variable:
```bash
export LOG_LEVEL=DEBUG
python main.py
```

Look for:
```
DEBUG - Tier 1 found X candidates for 'Title' by 'Artist'
DEBUG - Match score for 'X' vs 'Y': 82.5
DEBUG - Tier 2 fallback activated for...
DEBUG - Tier 2 found X candidates for exact title match
```

---

## Contact & Questions

For matching engine issues:
1. Check [troubleshooting section](#troubleshooting)
2. Enable DEBUG logging and collect logs
3. Reproduce with minimal example
4. Check if profile weights need adjustment
5. Review SQL query in web/routes/playlists.py

---

**Document Version:** 2.0  
**Last Update:** January 17, 2026  
**Maintainer:** SoulSync Development Team
