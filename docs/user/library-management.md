# Library Management & Ingestion Workflows

## 1. Overview

EchoSync manages physical audio media through an automated, zero-loss ingestion and metadata enrichment pipeline. Files placed in staging directories (`/data/downloads`) are ingested, matched against canonical music graphs, renamed according to pathing rules, and linked to media server integrations.

---

## 2. Ingestion & Automated Metadata Pipeline

```text
Incoming Audio File (/data/downloads)
       │
       ▼
[Rust Engine Scanner] ──► Lofty Tag Extraction (0-copy header parsing)
       │
       ▼
[working.db Staging Queue] ──► Ingestion Telemetry Event Emitted
       │
       ▼
[6-Stage Metadata Resolution Waterfall]
       ├── Stage 1: Embedded MBID Fast-Path
       ├── Stage 2: Local Fingerprint Cache
       ├── Stage 3: AcoustID Acoustic Fingerprint (Rust Symphonia + Chromaprint)
       ├── Stage 4: ISRC Validation
       ├── Stage 5: MusicBrainz Text Waterfall (8s parabolic decay)
       └── Stage 6: Spotify Plugin Enrichment
       │
       ├── Match Score >= Auto-Apply Threshold (e.g., 0.90) ──► Auto-Promotion to library.db
       └── Match Score < Threshold ──► Metadata Review Queue (`/api/v1/core/metadata_review`)
```

---

## 3. Atomic Promotion & Zero-Trust File Operations

When a track is promoted from staging (`working.db`) to the canonical library (`library.db`):

1. **Path Resolution:** The target destination path is computed using structured naming templates (e.g. `{artist}/{album} ({year})/{track_number} - {title}.{ext}`).
2. **IO Gatekeeper Dispatch:** All physical file relocation and tag embedding operations route strictly through `core/io_gatekeeper.py` calling native `echosync_core` functions (`safe_move_file`, native Lofty tag writing).
3. **Database Promotion:** `PhysicalMedia` records are written to `library.db` and linked to `CanonicalTrack` entities via dual-session context handlers.
4. **Media Server Refresh:** Downstream plugins (Plex, Jellyfin, Navidrome) receive sync events via `EventBus` to notify media servers of new content.

---

## 4. Metadata Review Queue Operations

Tracks requiring manual intervention appear in the Metadata Review Queue.

### Review Queue API Endpoints

- **List Review Tasks:** `GET /api/v1/core/metadata_review`
- **Trigger Stage 3 AcoustID Scan:** `POST /api/v1/core/metadata_review/{task_id}/lookup/acoustid`
- **Trigger Stage 5 MusicBrainz Lookup:** `POST /api/v1/core/metadata_review/{task_id}/lookup/musicbrainz`
- **Approve Selected Candidate:** `POST /api/v1/core/metadata_review/{task_id}/approve`
- **Ignore Task:** `DELETE /api/v1/core/metadata/queue/ignore`

---

## 5. Duplicate Detection & Library Hygiene

EchoSync detects duplicate physical tracks using a dual strategy:

1. **Acoustic Fingerprint Hash:** Exact Chromaprint raw hash matching identifies bit-identical audio content regardless of file format or metadata variations.
2. **Canonical Metadata Keying:** Matching ISRC codes or normalized `(title, artist, duration_delta <= 2s)` pairs.

### Resolution Options
- **In-Place Upgrade:** Automatically replace a lower-bitrate file (e.g. 128kbps MP3) with a higher-quality acquisition (e.g. 24-bit FLAC).
- **Safe Purge:** Retain the canonical highest-quality track and delete redundant physical media via `IO Gatekeeper`.

---

## 6. Troubleshooting Table

| Symptom | Probable Cause | Corrective Action |
| :--- | :--- | :--- |
| Ingested file stuck in Review Queue | Match score fell below `auto_apply_confidence` threshold | Open Review Queue UI (`/api/v1/core/metadata_review`), trigger manual lookup or adjust threshold in Settings |
| `GatekeeperError: Path Outside Sandbox` | File destination path resolves outside `/data/library` root | Verify `system.library_path` setting and target file path permissions |
| Duplicate detection missed a track | AcoustID scan skipped or duration delta > 2.0s | Run AcoustID lookup manually via API or adjust `metadata.acoustid_duration_gate` |
