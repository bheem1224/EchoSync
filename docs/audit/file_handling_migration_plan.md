# `core/file_handling/` Dependency & Migration Audit

**Role:** Senior Codebase Systems Auditor & Refactoring Architect
**Target:** `core/file_handling/`

## 1. Executive Summary
The `core/file_handling/` module is currently a hybrid of low-level I/O tasks (tagging, moving, path validation) and high-level Python orchestration (storage configuration). This audit proposes a structured disassembly plan to route heavy I/O tasks to the high-performance `echosync_core` Rust module while shifting standard orchestration logic into standard repository patterns.

This migration strategy adheres to strict architectural constraints: a modular Rust core structure, rigid database access boundaries, a Python-owned concurrency model (`TaskManager`), and a Pre-Flight Gatekeeper for security.

---

## 2. Module Classification & Migration Mapping

### Bucket A (Rust Engine Candidates)
**High-throughput, CPU/IO-bound tasks to be migrated to `echosync_core`.**
- `audio_inspector.py`: Tag parsing, file profiling, and integrity checks.
- `tagging_io.py`: ID3/Vorbis/FLAC tagging and metadata extraction.
- `base_io.py`: `safe_move`, `safe_delete`, `safe_write_text`.
- `local_io.py`: Wrappers around `base_io` and `tagging_io`.
- `jail.py`: Path traversal boundary enforcement.
- `post_processor.py` (I/O subset): `_embed_cover_art`, file system operations.

### Bucket B (Python Orchestration Services)
**High-level logic moving to repository services.**
- `storage.py`: Handles accounts, tokens, and database connections. Move to `services/storage_service.py` (or integrate directly with `database/config_database.py`).
- `path_mapper.py`: Resolves Docker/remote paths and extracts string data. Migrate into a flat `core/utils.py` file (No `core/utils/` directory).
- `post_processor.py` (Logic subset): Path pattern generation, sanitization, and workflow coordination. Move to `services/post_processing_service.py`.

### Bucket C (Dead Code / Technical Debt)
**Targets for immediate/eventual deletion.**
- The facade layer in `local_io.py` can be purged once consumers switch to direct `echosync_core` or Python util calls.
- `jail.LockManager`: Concurrency locks will be natively handled by the Python `TaskManager`, rendering this module obsolete.
- `core/file_handling/__init__.py`: Delete upon complete directory disassembly.

---

## 3. Architectural Mandates & System Design

### 3.1 Modular Rust Engine Structure (`echosync_core`)
The Rust engine will abandon a monolithic design in favor of dedicated sub-modules:
- `src/lib.rs`: Strict PyO3 module registration and C-FFI entry points ONLY.
- `src/file_handling/`:
  - `scanner.rs`: High-speed, mtime-cached directory crawling.
  - `integrity.rs`: Chunk-header and magic binary validation to detect Fake FLACs or ghost files.
  - `fs_ops.rs`: Root-bounded batch file operations (move, copy, delete).
- `src/metadata/`:
  - `extractor.rs`: High-speed tag extraction via `lofty`.
  - `writer.rs`: Atomic tag writing.
- `src/database/`: Lightweight `rusqlite` WAL interactions restricted EXCLUSIVELY to `working.db`.

### 3.2 Database Boundary & Security
- **Strict Separation:** Rust is strictly prohibited from connecting to `media_library.db`. `media_library.db` is managed exclusively by Python's SQLAlchemy 2.0 ORM to preserve Native RLS (`contextvars`), `@event.listens_for` hooks, and AST DDL guards.
- **Data Handoff:** For ingestion pipelines, Rust modules must yield `PyDict` or primitive arrays back to Python. Python will then map these to DTOs for safe batch insertion into `media_library.db`.

### 3.3 The Pre-Flight Gatekeeper Pattern (`core/io_gatekeeper.py`)
To enforce zero-trust security and prevent unauthorized FFI calls by plugins:
- Unprivileged plugins must **never** call the Rust FFI directly.
- All I/O requests must route through a new `core/io_gatekeeper.py` module.
- The Gatekeeper validates the calling plugin's identity (via `plugin_id` and strict path provenance), evaluates manifest permissions once per batch, and then passes the authorized, pre-computed root paths to the Rust engine for execution.

### 3.4 Task Management & Concurrency
- Concurrency locks belong strictly to Python's `TaskManager`.
- Rust will not implement custom threading locks or mutexes for file access. It executes synchronous or parallel jobs entirely within the thread pool allocation granted by the Python `TaskManager`, eliminating deadlocks between runtimes.

---

## 4. Deconstruction Roadmap

### Phase 1: Engine Foundation & Data Structures
1. Scaffold the modular Rust architecture (`src/file_handling`, `src/metadata`, `src/database`).
2. Implement `working.db` exclusive SQLite connectivity in Rust.
3. Migrate `path_mapper.py` into a flat `core/utils.py` and delete `path_mapper.py`.
4. Migrate `storage.py` into `services/storage_service.py` and update imports.

### Phase 2: Gatekeeper & Metadata Engine
1. Implement `core/io_gatekeeper.py` to intercept and authorize plugin I/O requests.
2. Develop `extractor.rs` and `writer.rs` in Rust, returning `PyDict` objects.
3. Hook `metadata_enhancer.py` and plugin endpoints to route through `io_gatekeeper.py` instead of `tagging_io.py`.

### Phase 3: File System Operations & Integrity
1. Develop `fs_ops.rs` (safe move/delete with root bounding) and `integrity.rs` (header validation).
2. Wire up `base_io.py` and `local_io.py` legacy consumers to use the new Gatekeeper `safe_move`/`safe_delete` abstractions.
3. Refactor `post_processor.py` logic into `services/post_processing_service.py`, deferring physical embedding and path generation to Rust via the Gatekeeper.

### Phase 4: Purge & Verification
1. Delete `core/file_handling/jail.py`, `local_io.py`, `base_io.py`, `tagging_io.py`, `audio_inspector.py`, and `post_processor.py`.
2. Remove the `core/file_handling/` directory entirely.
3. Execute the full test suite (`uv run pytest`) to verify that all API endpoints and background jobs continue functioning under the new architecture.
