# Media Manager Workflows & Identification Pipeline

## 1. Automated Import Pipeline (`AutoImporter`)

When new files arrive in `/data/downloads`, the `AutoImporter` service processes them through a multi-tier identification pipeline:

```text
Incoming Audio File
        │
        ▼
Step 0/1: Read Tags (Rust lofty) ────► Has MBID? ───► Auto-Bind Track
        │ (No)
        ▼
Step 2: ISRC Fast-Path Lookup ────────► Has ISRC? ───► Auto-Bind Track
        │ (No)
        ▼
Step 3: Cached Chromaprint ──────────► Has Hash? ───► Auto-Bind Track
        │ (No)
        ▼
Step 4: Generate Chromaprint (Rust) ──► Match? ─────► Auto-Bind Track
        │ (No)
        ▼
Step 5: Text Fallback Search ─────────► Score >= 85 ─► Auto-Bind Track
        │ (Score < 85)
        ▼
Queue in Review Desk (`working.db`)
```

---

## 2. Interactive Review Desk

Files with matching confidence below `MATCHING_THRESHOLD` (default 85) are moved to the **Review Desk** in `working.db`.
Users can manually approve candidate matches, edit metadata, or trigger manual searches.

---

## 3. Metadata Enhancement (`MetadataEnhancerService`)

Runs as a background job to retroactively scan existing tracks in `library.db` and retrieve missing attributes (MusicBrainz IDs, album artwork, lyrics, genres).
