# V3.0 Modularity Roadmap: The Path to "Nexus Framework"

**Date:** 2026-03-24
**Scope:** Architectural Limit Audit for Extreme Modularity Edge Cases

This document evaluates the limits of the v2.5.0 plugin sandbox and outlines the required hooks, SDK abstractions, and architecture changes needed to achieve the v3.0 "Nexus Framework" ecosystem.

---

## 1. Database Write Boundaries & Core Overrides

### Writing to Core Tables
* **Is it possible today?** **YES, but dangerously so.**
* **Analysis:** The `ProviderStorageBox` and its underlying `RestrictedConnection` successfully block structural DDL (`DROP TABLE`, `ALTER TABLE`) against core tables. However, it does **not** block Data Manipulation Language (DML) like `INSERT`, `UPDATE`, or `DELETE`. A plugin currently has raw SQL write access to the core `TRACKS` or `USERS` table if it maliciously routes a query.
* **V3.0 Roadmap Requirement:** The `RestrictedConnection` SDK must intercept `DELETE`, `UPDATE`, and `INSERT` statements to enforce read-only status on core tables unless specifically granted elevated privileges via a `CORE_WRITE_OVERRIDE` hook.

### DB Engine Swaps (PostgreSQL/MySQL)
* **Is it possible today?** **NO.**
* **Analysis:** In both `music_database.py` and `working_database.py`, the SQLAlchemy engine is hardcoded to `f"sqlite:///{self.database_path}"`.
* **V3.0 Roadmap Requirement:** The DB path construction must read from `config.json` (e.g., `database.uri`). We need an `ON_DB_ENGINE_INIT` hook allowing a plugin (like a Postgres Adapter) to parse that URI and configure the dialect dynamically before `create_engine()` is called.

---

## 2. The "VUEtorrent" Test (Total UI & API Freedom)

### Frontend Override
* **Is it possible today?** **NO.**
* **Analysis:** The `serve_frontend` route in `web/api_app.py` has a hardcoded `static_folder` path mapping directly to `../webui/build`. It does not read any `webui_path` string from the configuration manager.
* **V3.0 Roadmap Requirement:** Add a `webui.path` setting in `config.json`. If populated, `serve_frontend` should route to the custom directory. Alternatively, provide an `ON_FRONTEND_REQUEST` skip-hook in Flask to allow plugins to intercept and serve their own HTML templates entirely.

### Log Reading & Streaming
* **Is it possible today?** **NO.**
* **Analysis:** The AST Sandbox explicitly blocks `open`, `read`, and `pathlib.Path.read_text`. A plugin cannot read the internal log files. Furthermore, the core `/api/logs` endpoint is currently a hardcoded `TODO` returning an empty array.
* **V3.0 Roadmap Requirement:** The core application must properly implement the `/api/logs` endpoint via the `LocalFileHandler`. Alternatively, a `LogStreamer` SDK class should be provided to plugins, safely yielding log lines without granting raw `os` read permissions.

---

## 3. Core Service Eradication (Replacing the Un-replaceable)

### Media Manager & Download Manager Bypass
* **Is it possible today?** **NO.**
* **Analysis:** Core backend routers (like `web/routes/downloads.py`) tightly couple to the `get_download_manager().process_downloads_now()` singleton.
* **V3.0 Roadmap Requirement:** We need top-level Skip-Hooks like `ON_DOWNLOAD_MANAGER_START` and `ON_MEDIA_MANAGER_INIT`. If a plugin intercepts these and returns `"SKIP"`, the core should defer all queue processing, deduplication, and caching completely to the plugin logic.

### Caching Backend Swaps
* **Is it possible today?** **NO.**
* **Analysis:** `ProviderCache` in `core/caching/provider_cache.py` is hardcoded to `MusicDatabase` executing `SELECT * FROM parsed_tracks`.
* **V3.0 Roadmap Requirement:** Implement a standard `ICacheAdapter` interface. The core should provide a hook `RESOLVE_CACHE_BACKEND` where a plugin can inject its own Redis or Memcached adapter class.

### File Type & Tagger Extensibility
* **Is it possible today?** **NO.**
* **Analysis:** `core/file_handling/tagging_io.py` hardcodes checking for `.mp3`, `.flac`, `.wav`, etc., manually routing them to specific `mutagen` handlers (`_tag_mp3`, `_tag_flac`).
* **V3.0 Roadmap Requirement:** Create a `TAGGER_REGISTRY` mapping extensions to handler functions. Add a `register_audio_format` hook so plugins can inject support for `.dsd`, `.aiff`, or specialized formats.

---

## 4. Binary Execution & Advanced Matching

### Compiled Binaries (C++/Rust)
* **Is it possible today?** **NO.**
* **Analysis:** The AST Sandbox restricts `subprocess`, `os.system`, and `ctypes` imports completely. A plugin cannot execute a compiled binary for tasks like spectral analysis.
* **V3.0 Roadmap Requirement:** Architect an "Approved Binary Pathway" in the SDK (e.g., `CoreBinaryRunner`). Plugins must declare their bundled binaries in `manifest.json`. The SDK runner will validate the binary signature/path, sandbox the execution via the core, and return stdout/stderr without granting the plugin direct shell execution rights.

### Advanced Matching Engine Weights
* **Is it possible today?** **NO.**
* **Analysis:** The `WeightedMatchingEngine` calculates confidence using a rigid `ScoringWeights` dataclass (`text_weight`, `duration_weight`, etc.). While plugins can boost the final numerical score via `scoring_modifier`, they cannot dynamically inject new *categories* (e.g., `acoustic_fingerprint_delta`) into the algorithm matrix or into the `MatchResult` data structure.
* **V3.0 Roadmap Requirement:** Refactor `ScoringWeights` into a dynamic dictionary or class array. Add an `ON_SCORING_WEIGHTS_CALCULATE` hook allowing plugins to inject an entire `IScoringCategory` module, enabling the final confidence to be dynamically calculated across core + plugin metrics.
