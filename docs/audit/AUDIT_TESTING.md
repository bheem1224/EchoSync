# AUDIT_TESTING.md (Security & Resilience)

## 🚨 V2.1.0 CRITICAL BLOCKERS

- [ ] **Path Traversal Vulnerability (`providers/slskd/client.py`):** The `filename` string returned from the Slskd API is frequently used as a local variable/target path (e.g., lines 338, 340, 621-650). It comes directly from the remote peer's file system without sanitation, leaving an exploitable window if combined with local path writes. `os.path.basename(filename)` or similar strict sanitization is missing before writing to disk.
- [ ] **Missing DB Connection Isolation Tests (`core/job_queue.py`):** The `is_running` concurrency lock logic has missing unit tests verifying that simultaneous manual + scheduled triggers do not create overlapping threads. We must verify that exceptions in the worker thread consistently execute `self._is_running[name] = False`.
- [ ] **SQL Injection Exposure (`core/personalized_playlists.py` & `core/watchlist_scanner.py`):** While most strings are parameterized, verify all `LIKE` clauses (e.g., `f'%{category}%'`) are strictly parameterized to prevent malformed strings escaping into the `execute()` call.

## Warnings / Tech Debt

- [ ] **API Token Exposure (`core/tiered_logger.py`):** The logging utilities allow tiered verbosity levels. However, verify that no `access_token` or `refresh_token` payload dictionaries are being serialized to the raw logs without regex masking or redaction on `DEBUG` level. Ensure `is_sensitive=True` fields from DB are caught.
- [ ] **Execution Limits/Timeouts:** The `execute_job_now` and `_execute_job` threads currently do not have a hard timeout. A hanging HTTP connection in `requests.get` could block a queue worker indefinitely. Ensure `RequestManager` enforces timeouts.
