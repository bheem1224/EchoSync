# 0001 — Metadata Resolution Waterfall

**Status:** Accepted  
**Date:** 2026-09-18  
**Supersedes:** *(none)*  
**Superseded by:** *(none)*

---

## Context & Problem Statement

`core/metadata/engine.py` (2,125 lines as of 2026-09-18) implements a monolithic
`MetadataResolutionEngine` class that conflates five distinct concerns:

1. **Physical DSP** — Rust FFI calls via `echosync_core` for audio probing, channel
   detection, duration extraction, and Chromaprint fingerprinting.
2. **In-memory & SQLite caching** — A bounded LRU `OrderedDict` (max 200 entries) and a
   peer-track lookup against `library.db` via SQLAlchemy.
3. **AcoustID resolution with Picard disambiguation** — HTTP egress to AcoustID,
   pre-network MBID filtering, parabolic duration weighting, studio album scoring, and
   compilation demotion.
4. **ISRC lookup** — Provider-agnostic dispatch through `dispatch_isrc_lookup`.
5. **Scoped text waterfall** — MusicBrainz `recording: + artist:` search with linear
   duration decay.

The docstring at line 3 originally described a 5-stage waterfall; the implementation has
grown to six stages plus an alias resolution hook. Without a formal specification, the
waterfall boundaries, scoring constants, and trust-gate semantics are undocumented and
prone to drift across `services/metadata_enhancer.py` and `web/routes/metadata_review.py`.

This ADR:
- Formalises the **6-stage waterfall** as the authoritative specification.
- Records all scoring constants, decay curves, and compilation heuristics.
- Defines the target modular decomposition of `engine.py` for a future extraction sprint.
- Establishes invariants that no future change may silently violate.

---

## Decision Drivers

- **Correctness:** 2,812 tracks carry "Unknown Artist" due to missing relational
  reconciliation during tag hydration — a bug enabled by the lack of a formal ORM
  adapter boundary.
- **Auditability:** Scoring constants (`+25.0` studio bonus, `-35.0` compilation penalty,
  parabolic `(delta/2.0)²` curve) are embedded inline without documentation.
- **Extensibility:** New providers (Spotify, Deezer) cannot be added without modifying
  `engine.py` directly, violating the Plugin Extensibility Invariant (INV-META-4).
- **Testability:** The 2,125-line monolith cannot be unit-tested at the component level.
  Mocking `echosync_core` and `PluginRegistry` requires full engine instantiation.
- **Security:** The `ECHOSYNC_SIGNATURE` invariant (INV-META-5) is enforced only by
  convention, not by module-level guards.

---

## Considered Options

### Option A — Status Quo (No Extraction)
Keep `engine.py` monolithic; document it with inline comments and docstrings only.

**Pros:** Zero migration risk; no interface changes.  
**Cons:** Untestable at component level; provider extensibility blocked; invariant drift
continues; future agents cannot reason about module boundaries via Graphify.

### Option B — Full Extraction (Six Modules)
Decompose `engine.py` into six focused modules:
`dsp.py`, `cache.py`, `scoring.py`, `plugins.py`, `resolver.py`, `adapter.py`.

**Pros:** Each module is testable in isolation; providers are fully plugin-dispatched;
ORM reconciliation is encapsulated in `adapter.py`; Graphify can index six distinct
architectural nodes.  
**Cons:** Requires careful interface design; breaking import changes for
`services/metadata_enhancer.py` and `web/routes/metadata_review.py`.

### Option C — Partial Extraction (Two Modules)
Extract only `scoring.py` and `adapter.py`; keep DSP, cache, and plugin dispatch inline.

**Pros:** Lower migration risk than Option B.  
**Cons:** Fails to resolve the ORM reconciliation bug class; provider extensibility still
blocked; cache eviction logic remains entangled with HTTP egress code.

---

## Decision Outcome

**Chosen option:** Option B — Full extraction into six modules.

