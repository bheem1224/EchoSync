# Architectural Invariant Violation Ledger

*Last Audited: 2026-04-15 12:00:00 UTC*

This document tracks all detected violations of EchoSync architectural invariants across core orchestrators, background services, route controllers, and plugin sub-frameworks.

| Violation Type | File Path | Line Number | Observed Pattern | Architectural Remediation |
| :--- | :--- | :--- | :--- | :--- |
| Ungated File Move | `services/library_sync_service.py` | 254 | `shutil.move(file_path, dest_path)` | Route file relocation through `Gatekeeper.authorize_and_execute` / `echosync_core.safe_move_file`. |
| Ungated File Move | `services/download_manager.py` | 1951 | `shutil.move(str(src), str(dest))` | Route staging transitions through `Gatekeeper.authorize_and_execute` / `echosync_core.safe_move_file`. |
| Ungated File Delete | `web/routes/metadata_review.py` | 911 | `os.unlink(str(resolved_file))` | Route file deletion through `Gatekeeper.authorize_and_execute` / `echosync_core.delete_file`. |
| Ungated File Delete | `web/routes/system.py` | 170 | `os.remove(tmp_path)` | Route temp file deletion through `Gatekeeper.authorize_and_execute` / `echosync_core.delete_file`. |
| Ungated File Delete | `web/routes/system.py` | 923 | `os.remove(db_path)` | Route DB file purge through `Gatekeeper.authorize_and_execute` / `echosync_core.delete_file`. |
| Ungated File Delete | `core/task_manager/system_jobs.py` | 956 | `os.remove(db_file)` | Route orphan database cleanup through `Gatekeeper.authorize_and_execute`. |
| Direct SQLite Connection | `core/matching_engine/fingerprinting.py` | 292, 321, 355, 379 | `sqlite3.connect(self.db_path)` | Refactor direct driver calls to use scoped SQLAlchemy sessions via `DatabaseGateway`. |
| Direct SQLite Connection | `core/db/migrations.py` | 86 | `sqlite3.connect(db_path)` | Route migration checks through Alembic migration runner or SQLAlchemy engine connection. |
| Direct SQLite Connection | `core/backup_manager.py` | 29, 30 | `sqlite3.connect(str(source_path))` | Wrap backup operations in SQLAlchemy database backup utilities or streaming session dumps. |
| Direct SQLite Connection | `database/engine.py` | 34 | `sqlite3.connect(self.db_path)` | Encapsulate driver connection inside `DatabaseGateway` connection pool initializer. |
| Direct SQLite Connection | `database/config_database.py` | 48, 85 | `sqlite3.connect(str(self.database_path))` | Use `session_scope()` context manager rather than opening unpooled driver connections. |
| Direct SessionLocal Access | `services/state_listener.py` | 16 | `SessionLocal()` fallback | Remove direct `SessionLocal()` instantiation; use `with get_working_database().session_scope()`. |
| Rate Limiter Evasion | `core/request_manager.py` | 79-80 | `self._last_call_ts = 0.0` per instance | Centralize rate limiting timestamps per provider across all instances using shared state. |
| Async Race Condition | `core/rate_limiter.py` | 37-47 | Unlocked `timestamps.append()` | Wrap timestamp pruning and append operations inside an `asyncio.Lock()` block. |
| AST Sandbox Escape | `core/nexus_framework/plugin_loader.py` | 61-120 | Static string AST checks | Replace static AST parsing with Python audit hooks (`sys.addaudithook`) or `sys.meta_path` import hooks. |
| Plugin Identity Spoofing | `core/nexus_framework/plugin_loader.py` | 829-840 | Unvalidated `ProviderClass` registration | Force-overwrite provider class `name` and `plugin_id` with canonical integers upon registry import. |
| SDK Identity Spoofing | `core/nexus_framework/plugin_SDK.py` | 270-287 | Stack inspection (`inspect.currentframe()`) | Eliminate stack frame parsing; pass explicit capability tokens during plugin initialization. |
| Disk I/O DB Copy | `core/nexus_framework/plugin_store.py` | 942, 1046 | `shutil.copy2` on active SQLite DBs | Cease hardcopying `.db` files; leverage SQLite `ATTACH DATABASE` or explicit migration scripts. |
| Event Bus Bottleneck | `core/event_bus.py` | 92-115 | Sync subscriber loop in publisher lock | Queue event payloads into `queue.Queue` and process handlers asynchronously via background worker. |
| Session Poisoning | `core/job_queue.py` | 310-316 | Unhandled exception leaves session open | Wrap worker execution in explicit `try...except` block with mandatory `session.rollback()` and `.remove()`. |
