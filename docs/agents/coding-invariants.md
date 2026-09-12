# Agent Coding Invariants & Directives

## 1. System Coding Directives

1. **Audio Tagging & Native DSP:** Tag mutations and Chromaprint generation must route strictly through native `echosync_core` (lofty/symphonia). Direct imports of `mutagen`, `tinytag`, or `taglib` are forbidden. Verify with `uv run python tools/lint_audio_calls.py`.
2. **Zero-Trust Filesystem (IO Gatekeeper):** All file moves, renames, and deletions must route through `core/io_gatekeeper.py`. Raw `os.rename`, `shutil.move`, or `Path.unlink` are forbidden.
3. **Outbound HTTP (RequestManager):** Outbound HTTP calls must route strictly through `core.request_manager.RequestManager` to enforce rate limits. Raw `requests.*` or `httpx.*` are forbidden in services and plugins.
4. **Three-Database Concurrency:** `config.db` (encrypted settings), `working.db` (ephemeral tasks/queues), `library.db` (canonical entities). Direct `sqlite3.connect` calls are prohibited; all access must use `DatabaseGateway` scoped sessions.
5. **No Legacy Shims:** Deprecated methods or architectural shims must be completely removed rather than maintained via compatibility wrappers.
