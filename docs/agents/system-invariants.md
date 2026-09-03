# Core System Architectural Invariants for Autonomous Coding Agents

## 1. Executive Directive

Autonomous coding agents (e.g. Jules, AI assistants) contributing code to EchoSync must adhere strictly to these non-negotiable architectural invariants.

---

## 2. Invariant Rules Matrix

### Rule 1: Audio Tagging & Mutagen Prohibition
- Tag reading, writing, and Chromaprint extraction MUST route strictly through native `lofty` in `echosync_core` (`src/metadata/`).
- Direct imports of `mutagen`, `tinytag`, or `taglib` in runtime Python code are critical violations.
- Verification command: `uv run python tools/lint_audio_calls.py`.

### Rule 2: Zero-Trust Filesystem Mutations (Gatekeeper Protocol)
- All physical file relocations, renames, and deletions MUST route through `core/io_gatekeeper.py`, invoking `echosync_core.safe_move_file`, `copy_file`, or `delete_file`.
- Raw `os.rename`, `os.remove`, or `shutil.move` calls within services or route controllers violate the Gatekeeper boundary.

### Rule 3: Three-Database Partitioning & Concurrency
- `config.db`: Read-heavy system configuration, credentials, and encrypted tokens.
- `working.db`: Ephemeral task state, ingestion buffers (`VirtualTrackCache`), review queues.
- `library.db`: Pristine canonical entity graph (`Track`, `LocalMedia`).
- Direct `sqlite3.connect()` calls and synchronous N+1 write loops are forbidden. All operations must use batched SQLAlchemy sessions via `session_scope()`.

### Rule 4: Lightweight Event Bus Identity
- Events published via `core/event_bus.py` MUST transmit lightweight entity identifiers (`sync_id`, `media_id`), never monolithic serialized track dictionaries.
- Serialization MUST occur in the caller thread before pushing payload to queue to prevent race conditions.

### Rule 5: Backend Primitive Payloads & Frontend Formatting Boundary
- Backend API endpoints must return raw primitive values (e.g. rounded integer seconds for duration/uptime).
- String formatting, humanization, and localization are strictly responsibilities of the decoupled Svelte frontend.

### Rule 6: No Legacy Shims
- When a method or pattern is deprecated, remove it completely instead of writing backward-compatibility wrapper shims.
