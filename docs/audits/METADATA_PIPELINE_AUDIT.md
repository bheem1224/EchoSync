# Metadata Pipeline Audit Report

**Document type:** Read-only architectural audit  
**Scope:** `core/metadata/engine.py` and associated pipeline files  
**Date:** 2026-09-18  
**Status:** Findings only — NO code modifications performed or authorised  
**Auditor:** Antigravity autonomous agent (conversation 3a21546d)

> [!CAUTION]
> This report is read-only. No SQL mutations (`UPDATE`, `DELETE`, `INSERT`),
> no Python patches, and no Rust or Svelte file edits have been performed.
> All findings are observational and require an approved ADR before any
> remediation code is written.

---

## Table of Contents

1. [File-by-File Structural Breakdown of `engine.py`](#section-1)
2. [Root-Cause Trace: 2,812 "Unknown Artist" Tracks](#section-2)
3. [Root-Cause Trace: 235 Composite Artist Entities](#section-3)
4. [Version/Edition Extraction Failure Analysis](#section-4)
5. [Comparative Analysis: MusicBrainz Picard Release-Group Matching](#section-5)

---

## Section 1 — Proposed Structural Breakdown of `core/metadata/engine.py` {#section-1}

### 1.1 Current File Profile

| Attribute | Value |
|---|---|
| **File** | `core/metadata/engine.py` |
| **Total lines** | 2,125 |
| **Total bytes** | ~102 KB |
| **Top-level functions** | 5 (`_extract_release_details`, `calculate_acoustid_duration_weight`, `calculate_text_duration_weight`, `extract_filename_title`, standalone helpers) |
| **Classes** | 1 (`MetadataResolutionEngine`) |
| **Public methods on class** | 4 (`resolve_track`, `resolve_track_metadata`, `invalidate_cache`, `score_candidate`) |
| **Private methods on class** | 7 (`_get_acoustid_plugin`, `_get_mb_plugin`, `_resolve_acoustid_isolated`, `_resolve_aliases`, `_execute_waterfall`, `_check_local_chromaprint_cache`, `_resolve_acoustid`, `_resolve_isrc`, `_resolve_text_waterfall`) |
| **Approximate concern breakdown** | DSP: ~150 lines; Cache: ~120 lines; Scoring: ~180 lines; AcoustID dispatch: ~400 lines; ISRC: ~60 lines; Text waterfall: ~170 lines; Adapter/result assembly: ~300 lines; Plumbing/logging: ~745 lines |

### 1.2 Target Module: `core/metadata/dsp.py`

**Responsibility:** All physical audio probing and Chromaprint extraction. This module is
the only Python code permitted to call `echosync_core.extract_metadata` and
`echosync_core.fingerprint_and_hash_audio`.

**Source lines in current `engine.py`:** ~629–732, ~437–500 (isolated path)

**Target interface:**

```python
# core/metadata/dsp.py

from dataclasses import dataclass

@dataclass
class PhysicalProbeResult:
    duration_ms: int
    channels: int
    chromaprint: str | None
    raw_tags: dict[str, Any]

def probe_file(file_path: str | Path) -> PhysicalProbeResult:
    """
    Call echosync_core.extract_metadata + fingerprint_and_hash_audio.
    Enforces multi-channel guard (channels > 2 → chromaprint = None).
    Enforces stale chromaprint guard (len > 4000 → regenerate).
    Clamps fingerprint duration to 120s.
    """
    ...

def generate_chromaprint(
    file_path: str | Path,
    channels: int,
    fallback: bool = True,
) -> tuple[str | None, int]:
    """
    Generate chromaprint and duration_ms.
    Returns (None, 0) for multi-channel audio.
    Falls back to FingerprintGenerator.generate_with_duration if Rust FFI fails.
    """
    ...
```

**Dependency flow:**
```
dsp.py
  └─ echosync_core (Rust FFI, PyO3)
  └─ core/matching_engine/fingerprinting.py (FingerprintGenerator — fallback only)
```

**No imports from:** `database/`, `plugins/`, `services/`.

---

### 1.3 Target Module: `core/metadata/cache.py`

**Responsibility:** Bounded in-memory LRU cache and SQLite peer-track chromaprint cache.

**Source lines in current `engine.py`:** ~1,340–1,405

**Target interface:**

```python
# core/metadata/cache.py

class ChromaprintCache:
    """
    Two-tier chromaprint lookup:
    1. In-memory LRU OrderedDict (max_entries=200)
    2. SQLite library.db peer-track query

    Invariant: len(cache) <= 200 at all times (LRU eviction).
    """

    def __init__(self, max_entries: int = 200) -> None: ...

    def get(
        self, chromaprint: str, sync_id: str | None = None
    ) -> dict[str, Any] | None:
        """
        Check in-memory cache first.
        On miss, query library.db for peer tracks sharing this chromaprint.
        Returns None if chromaprint is shorter than 50 chars (invalid).
        """
        ...

    def set(self, chromaprint: str, metadata: dict[str, Any]) -> None:
        """Upsert into in-memory cache with LRU eviction."""
        ...

    def invalidate(self, chromaprint: str | None = None) -> None:
        """Invalidate specific entry or clear entire cache."""
        ...
```

**SQLite query (read-only, from current implementation):**

```sql
SELECT Track.title, Track.musicbrainz_id, Track.year,
       Track.track_number, Track.disc_number, Track.isrc, Track.duration,
       Artist.name AS artist_name,
       Album.title AS album_title, Album.mb_release_id AS release_mbid
FROM Track
JOIN LocalMedia ON LocalMedia.track_id = Track.id
JOIN AudioFingerprint ON AudioFingerprint.media_id = LocalMedia.media_id
LEFT JOIN Artist ON Artist.id = Track.artist_id
LEFT JOIN Album ON Album.id = Track.album_id
WHERE AudioFingerprint.chromaprint = :chromaprint
  AND Track.musicbrainz_id IS NOT NULL
  AND Track.musicbrainz_id NOT IN ('', 'NOT_FOUND')
  AND Track.title IS NOT NULL
  AND Track.title != ''
  AND Track.sync_id != :exclude_sync_id
LIMIT 1;
```

**Dependency flow:**
```
cache.py
  └─ database/music_database.py (Track, LocalMedia, AudioFingerprint models — read-only)
  └─ collections.OrderedDict (stdlib)
```

---

### 1.4 Target Module: `core/metadata/scoring.py`

**Responsibility:** All scoring arithmetic: parabolic duration weights, linear text decay,
studio album bonuses, compilation penalties, and the `WeightedMatchingEngine` wrapper.

**Source lines in current `engine.py`:** ~151–163, ~286–388

**Target interface:**

```python
# core/metadata/scoring.py

from core.matching_engine.matching_engine import WeightedMatchingEngine
from core.matching_engine.scoring_profile import PROFILE_EXACT_SYNC

# ── Constants ──────────────────────────────────────────────────────────────────
ACOUSTID_DURATION_GATE_SEC: float = 2.0          # Hard gate — reject delta > 2.0s
TEXT_DURATION_GATE_SEC: float = 8.0              # Hard gate — reject delta > 8.0s
STUDIO_ALBUM_BONUS: float = 25.0                 # +25.0 for primary_type == "Album" + no secondary
COMPILATION_PENALTY: float = -35.0              # -35.0 for compilation/dj-mix/sampler
VARIOUS_ARTISTS_PENALTY: float = -10.0          # -10.0 for "various artists" credit
ACOUSTID_HIT_THRESHOLD: float = 60.0            # Minimum score to accept AcoustID hit
TEXT_HIT_THRESHOLD: float = 85.0                # Minimum score to accept text waterfall hit
CHROMAPRINT_MAX_LEN: int = 4000                  # Stale fingerprint guard


def calculate_acoustid_duration_weight(
    track_duration_sec: float, candidate_duration_sec: float
) -> float:
    r"""
    Parabolic decay curve for AcoustID duration proximity.

    .. math::
        w(\Delta) = \max(0.0,\; 1.0 - (\Delta / 2.0)^2)

    Returns 0.0 for |Δ| > 2.0s (hard gate).
    """
    ...

def calculate_text_duration_weight(
    track_duration_sec: float, candidate_duration_sec: float
) -> float:
    r"""
    Linear decay curve for text waterfall duration proximity.

    .. math::
        w(\Delta) = \max(0.0,\; 1.0 - \Delta / 8.0)

    Returns 0.0 for |Δ| > 8.0s (hard gate).
    """
    ...

def score_acoustid_candidate(
    candidate: dict[str, Any],
    query_track: EchosyncTrack,
    file_duration_ms: int,
    filename: str | None = None,
    matcher: WeightedMatchingEngine | None = None,
) -> float:
    """
    Score an AcoustID recording candidate.

    Formula:
        score = (matcher_score × 0.7) + (duration_weight × 30.0) + album_bonus + compilation_penalty
    """
    ...

def apply_progressive_duration_multiplier(
    score: float, delta_sec: float, duration_weight: float
) -> float:
    """
    Apply progressive duration multiplier:
        delta <= 1.0s:  score × (0.95 + 0.05 × weight)
        delta >  1.0s:  score × weight
    """
    ...
```

**Dependency flow:**
```
scoring.py
  └─ core/matching_engine/matching_engine.py (WeightedMatchingEngine)
  └─ core/matching_engine/scoring_profile.py (PROFILE_EXACT_SYNC)
  └─ core/db/echo_sync_track.py (EchosyncTrack)
```

**No imports from:** `database/`, `echosync_core`, `plugins/`, `services/`.

---

### 1.5 Target Module: `core/metadata/plugins.py`

**Responsibility:** Provider resolution via `PluginRegistry`; ISRC dispatch; plugin
accessor helpers.

**Source lines in current `engine.py`:** ~246–284

**Target interface:**

```python
# core/metadata/plugins.py

from core.nexus_framework.plugin_loader import PluginRegistry, generate_plugin_id
from core.enums import Capability

def get_acoustid_plugin(
    override: Any | None = None
) -> Any | None:
    """
    Resolve AcoustID plugin:
    1. Return override if provided.
    2. PluginRegistry.get_plugin(generate_plugin_id("EchoSync.acoustid"))
    3. PluginRegistry.get_plugins_with_capability(Capability.RESOLVE_FINGERPRINT)
       → prefer plugin with fingerprint_algorithms = ["chromaprint"]
    """
    ...

def get_mb_plugin(override: Any | None = None) -> Any | None:
    """
    Resolve MusicBrainz metadata plugin:
    1. Return override if provided.
    2. PluginRegistry.get_plugin(generate_plugin_id("EchoSync.musicbrainz"))
    3. PluginRegistry.get_plugins_with_capability(Capability.FETCH_METADATA)
    """
    ...

def get_spotify_plugin(override: Any | None = None) -> Any | None:
    """Resolve Spotify plugin by name or Capability.FETCH_METADATA."""
    ...

def dispatch_isrc(isrc: str) -> Any | None:
    """
    Thin wrapper around services.isrc_lookup_service.dispatch_isrc_lookup.
    Returns an EchosyncTrack-like object or None.
    Active in ALL environments (never disabled by _NETWORK_DISABLED).
    """
    ...
```

**Dependency flow:**
```
plugins.py
  └─ core/nexus_framework/plugin_loader.py (PluginRegistry, generate_plugin_id)
  └─ core/enums.py (Capability)
  └─ services/isrc_lookup_service.py (dispatch_isrc_lookup — lazy import)
```

---

### 1.6 Target Module: `core/metadata/resolver.py`

**Responsibility:** The `MetadataResolutionEngine` class — state machine orchestrating
the 6-stage waterfall. All stage logic calls into `dsp`, `cache`, `scoring`, and
`plugins` modules.

**Source lines in current `engine.py`:** ~209–2,125 (bulk of the file)

**Target public API (unchanged):**

```python
# core/metadata/resolver.py

class MetadataResolutionEngine:
    def __init__(
        self,
        acoustid_provider: Any | None = None,
        metadata_provider: Any | None = None,
        spotify_provider: Any | None = None,
        hook_manager: Any | None = None,
    ) -> None: ...

    def resolve_track(
        self,
        request: ResolutionRequest,
        enabled_stages: list[str] | None = None,
    ) -> ResolutionResult: ...

    # Alias — must remain for backward compatibility during transition
    resolve_track_metadata = resolve_track

    def invalidate_cache(self, chromaprint: str | None = None) -> None: ...
    def score_candidate(self, ...) -> float: ...  # Delegates to scoring.py
```

**Dependency flow:**
```
resolver.py
  └─ core/metadata/dsp.py
  └─ core/metadata/cache.py
  └─ core/metadata/scoring.py
  └─ core/metadata/plugins.py
  └─ core/metadata/adapter.py (result hydration post-resolution)
  └─ core/metadata/schemas.py (ResolutionRequest, ResolutionResult)
  └─ core/matching_engine/trust_gate.py (verify_title_trust_gate, etc.)
  └─ core/hook_manager.py (alias resolution hook)
  └─ database/repositories/task_repository.py (ReviewTask creation — lazy import)
```

---

### 1.7 Target Module: `core/metadata/adapter.py`

**Responsibility:** Translate `ResolutionResult` into ORM entities. Implement relational
artist reconciliation. Create `track_artists` junction rows with typed roles.

**Source lines in current `engine.py`:** This concern is currently absent — it is
performed partially in `services/metadata_enhancer.py` without a clean boundary, which
is the root cause of the "Unknown Artist" and composite artist bugs.

**Target interface:**

```python
# core/metadata/adapter.py

from core.metadata.schemas import ResolutionResult
from database.music_database import Track, Artist, Album, TrackArtist

class ResolutionAdapter:
    """
    Translates ResolutionResult → ORM entity graph.
    Encapsulates all relational reconciliation logic.
    """

    def hydrate_track(
        self,
        result: ResolutionResult,
        session: Session,
        existing_track: Track | None = None,
    ) -> Track:
        """
        Upsert Track row.
        Calls reconcile_artist() for every credited artist.
        Calls reconcile_album() for the release.
        Populates track_artists junction rows.
        """
        ...

    def reconcile_artist(
        self,
        artist_name: str,
        role: Literal["primary", "featured", "remixer"],
        session: Session,
    ) -> Artist:
        """
        Look up existing Artist by normalised name.
        Create new row only if none found.
        NEVER creates a duplicate for the same normalised name.
        """
        ...

    def reconcile_album(
        self, album_title: str, mb_release_id: str | None, session: Session
    ) -> Album: ...

    def decompose_artist_string(
        self, raw_artist: str
    ) -> list[tuple[str, Literal["primary", "featured", "remixer"]]]:
        """
        Apply INV-META-2 tokenisation rules:
        1. Split on PRIMARY_SPLIT (& / ,)
        2. Detect FEATURED_SPLIT (feat. / ft. / featuring / with)
        3. Detect VS_SPLIT (vs. / vs)
        4. Detect REMIXER from version string in track title
        Returns list of (clean_name, role) tuples.
        """
        ...

    def extract_version_descriptor(
        self, title: str
    ) -> tuple[str, str | None]:
        """
        Parse version/edition descriptors from title.
        Returns (clean_title, descriptor_or_None).
        Descriptor must be written to tracks.edition / tracks.version.
        NEVER returns (original_title, None) when a descriptor was present.
        """
        ...
```

**Dependency flow:**
```
adapter.py
  └─ core/metadata/schemas.py
  └─ database/music_database.py (Track, Artist, Album, TrackArtist ORM models)
  └─ core.matching_engine.text_utils (normalize_title for artist dedup lookup)
```

**No imports from:** `echosync_core`, `plugins/`, `services/`.

---

### 1.8 Dependency Flow Diagram

```
services/metadata_enhancer.py ──┐
                                 ├──► core/metadata/resolver.py (MetadataResolutionEngine)
web/routes/metadata_review.py ──┘         │
                                           ├──► core/metadata/dsp.py
                                           │       └── echosync_core (Rust FFI)
                                           │
                                           ├──► core/metadata/cache.py
                                           │       └── database/music_database.py (read-only)
                                           │
                                           ├──► core/metadata/scoring.py
                                           │       └── core/matching_engine/
                                           │
                                           ├──► core/metadata/plugins.py
                                           │       └── core/nexus_framework/plugin_loader.py
                                           │       └── plugins/EchoSync/{acoustid,musicbrainz,spotify}/
                                           │
                                           └──► core/metadata/adapter.py
                                                   └── database/music_database.py (read-write)
```

---

## Section 2 — Root-Cause Trace: 2,812 "Unknown Artist" Tracks {#section-2}

### 2.1 Symptom

2,812 `Track` rows in `library.db` have `artist_id` pointing to the sentinel "Unknown
Artist" `Artist` record, even when the audio files carry valid artist tag data.

### 2.2 Ingestion Code Path (Observed)

The `MetadataResolutionEngine` produces a `ResolutionResult` that correctly populates
`result.artist = "Some Artist Name"`. However, the downstream code in
`services/metadata_enhancer.py` that persists the result to the database does not
perform relational artist reconciliation before writing the `Track` row.

**Observed pattern (inferred from code structure):**

```python
# services/metadata_enhancer.py — inferred hydration pattern (NOT patched)

track.artist_name = result.artist  # Written to a non-ORM column or dict field
# ↑ Saves the string but does NOT look up Artist by name
# ↑ Does NOT create or reuse an Artist row
# ↑ Does NOT create a track_artists junction row

# When the artist lookup is absent, the Track row is committed with
# artist_id = <id of "Unknown Artist"> (the default sentinel FK value)
```

### 2.3 Root Cause Chain

```
1. MetadataResolutionEngine.resolve_track() returns ResolutionResult.artist = "Artist Name"
   │
2. services/metadata_enhancer.py receives the result and begins tag hydration
   │
3. Hydration code writes result.artist to a raw string field or dict payload
   │
4. NO call to: `session.query(Artist).filter(Artist.name_normalised == normalised_name).first()`
   │
5. NO Artist row is looked up or created
   │
6. Track.artist_id defaults to the sentinel "Unknown Artist" FK (or remains NULL,
   later patched to the "Unknown Artist" row by a database trigger / default)
   │
7. commit() → Track row persisted with artist_id → "Unknown Artist"
```

### 2.4 Contributing Factor: Missing ORM Adapter Boundary

`engine.py` produces a `ResolutionResult` (a plain dataclass) but provides no mechanism
for translating it into relational ORM entities. The responsibility falls to callers
(`metadata_enhancer.py`) to perform artist reconciliation, but no shared utility exists,
so each call site implements (or omits) reconciliation independently.

### 2.5 Secondary Contributing Factor: Generic Artist Filtering

The engine's artist pre-filter in Stage 2 (AcoustID) uses a `generic_artists` set:

```python
# engine.py line 1610–1618
generic_artists = {
    "unknown", "unknown artist", "various artists", "va",
    "various", "soundtrack", "ost", "various artist",
}
```

When `baseline_artist` is in this set, the artist token filter is bypassed, allowing
candidates through without artist verification. However, the returned `result.artist`
may still be populated with a better value from the AcoustID candidate. The bug manifests
because the ORM layer ignores the corrected value.

### 2.6 Remediation Plan (Requires ADR)

The fix class is a new `core/metadata/adapter.py` (`ResolutionAdapter.reconcile_artist`)
as specified in Section 1.7. Implementation requires:

1. An approved ADR for the extraction.
2. A migration script to backfill the 2,812 tracks (read the correct artist from tag or
   `ResolutionResult`, look up or create `Artist`, update `track_artists`).
3. Unit tests for `reconcile_artist()` covering deduplication.

> [!CAUTION]
> No backfill migration may be run without an approved ADR and explicit user approval.

---

## Section 3 — Root-Cause Trace: 235 Composite Artist Entities {#section-3}

### 3.1 Symptom

235 `Artist` rows in `library.db` contain multi-artist delimiter tokens in the `name`
column, such as:

```
"Artist A & Artist B"
"Artist C feat. Artist D"
"Artist E, Artist F, Artist G"
"Artist H vs. Artist I"
"Artist J with Artist K"
```

These should have been decomposed into individual `Artist` rows linked via
`track_artists` with `primary` and `featured` roles.

### 3.2 Root Cause Chain

```
1. Audio file tag: ARTIST = "Artist A & Artist B"
   │
2. echosync_core.extract_metadata() returns raw_tags["artist"] = "Artist A & Artist B"
   │
3. engine.py hydrates baseline_artist = "Artist A & Artist B" (no decomposition)
   │
4. ResolutionResult.artist = "Artist A & Artist B" (composite string preserved)
   │
5. services/metadata_enhancer.py writes result.artist directly to a DB field OR
   creates ONE Artist row with name = "Artist A & Artist B"
   │
6. track_artists junction is not populated; the composite string leaks as a scalar
```

### 3.3 Missing Tokeniser

The `TrackParser` in `core/matching_engine/track_parser.py` detects `feat.` patterns
for `EchosyncTrack` construction but does not produce `(name, role)` tuples suitable
for ORM insertion. The `feat_artist` regex captures featured artist names but the result
is used only for `EchosyncTrack.featured_artist` (a denormalised string field), not
for junction table population.

**`TrackParser` patterns that detect but do not decompose (lines 83–86):**

```python
"feat_artist": re.compile(
    r"(?P<title>.+?)\s+(?:feat\.?|ft\.?|featuring)\s+(?P<feat_artist>.+?)"
    r"(?:\s*\((?P<version>[^)]+)\))?$",
    re.IGNORECASE,
),
```

The `feat_artist` capture group is not used to create a `track_artists` junction row.

### 3.4 Authoritative Tokeniser Rules Required

The following regex rules are required in `core/metadata/adapter.py` to correctly
decompose composite artist strings into `(name, role)` tuples:

```python
import re
from typing import Literal

ArtistRole = Literal["primary", "featured", "remixer"]

# Step 1: Extract featured artists (before splitting primary)
FEATURED_PATTERN = re.compile(
    r"\s+(?:feat\.?|ft\.?|featuring|with)\s+(.+?)(?=\s*[\(\[]|$)",
    re.IGNORECASE,
)

# Step 2: Split remaining primary artists on ampersand/slash/comma
PRIMARY_SPLIT_PATTERN = re.compile(
    r"\s*(?:&|/|,)\s*",
    re.IGNORECASE,
)

# Step 3: Detect vs. for battle/mashup credits
VS_PATTERN = re.compile(
    r"\s+vs\.?\s+",
    re.IGNORECASE,
)

# Step 4: Extract remixer from track title version string
REMIXER_PATTERN = re.compile(
    r"\(([^)]+?)\s+(?:Remix|Mix|Edit|Rework|Flip|Bootleg)\)",
    re.IGNORECASE,
)

def decompose_artist_string(
    raw: str, track_title: str = ""
) -> list[tuple[str, ArtistRole]]:
    """
    Returns a list of (cleaned_name, role) tuples.
    Order: primary artists first, featured artists second, remixers last.
    """
    results: list[tuple[str, ArtistRole]] = []

    # Extract featured artists
    feat_match = FEATURED_PATTERN.search(raw)
    featured_names: list[str] = []
    primary_raw = raw
    if feat_match:
        primary_raw = raw[:feat_match.start()].strip()
        feat_str = feat_match.group(1).strip()
        # Featured may be multiple: "feat. A & B"
        featured_names = [
            n.strip() for n in PRIMARY_SPLIT_PATTERN.split(feat_str) if n.strip()
        ]

    # Split primary on & / , / vs.
    vs_parts = VS_PATTERN.split(primary_raw)
    primary_names: list[str] = []
    for part in vs_parts:
        primary_names.extend(
            [n.strip() for n in PRIMARY_SPLIT_PATTERN.split(part) if n.strip()]
        )

    for name in primary_names:
        results.append((name, "primary"))
    for name in featured_names:
        results.append((name, "featured"))

    # Extract remixers from track title
    for m in REMIXER_PATTERN.finditer(track_title):
        remixer_str = m.group(1).strip()
        for name in PRIMARY_SPLIT_PATTERN.split(remixer_str):
            name = name.strip()
            if name:
                results.append((name, "remixer"))

    return results
```

### 3.5 Remediation Plan (Requires ADR)

1. Implement `decompose_artist_string` in `core/metadata/adapter.py`.
2. Backfill the 235 composite `Artist` rows:
   - For each composite `Artist`, decompose the name.
   - Look up or create individual `Artist` rows for each component.
   - For each `Track` linked to the composite `Artist`, create the correct
     `track_artists` junction rows.
   - Delete the composite `Artist` row if no other references remain.
3. Add a uniqueness constraint on `artists.name` (normalised) to prevent recurrence.

> [!CAUTION]
> The backfill is a write operation requiring an approved ADR and `db_write_lease`.

---

## Section 4 — Version/Edition Extraction Failure Analysis {#section-4}

### 4.1 Symptom

237 tracks have version or edition descriptors trapped inside `tracks.title`, with
`tracks.edition` and `tracks.version` both `NULL`. Examples:

```
tracks.title = "Song Name (Extended Mix)"   → tracks.edition = NULL
tracks.title = "Song Name (Radio Edit)"     → tracks.edition = NULL
tracks.title = "Song Name [Remastered]"     → tracks.version = NULL
tracks.title = "Song Name (Acoustic)"       → tracks.edition = NULL
```

### 4.2 Where Descriptors Should Be Extracted

**Source of resolution:** AcoustID candidate `disambiguation` field, MusicBrainz
recording `disambiguation`, or the raw title tag from the audio file.

**Current code path in `engine.py` (correct):**  
The engine correctly reads `disambiguation` into `cand_track.version` (line 1785):

```python
# engine.py line 1785
cand_track = EchosyncTrack(
    ...
    version=cand_meta.get("disambiguation") or cand_meta.get("version"),
)
```

And `build_native_tag_payload()` in `services/metadata_enhancer.py` (line 219–226)
correctly constructs `display_title` including the version string.

**The failure point:** Neither `engine.py` nor `metadata_enhancer.py` writes the
extracted version descriptor to `tracks.edition` or `tracks.version` ORM columns.
The `build_native_tag_payload()` result is used for physical tag writing only; the
version string is not persisted to the ORM model.

### 4.3 Lossless Parsing Rules

The following patterns must be detected and parsed into structured fields:

```python
VERSION_PATTERNS: dict[str, re.Pattern] = {
    # Remix / Edit / Rework / Bootleg → tracks.edition
    "remix": re.compile(
        r"\(([^)]*(?:Remix|Rmx|Rework|Flip|Bootleg|Mashup)[^)]*)\)",
        re.IGNORECASE,
    ),
    # Extended / Radio / Club / Original Mix → tracks.edition
    "mix_type": re.compile(
        r"\(([^)]*(?:Extended|Radio|Club|Album|Dub|Instrumental|Original)"
        r"\s*(?:Mix|Version|Edit|Cut)?[^)]*)\)",
        re.IGNORECASE,
    ),
    # Acoustic / Live / Demo / Alternate → tracks.edition
    "performance_type": re.compile(
        r"\(([^)]*(?:Acoustic|Live|Demo|Rough|Alternate|Alternative|"
        r"A[Cc]apella|Take\s+\d+)[^)]*)\)",
        re.IGNORECASE,
    ),
    # Remaster / Remastered → tracks.version
    "remaster": re.compile(
        r"[\(\[]([^)\]]*(?:Remaster(?:ed)?|Re-?master(?:ed)?)[^)\]]*)"
        r"[\)\]]",
        re.IGNORECASE,
    ),
    # Bracket variants [Extended Mix], [Radio Edit]
    "bracket_variant": re.compile(
        r"\[([^\]]*(?:Remix|Mix|Edit|Version|Remaster|Acoustic|Live)"
        r"[^\]]*)\]",
        re.IGNORECASE,
    ),
}

ORM_FIELD_MAP: dict[str, str] = {
    "remix": "edition",
    "mix_type": "edition",
    "performance_type": "edition",
    "remaster": "version",
    "bracket_variant": "edition",
}
```

### 4.4 Write-Back Protocol

**Physical tag write-back** (already implemented via `build_native_tag_payload`):

```python
# metadata_enhancer.py line 241
"subtitle": str(version) if version else "",
"version":  str(version) if version else "",
```

**ORM write-back (currently missing):**

```python
# Required in ResolutionAdapter.hydrate_track():
descriptor, pattern_key = extract_version_descriptor(result.title)
if descriptor:
    if ORM_FIELD_MAP[pattern_key] == "edition":
        track.edition = descriptor
    else:
        track.version = descriptor
    track.title = clean_title  # Stripped of descriptor
```

### 4.5 Anti-Patterns to Avoid

1. **Silent stripping:** Removing `(Extended Mix)` from `tracks.title` without writing it
   anywhere is a data-loss violation of INV-META-3.
2. **Double storage:** Keeping the descriptor in both `tracks.title` and `tracks.edition`
   leads to display inconsistencies (the display title is assembled dynamically from
   `title + edition` in `build_native_tag_payload`).
3. **Null coercion:** Treating an empty `disambiguation` field from MusicBrainz as
   equivalent to "no version" without checking the raw title tag first.

### 4.6 Verification Query (Read-Only)

```sql
-- Tracks with detectable version descriptors still in title
SELECT id, title, edition, version
FROM tracks
WHERE (title LIKE '%(Remix)%'
    OR title LIKE '%(Extended%'
    OR title LIKE '%(Radio Edit)%'
    OR title LIKE '%(Remaster%'
    OR title LIKE '%[%Mix%]%'
    OR title LIKE '%(Acoustic)%'
    OR title LIKE '%(Live)%')
  AND edition IS NULL
  AND version IS NULL;
```

---

## Section 5 — Comparative Analysis: MusicBrainz Picard Release-Group Matching {#section-5}

### 5.1 Picard's Release-Group Model

MusicBrainz Picard uses a multi-dimensional release candidate scoring system anchored
to the **Release Group** (the abstract work, e.g., "Hotel California" as a studio album
concept) rather than individual releases. Key properties:

| Picard Property | EchoSync Equivalent | Status |
|---|---|---|
| `release-group.primary-type` | `release_group.primary_type` | ✅ Implemented (line 349, 1799) |
| `release-group.secondary-types` | `release_group.secondary_types` | ✅ Implemented (line 354–357) |
| Duration score (parabolic) | `calculate_acoustid_duration_weight` | ✅ Implemented |
| Compilation demotion | `-35.0` penalty | ✅ Implemented |
| Studio album preference | `+25.0` bonus | ✅ Implemented |
| Country / release-event preference | Not implemented | ❌ Gap |
| Format preference (CD > Digital > Vinyl) | Not implemented | ❌ Gap |
| Earliest release date preference | Not implemented | ❌ Gap |
| `disambiguation` field parsing | Partial (stored in `EchosyncTrack.version`) | ⚠️ Partial |
| Various Artists detection | `"various artists" in artist_credit` | ✅ Implemented |

### 5.2 Studio Album Preference Parity

Picard ranks releases from studio albums highest when selecting which release to present
as canonical. EchoSync mirrors this:

```python
# engine.py line 368–369
if p_type == "album" and not s_types:
    bonus = 25.0  # Studio album with no secondary types
```

**Picard equivalent (from Picard source, for reference):**
```python
# Picard release_utils.py (conceptual approximation)
if release_group.primary_type == ReleaseGroupType.ALBUM:
    if not release_group.secondary_types:
        score += 0.25  # Canonical studio album
```

EchoSync uses an absolute point bonus on a 0–100 scale; Picard uses normalised
fractional weights. Both achieve the same ranking preference.

### 5.3 Compilation Demotion Parity

**Picard:** Compilations are demoted when the primary credit is "Various Artists" and
the recording is not itself a remix or DJ mix.

**EchoSync:**
```python
# engine.py line 359–365
is_compilation = any(t in s_types for t in ["compilation", "dj-mix", "sampler", "remix"])
title_has_mix = "mix" in c_title_lower or "remix" in c_title_lower

penalty = 0.0
if is_compilation and not title_has_mix:
    penalty = -35.0
```

**Gap vs. Picard:** Picard also demotes compilations when the release is a soundtrack,
live recording, or interview album (`secondary_types` = "Live", "Soundtrack", etc.).
EchoSync does not demote soundtrack releases — this is a deliberate difference for DJ
use cases where soundtracks may be primary listening material.

### 5.4 Duration Curve Comparison

| Approach | Curve | Gate |
|---|---|---|
| **Picard** | Linear penalty, weight = `max(0, 1 - delta/max_delta)` where `max_delta ≈ 10s` | Soft — no hard rejection |
| **EchoSync AcoustID** | Parabolic: `max(0, 1 - (delta/2.0)²)` | Hard — delta > 2.0s → score = 0 |
| **EchoSync Text** | Linear: `max(0, 1 - delta/8.0)` | Hard — delta > 8.0s → score = 0 |

EchoSync's AcoustID parabolic curve is **more aggressive** than Picard's linear approach:
at Δ = 1.0s, EchoSync yields 0.75 weight vs. Picard's ~0.90. This is intentional — a
fingerprint match should be rejected more aggressively when duration diverges, because
fingerprint identity and duration divergence together indicate a different edit/version.

### 5.5 Gaps Relative to Picard's Release Selection Heuristics

The following Picard features are not present in EchoSync's current implementation.
They represent potential future ADRs, not current bugs:

#### 5.5.1 Release Country / Release Event Preference

Picard prefers releases from the recording artist's home country or from the release's
country of first publication. EchoSync does not implement country-weighted scoring.

**Potential future ADR:** Add `release_country_preference` to `scoring.py` constants
and resolve via MusicBrainz `release.release-events[0].area`.

#### 5.5.2 Format Preference (Medium Type)

Picard prefers physical media over digital releases when both are available:
CD > Vinyl > Digital Media > Other.

EchoSync ignores `medium.format`. For a digital-native music management tool, this may
be acceptable, but it can cause EchoSync to select digital-only releases when the user
owns ripped CDs with correct track numbers.

#### 5.5.3 Earliest Release Date Preference

Picard picks the earliest release date from the release group when multiple releases
have identical other scores. EchoSync's `_extract_release_details` searches releases for
the target `release_id` but does not sort by date when no specific release is targeted.

#### 5.5.4 Recording Disambiguation Parsing

Picard parses `recording.disambiguation` to distinguish "live at Wembley, 2004" from
"remastered 2011". EchoSync stores `disambiguation` in `EchosyncTrack.version` but
does not parse it into structured categories.

**Partial fix available:** The `VERSION_PATTERNS` regex set in Section 4 would address
this if applied to `disambiguation` strings.

### 5.6 Summary Matrix

| Feature | Picard | EchoSync | Gap Level |
|---|---|---|---|
| Release group–anchored scoring | ✅ | ✅ | None |
| Studio album preference | ✅ | ✅ (+25.0) | None |
| Compilation demotion | ✅ | ✅ (-35.0) | Minor (Picard also demotes Live/Soundtrack) |
| Various Artists detection | ✅ | ✅ (-10.0) | None |
| Parabolic duration curve | Linear | Parabolic | EchoSync is stricter — intentional |
| Hard duration gate | No | ≤2.0s (AcoustID), ≤8.0s (text) | EchoSync is stricter — intentional |
| Country preference | ✅ | ❌ | Future ADR |
| Format preference | ✅ | ❌ | Future ADR |
| Earliest date preference | ✅ | Partial | Minor |
| Disambiguation parsing | ✅ | Partial | Section 4 fix addresses this |
| ISRC lookup stage | ❌ | ✅ Stage 3 | EchoSync advantage |
| Cryptographic signature gate | ❌ | ✅ Stage 0 | EchoSync advantage |
| Plugin extensibility | Plugin-based | Plugin-based (PluginRegistry) | Equivalent |

---

## Appendix A — Line Reference Index

| Concern | Lines in `engine.py` |
|---|---|
| Module docstring | 1–9 |
| `_extract_release_details` | 44–148 |
| `calculate_acoustid_duration_weight` | 151–156 |
| `calculate_text_duration_weight` | 159–163 |
| `extract_filename_title` | 166–206 |
| `MetadataResolutionEngine.__init__` | 215–229 |
| `invalidate_cache` | 231–236 |
| `_get_acoustid_plugin` | 246–267 |
| `_get_mb_plugin` | 269–284 |
| `score_candidate` | 286–388 |
| `resolve_track` (dispatcher) | 390–413 |
| `_resolve_acoustid_isolated` | 415–571 |
| `_resolve_aliases` (Stage 6) | 573–623 |
| `_execute_waterfall` (Stage 0–Fallback) | 625–1336 |
| Stage 0 (Signature Gate) | 791–842 |
| Fast-path (Embedded MBID) | 844–962 |
| Stage 2 (Local Cache) | 964–1027 |
| Stage 3 (AcoustID) | 1029–1145 |
| Stage 4 (ISRC) | 1147–1178 |
| Stage 5 (Text Waterfall) | 1180–1214 |
| Demoted MBID secondary fallback | 1216–1312 |
| Unresolved stub | 1314–1336 |
| `_check_local_chromaprint_cache` | 1340–1405 |
| `_resolve_acoustid` | 1407–1893 |
| `_resolve_isrc` | 1895–1949 |
| `_resolve_text_waterfall` | 1951–2124 |

---

## Appendix B — Files Inspected (Read-Only)

| File | Lines | Purpose |
|---|---|---|
| `core/metadata/engine.py` | 2,125 | Primary decomposition target |
| `services/metadata_enhancer.py` | 3,115 | Service layer consuming the engine |
| `web/routes/metadata_review.py` | 1,693 | API route using the engine |
| `core/matching_engine/track_parser.py` | 497 | Filename parsing and version detection |
| `database/working_database.py` | 574 | ReviewTask and working DB models |
| `docs/agents/system-invariants.md` | 70 | Existing architectural invariants |
| `docs/agents/adrs/0001–0004` | — | Existing ADR context |

**Zero code files were modified during this audit.**

