# Architectural Invariant Violation Ledger

*Last Audited: 2026-05-27 18:00:00 UTC*

| Violation Type | File Path | Line Number | Observed Pattern | Architectural Remediation |
| :--- | :--- | :--- | :--- | :--- |
| Ungated File Move | `services/library_sync_service.py` | 254 | `shutil.move(file_path, dest_path)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core.safe_move_file` |
| Ungated File Deletion | `services/media_manager.py` | 229 | `os.remove(file_path)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core.delete_file` |
| Ungated File Deletion | `web/routes/metadata_review.py` | 911 | `os.unlink(str(resolved_file))` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core.delete_file` |
| Ungated File Deletion | `web/routes/system.py` | 170 | `os.remove(tmp_path)` | Route through `Gatekeeper.authorize_and_execute` |
| Ungated DB Deletion | `web/routes/system.py` | 923 | `os.remove(db_path)` | Route through `Gatekeeper.authorize_and_execute` |
| Direct SQLite Connection | `core/matching_engine/fingerprinting.py` | 292 | `sqlite3.connect(self.db_path, timeout=30.0)` | Refactor to use DatabaseGateway scoped ORM sessions (`session_scope()`) |
| Direct SQLite Connection | `core/matching_engine/fingerprinting.py` | 321 | `sqlite3.connect(self.db_path, timeout=30.0)` | Refactor to use DatabaseGateway scoped ORM sessions (`session_scope()`) |
| Direct SQLite Connection | `core/matching_engine/fingerprinting.py` | 355 | `sqlite3.connect(self.db_path, timeout=30.0)` | Refactor to use DatabaseGateway scoped ORM sessions (`session_scope()`) |
| Direct SQLite Connection | `core/matching_engine/fingerprinting.py` | 379 | `sqlite3.connect(self.db_path, timeout=30.0)` | Refactor to use DatabaseGateway scoped ORM sessions (`session_scope()`) |
| Direct SQLite Connection | `core/db/migrations.py` | 86 | `sqlite3.connect(db_path, timeout=30.0)` | Use Alembic / DatabaseGateway connection abstraction |
| Direct SQLite Connection | `core/backup_manager.py` | 29 | `sqlite3.connect(str(source_path))` | Wrap backup operations in DatabaseGateway / SQLite Online Backup API |
| Direct SQLite Connection | `database/engine.py` | 34 | `sqlite3.connect(self.db_path, timeout=60.0)` | Encapsulate inside SQLAlchemy engine setup |
| Direct SQLite Connection | `database/config_database.py` | 48 | `sqlite3.connect(str(self.database_path), timeout=30.0)` | Refactor to use ConfigDatabase SQLAlchemy session scope |
| Direct SQLite Connection | `database/config_database.py` | 85 | `sqlite3.connect(str(self.database_path), timeout=60.0)` | Refactor to use ConfigDatabase SQLAlchemy session scope |
| Ungated Directory Removal | `core/nexus_framework/plugin_loader.py` | 714 | `shutil.rmtree(author_item, ignore_errors=True)` | Route through `Gatekeeper` filesystem purge methods |
| Ungated File Rename | `core/nexus_framework/plugin_store.py` | 850 | `os.rename(str(target_dir), str(backup_dir))` | Route through `Gatekeeper` atomic move routines |
| Ungated Directory Copy | `core/nexus_framework/plugin_store.py` | 942 | `shutil.copy2(stable_db_path, beta_db_path)` | Use SQLite ATTACH DATABASE or migration scripts instead of raw DB file copies |
| Ungated File Deletion | `core/tiered_logger.py` | 68 | `os.remove(dfn)` | Route log rotations through managed file logger handlers |
| Rate Limiter Instance Evasion | `core/request_manager.py` | 79 | `self._last_call_ts = 0.0` (Instance-level rate state) | Centralize rate limiting state per provider in shared global map |
| Session Resource Leak | `core/request_manager.py` | 76 | `self._session = requests.Session()` without context manager | Implement `__enter__`/`__exit__` context manager or global connection pool |
| Unlocked Async Rate Limiter | `core/rate_limiter.py` | 45 | Missing `asyncio.Lock` around timestamp queue mutations | Wrap timestamp modifications in `asyncio.Lock` to prevent concurrent bursting |
| Incomplete Module Purge | `core/nexus_framework/plugin_loader.py` | 215 | `del sys.modules[m]` without `__teardown__` hook | Implement mandatory plugin `__teardown__` hooks and explicit GC collection |
| Sandbox CPU Bloat | `core/nexus_framework/plugin_loader.py` | 147 | Overzealous AST Node Traversal on all method calls | Refactor to sys.meta_path import hooks or Python audit hooks |
| Sync I/O in Async Context | `core/nexus_framework/plugin_loader.py` | 586 | Synchronous `py_file.read_text()` during plugin scans | Offload plugin scanning to `asyncio.to_thread()` threadpool |
| Swallowed Dependency Error | `core/nexus_framework/plugin_SDK.py` | 341 | `except ImportError: pass` on missing `wasmtime` | Log explicit warning and mark WASM plugin state as disabled/unsupported |
