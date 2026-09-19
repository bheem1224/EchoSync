# Metadata Pipeline Final Verification Audit

## Overview
This report documents the findings of the final verification audit for the fully modernized metadata pipeline, ensuring compliance with the "Trust but Verify" sequence, Signed Track Partial Updates, Dynamic Preference Injection, and Canonical Model Unification.

## 1. Queue & `--force` Logic (`track_repository.py`, `engine.py`)
**Status: PASS**

### Findings:
- **`track_repository.py`**: The SQL queue is correctly prioritized using a multi-tiered `ORDER BY CASE` expression (lines 232-236). It prioritizes tracks with NO `ECHOSYNC_SIGNATURE` (1), followed by tracks WITH a signature but missing supplemental info (2), and finally fully populated tracks (3).
- **`engine.py`**: The `--force` mandate (`request.ignore_embedded_mbid`) correctly bypasses trust gates and cached data.
  - Stage 0 bypass (line 701): `if force_mode: signature_valid = False`.
  - Stage 1 Fast-Path bypass (line 711): `if signature_valid and embedded_mbid and not force_mode:`.
  - Stage 2 Cache bypass (line 854): `if chromaprint and not request.ignore_cache and not force_mode:`.
  - Stage 4 ISRC bypass (line 1019): `if tag_isrc and not force_mode:`.

## 2. Trust Gates & Signed Merges (`engine.py`)
**Status: PASS**

### Findings:
- **`engine.py`**: The pipeline successfully implements the "Trust but Verify" architecture.
  - The `verify_title_trust_gate` function has been removed from the main flow of Stage 3 (`_resolve_acoustid`). Instead, AcoustID candidate filtering is performed using the `should_bypass_filename_trust_gate` function, relying entirely on waveform scoring to override corrupted filenames when appropriate (line 1408).
  - Signed tracks securely merge data. If a cryptographic signature is valid (`signature_valid = True`), the engine correctly identifies divergent AcoustID candidates (`title_sim < 0.85`), stages a `ReviewTask` via `TaskRepository.create_review_task` with reason `SIGNED_METADATA_DIVERGENCE`, and explicitly preserves the original signed baseline title and artist during result assembly (lines 936-998).

## 3. Audit Dynamic Preferences (`metadata_enhancer.py` & `scoring.py`)
**Status: PASS**

### Findings:
- **`scoring.py`**: Dynamic preferences for Studio Albums are perfectly implemented. The `prefer_studio_album` parameter gates the +25.0 bonus correctly (line 102).
- **`metadata_enhancer.py`**: The `group_standalone_singles` preference is now fully wired into the metadata enhancement flow.
  - The dynamic configuration fetch for `metadata_enhancement.group_standalone_singles` was added to the orchestration blocks (`identify_file`, `enhance_track`, and `_enhance_library_metadata_loop`).
  - The `normalize_singles_metadata` helper is actively invoked, receiving both the `EchosyncTrack` and the user's config boolean immediately before database hydration (`adapter.hydrate_track`), successfully enforcing singles groupings or correctly bypassing it for exact AlbumArtist retention depending on the setting.

## 4. Audit Canonical Model Uniformity (`dsp.py`, `adapter.py`)
**Status: PASS**

### Findings:
- **`dsp.py`**: Successfully returns fully structured `EchosyncTrack` instances. Functions `extract_physical_tags` (line 97) and `probe_physical_audio` (line 110) completely eliminate raw tuple/dictionary leaks at the extraction phase, propagating strongly typed domains downstream.
- **`adapter.py`**: The `ResolutionAdapter` flawlessly bridges the canonical model and the database. The `hydrate_track` method natively accepts an `EchosyncTrack` (line 32) and maps it precisely to the `Track` ORM model, correctly invoking `extract_version_descriptors` and extracting relational components like `primary_artists`, `featured_artists`, and `remixers` to hydrate the `TrackArtist` junction tables.

