# `core/file_handling/` Dependency & Migration Audit

**Role:** Senior Codebase Systems Auditor & Refactoring Architect
**Target:** `core/file_handling/`

## 1. Executive Summary
The `core/file_handling/` module is currently a hybrid of low-level I/O tasks (tagging, moving, path validation) and high-level Python orchestration (storage configuration). This audit proposes a structured disassembly plan to route heavy I/O tasks to the high-performance `echosync_core` Rust module while shifting standard orchestration logic into standard repository patterns.

An analysis of `src/lib.rs` reveals that the `echosync_core` Rust module currently only supports `scan_directory` (batch metadata extraction). Thus, significant FFI gaps exist for single-file operations, tagging, and path validation.

---

## 2. Dependency Matrix (Call Graph Audit)
A recursive grep across the codebase revealed the following dependencies on `core/file_handling/`:

### `core.file_handling.storage` (StorageService)
- **services/sync_service.py**
- **services/media_manager.py**
- **plugins/EchoSync/musicbrainz/routes.py**
- **plugins/EchoSync/spotify/routes.py**
- **plugins/EchoSync/tidal/oauth_routes.py**
- **web/routes/accounts.py**, **web/routes/playlists.py**, **web/routes/plugins_api.py**
- **core/storage.py**
- **core/task_manager/health_service.py**, **backend_services.py**

### `core.file_handling.local_io` (LocalFileHandler)
- **services/auto_importer.py**
- **services/library_watcher.py**
- **plugins/EchoSync/local_server/client.py**

### `core.file_handling.path_mapper` (PathMapper, extract_primary_artist)
- **services/auto_importer.py** (extract_primary_artist)
- **services/library_reorganizer.py** (extract_primary_artist)
- **services/metadata_enhancer.py**
- **services/media_manager.py**
- **plugins/EchoSync/plex/client.py**
- **scratch/check_enhancer_db.py**

### `core.file_handling.tagging_io` (read_tags, write_tags)
- **services/metadata_enhancer.py**
- **plugins/EchoSync/local_metadata/client.py**
- **web/routes/metadata_review.py**
- **tools/scan_diagnostics.py**

### `core.file_handling.audio_inspector` (inspect_audio_file)
- **plugins/EchoSync/local_server/client.py**
- **web/routes/metadata.py**
- **tools/lint_audio_calls.py**

### `core.file_handling.base_io` (safe_write_text)
- **plugins/EchoSync/lrclib/client.py**

### `core.file_handling.post_processor` (PostProcessor)
- **web/routes/metadata_review.py**

---

## 3. Module Classification & Migration Mapping

### Bucket A (Rust Engine Candidates)
**High-throughput, CPU/IO-bound tasks to be migrated to `echosync_core`.**
- `audio_inspector.py`: Tag parsing and audio profiling.
- `tagging_io.py`: ID3/Vorbis/FLAC tagging and metadata extraction.
- `base_io.py`: `safe_move`, `safe_delete`, `safe_write_text`.
- `local_io.py`: Wrappers around `base_io` and `tagging_io`.
- `jail.py`: Path traversal boundary enforcement.
- `post_processor.py` (I/O subset): `_embed_cover_art`, file system operations.

**Rust Capabilities Gap Analysis & Proposed FFI Signatures:**
The current `echosync_core` lacks single-file operations. We must implement:
- `def inspect_file(path: str) -> dict:` (Replaces `audio_inspector.inspect_audio_file`)
- `def read_tags(path: str) -> dict:` (Replaces `tagging_io.read_tags`)
- `def write_tags(path: str, metadata: dict) -> None:` (Replaces `tagging_io.write_tags`)
- `def safe_move(src: str, dest: str, allowed_roots: list[str]) -> str:` (Replaces `base_io.safe_move` + `jail.py`)
- `def safe_delete(path: str, trash_dir: str, allowed_roots: list[str]) -> None:` (Replaces `base_io.safe_delete`)
- `def validate_path(path: str, allowed_roots: list[str]) -> bool:` (Replaces `jail.FileJail.validate`)

### Bucket B (Python Orchestration Services)
**High-level logic moving to repository services.**
- `storage.py`: Handles accounts, tokens, and database connections. Move to `services/storage_service.py` (or integrate directly with `database/config_database.py`).
- `path_mapper.py`: Resolves Docker/remote paths and extracts string data (`extract_primary_artist`). Move to `core/utils/path_utils.py` and `core/utils/text_utils.py`.
- `post_processor.py` (Logic subset): Path pattern generation, sanitization, and workflow coordination. Move to `services/post_processing_service.py`.

### Bucket C (Dead Code / Technical Debt)
**Targets for immediate/eventual deletion.**
- The facade layer in `local_io.py` can be purged once consumers switch to direct `echosync_core` or Python util calls.
- `jail.LockManager`: Concurrency locks will be natively handled in Rust, rendering the Python `threading.Lock` layer obsolete.
- `core/file_handling/__init__.py`: Delete upon complete directory disassembly.

---

## 4. Security & Sandboxing Verification (`jail.py`)

**Current State:**
`jail.py` ensures that paths are resolved (`Path.resolve()`) and checked against `allowed_roots` using `is_relative_to()`. It neutralizes `../` traversal attacks before disk access occurs. `plugins/` interface with this via `base_io` and `local_io`.

**Rust Migration Strategy:**
To preserve zero-trust security when moving path validation to Rust:
1. **No Python Pre-processing:** The Rust FFI must accept raw string paths and perform its own canonicalization (`std::fs::canonicalize`). Trusting Python `Path.resolve()` output over the FFI boundary is a vulnerability if a plugin directly invokes the Rust FFI with spoofed absolute strings.
2. **Strict Root Enforcement:** The Rust FFI functions (`safe_move`, `safe_delete`, `read_tags`, etc.) must strictly require an `allowed_roots` array parameter (injected by the trusted core, never by the plugin).
3. **Internal Verification:** In Rust, canonicalized paths must strictly start with one of the canonicalized `allowed_roots`. Any traversal attempt must throw a Rust error that maps to a Python `SecurityError`.

---

## 5. Deconstruction Plan

**Phase 1: Foundation & Rust Preparation**
1. Implement the missing FFI bindings in `src/lib.rs` (tagging, inspection, safe I/O, path validation).
2. Compile and test `echosync_core` to ensure parity with `mutagen`/`shutil` behavior.
3. Move `storage.py` to `services/storage_service.py` and update imports across all 15+ caller files. Run `uv run pytest`.

**Phase 2: Logic Relocation**
1. Move `path_mapper.py` logic to `core/utils/`. Update imports in `auto_importer.py`, `media_manager.py`, etc.
2. Refactor `post_processor.py`, splitting logic into `services/post_processing_service.py` and routing I/O to the new Rust FFI.

**Phase 3: FFI Integration & Swap**
1. Replace calls to `audio_inspector.py` and `tagging_io.py` with `echosync_core.inspect_file` and `echosync_core.read_tags`/`write_tags`.
2. Route `base_io.py` and `local_io.py` consumer calls directly to `echosync_core.safe_move`/`safe_delete`.

**Phase 4: Purge & Verification**
1. Delete `core/file_handling/jail.py`, `local_io.py`, `base_io.py`, `tagging_io.py`, and `audio_inspector.py`.
2. Delete `core/file_handling/` directory.
3. Execute `uv run pytest` to guarantee active test suites and API endpoints remain functional.
