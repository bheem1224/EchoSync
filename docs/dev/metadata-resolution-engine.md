# Metadata Resolution Engine Architecture

## 1. Executive Summary

EchoSync employs a centralized, 6-Stage Metadata Resolution Waterfall to evaluate incoming audio files, resolve canonical track identities, and attach high-confidence metadata attributes. Hand-rolled integer scoring algorithms (`score_recording_candidate`) have been completely purged from `services/metadata_enhancer.py`. Candidate scoring and ranking across all stages are governed strictly by `WeightedMatchingEngine(PROFILE_EXACT_SYNC)`.

---

## 2. The 6-Stage Resolution Waterfall

```text
Incoming Physical / Virtual Media Item
                 │
                 ▼
 ┌──────────────────────────────┐
 │ Stage 1: Embedded MBID       │ ──► Match found? ──► Terminate Waterfall
 └──────────────┬───────────────┘
                │ Miss
                ▼
 ┌──────────────────────────────┐
 │ Stage 2: Fingerprint Cache   │ ──► Match found? ──► Terminate Waterfall
 └──────────────┬───────────────┘
                │ Miss
                ▼
 ┌──────────────────────────────┐
 │ Stage 3: AcoustID Acoustic   │ ──► Confidence >= 0.90? ──► Terminate Waterfall
 └──────────────┬───────────────┘
                │ Miss / Low Confidence
                ▼
 ┌──────────────────────────────┐
 │ Stage 4: ISRC Validation     │ ──► Match found? ──► Terminate Waterfall
 └──────────────┬───────────────┘
                │ Miss
                ▼
 ┌──────────────────────────────┐
 │ Stage 5: MusicBrainz Text    │ ──► Candidate List ──► Rank via Weighted Engine
 └──────────────┬───────────────┘
                │
                ▼
 ┌──────────────────────────────┐
 │ Stage 6: Spotify Enrichment  │ ──► Enrich Artwork / Genres / Popularity
 └──────────────────────────────┘
```

### Stage 1: Embedded MBID Fast-Path
- Checks incoming audio tags for pre-existing `musicbrainz_trackid`, `musicbrainz_releasetrackid`, or `musicbrainz_recordingid`.
- If a valid MBID is detected, the engine bypasses external search queries and directly fetches the canonical entity from the MusicBrainz API / local cache.

### Stage 2: Local Fingerprint Cache
- Computes raw Chromaprint fingerprint of the track.
- Queries `library.db` and `working.db` cached fingerprint tables for exact or high-similarity matches ($\ge 0.95$).

### Stage 3: AcoustID Acoustic Scan
- **Sample Window Cap:** Native Rust Symphonia decoder extracts raw audio PCM data capped strictly at a 120-second sample window to guarantee fast execution without unbounded I/O.
- **Filename Stem Pre-Ranking:** Filename stems are tokenized and pre-ranked to reduce AcoustID candidate search spaces.
- **Duration Gate:** Strict duration constraint filter: $\Delta t = |t_{\text{file}} - t_{\text{candidate}}| \le 2.0\text{s}$. Candidates exceeding 2.0 seconds duration difference are instantly discarded.
- **API Call Rate Cap:** Capped at a maximum of 2 external MusicBrainz API calls per track scan.

### Stage 4: ISRC Validation
- Validates embedded audio ISRC codes against MusicBrainz and streaming provider indexes.
- Provides high-confidence matching for modern commercial releases.

### Stage 5: MusicBrainz Text Waterfall
- Executes structured text queries (`title`, `artist`, `album`, `year`).
- Applies an **8.0s parabolic decay curve** to score title/artist similarity while heavily penalizing length mismatch.

### Stage 6: Spotify Plugin Enrichment
- Executes post-resolution enrichment to populate high-resolution album artwork (640x640), Spotify popularity metrics, and genre tags.

---

## 3. Candidate Scoring & Weighted Matching Engine

All candidates emitted during Stages 3, 4, and 5 pass through `WeightedMatchingEngine` using the `PROFILE_EXACT_SYNC` profile configuration:

```python
PROFILE_EXACT_SYNC = {
    "title_weight": 0.35,
    "artist_weight": 0.30,
    "album_weight": 0.15,
    "duration_weight": 0.15,
    "year_weight": 0.05,
    "decay_factor": 8.0
}
```

### Decision Thresholds

- **Match Score $\ge 0.90$:** Automated Promotion. Metadata is written to file via `IO Gatekeeper`, and track is inserted into `library.db`.
- **Match Score $0.60 \le S < 0.90$:** Pushed to Metadata Review Queue (`/api/v1/core/metadata_review`) for manual inspection.
- **Match Score $< 0.60$:** Unmatched / Flagged as missing canonical metadata.

---

## 4. Verification & Audit Metrics

Verification of the resolution engine logic is enforced via unit and integration tests:
- `tests/services/test_metadata_resolution.py`
- `tests/core/test_matching_engine.py`
