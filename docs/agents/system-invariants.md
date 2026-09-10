# Core System Architectural Invariants for Autonomous Coding Agents

## 1. Executive Directive

Autonomous coding agents (e.g. Jules, AI assistants) contributing code to EchoSync must adhere strictly to these non-negotiable architectural invariants.

## 2. Core Invariants Summary

1. **Audio Tagging & Native DSP Prohibition**: Audio tag reading/writing and Chromaprint extraction must route strictly through native `echosync_core` (`lofty`/`symphonia`). Direct imports of `mutagen`, `tinytag`, or `taglib` in runtime Python code are prohibited.
2. **Zero-Trust Filesystem Mutations (Gatekeeper Protocol)**: Physical file relocations, renames, and deletions must route through `core/io_gatekeeper.py`, invoking `echosync_core.safe_move_file`, `copy_file`, or `delete_file`.
3. **Outbound HTTP Client Prohibition (RequestManager Protocol)**: External HTTP requests must route strictly through `core.request_manager.RequestManager` to enforce rate limits and token-bucket contracts.
4. **Three-Database Partitioning**: Strictly isolate `config.db` (settings/credentials), `working.db` (ephemeral queues/staging), and `library.db` (canonical media graph). Direct `sqlite3.connect()` calls in application code are forbidden.
5. **Event Bus Lightweight Identity**: Events published via `core/event_bus.py` must transmit lightweight entity identifiers (`sync_id`, `media_id`), never monolithic track dictionaries.
