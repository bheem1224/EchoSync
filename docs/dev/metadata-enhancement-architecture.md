# Metadata Enhancement Architecture, Matching Engine & Download Pipeline

## 1. Executive Summary & Architectural Overview

Metadata enhancement, candidate matching, and download pipeline management in EchoSync transform raw audio files, loose downloaded tracks, virtual candidates, and poorly tagged library items into canonical, structured, and verified library entities.

The subsystem bridges audio digital signal processing (Chromaprint / AcoustID), external metadata provider synchronization (MusicBrainz, Spotify), fuzzy text matching engines, database transaction pipelines across partitioned stores (`library.db` and `working.db`), native Rust file tagging via `echosync_core`, and the download lifecycle pipeline.

---

## 2. Ingress Pathways & Architecture

EchoSync provides four distinct entry points into the metadata pipeline:

1. **AutoImporter Daemon (`services/auto_importer.py` / `core/auto_importer.py`)**: Real-time monitoring of download/import directories, file fingerprinting, auto-matching, and file ingestion.
2. **Retroactive Enhancer (`services/metadata_enhancer.py`)**: Scheduled system job scanning the local library for unidentified or incomplete tracks, executing a 5-step cascading identification pipeline.
3. **Manual Review Queue (`web/routes/metadata_review.py`)**: UI review modal for single-track or batch ambiguous match resolution.
4. **Track & Library Manager (`web/routes/manager.py`, `web/routes/tracks.py`)**: In-library track editing, forced re-identifications, and metadata updates.

```
[Audio Ingress]
  ├── AutoImporter (File Watcher)
  ├── Retroactive System Job
  ├── Web Review Queue
  └── Library Manager Edit
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│              Cascading 5-Stage Identification               │
│  Stage 1: AcoustID / Chromaprint DSP Fingerprint          │
│  Stage 2: External Identifier Lookups (ISRC, MBID)          │
│  Stage 3: MusicBrainz / Spotify Provider Queries            │
│  Stage 4: Token-Sort Weighted Text Matching                 │
│  Stage 5: Directory Album-Cluster Voting & Fallbacks       │
└──────────────────────────────┬──────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
 [High Confidence (≥0.85)]            [Ambiguous (<0.85)]
   Automatic Tag & Import              Stage to review_tasks
```

---

## 3. Five-Stage Cascading Decision Tree

### Stage 1: Audio Fingerprinting (Chromaprint / AcoustID)
- Native extraction of Chromaprint fingerprints via `echosync_core`.
- High-confidence match ($score \ge 0.85$) resolves recording MBID directly.
- Resolves duration discrepancies and file renaming mismatches.

### Stage 2: Direct External Identifiers (ISRC / MBID)
- If track contains ISRC tag or `musicbrainz_trackid`, query MusicBrainz or Spotify directly.
- $1:1$ deterministic match bypasses fuzzy text heuristics.

### Stage 3: Provider API Metadata Queries
- Query MusicBrainz, Spotify, and Plex using normalized title, artist, and album parameters.
- Fetch candidate recordings, release groups, and album tracklists.

### Stage 4: Weighted Text & Duration Matching Engine
- Token-sort fuzzy matching with duration tolerance checking ($|\Delta t| \le 5000\text{ms}$).
- Edition detection guard (Remix, Live, Acoustic, Remastered).

### Stage 5: Directory Album Cluster Voting
- Group files by directory path. If $>70\%$ of files match a common MusicBrainz Release Group, force remaining tracks to bind to that release.

---

## 4. Matching Engine & Scoring Formulas (`core/matching_engine/`)

### 4.1 Weighted Score Calculation
The matching engine evaluates candidate pairs ($T_{local}, T_{candidate}$) on a scale from $0.0$ to $100.0$:

$$\text{Final Score} = (W_{title} \times S_{title}) + (W_{artist} \times S_{artist}) + (W_{album} \times S_{album}) + (W_{dur} \times S_{dur}) - P_{edition}$$

Where default weights are:
- $W_{title} = 0.40$
- $W_{artist} = 0.30$
- $W_{album} = 0.15$
- $W_{dur} = 0.15$

### 4.2 Duration Scoring
Duration score $S_{dur}$ applies a gaussian decay penalty for duration differences:

$$S_{dur} = \max\left(0, 100 - \left(\frac{|\Delta t_{\text{ms}}|}{1000} \times 10\right)\right)$$

Matches with $|\Delta t| > 15\,000\text{ms}$ are assigned $S_{dur} = 0$ and penalized heavily.

### 4.3 Edition & Version Safeguards
The matcher detects edition tokens (`remix`, `live`, `acoustic`, `instrumental`, `remastered`, `clean`, `explicit`, `deluxe`).
If $T_{local}$ lacks an edition token present in $T_{candidate}$, a fixed edition mismatch penalty ($P_{edition} = 35.0$) is applied to prevent remix drift.

---

## 5. Download Lifecycle Pipeline (`services/download_manager.py`)

When missing or upgrade-candidate tracks are identified, the Download Manager manages the acquisition state machine:

```
[Download Intent Event]
         │
         ▼
 Candidate Search (Slskd, Tidal, etc.)
         │
         ▼
 Candidate Ranking (Quality Profile & Bitrate Scoring)
         │
         ▼
 Staged in Download Queue (working.db)
         │
         ▼
 Acquisition & Transfer
         │
         ▼
 Stream Verification & Fingerprinting
         │
         ▼
 Gatekeeper Relocation -> Ingestion & Promotion
```

### Candidate Ranking Matrix
Candidates are scored against the active Quality Profile:
- **Format Rank**: FLAC / Lossless (+50) > 320kbps MP3 (+30) > Low Bitrate (-50).
- **Preferred Words**: Match bonus for release groups or specific encoders.
- **Ignored Words**: Immediate disqualification for prohibited terms (e.g. `talkover`, `bootleg`).

---

## 6. Data Mutations, Tagging & Hook Lifecycle

### 6.1 Database Mutations Matrix

```
[Incoming Metadata]
         │
         ├───────────────────────────────────────────────────────┐
         ▼                                                       ▼
   [library.db]                                             [working.db]
   ├── tracks                                               ├── review_tasks
   │   ├── title, normalized_title                          │   ├── status ('pending', 'approved')
   │   ├── artist_id, album_id                              │   ├── confidence_score
   │   ├── musicbrainz_id, isrc                             │   └── detected_metadata (JSON)
   │   └── metadata_status (JSON)                           │
   ├── local_media                                          └── download_queue
   │   └── file_path (relocation updates)                       ├── task_id
   ├── albums                                                   └── status ('queued', 'completed')
   ├── artists
   └── audio_fingerprints
       ├── media_id
       ├── chromaprint
       └── acoustid_id
```

### 6.2 File Tagging & Verification (`services/metadata_enhancer.py`)
Physical file tagging executes a zero-trust write-and-verify lifecycle:
1. Build native tag payload using display title, canonical title, artist, album, MBIDs, and AcoustID.
2. Escalated file permissions check.
3. Native Rust FFI write via `echosync_core.write_metadata(file_path, tags_to_write)` using lofty crate.
4. Immediate readback extraction and verification.

---

## 7. Rate Limiting & HTTP Client Governance (`core/request_manager.py`)

All external provider calls pass through `RequestManager`:
- **AcoustID API**: Rate limited to **1.0 req/s**.
- **MusicBrainz API**: Rate limited to **1.0 req/s** with mandated custom User-Agent (`Echosync/0.1.0`).
- Exponential backoff with jitter on HTTP 429 and 503 responses.
