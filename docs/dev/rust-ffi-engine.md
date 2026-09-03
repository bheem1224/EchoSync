# `echosync_core` Native Rust FFI Engine

## 1. Overview & Crate Architecture

The `echosync_core` Rust crate provides high-performance native operations for EchoSync. It is compiled into a Python C-extension module using **PyO3** and **Maturin**.

### Directory Layout (`src/`)

```text
src/
├── lib.rs              # PyO3 module registration and Python bindings
├── errors.rs           # Rust-to-Python exception mappings
├── file_handling/
│   ├── scanner.rs      # High-speed directory traversal via walkdir
│   └── fs_ops.rs       # Safe atomic file move, copy, delete with path canonicalization
├── metadata/
│   ├── extractor.rs    # Audio tag extraction via lofty
│   └── fingerprint.rs  # Chromaprint acoustic fingerprint calculation
└── database/
    └── rusqlite_ops.rs # High-speed ephemeral reads for working.db only
```

---

## 2. Directory Scanner & PyO3 Callback Batching

To process massive libraries without triggering Python memory spikes, `scanner.rs` uses recursive `walkdir` traversal and callbacks into Python with chunks of audio records:

```rust
// PyO3 Bound API callback pattern
let py_dict = PyDict::new_bound(py);
py_dict.set_item("path", path_str)?;
py_dict.set_item("size", metadata.len())?;
py_dict.set_item("title", tag.title())?;
```

---

## 3. Native Audio Tagging & Chromaprint (`lofty`)

All audio tagging and fingerprinting operations route strictly through `lofty` in `src/metadata/`:

- Reads ID3v1, ID3v2, Vorbis Comments, APE, and MP4 atoms.
- Computes Chromaprint raw buffer hashes for MusicBrainz lookup.
- Prohibition: Python modules must NEVER import `mutagen`, `tinytag`, or `taglib`. Verified via `tools/lint_audio_calls.py`.

---

## 4. Zero-Trust Path Sandboxing in Rust

Before performing file operations (`safe_move_file`, `copy_file`, `delete_file`), Rust resolves canonical paths (`std::fs::canonicalize`) and verifies they fall strictly within allowed root paths passed by `Gatekeeper`.
