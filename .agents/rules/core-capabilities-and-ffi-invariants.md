---
trigger: always_on
description: Absolute native Rust FFI audio isolation, prohibition of Python audio packages, and deterministic plugin/provider ID hashing.
---

# Core Capabilities, FFI Invariants & Identifier Schemas

## 1. Native Rust Audio & DSP Isolation (`echosync_core`)
- **Strict Prohibition:** You are strictly forbidden from importing, installing, or executing third-party Python audio or tagging libraries (e.g., `acoustid`, `pyacoustid`, `mutagen`, `pydub`, `scipy`, `librosa`).
- **Native Accelerator Contract:** All audio stream probing, metadata extraction, physical tag writing, Chromaprint generation, and Chromaprint comparison (Hamming/Bit-error distance) MUST run through `echosync_core` via PyO3 FFI bindings.
- **Available Native Primitives:**
  - `echosync_core.read_metadata(path)`: Fast header and tag reading.
  - `echosync_core.write_metadata(path, tags)`: Safe UTF-8 byte-bounded physical tag writes.
  - `echosync_core.fingerprint_audio(path)`: Native chromaprint extraction.
  - `echosync_core.compare_chromaprints(fp1, fp2)`: Bit-exact native waveform comparison returning `[0.0, 1.0]`.

## 2. Deterministic Plugin & Provider Identifiers
- In EchoSync, `plugin_id` is an unsigned 32-bit integer derived strictly via:
  ```python
  import zlib
  plugin_id = zlib.crc32(canonical_namespace.encode("utf-8")) & 0xFFFFFFFF
  ```
- **Prohibition:** NEVER assign arbitrary, sequential, or mock integers (e.g., `575`) to any `plugin_id` column or attribute. All plugin IDs must be deterministic and reproducible across clean database boots.

## 3. Physical File vs Logical Track Invariant
- `LocalMedia` represents the physical reality on disk (exact path, format, bit depth, sample rate, mtime, inode).
- `Track` represents the canonical metadata entity (title, artist, album, edition).
- Physical file operations (moving, renaming, deleting, fingerprinting) must be anchored to `LocalMedia`. Never assume multiple `LocalMedia` files attached to a single `Track` share the same audio waveform without verifying via `echosync_core.compare_chromaprints`.

