# Metadata Pipeline Audit Report: Flow & Strict Alignment

**Date:** 2026-09-19
**Auditor:** Antigravity (Architect Mode)
**Target:** `core/metadata/engine.py`, `services/metadata_enhancer.py`, `core/metadata/dsp.py`
**Scope:** "Trust but Verify" sequence, `--force` mode behavior, user preference integration, Rust-only file handling, and canonical model alignment.

## 1. `--force` Mode & AcoustID Trust Logic
The pipeline's mandate is that `--force` mode (`ignore_embedded_mbid`) should rely entirely on acoustic waveform scoring, ignoring embedded tags, ISRC fast-paths, and filename similarity trust gates.

**Findings & Violations:**
* **Stage 1 (Embedded MBID):** **PASS.** The engine correctly skips Stage 1 when `request.ignore_embedded_mbid` is `True`.
* **Stage 4 (ISRC Resolution):** **FAIL.** There is no bypass logic for ISRC resolution. Even when forced/ignoring embedded MBIDs, if a `tag_isrc` exists, the engine unconditionally executes `self._resolve_isrc()`.
* **Stage 3 (AcoustID Trust Gate):** **FAIL.** The `--force` flag is **not** passed down into `_resolve_acoustid`. The method continues to execute the `verify_title_trust_gate` and performs filename stem similarity checks, which actively filters out valid acoustic candidates if they don't match the corrupted physical filename.

## 2. Rust Core Isolation (`dsp.py`)
The architectural golden rule dictates zero Python-based file I/O or fingerprinting, deferring entirely to the `echosync_core` Rust FFI.

**Findings & Violations:**
* **Tag Extraction:** **PASS.** `extract_physical_tags` strictly wraps `echosync_core.extract_metadata`.
* **Fingerprinting:** **FAIL.** Inside `probe_physical_audio`, if the `echosync_core.fingerprint_and_hash_audio` Rust FFI fails, there is a hardcoded Python `try/except` fallback that invokes `FingerprintGenerator.generate_with_duration(str(file_path))`.
* **Fallback Detail:** `FingerprintGenerator` relies on `pyacoustid` (Python standard `chromaprint` bindings), which violates the strict Rust-only isolation mandate.

## 3. User Preference Integration
The audit investigated whether the orchestration layer dynamically reads user settings for metadata overrides.

**Findings & Violations:**
* **"Prefer Canonical Studio Album":** **FAIL.** The pipeline does not actively read a user preference for this. Instead, `core/metadata/scoring.py` implements this as a hardcoded static bonus (`bonus = 25.0`) for any release group matching `primary_type == "album"`.
* **"Group Standalone Singles":** **FAIL.** This is not a dynamic toggle. `services/metadata_enhancer.py` implements a hardcoded text-matching heuristic (`is_single_or_standalone`) targeting specific placeholders like `[standalone recordings]`.
* **Conclusion:** The pipeline lacks dynamic config injection for these heuristics; they are permanently enforced behaviors.

## 4. Canonical Model Alignment
The mandate requires `EchosyncTrack` to be the sole data vehicle across the pipeline boundaries, ensuring strong typing and relational hydration.

**Findings & Violations:**
* **`dsp.py` Boundary:** **FAIL.** `dsp.py` leaks unmapped raw tuples (`tuple[str | None, int]`) and raw tag dictionaries (`dict[str, Any]`) to the orchestrator.
* **`engine.py` Boundary:** **FAIL.** The `MetadataResolutionEngine` (`engine.py`) destructures raw dictionaries and pipes them into a `ResolutionResult` dataclass, not an `EchosyncTrack`.
* **Execution Flow:** `ResolutionResult` is passed from the engine back to `services/metadata_enhancer.py`, which then translates it using `ResolutionAdapter.hydrate_track(result, session, track)`.
* **Conclusion:** While `EchosyncTrack` is used deeply internally for string similarity matching (in `scoring.py`), it is **not** the unified cross-boundary transport model. Data flows sequentially as `Raw Dict/Tuple` -> `ResolutionResult` -> `Adapter` -> `SQLAlchemy ORM`.

