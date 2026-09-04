# Native Rust FFI Engine (`echosync_core`)

## 1. Crate Architecture & PyO3 Integration

The native Rust core engine is located in `src/` and compiled alongside the Python package using `maturin` and PyO3 native bindings. It provides high-speed execution for CPU-bound and I/O-heavy operations that would otherwise introduce thread blocking in Python.

```text
src/
├── lib.rs                   # PyO3 module registration and FFI entry points
├── file_handling/           # Native filesystem scanner and file operations
│   ├── mod.rs
│   ├── scanner.rs           # Multi-threaded walkdir recursive directory traversal
│   └── fs_ops.rs            # Safe file move, copy, and delete with path verification
├── metadata/                # Audio tag reading and writing via lofty
│   ├── mod.rs
│   ├── extractor.rs         # High-speed tag extraction (ID3, FLAC, MP4, OGG)
│   └── writer.rs            # Native tag writing and Chromaprint fingerprinting
└── database/                # Ephemeral database writer
    ├── mod.rs
    └── cache.rs             # Direct rusqlite writer for working.db scan buffers
```

---

## 2. High-Speed Recursive Ingestion (`walkdir`)

The directory scanner in `src/file_handling/scanner.rs` leverages the Rust `walkdir` and `rayon` crates for concurrent directory traversal.

- **Batch Callback Execution:** Instead of building a massive in-memory list of thousands of audio files, `scan_directory` yields chunks (e.g. 500 records) back to Python via PyO3 callbacks using the modern `PyDict::new_bound` API.
- **Flat Memory Footprint:** Batching prevents memory spikes during initial library ingestion scans covering 100,000+ files.
- **Raw PyDict Conversion:** Rust constructs raw Python dictionary instances that map directly to SQLAlchemy ORM creation kwargs, eliminating intermediate Pydantic validation overhead.

---

## 3. Native Audio Tagging with `lofty`

All audio tagging operations in EchoSync route through the Rust `lofty` crate in `src/metadata/`.

### Supported Audio Formats
- FLAC (Vorbis Comments)
- MP3 (ID3v1, ID3v2.3, ID3v2.4)
- MP4 / M4A (iTunes-style atoms)
- OGG Vorbis / Opus
- WAV / AIFF (RIFF INFO tags)

### Prohibition of Python Tagging Libraries
To prevent corruption, character encoding mismatches, and lock contention:
- Python code **must never** import `mutagen`, `tinytag`, or `taglib`.
- Tag extraction and tag writing calls are exposed to Python exclusively through `echosync_core.read_tags(file_path)` and `echosync_core.write_tags(file_path, tags_dict)`.

---

## 4. Zero-Trust Path Traversal Sandboxing Boundary

To protect host filesystems from path traversal vulnerabilities in user-submitted metadata or plugin configurations, all native file operations enforce strict path canonicalization:

```rust
// Canonicalize path and verify root prefix in Rust before opening file handle
pub fn validate_and_canonicalize(path: &Path, root_boundary: &Path) -> Result<PathBuf, FfiError> {
    let canonical_path = path.canonicalize()?;
    let canonical_root = root_boundary.canonicalize()?;

    if canonical_path.starts_with(&canonical_root) {
        Ok(canonical_path)
    } else {
        Err(FfiError::PathTraversalViolation)
    }
}
```

- **Execution Gate:** Path resolution and canonicalization occur **inside the Rust FFI boundary** before any file descriptors are created.
- **Gatekeeper Pattern:** Unprivileged code and plugins cannot trigger Rust file operations directly; requests pass through `core/io_gatekeeper.py` to evaluate permissions once per batch before delegating execution to `echosync_core`.
