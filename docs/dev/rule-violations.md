# Architectural Invariant Violation Ledger

*Last Audited: 2026-09-10 12:16:12 UTC*

| Violation Type | File Path | Line Number | Observed Pattern | Architectural Remediation |
| :--- | :--- | :--- | :--- | :--- |
| Rogue HTTP Client | `plugins/EchoSync/navidrome/routes.py` | 35 | `import requests` | Route through `RequestManager` |
| Rogue HTTP Client | `plugins/EchoSync/navidrome/routes.py` | 46 | `response = requests.get(auth_url, params=params, timeout=5)` | Route through `RequestManager` |
| Rogue HTTP Client | `plugins/EchoSync/navidrome/routes.py` | 143 | `import requests` | Route through `RequestManager` |
| Rogue HTTP Client | `plugins/EchoSync/navidrome/routes.py` | 155 | `response = requests.get(auth_url, params=params, timeout=10)` | Route through `RequestManager` |
| Rogue HTTP Client | `plugins/EchoSync/slskd/client.py` | 404 | `import requests` | Route through `RequestManager` |
| Rogue HTTP Client | `plugins/EchoSync/slskd/client.py` | 407 | `response = requests.get(` | Route through `RequestManager` |
| Rogue HTTP Client | `plugins/EchoSync/tidal/api_v2.py` | 3 | `import requests` | Route through `RequestManager` |
| Rogue HTTP Client | `plugins/EchoSync/tidal/api_v2.py` | 25 | `response = requests.get(url, headers=self.headers, params=params)` | Route through `RequestManager` |
| Rogue HTTP Client | `plugins/EchoSync/tidal/__init__.py` | 15 | `import requests` | Route through `RequestManager` |
| Rogue HTTP Client | `plugins/EchoSync/tidal/__init__.py` | 18 | `resp = requests.get("https://api.tidal.com/v1/", timeout=5)` | Route through `RequestManager` |
| Rogue HTTP Client | `plugins/EchoSync/plex/routes.py` | 353 | `import requests` | Route through `RequestManager` |
| Rogue HTTP Client | `plugins/EchoSync/plex/routes.py` | 364 | `resp = requests.get(` | Route through `RequestManager` |
| Rogue HTTP Client | `plugins/EchoSync/jellyfin/routes.py` | 35 | `import requests` | Route through `RequestManager` |
| Rogue HTTP Client | `plugins/EchoSync/jellyfin/routes.py` | 44 | `response = requests.post(` | Route through `RequestManager` |
| Rogue HTTP Client | `plugins/EchoSync/jellyfin/routes.py` | 144 | `import requests` | Route through `RequestManager` |
| Rogue HTTP Client | `plugins/EchoSync/jellyfin/routes.py` | 153 | `response = requests.post(auth_url, json=auth_data, headers=headers, timeout=10)` | Route through `RequestManager` |
| Rogue HTTP Client | `plugins/EchoSync/jellyfin/routes.py` | 167 | `info_response = requests.get(info_url, headers=info_headers, timeout=5)` | Route through `RequestManager` |
| Rogue HTTP Client | `core/nexus_framework/plugin_store.py` | 9 | `import requests` | Route through `RequestManager` |
| Rogue HTTP Client | `core/nexus_framework/plugin_store.py` | 296 | `resp = requests.get(api_url, timeout=10, allow_redirects=False)` | Route through `RequestManager` |
| Rogue HTTP Client | `core/nexus_framework/plugin_store.py` | 302 | `dir_resp = requests.get(` | Route through `RequestManager` |
| Rogue HTTP Client | `core/nexus_framework/plugin_store.py` | 309 | `manifest_resp = requests.get(` | Route through `RequestManager` |
| Rogue HTTP Client | `core/nexus_framework/plugin_SDK.py` | 1038 | `MANDATORY: All HTTP requests must use this, not requests.get() directly.` | Route through `RequestManager` |
| Ungated File Deletion | `run_api.py` | 100 | `lock_file.unlink()` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `services/auto_importer.py` | 254 | `file_p.unlink(missing_ok=True)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Move | `services/download_manager.py` | 2424 | `shutil.move(str(src), str(dest))` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Move | `services/media_manager.py` | 296 | `This is the ONLY place in the backend where physical os.remove() and` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `web/routes/metadata_review.py` | 1147 | `os.unlink(str(resolved_file))` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Move | `web/routes/system.py` | 180 | `os.remove(tmp_path)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Move | `web/routes/system.py` | 1018 | `os.remove(db_path)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Move | `core/tiered_logger.py` | 69 | `os.remove(dfn)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Move | `core/tiered_logger.py` | 73 | `os.rename(sfn, dfn)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Move | `core/tiered_logger.py` | 84 | `os.remove(dfn)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Move | `core/tiered_logger.py` | 89 | `os.rename(self.baseFilename, dfn)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `core/backup_manager.py` | 105 | `shutil.rmtree(staging_dir, ignore_errors=True)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `core/backup_manager.py` | 175 | `shutil.rmtree(staging_dir, ignore_errors=True)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Move | `core/nexus_framework/plugin_loader.py` | 289 | `- ``os.remove/unlink/rename(...)``           direct OS-level ops` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Move | `core/nexus_framework/plugin_loader.py` | 290 | `- ``shutil.move/copy/rmtree(...)``           shutil destructive ops` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `core/nexus_framework/plugin_loader.py` | 291 | `- ``<any>.unlink()``                         pathlib.Path.unlink` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `core/nexus_framework/plugin_loader.py` | 955 | `shutil.rmtree(author_item, ignore_errors=True)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `core/nexus_framework/plugin_store.py` | 730 | `shutil.rmtree(tmp_dir, ignore_errors=True)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `core/nexus_framework/plugin_store.py` | 908 | `shutil.rmtree(tmp_dir, ignore_errors=True)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `core/nexus_framework/plugin_store.py` | 1086 | `shutil.rmtree(beta_dir, ignore_errors=True)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `core/nexus_framework/plugin_store.py` | 1092 | `shutil.rmtree(backup_dir, ignore_errors=True)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Move | `core/nexus_framework/plugin_store.py` | 1094 | `os.rename(str(target_dir), str(backup_dir))` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `core/nexus_framework/plugin_store.py` | 1104 | `shutil.rmtree(target_dir, ignore_errors=True)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Move | `core/nexus_framework/plugin_store.py` | 1110 | `os.rename(str(tmp_dir), str(target_dir))` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `core/nexus_framework/plugin_store.py` | 1115 | `shutil.rmtree(backup_dir, ignore_errors=True)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Move | `core/nexus_framework/plugin_store.py` | 1123 | `os.rename(str(backup_dir), str(target_dir))` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `core/nexus_framework/plugin_store.py` | 1281 | `shutil.rmtree(target_dir, ignore_errors=True)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Move | `core/nexus_framework/plugin_store.py` | 1282 | `os.rename(str(backup_dir), str(target_dir))` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Move | `core/nexus_framework/plugin_store.py` | 1478 | `os.remove(tmp_zip_path)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `core/nexus_framework/plugin_store.py` | 1480 | `shutil.rmtree(tmp_dir, ignore_errors=True)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `core/nexus_framework/plugin_store.py` | 1496 | `shutil.rmtree(beta_path, ignore_errors=True)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `core/nexus_framework/plugin_store.py` | 1825 | `shutil.rmtree(dest_dir, ignore_errors=True)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `core/db/migrations.py` | 59 | `music_db.unlink()` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `core/utils/file_utils.py` | 59 | `junk.unlink()` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Deletion | `core/utils/file_utils.py` | 106 | `junk.unlink()` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Ungated File Move | `core/task_manager/system_jobs.py` | 1254 | `os.remove(db_file)` | Route through `Gatekeeper.authorize_and_execute` / `echosync_core` |
| Direct SQLite Conn | `database/engine.py` | 37 | `conn = sqlite3.connect(self.db_path, timeout=60.0, check_same_thread=False)` | Use `DatabaseGateway` scoped ORM sessions (`session_scope()`) |
| Direct SQLite Conn | `database/config_database.py` | 59 | `conn = sqlite3.connect(str(self.database_path), timeout=30.0)` | Use `DatabaseGateway` scoped ORM sessions (`session_scope()`) |
| Direct SQLite Conn | `database/config_database.py` | 126 | `conn = sqlite3.connect(str(self.database_path), timeout=60.0)` | Use `DatabaseGateway` scoped ORM sessions (`session_scope()`) |
| Direct SQLite Conn | `core/backup_manager.py` | 31 | `src_conn = sqlite3.connect(str(source_path))` | Use `DatabaseGateway` scoped ORM sessions (`session_scope()`) |
| Direct SQLite Conn | `core/backup_manager.py` | 32 | `dst_conn = sqlite3.connect(str(target_path))` | Use `DatabaseGateway` scoped ORM sessions (`session_scope()`) |
| Direct SQLite Conn | `core/matching_engine/fingerprinting.py` | 272 | `sqlite3.connect(self.db_path, timeout=30.0)` | Use `DatabaseGateway` scoped ORM sessions (`session_scope()`) |
| Direct SQLite Conn | `core/matching_engine/fingerprinting.py` | 304 | `sqlite3.connect(self.db_path, timeout=30.0)` | Use `DatabaseGateway` scoped ORM sessions (`session_scope()`) |
| Direct SQLite Conn | `core/matching_engine/fingerprinting.py` | 341 | `sqlite3.connect(self.db_path, timeout=30.0)` | Use `DatabaseGateway` scoped ORM sessions (`session_scope()`) |
| Direct SQLite Conn | `core/matching_engine/fingerprinting.py` | 368 | `sqlite3.connect(self.db_path, timeout=30.0)` | Use `DatabaseGateway` scoped ORM sessions (`session_scope()`) |
| Direct SQLite Conn | `core/db/migrations.py` | 89 | `with contextlib.closing(sqlite3.connect(db_path, timeout=30.0)) as conn:` | Use `DatabaseGateway` scoped ORM sessions (`session_scope()`) |
| Direct SessionLocal Access | `services/state_listener.py` | 16 | `self.Session = get_working_database().SessionLocal` | Use `DatabaseGateway.session_scope()` context manager |
| Instance Rate Limiter State | `core/request_manager.py` | 79 | `self._last_call_ts = 0.0` | Centralize rate limit state in global dictionary per provider |
| Missing Async Lock | `core/rate_limiter.py` | 37 | `RateLimiter.wait()` un-locked timestamps modify | Wrap timestamp check/append in `asyncio.Lock()` |
