# Native Rust Core & PyO3 FFI Architecture

## 1. Overview

`echosync_core` is a native Rust extension module compiled via Maturin and exposed to Python via PyO3 bindings. It isolates high-throughput, multi-threaded CPU and I/O bound operations from Python's GIL (Global Interpreter Lock).

---

## 2. Component Structure (`src/`)

```text
src/
├── lib.rs                   # PyO3 module initialization & Python FFI exports
├── file_handling/
│   ├── scanner.rs           # Multi-threaded recursive filesystem scanner (walkdir)
│   ├── integrity.rs         # File checksum & validation routines
│   └── fs_ops.rs            # Atomic move, copy, and delete implementations
├── metadata/
│   ├── extractor.rs         # Lofty metadata & tag parsing (FLAC, MP3, WAV, M4A, DSD)
│   ├── writer.rs            # Non-blocking, safe tag mutation writer
│   └── chromaprint.rs       # Symphonia audio decoding & Chromaprint fingerprint generator
└── database/
    └── rusqlite_working.rs  # High-speed direct ingestion buffer writes to working.db
```

---

## 3. High-Speed Multi-Threaded Filesystem Scanner

The Rust scanner uses `walkdir` and parallel thread pools to traverse large media libraries without blocking the Python event loop.

- **Performance Benchmark:** Indexes 50,000+ files in under 2 seconds.
- **PyO3 Batch Yielding:** Emits native Python dictionaries (`PyDict::new_bound`) in configurable chunks (e.g., 1,000 files per callback batch) to maintain a flat memory footprint and prevent memory spikes.

---

## 4. Lofty Audio Tagging & Symphonia Fingerprinting

### Tag Extraction & Mutation
- Uses native `lofty` Rust library to read and write audio tags without Python overhead.
- **Prohibition Enforcement:** Python libraries (`mutagen`, `tinytag`, `taglib`) are strictly prohibited in EchoSync core code and verified via `tools/lint_audio_calls.py`.

### Acoustic Fingerprinting
- Decodes audio streams using `symphonia`.
- Applies a **120-second sample window cap** to limit CPU usage per track during AcoustID fingerprint calculation.
- Passes raw PCM streams to `chromaprint` native bindings to emit Chromaprint hashes.

---

## 5. Security & Path Traversal Validation

To prevent zero-trust sandbox escapes:
1. Path validation occurs strictly within Rust prior to file handle operations using `std::fs::canonicalize`.
2. Target paths are checked against authorized root prefixes passed down by `IO Gatekeeper`.