The extraction must be preceded by this ADR (status: Accepted) and a dedicated
implementation ADR (0005 or next available) that specifies the exact public interfaces.
**No code changes may be made until the implementation ADR is approved.**

The waterfall specification below is the binding reference for both the current monolith
and the target decomposed architecture.

---

## Authoritative Waterfall Specification

### Stage 0 — Zero-Trust Cryptographic Signature

**Entry condition:** `raw_tags["echosync_signature"]` or `raw_tags["ECHOSYNC_SIGNATURE"]`
is present, and `baseline_title` and `baseline_artist` are both non-empty.

**Behaviour:**
1. Call `echosync_core.verify_audio_signature(file_path, title, artist, sig_tag)`.
2. If verification passes → return `ResolutionResult` with `confidence_score=1.0` and
   `resolution_method="signature_verified"` immediately, bypassing all subsequent stages.
3. If verification fails → log a warning; set `signature_valid = False`; **do not** short-circuit.
   The file continues through the waterfall.
4. If a valid embedded MBID exists but `signature_valid` is `False` → demote the MBID to
   `deferred_embedded_mbid` (secondary fallback after Stage 5); do not fast-path it.

**Invariants:**
- INV-0001-S0-1: A file whose signature fails verification must never be returned with
  `confidence_score=1.0`.
- INV-0001-S0-2: `ECHOSYNC_SIGNATURE` is verified via `echosync_core` only; no Python
  reimplementation is permitted.

---

### Stage 1 — Physical DSP & Bounded Chromaprint Cache

#### 1a — Physical DSP

**Primary path:** `echosync_core.fingerprint_and_hash_audio(file_path, False)`  
Returns `(chromaprint: str, duration_sec: float)` tuple.

**Fallback:** `FingerprintGenerator.generate_with_duration(file_path)` (Python wrapper).

**Multi-channel guard:**  
If `raw_tags["channels"] > 2` → skip Chromaprint extraction entirely.  
Rationale: Chromaprint is undefined for surround-sound audio; extraction produces
corrupt fingerprints.

**Duration normalisation:**  
`duration_ms = round(duration_sec * 1000)` when `duration_sec < 10000` (seconds unit);  
`duration_ms = round(duration_sec)` otherwise (milliseconds unit).

**Stale fingerprint guard:**  
If `len(chromaprint) > 4000` → invalidate and regenerate.

#### 1b — Bounded Local Chromaprint Cache

**Lookup order:**
1. In-memory `OrderedDict` (LRU, max 200 entries).
2. SQLite `library.db` peer-track query:
   ```sql
   SELECT Track.* FROM Track
   JOIN LocalMedia ON LocalMedia.track_id = Track.id
   JOIN AudioFingerprint ON AudioFingerprint.media_id = LocalMedia.media_id
   WHERE AudioFingerprint.chromaprint = :cp
     AND Track.musicbrainz_id IS NOT NULL
     AND Track.musicbrainz_id NOT IN ('', 'NOT_FOUND')
     AND Track.title IS NOT NULL
     AND Track.sync_id != :current_sync_id
   LIMIT 1
   ```
3. Cache hit → verify via `verify_title_trust_gate(min_similarity=0.60)` and filename
   contradiction check before returning.
4. Cache eviction: when `len(cache) >= 200`, evict the oldest entry (LRU via
   `OrderedDict.popitem(last=False)`).

**Invariants:**
- INV-0001-S1-1: Cache capacity must never exceed 200 entries.
- INV-0001-S1-2: A cache hit must pass the trust gate before being returned; it must
  be invalidated and not returned if the candidate title contradicts the physical filename
  (similarity < 0.60).

---

### Stage 2 — AcoustID Resolution with Picard Disambiguation

> **Note:** Internally labelled "Stage 3" in the current source at line 1029 due to a
> legacy numbering artefact. This ADR normalises it as Stage 2 (AcoustID) with the
> cache bump as Stage 1b above.

**Precondition:** `chromaprint` is non-None and `duration_ms > 0`.

