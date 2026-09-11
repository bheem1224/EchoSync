# Architectural Invariant Violation Ledger
*Last Audited: 2026-09-11 12:30:01 UTC*

| Violation Type | File Path | Line Number | Observed Pattern | Architectural Remediation |
| :--- | :--- | :--- | :--- | :--- |
| Direct SQLite Conn | `core/backup_manager.py` | 31 | `src_conn = sqlite3.connect(str(source_path))` | Use DatabaseGateway scoped ORM sessions (session_scope()) |
| Direct SQLite Conn | `core/backup_manager.py` | 32 | `dst_conn = sqlite3.connect(str(target_path))` | Use DatabaseGateway scoped ORM sessions (session_scope()) |
| Direct SQLite Conn | `core/db/migrations.py` | 89 | `with contextlib.closing(sqlite3.connect(db_path, timeout=30.0)) as conn:` | Use DatabaseGateway scoped ORM sessions (session_scope()) |
| Direct SQLite Conn | `core/matching_engine/fingerprinting.py` | 253 | `with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:` | Use DatabaseGateway scoped ORM sessions (session_scope()) |
| Direct SQLite Conn | `core/matching_engine/fingerprinting.py` | 283 | `with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:` | Use DatabaseGateway scoped ORM sessions (session_scope()) |
| Direct SQLite Conn | `core/matching_engine/fingerprinting.py` | 318 | `with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:` | Use DatabaseGateway scoped ORM sessions (session_scope()) |
| Direct SQLite Conn | `core/matching_engine/fingerprinting.py` | 343 | `with contextlib.closing(sqlite3.connect(self.db_path, timeout=30.0)) as conn:` | Use DatabaseGateway scoped ORM sessions (session_scope()) |
| Direct SQLite Conn | `database/config_database.py` | 60 | `conn = sqlite3.connect(str(self.database_path), timeout=30.0)` | Use DatabaseGateway scoped ORM sessions (session_scope()) |
| Direct SQLite Conn | `database/config_database.py` | 117 | `conn = sqlite3.connect(str(self.database_path), timeout=60.0)` | Use DatabaseGateway scoped ORM sessions (session_scope()) |
| Direct SQLite Conn | `database/engine.py` | 37 | `conn = sqlite3.connect(self.db_path, timeout=60.0, check_same_thread=False)` | Use DatabaseGateway scoped ORM sessions (session_scope()) |
| Direct SQLite Conn | `scratch/check_indexes.py` | 8 | `conn = sqlite3.connect(db_path)` | Use DatabaseGateway scoped ORM sessions (session_scope()) |
| Direct SQLite Conn | `scratch/check_schema.py` | 20 | `conn = sqlite3.connect(db_path)` | Use DatabaseGateway scoped ORM sessions (session_scope()) |
| Direct SQLite Conn | `scratch/cleanup_tmp_tables.py` | 28 | `conn = sqlite3.connect(path)` | Use DatabaseGateway scoped ORM sessions (session_scope()) |
| Direct SQLite Conn | `scratch/find_dbs.py` | 12 | `conn = sqlite3.connect(fp)` | Use DatabaseGateway scoped ORM sessions (session_scope()) |
| Direct SQLite Conn | `scripts/inspect_dbs.py` | 7 | `conn = sqlite3.connect(path)` | Use DatabaseGateway scoped ORM sessions (session_scope()) |
| Direct SQLite Conn | `scripts/inspect_service_config.py` | 3 | `conn = sqlite3.connect("config/config.db")` | Use DatabaseGateway scoped ORM sessions (session_scope()) |
| Direct SQLite Conn | `scripts/inspect_services.py` | 3 | `conn = sqlite3.connect("config/config.db")` | Use DatabaseGateway scoped ORM sessions (session_scope()) |
| Rogue HTTP Client | `core/nexus_framework/plugin_store.py` | 9 | `import requests` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `core/nexus_framework/plugin_store.py` | 308 | `resp = requests.get(api_url, timeout=10, allow_redirects=False)` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `core/nexus_framework/plugin_store.py` | 314 | `dir_resp = requests.get(` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `core/nexus_framework/plugin_store.py` | 321 | `manifest_resp = requests.get(` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `plugins/EchoSync/jellyfin/routes.py` | 35 | `import requests` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `plugins/EchoSync/jellyfin/routes.py` | 44 | `response = requests.post(` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `plugins/EchoSync/jellyfin/routes.py` | 144 | `import requests` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `plugins/EchoSync/jellyfin/routes.py` | 153 | `response = requests.post(auth_url, json=auth_data, headers=headers, timeout=10)` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `plugins/EchoSync/jellyfin/routes.py` | 167 | `info_response = requests.get(info_url, headers=info_headers, timeout=5)` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `plugins/EchoSync/navidrome/routes.py` | 35 | `import requests` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `plugins/EchoSync/navidrome/routes.py` | 46 | `response = requests.get(auth_url, params=params, timeout=5)` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `plugins/EchoSync/navidrome/routes.py` | 143 | `import requests` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `plugins/EchoSync/navidrome/routes.py` | 155 | `response = requests.get(auth_url, params=params, timeout=10)` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `plugins/EchoSync/plex/routes.py` | 353 | `import requests` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `plugins/EchoSync/plex/routes.py` | 364 | `resp = requests.get(` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `plugins/EchoSync/slskd/client.py` | 404 | `import requests` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `plugins/EchoSync/slskd/client.py` | 407 | `response = requests.get(` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `plugins/EchoSync/tidal/__init__.py` | 15 | `import requests` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `plugins/EchoSync/tidal/__init__.py` | 18 | `resp = requests.get("https://api.tidal.com/v1/", timeout=5)` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `plugins/EchoSync/tidal/api_v2.py` | 3 | `import requests` | Route through RequestManager.get() or RequestManager session |
| Rogue HTTP Client | `plugins/EchoSync/tidal/api_v2.py` | 25 | `response = requests.get(url, headers=self.headers, params=params)` | Route through RequestManager.get() or RequestManager session |
| Ungated File Operation | `core/db/migrations.py` | 59 | `music_db.unlink()` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `core/nexus_framework/plugin_store.py` | 65 | `custom_repos.remove(url)` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `core/nexus_framework/plugin_store.py` | 1106 | `os.rename(str(target_dir), str(backup_dir))` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `core/nexus_framework/plugin_store.py` | 1122 | `os.rename(str(tmp_dir), str(target_dir))` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `core/nexus_framework/plugin_store.py` | 1135 | `os.rename(str(backup_dir), str(target_dir))` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `core/nexus_framework/plugin_store.py` | 1294 | `os.rename(str(backup_dir), str(target_dir))` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `core/nexus_framework/plugin_store.py` | 1490 | `os.remove(tmp_zip_path)` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `core/task_manager/system_jobs.py` | 1254 | `os.remove(db_file)` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `core/tiered_logger.py` | 69 | `os.remove(dfn)` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `core/tiered_logger.py` | 73 | `os.rename(sfn, dfn)` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `core/tiered_logger.py` | 84 | `os.remove(dfn)` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `core/tiered_logger.py` | 89 | `os.rename(self.baseFilename, dfn)` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `core/utils/file_utils.py` | 59 | `junk.unlink()` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `core/utils/file_utils.py` | 106 | `junk.unlink()` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `run_api.py` | 100 | `lock_file.unlink()` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `services/auto_importer.py` | 254 | `file_p.unlink(missing_ok=True)` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `services/download_manager.py` | 2424 | `shutil.move(str(src), str(dest))` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `web/routes/metadata_review.py` | 982 | `os.unlink(str(resolved_file))` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `web/routes/system.py` | 180 | `os.remove(tmp_path)` | Route through Gatekeeper.authorize_and_execute / echosync_core |
| Ungated File Operation | `web/routes/system.py` | 1016 | `os.remove(db_path)` | Route through Gatekeeper.authorize_and_execute / echosync_core |
