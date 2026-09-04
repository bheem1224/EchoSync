# System Invariants for Autonomous Coding Agents

## 1. Absolute Directives

Autonomous coding agents modifying EchoSync must strictly obey the following rules:

### Audio Tagging & Mutagen Prohibition
- **Inviolable Rule:** Python code MUST NOT import `mutagen`, `tinytag`, or `taglib`.
- **Enforcement:** All audio tag reading, writing, and Chromaprint fingerprinting MUST route strictly through native Rust `lofty` in `echosync_core`.
- **Verification:** Execute `uv run python tools/lint_audio_calls.py` before submitting any changes.

### Zero-Trust Filesystem Mutations (Gatekeeper Protocol)
- **Inviolable Rule:** Raw Python `os.rename`, `os.remove`, `os.unlink`, or `shutil.move` calls are prohibited for physical media in core services.
- **Enforcement:** Relocations and deletions MUST route through `core/io_gatekeeper.py`, invoking `echosync_core.safe_move_file`, `copy_file`, or `delete_file`.

### Three-Database Partitioning
- **`config.db`**: System config and credentials.
- **`working.db`**: High-churn task state and ingestion queues.
- **`library.db`**: Canonical entity graph (`CanonicalTrack`, `PhysicalMedia`, `VirtualMedia`).
- **Inviolable Rule:** No direct `sqlite3.connect()` calls or synchronous N+1 write loops. All database access MUST use batched SQLAlchemy sessions via `session_scope()`.

### Event Bus Lightweight Payload Boundary
- **Inviolable Rule:** Events published via `core/event_bus.py` MUST transmit scalar IDs (`sync_id`, `media_id`), never monolithic serialized track dictionaries.

### Frontend UI Boundaries
- Frontend is SvelteKit 2 + Svelte 5 (`webui/`).
- Plugins compile Web Components (`customElement: true`) mounted via `DynamicPluginLoader.svelte`.
