# `echosync_core` Native Rust FFI Engine

## 1. Overview & Crate Architecture

The `echosync_core` Rust crate provides high-performance native operations for EchoSync. It is compiled into a Python C-extension module using **PyO3** and **Maturin**.

### Directory Layout (`src/`)

```text
src/
├── lib.rs              # PyO3 module registration and Python FFI bindings
├── errors.rs           # Rust-to-Python exception mappings
├── file_handling/
│   ├── mod.rs          # File handling module definitions
│   ├── scanner.rs      # High-speed directory traversal via walkdir
│   ├── fs_ops.rs       # Safe atomic file move, copy, delete with path canonicalization
│   └── integrity.rs    # High-speed checksum and file integrity calculation
├── metadata/
│   ├── mod.rs          # Metadata module definitions
│   ├── extractor.rs    # Audio tag extraction via lofty (ID3, Vorbis, FLAC, MP4 atoms)
│   └── writer.rs       # Native audio tag writing via lofty
└── database/
    ├── mod.rs          # Database module definitions
    └── working_db.rs   # High-speed ephemeral reads/writes for working.db
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

## 3. Native Audio Tagging (`lofty`) & Chromaprint Boundary

All audio tag reading and tag writing operations route strictly through `lofty` in `src/metadata/` (`extractor.rs` and `writer.rs`):

- Reads and writes ID3v1, ID3v2, Vorbis Comments, APE, and MP4 atoms.
- **Architectural Boundary:** Acoustic Chromaprint fingerprint calculation is handled separately in Python at `core/matching_engine/fingerprinting.py`.
- **Prohibition:** Python modules must NEVER import `mutagen`, `tinytag`, or `taglib`. Verified via `tools/lint_audio_calls.py`.

---

## 4. Zero-Trust Path Sandboxing in Rust

Before performing file operations (`safe_move_file`, `copy_file`, `delete_file` in `src/file_handling/fs_ops.rs`), Rust resolves canonical paths (`std::fs::canonicalize`) and verifies they fall strictly within allowed root paths passed by `Gatekeeper`.
