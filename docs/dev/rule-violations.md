# Architectural Invariant Violation Ledger

*Last Audited: 2026-05-27 18:30:00 UTC*

| Violation Type | File Path | Line Number | Observed Pattern | Architectural Remediation |
| :--- | :--- | :--- | :--- | :--- |
| Ungated File Move | `services/library_sync_service.py` | 321 | `shutil.move(file_path, dest_path)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core.safe_move_file` |
| Ungated File Move | `services/download_manager.py` | 2424 | `shutil.move(str(src), str(dest))` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core.safe_move_file` |
| Ungated File Deletion | `services/media_manager.py` | 283 | `os.remove(file_path)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core.delete_file` |
| Ungated File Deletion | `web/routes/metadata_review.py` | 1092 | `os.unlink(str(resolved_file))` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core.delete_file` |
| Ungated File Deletion | `web/routes/system.py` | 180 | `os.remove(tmp_path)` | Route through `Gatekeeper.authorize_and_execute` |
| Ungated DB Deletion | `web/routes/system.py` | 1017 | `os.remove(db_path)` | Route through `Gatekeeper.authorize_and_execute` |
| Direct SQLite Connection | `core/matching_engine/fingerprinting.py` | 349 | `sqlite3.connect(self.db_path, timeout=30.0)` | Refactor to use DatabaseGateway scoped ORM sessions (`session_scope()`) |
| Direct SQLite Connection | `core/matching_engine/fingerprinting.py` | 381 | `sqlite3.connect(self.db_path, timeout=30.0)` | Refactor to use DatabaseGateway scoped ORM sessions (`session_scope()`) |
| Direct SQLite Connection | `core/matching_engine/fingerprinting.py` | 418 | `sqlite3.connect(self.db_path, timeout=30.0)` | Refactor to use DatabaseGateway scoped ORM sessions (`session_scope()`) |
| Direct SQLite Connection | `core/matching_engine/fingerprinting.py` | 445 | `sqlite3.connect(self.db_path, timeout=30.0)` | Refactor to use DatabaseGateway scoped ORM sessions (`session_scope()`) |
| Direct SQLite Connection | `core/db/migrations.py` | 89 | `sqlite3.connect(db_path, timeout=30.0)` | Use Alembic / DatabaseGateway connection abstraction |
| Direct SQLite Connection | `core/backup_manager.py` | 31 | `sqlite3.connect(str(source_path))` | Wrap backup operations in DatabaseGateway / SQLite Online Backup API |
| Direct SQLite Connection | `database/engine.py` | 37 | `sqlite3.connect(self.db_path, timeout=60.0)` | Encapsulate inside SQLAlchemy engine setup |
| Direct SQLite Connection | `database/config_database.py` | 59 | `sqlite3.connect(str(self.database_path), timeout=30.0)` | Refactor to use ConfigDatabase SQLAlchemy session scope |
| Direct SQLite Connection | `database/config_database.py` | 126 | `sqlite3.connect(str(self.database_path), timeout=60.0)` | Refactor to use ConfigDatabase SQLAlchemy session scope |
| Direct SQLite Connection | `services/state_listener.py` | 16 | `get_working_database().SessionLocal` | Use DatabaseGateway `session_scope()` context manager |
| Ungated Directory Removal | `core/nexus_framework/plugin_loader.py` | 955 | `shutil.rmtree(author_item, ignore_errors=True)` | Route through `Gatekeeper` filesystem purge methods |
| Ungated File Rename | `core/nexus_framework/plugin_store.py` | 1094 | `os.rename(str(target_dir), str(backup_dir))` | Route through `Gatekeeper` atomic move routines |
| Ungated Directory Copy | `core/nexus_framework/plugin_store.py` | 1070 | `shutil.copy2(sandbox_db_path, sandbox_backup_path)` | Use SQLite ATTACH DATABASE or migration scripts instead of raw DB file copies |
| Ungated File Deletion | `core/tiered_logger.py` | 69 | `os.remove(dfn)` | Route log rotations through managed file logger handlers |
| Rate Limiter Instance Evasion | `core/request_manager.py` | 79 | `self._last_call_ts = 0.0` (Instance-level rate state) | Centralize rate limiting state per provider in shared global map |
| Session Resource Leak | `core/request_manager.py` | 76 | `self._session = requests.Session()` without context manager | Implement `__enter__`/`__exit__` context manager or global connection pool |
| Unlocked Async Rate Limiter | `core/rate_limiter.py` | 37 | Missing `asyncio.Lock` around timestamp queue mutations | Wrap timestamp modifications in `asyncio.Lock` to prevent concurrent bursting |
| Incomplete Module Purge | `core/nexus_framework/plugin_loader.py` | 215 | `del sys.modules[m]` without `__teardown__` hook | Implement mandatory plugin `__teardown__` hooks and explicit GC collection |
| Sandbox CPU Bloat | `core/nexus_framework/plugin_loader.py` | 147 | Overzealous AST Node Traversal on all method calls | Refactor to `sys.meta_path` import hooks or Python audit hooks |
| Sync I/O in Async Context | `core/nexus_framework/plugin_loader.py` | 586 | Synchronous `py_file.read_text()` during plugin scans | Offload plugin scanning to `asyncio.to_thread()` threadpool |
| Swallowed Dependency Error | `core/nexus_framework/plugin_SDK.py` | 341 | `except ImportError: pass` on missing `wasmtime` | Log explicit warning and mark WASM plugin state as disabled/unsupported |
| Synchronous Event Dispatch | `core/event_bus.py` | 92 | `for handler in specific: handler(...)` holding `_lock` | Dispatch via asynchronous queue/threadpool; unlock event loop |
| Poisoned Transaction State | `core/job_queue.py` | 310 | `_execute_job_logic(job)` without `except Exception` rollback | Wrap job execution in `except Exception:` and execute `session.rollback()` |
| Resource Orphan on Thread Kill | `core/job_queue.py` | 326 | `process.terminate()` / `ctypes` thread killing | Replace force-kills with cooperative cancellation tokens (`threading.Event`) |
| Lock Contention in Loop | `services/metadata_enhancer.py` | 396 | `ServiceRegistry.resolve('matching_engine')` inside track loop | Resolve service engine once outside the candidate processing loop |
| Dynamic Regex Parsing Overhead | `core/matching_engine/text_utils.py` | 497 | `re.search(pattern, ...)` with uncompiled pattern strings | Pre-compile regex patterns at module level via `re.compile()` |
| Duplicate Hook Execution | `core/matching_engine/matching_engine.py` | 429 | Double-firing `scoring_modifier` hook per candidate | Compute modifiers once per candidate match to prevent redundant hook passes |
| Orphaned String Namespace | `core/nexus_framework/plugin_loader.py` | 192 | `clean_ns = base_ns.split('@')[0]` string parsing | Eradicate string namespaces; strictly use integer `plugin_id` |
| Micro-Venv Subprocess Bloat | `core/nexus_framework/plugin_venv.py` | 49 | Subprocess `pip install` per plugin venv | Use shared dependency graph resolver / unified site-packages |
| Deprecated Table Method | `database/working_database.py` | 485 | `create_table(table_name=f"prv_{...}")` | Deprecate `prv_` creation methods and enforce standard ORM tables |
| AST Sandbox Escape | `core/nexus_framework/plugin_loader.py` | 61 | Static AST bypassed via `getattr`/`eval` dynamic execution | Enforce runtime Python audit hooks (`sys.addaudithook`) |
| Call Stack Spoofing | `core/nexus_framework/plugin_SDK.py` | 372 | `inspect.currentframe()` stack frame validation | Pass capability tokens upon plugin instantiation; remove stack inspection |
| Unlocked Router Dict Mutation | `core/nexus_framework/plugin_router.py` | 15 | Unlocked `cls._routers` modifications | Protect router registry mutations with `threading.RLock()` |
| Instantiation DB Overhead | `core/nexus_framework/plugin_loader.py` | 108 | Database query per `plugin_id` instantiation | Cache resolved `plugin_id -> provider_cls` mapping in `PluginRegistry` |
| Identity Spoofing | `core/nexus_framework/plugin_loader.py` | 829 | Exported `ProviderClass` registered unvalidated | Forcefully overwrite `name` and `plugin_id` on imported plugin instances |
| Unsigned Manifest Trust | `core/nexus_framework/plugin_loader.py` | 556 | Direct trust of unverified `privileged` flag in JSON | Authenticate manifests cryptographically; store authorization flags in DB |
