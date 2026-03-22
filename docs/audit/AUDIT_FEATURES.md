# AUDIT_FEATURES.md (Performance & Memory)

## 🚨 V2.1.0 CRITICAL BLOCKERS

- [ ] **N+1 Database Query Loop (`services/user_history_service.py`):** In the `_process_interactions` loop (lines ~220-290), each individual interaction generates a `music_session.query(Track)` lookup and potentially a `work_session.query(UserRating)` lookup in a `for` loop. This must be refactored into a bulk query and `session.bulk_save_objects` or `INSERT ... ON CONFLICT DO UPDATE`.
- [ ] **Missing CPU Optimization (`services/download_manager.py`):** In `_execute_waterfall_search_and_download` (lines ~415+), the loop processes provider candidates but does not gate the `matching_engine` execution with the `provider.supports_pre_filtering` flag. If `supports_pre_filtering` is true, the engine could bypass deep textual/fingerprint matching on known perfect hits.
- [ ] **Task Concurrency Lock Leak (`core/job_queue.py`):** The `is_running` mutex lock properly flags jobs in `execute_job_now` and `_execute_job`. However, if the `worker()` thread crashes or encounters an `os._exit()`, `is_running` remains stuck to `True`. Additionally, `get_working_database().session_scope()` is not explicitly closed or tracked in the job thread if the thread is killed.

## Warnings / Tech Debt

- [ ] **Database Session Management (`core/job_queue.py`):** Ensure long-running periodic background jobs do not hold open database connections or fail to return them to the `NullPool` immediately after use.
- [ ] **Overly Broad Selects:** Several raw SQL queries in `core/personalized_playlists.py` and `core/watchlist_scanner.py` use `ORDER BY RANDOM()` on large sets and do not paginate properly, which could inflate memory usage over time.
