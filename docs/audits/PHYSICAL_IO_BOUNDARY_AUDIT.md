# Physical I/O Boundary Audit

## Overview
This report documents the findings of the strict read-only audit concerning physical library I/O boundaries. It evaluates the mapping of tags during Database Updates/Scans to the unified `EchosyncTrack` model, the reconstruction of rich titles during physical tag writing, and the respect for grouping preferences during library reorganization.

## 1. Database Update / Scanner Ingestion
**Status: FAIL**

### Findings:
- **`services/library_sync_service.py`**: The `parse_file` method (lines 191-200) bypasses the canonical `dsp.probe_physical_audio` and `dsp.extract_physical_tags` wrappers. Instead, it directly invokes `echosync_core.read_metadata` to retrieve a raw dictionary.
- **`core/orchestrator/ingestion.py`**: The raw dictionary is fed into `_parse_telemetry_dict` (lines 26-100), which performs dictionary cleansing before instantiating an `EchosyncTrack`.
- **Missing `TrackParser` Routing (`core/db/echo_sync_track.py`)**: `EchosyncTrack` does **not** route the raw title through `TrackParser.extract_version_descriptors`. Instead, `__post_init__` relies on an outdated, hardcoded regular expression (`_VERSION_KEYWORDS_PATTERN`, lines 289-331) to strip tags like `(Remix)` or `[Live]` and populate the `edition` field. 
- **Consequence**: This architectural divergence fails to correctly leverage the `TrackParser` boundary, resulting in inconsistent edition extraction and leaking scalar composite artist strings into the database instead of decomposing them into `primary_artists`, `featured_artists`, and `remixers`.

## 2. Physical Tag Writer (`metadata_enhancer.py`)
**Status: PASS**

### Findings:
- **Payload Construction (`build_native_tag_payload`)**: The tag writer successfully reconstructs rich display titles before writing to the physical file. If an `edition` or `version` exists, it securely concatenates it (e.g., `f"{raw_title} ({version})"`) into the `display_title` which populates the physical `TITLE` tag (lines 209-226).
- **Rust Isolation (`tag_file_verified`)**: The `tag_file_verified` method (lines 1335-1406) confirms that the actual file tag modifications are exclusively handed off to the Rust core (`echosync_core.write_metadata` or `echosync_core.write_tags`). Python is restricted to payload preparation and post-write verification logic.

## 3. Library Reorganizer (`library_reorganizer.py`)
**Status: PASS**

### Findings:
- **Dynamic Preferences Integration**: The reorganizer correctly dynamically fetches the `metadata_enhancement.group_standalone_singles` preference from the database config block (lines 145-149).
- **Routing & Normalization**: It invokes `normalize_singles_metadata` on the reconstructed track dictionary, injecting the fetched preference (line 152). If the user preference enables grouping and the track qualifies, it overrides the `album` property to `Singles` and `is_single` to `True`, which `build_destination_path` subsequently honors to successfully route the physical file into the dedicated Singles directory.