**Provider dispatch:**  
`PluginRegistry.get_plugins_with_capability(Capability.RESOLVE_FINGERPRINT)` →
prefer plugins advertising `fingerprint_algorithms = ["chromaprint"]`.

#### 2a — AcoustID Network Call

```python
details = acoustid_plugin.resolve_fingerprint_details(
    fingerprint=chromaprint,
    duration=round(duration_ms / 1000.0)
)
```

Returns: `{"acoustid_id": str, "recordings": list[dict], "mbids": list[str]}`.

#### 2b — Pre-Network In-Memory Filtering (Three Steps)

Before any MusicBrainz HTTP call, filter candidate MBIDs:

**Step A — Hard Duration Gate:**

$$\Delta = |t_{\text{candidate}} - t_{\text{file}}| \quad (\text{seconds})$$

If $\Delta > 2.0\text{s}$ → discard candidate. No exceptions.

**Step B — Artist Token Filter:**  
Skip if `baseline_artist` is empty, `"Unknown Artist"`, or in the generic sentinel set.
Otherwise: require token overlap (substring containment OR word-token intersection OR
`SequenceMatcher.ratio() >= 0.50`) between `baseline_artist` and candidate artist.

**Step C — Title Pre-Filter (filename-first):**  
Derive `filename_stem` from `extract_filename_title(filename)`, not from `baseline_title`.

Pre-rank score = `(title_similarity × 0.8) + (acoustid_cluster_score × 0.2)`.

Discard candidates where `title_similarity < 0.35` unless veto applies.

Veto conditions (via `should_bypass_filename_trust_gate`):
- `acoustid_score >= 0.95` **and** `duration_delta <= 1.0s`
- `has_signature = True`
- `has_identifiable_tags = True`

#### 2c — MusicBrainz Detail Lookup

Top 2 pre-filtered candidates are queried via:
```python
mb_plugin.get_metadata(mbid_str)  # Capability.FETCH_METADATA
```

**Step D — Secondary Duration Gate on MB metadata:**  
Same ≤2.0s gate applied to the authoritative MB `length` field (in milliseconds).
Reject candidates exceeding the gate.

#### 2d — Candidate Scoring

$$\text{score}_{\text{cand}} = \underbrace{(\text{matcher\_score} \times 0.7)}_{\text{WeightedMatchingEngine}} + \underbrace{(\text{dur\_weight} \times 30.0)}_{\text{parabolic}} + \underbrace{\text{album\_bonus}}_{\text{studio}}$$

**Parabolic AcoustID Duration Weight:**

$$\text{weight}(\Delta) = \begin{cases} \max(0.0,\ 1.0 - (\Delta / 2.0)^2) & \Delta \le 2.0\text{s} \\ 0.0 & \Delta > 2.0\text{s} \end{cases}$$

Key values:
| $\Delta$ (s) | Weight |
|---|---|
| 0.0 | 1.000 |
| 0.5 | 0.938 |
| 1.0 | 0.750 |
| 1.5 | 0.438 |
| 2.0 | 0.000 |

**Progressive Duration Multiplier (final score adjustment):**

$$\text{score}_{\text{final}} = \begin{cases} \text{score}_{\text{cand}} \times (0.95 + 0.05 \times \text{weight}) & \Delta \le 1.0\text{s} \\ \text{score}_{\text{cand}} \times \text{weight} & \Delta > 1.0\text{s} \end{cases}$$

**Studio Album Bonus: +25.0**  
Condition: `release_group.primary_type == "Album"` AND `release_group.secondary_types == []`

**Compilation Demotion: −35.0**  
Condition: `secondary_types` contains any of `{"compilation", "dj-mix", "sampler", "remix"}`  
**Exception:** No penalty if `candidate_title.lower()` contains `"mix"` or `"remix"`.

**Various Artists Penalty: −10.0**  
Condition: `"various artists"` in `str(artist_credit).lower()`

