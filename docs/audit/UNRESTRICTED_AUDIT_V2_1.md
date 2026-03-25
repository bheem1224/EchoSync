# SoulSync Unrestricted Audit Report V2.1

## Critical

### Database
**1. Missing Flask Context Teardown for Database Sessions**
*   **File:** `web/api_app.py`
*   **Line:** (Missing global handler)
*   **Vulnerability:** The Flask application missing a `@app.teardown_appcontext` hook to enforce `db.SessionLocal.remove()`. SQLAlchemy session scopes created outside standard context managers or detached objects will leak sessions across parallel API requests, eventually starving the connection pool or leaving dangling file descriptors in SQLite.

**2. Blocked Database Connections during File Streaming**
*   **File:** `web/routes/metadata_review.py`
*   **Line:** 449 (`stream_review_queue_item`)
*   **Vulnerability:** The endpoint uses `send_file` *inside* a `with db.session_scope() as session:` block. `send_file` creates a generator that yields chunks to the client. The database session remains open for the entire duration of the audio stream. A slow network client downloading a large FLAC file will block the database connection indefinitely, leading to connection exhaustion.

**3. Unbounded Database Writes Queue**
*   **File:** `database/engine.py`
*   **Line:** 24 (`_DBWriter._run`)
*   **Vulnerability:** The `_DBWriter` class spawns a background thread running a `while not self._stop.is_set():` loop. However, during application shutdown, if `stop()` is not called explicitly, the thread is abruptly killed (as it is a daemon thread), potentially leaving transactions uncommitted or databases corrupted. Furthermore, the queue size is unbounded, meaning a sudden burst of DB writes can cause an Out-Of-Memory error.

### Core Engine
**4. Unmanaged Fire-and-Forget Background Thread Leak**
*   **File:** `core/database_update_worker.py`
*   **Line:** 114 (`start()`)
*   **Vulnerability:** The `DatabaseUpdateWorker` spawns a background `threading.Thread` and keeps a reference to it, but there is no mechanism to track its lifecycle or join it. Repeated calls to routes triggering this worker will spawn unbounded rogue threads that bypass the `job_queue` semaphores and concurrency locks.

### Web API
**5. Duplicate Job Registration Race Condition**
*   **File:** `web/routes/metadata_review.py`
*   **Line:** 424-436 (`approve_review_queue_item`)
*   **Vulnerability:** The endpoint registers and executes *two* separate one-off background jobs for the exact same task (`approve_metadata_{task_id}` and `approve_review_task_{task_id}`). Both jobs attempt to call the metadata enhancer, tag the file, and import it into the database concurrently, leading to race conditions, file locking errors, and duplicated database entries.


## High

### Database
**6. N+1 Memory Spike during Hierarchy Fetch**
*   **File:** `database/music_database.py`
*   **Line:** 428 (`get_library_hierarchy`)
*   **Vulnerability:** The method attempts to solve the N+1 problem by using `joinedload(Artist.albums).joinedload(Album.tracks)`. However, doing this with `.all()` forces SQLAlchemy to load the *entire* music library (all artists, all albums, all tracks) into a single giant in-memory object graph before iterating. On libraries with 100k+ tracks, this will cause massive CPU spikes and Out-Of-Memory kills.

**7. Session Context Leak via Returned Objects**
*   **File:** `web/routes/manager.py`
*   **Line:** 93 (`_resolve_working_user_for_trends`)
*   **Vulnerability:** A `user` object fetched inside `with working_db.session_scope() as session:` is returned and accessed outside the scope (line 347 in `get_trends()`). Because the session is closed when the context manager exits, accessing lazy-loaded properties on this detached `user` object later will trigger a `DetachedInstanceError`.

### Providers
**8. OAuth Polling Infinite Loop Potential**
*   **File:** `providers/plex/routes.py`
*   **Line:** 142 (`poll_oauth`)
*   **Vulnerability:** The frontend polls this endpoint rapidly. If `requests.get` to Plex fails (e.g., DNS issue), the exception is swallowed by a generic `except Exception` block. While the session eventually cleans up after 15 minutes, thousands of failing HTTP requests can be spammed in the meantime, overwhelming the network stack.

**9. Spotify Token DB Transaction Leaks**
*   **File:** `providers/spotify/client.py`
*   **Line:** 37 (`ConfigCacheHandler.get_cached_token`)
*   **Vulnerability:** The cache handler directly invokes `storage.get_account_token()` but lacks robust error handling if the storage service raises an unexpected database error (e.g., lock timeout). Spotipy assumes token operations are purely local and fast; slow or failing DB queries here will block the authentication flow silently.

## Medium

### Core Engine
**10. Generic Exception Swallowing in Event Bus**
*   **File:** `core/event_bus.py`
*   **Line:** 34 & 41 (`publish_lightweight`)
*   **Vulnerability:** A generic `except Exception as e:` block wraps all subscriber callbacks, logging the error and moving on. While this prevents one bad listener from crashing the bus, it masks severe state desyncs where a critical listener (like a database updater) fails silently, leaving the application in an inconsistent state.

**11. Unbounded While Loop in Job Queue Execution**
*   **File:** `core/job_queue.py`
*   **Line:** 383 (`_execute_job` worker)
*   **Vulnerability:** The worker uses `while True:` for retry logic. If a job continually fails and its `max_retries` is accidentally set to a massive number or infinite, the background thread will be permanently tied up retrying, starving other jobs in the queue.

### Providers
**12. Generic Exception Abuse Across Providers**
*   **File:** All files in `providers/`
*   **Vulnerability:** A `grep` check revealed 291 instances of `except Exception:` inside the `providers/` directory. Broadly catching generic exceptions masks HTTP timeouts, rate limiting signals (`429`), and `KeyError` parsing failures, preventing the core `RequestManager` from properly applying exponential backoff or failing gracefully.


## Low

### Core Engine
**13. JobQueue Manual Execution Locking Edge Case**
*   **File:** `core/job_queue.py`
*   **Line:** 229 (`execute_job_now`)
*   **Vulnerability:** If the `threading.Thread(target=_run_job_thread)` fails to spawn (e.g., hitting thread limits), the `_is_running[name]` lock is cleared in the `except` block. However, if the thread spawns but is killed by the OS before reaching the `finally` block, the lock remains `True` permanently, blocking all future executions of that job.