**Compilation Provenance Caching (`COMPILATION_SOURCE`):**  
When a track is resolved from a compilation release group, the compilation album and
release MBID are preserved as `repack_source` / `repack_release_mbid` via
`realign_repack_metadata()` in `services/metadata_enhancer.py`. The canonical studio
release is then populated in `album` / `album_title` / `musicbrainz_album_id`.

**Confidence threshold for hit:** `candidate_score >= 60.0`

**Short-circuit condition:** If `matcher_score >= 80.0` AND `title_similarity >= 0.60` →
accept immediately without inspecting remaining candidates.

#### 2e — Signed File Divergence Check

If `signature_valid = True` and AcoustID candidate title diverges from the verified
baseline title (`SequenceMatcher.ratio() < 0.85`) → stage a `RESOLVE_METADATA_CONFLICT`
ReviewTask and return the signed metadata unchanged (`confidence_score=1.0`).

---

### Stage 3 — ISRC Lookup

**Precondition:** `tag_isrc` is non-None (never conditioned on environment or dev mode).

**Dispatch:**
```python
from services.isrc_lookup_service import dispatch_isrc_lookup
isrc_track = dispatch_isrc_lookup(isrc.strip())
```

**Trust gate:** Candidate title must pass `verify_title_trust_gate(min_similarity=0.60)`.

**Confidence score on hit:** `0.92`

**Invariant (INV-META-8):** ISRC resolution is active in ALL environments. It is never
disabled by `_NETWORK_DISABLED` or any other diagnostic flag.

---

### Stage 4 — Scoped Text Waterfall

**Precondition:** `baseline_title` and `baseline_artist` are both non-empty.

**Query strategy (anti-discography-leak):**  
MusicBrainz `recording: + artist:` search. Plain `artist:` searches that return entire
discographies are explicitly blocked.

**Title sanitisation:**  
Strip leading track-number prefixes before querying:
```python
re.sub(r"^(?:(?:\d{1,2}[.-])?\d{1,3}[\s\-_.]{1,3}\s*)+", "", baseline_title)
```

**Linear Duration Decay Curve:**

$$\text{weight}_{\text{text}}(\Delta) = \begin{cases} \max(0.0,\ 1.0 - \Delta / 8.0) & \Delta \le 8.0\text{s} \\ 0.0 & \Delta > 8.0\text{s} \end{cases}$$

Key values:
| $\Delta$ (s) | Weight |
|---|---|
| 0 | 1.000 |
| 2 | 0.750 |
| 4 | 0.500 |
| 6 | 0.250 |
| 8 | 0.000 |

**Scoring:** `score = WeightedMatchingEngine.calculate_match(query, candidate).confidence_score × text_dur_weight`

**Hit threshold:** `score >= 85.0` (0–100 scale).

**Confidence score on hit:** `score / 100.0` (normalised to 0–1).

---

### Stage 5 — ReviewTask Fallback (Unresolved Stub)

**Entry condition:** All Stages 0–4 (and the demoted embedded MBID secondary fallback)
have returned no result.

**Behaviour:**
- Return a zero-confidence `ResolutionResult` with `confidence_score=0.0` and
  `resolution_method="text_waterfall"`.
- Populate `artist = baseline_artist or "Unknown Artist"`.
- Populate `title = baseline_title or file_path.stem`.
- **Do NOT stamp `ECHOSYNC_SIGNATURE`.**
- Caller (`services/metadata_enhancer.py`) is responsible for creating a `ReviewTask`
  entry in `working.db`.

**Invariant (INV-0001-S5-1):** Stage 5 results must never carry a non-empty
`echosync_signature` field. Any code path that writes a signature in the fallback branch
is a critical invariant violation.

---

### Stage 6 — Entity Alias Resolution

**Always executes** after the main waterfall (Stages 0–5) for results with a `sync_id`.

**Dispatch:**
```python
self.hook_manager.execute_hook("resolve_entity_aliases", AliasResolutionContext(...))
```

Returns a list of `EntityAliasProposal` objects attached to `ResolutionResult.alias_proposals`.

---

## Target Modular Decomposition

The following six modules represent the planned extraction of `engine.py`. No code changes
are authorised under this ADR; they require a separate implementation ADR.

| Target Module | Responsibility | Key Classes / Functions |
|---|---|---|
| `core/metadata/dsp.py` | Rust FFI audio probing, channel detection, duration extraction, Chromaprint clamping | `extract_physical_tags()`, `generate_chromaprint()`, `MultiChannelGuard` |
| `core/metadata/cache.py` | Bounded LRU OrderedDict + SQLite peer-track chromaprint cache | `ChromaprintCache`, `LRUBoundedCache` |
| `core/metadata/scoring.py` | Parabolic duration curves, linear text decay, studio bonus, compilation demotion | `calculate_acoustid_duration_weight()`, `calculate_text_duration_weight()`, `score_candidate()` |
| `core/metadata/plugins.py` | PluginRegistry provider resolution for AcoustID, MB, Spotify; ISRC dispatch | `get_acoustid_plugin()`, `get_mb_plugin()`, `dispatch_isrc_lookup()` |
| `core/metadata/resolver.py` | State machine orchestrating Stages 0–6; trust-gate integration | `MetadataResolutionEngine`, `_execute_waterfall()`, `_resolve_*()` methods |
| `core/metadata/adapter.py` | Translating `ResolutionResult` → ORM entities; relational artist reconciliation; junction row creation | `ResolutionAdapter`, `hydrate_track()`, `reconcile_artist()`, `create_junction_row()` |

---

## Invariants

- **INV-0001-1:** The 6-stage waterfall order (0 → Fast-path → 1 → 2 → 3 → 4 → 5 → 6) must not be altered without a superseding ADR.
- **INV-0001-2:** The AcoustID hard duration gate is fixed at ≤2.0s. No file with |Δ| > 2.0s may produce a Stage 2 hit.
- **INV-0001-3:** The studio album bonus is exactly **+25.0** on the 0–100 scale; the compilation penalty is exactly **−35.0**.
- **INV-0001-4:** The compilation exception (no penalty when title contains "mix"/"remix") is mandatory and must not be removed.
- **INV-0001-5:** Stage 5 (ReviewTask fallback) must never stamp `ECHOSYNC_SIGNATURE`.
- **INV-0001-6:** ISRC resolution (Stage 3) must be active in all environments.
- **INV-0001-7:** `PluginRegistry` is the sole provider resolution mechanism. Direct plugin module imports in `core/` or `services/` are prohibited.
- **INV-0001-8:** Text waterfall hard duration cutoff is ≤8.0s (linear decay; zero weight at 8.0s).
- **INV-0001-9:** Cache capacity must never exceed 200 entries; eviction policy is LRU.
- **INV-0001-10:** `artists.name` must never contain multi-artist delimiter tokens; junction normalisation via `track_artists` is mandatory.

---

## Consequences

### Positive
- Formal specification enables deterministic unit tests per stage.
- Scoring constants are version-controlled and auditable.
- Modular decomposition plan resolves the 2,812 "Unknown Artist" bug class via `adapter.py`.
- Plugin extensibility is explicit; new providers require zero changes to `resolver.py`.

### Negative / Trade-offs
- Full extraction (Option B) requires careful interface design to avoid circular imports
  between `resolver.py` and `plugins.py`.
- `services/metadata_enhancer.py` and `web/routes/metadata_review.py` import paths will
  need updating once extraction is complete.

### Risks & Mitigations
| Risk | Mitigation |
|---|---|
| Extraction introduces regressions in trust-gate logic | Cover each stage with unit tests before extraction; run `uv run pytest tests/` after each module boundary |
| Scoring constant drift after extraction | Constants must be defined once in `scoring.py`; all other modules import from it |
| ORM reconciliation adapter creates N+1 queries | Batch artist lookups within a single `session_scope()` per batch |

