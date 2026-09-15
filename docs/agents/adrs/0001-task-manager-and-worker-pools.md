# ADR 0001: Two-Tier Worker Pools, SQLite Write Serialization, and Task Lifecycle Management

- **Status:** Implemented / Closed
- **Date:** 2026-09-12 (Adopted), 2026-09-13 (Implemented & Closed)
- **Authors:** EchoSync Architecture Group
- **Supercedes:** N/A
- **Governing Implementations:**
  - [`core/task_manager/task_queue.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/core/task_manager/task_queue.py) (Two-tier pools, job queue, db write lease)
  - [`core/task_manager/supervisor.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/core/task_manager/supervisor.py) (Process/thread tracking and cooperative cancellation)
  - [`database/engine.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/database/engine.py) (Supervised SQLite DBWriter connection engine)
  - [`scripts/audit_task_manager_adoption.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/scripts/audit_task_manager_adoption.py) (AST Concurrency Scanner)

---

## 1. Context & Problem Statement

EchoSync operates as an embedded music management and streaming engine powered by SQLite in WAL mode (`music_library.db`, `working.db`, `config.db`). Background synchronization, audio fingerprinting, MusicBrainz enrichment, and plugin reconciliation (e.g., CJK transliteration) compete for system resources with user-facing audio streaming, search, and WebUI interactions.

An architectural concurrency audit ([`tests/core/test_task_manager_concurrency_audit.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/tests/core/test_task_manager_concurrency_audit.py)) identified several critical vulnerabilities in the legacy `JobQueue` implementation:
1. **Unbounded Thread Spawning:** Worker semaphores (`_core_workers`, `_general_workers`) were initialized but never acquired in `_run_loop`. Every scheduled job spawned an unmanaged OS thread, leading to thread pool exhaustion during batch operations.
2. **SQLite Write Lock Contention:** SQLite WAL permits concurrent readers but strictly **one writer**. Background tasks categorized as `BACKGROUND_METADATA` (e.g., CJK reconciler, retroactive enhancer) bypassed `is_db_write_heavy_running()` checks, triggering `sqlite3.OperationalError: database is locked`.
3. **Queue Churn & Busy-Wait:** When a write-heavy job was blocked, it was rescheduled for `now + 0.5s`, causing 2 Hz polling churn instead of cleanly skipping the interval or yielding.
4. **Dead-Code Retry Mechanisms:** `max_retries` and exponential backoff parameters were ignored; failed one-shot jobs were permanently purged on first failure.

---

## 2. Decision Drivers

- **Zero Thread Exhaustion:** Bounded worker concurrency to protect OS threads and memory during massive ingestion passes.
- **Single-Writer Database Integrity:** Deterministic mutual exclusion on write-heavy tasks mutating `music_library.db` while allowing CPU DSP and network requests to run concurrently.
- **Interactive UI & Playback Latency:** User playback, audio streaming, and API searches must never be starved or blocked by background workers.
- **Deterministic Lifecycle Management:** Cooperative preemption, clean cancellation, and supervisor process boundaries for long-running or hung workers.
- **CPU Offloading:** Offload heavy audio DSP and decoding to native Rust to prevent Python GIL freeze.

---

## 3. Considered Options & Trade-offs

### Option A: Dispatch-Gated Single-Writer Mutex
- *Pros:* Complete isolation during the entire duration of write-heavy tasks.
- *Cons:* Coarse granularity. Tasks performing prolonged HTTP requests or DSP fingerprinting before small database commits hold the write lock unnecessarily, starving other operations.

### Option B: Hybrid Scoped Write Lease with Engine Scaling (Selected)
- *Pros:* Workers use a scoped context manager (`with job_queue.db_write_lease():`) for granular write transactions, allowing pre-write DSP and HTTP fetching to run concurrently. Under SQLite, single-writer (`max_writers = 1`) and WAL backpressure (>32MB) are enforced. When PostgreSQL is detected, concurrency scales dynamically to `database.max_workers`. Tasks requiring monolithic isolation can declare `exclusive_db_lease=True`.
- *Cons:* Requires disciplined use of `db_write_lease()` in worker tasks.

### Option C: External Distributed Task Queue (Celery / RQ / Redis)
- *Pros:* Industrial scalability, separate worker nodes.
- *Cons:* Heavy external dependencies incompatible with EchoSync’s self-contained, embedded desktop and homelab deployment model.

---

## 4. Decision Outcome & The 7 Architectural Tenets

We adopt the **Two-Tier Worker Pool and Governed Task Arbiter** architecture. All background execution, system jobs, and plugin workers must adhere to these 7 tenets:

### Tenet 1: Two-Tier Worker Pools
Execution slots are divided into two isolated worker pools:
- **Pool 1: Critical (Reserved):** Fixed 2 dedicated worker slots reserved strictly for `TaskCategory.CRITICAL` and interactive API operations (streaming playback, search queries, manual user actions, UI sync). Background jobs are strictly forbidden from acquiring Critical slots.
- **Pool 2: General (Bounded):** Bounded pool with $N$ worker slots (default 2, configurable up to CPU core count) for `TaskCategory.GENERAL`, `TaskCategory.DATABASE_WRITE_HEAVY`, and `TaskCategory.BACKGROUND_METADATA` tasks.

### Tenet 2: Hybrid Scoped Write Lease & Engine-Aware Scaling
- Tasks tagged as `DATABASE_WRITE_HEAVY` and `BACKGROUND_METADATA` acquire write leases via `with job_queue.db_write_lease():`.
- Under SQLite, `_db_write_lease` enforces `max_writers = 1`. Under PostgreSQL, concurrency scales dynamically to `database.max_workers`.
- Monolithic migrations or imports can set `exclusive_db_lease = True` on `ScheduledJob` to acquire the lease at dispatch and hold it until task completion.
- Blocked write tasks queue in FIFO order. If a recurring write job has `skip_if_blocked = True`, it advances directly to `now + interval_seconds`.

### Tenet 3: Three-Stage Lifecycle Escalation & Cooperative Shutdown Contract
Workers must support cooperative and forced termination:
1. **Cooperative Yield & Polling:** Long-running loops, retry backoffs, and rate limiters must periodically check `supervisor.is_current_task_cancelled()` or `job_queue.should_yield(task_name)`. Any wait intervals or retry sleeps must be sliced into small cooperative chunks (e.g. $\le 0.2\text{s}$) or executed via `Event.wait(timeout)` rather than un-interruptible `time.sleep()`.
2. **Graceful Cancellation:** When cancelled or stopped, `JobQueue` and `ProcessSupervisor` signal the task's `cancellation_event` or FFI cancellation token. The worker has a bounded grace period (default 3.0s) to abort cleanly, roll back partial transactions, and exit.
3. **Supervisor Process Termination:** If a detached worker thread or subprocess hangs beyond the grace period, `ProcessSupervisor` terminates the OS process/PID (`os.kill`) or interrupts the WASM epoch. Production Python threads must never be forcefully aborted via unsafe C-API calls (`PyThreadState_SetAsyncExc`).

### Tenet 4: Failure Classification, WAL Backpressure & Deduplicated Eviction
- **Transient Failures** (e.g., HTTP 429 rate limit, network drop, temporary SQLite busy lock): Reschedule with exponential backoff:
  $$\text{delay} = \text{backoff\_base} \times (\text{backoff\_factor}^{\text{current\_retries}-1})$$
  up to `max_retries`. Logged via `logger.warning()`.
- **Terminal Failures** (e.g., syntax error, corrupt payload, schema constraint violation): Mark task `TaskStatus.FAILED_TERMINAL`, record `last_error`, and log via `logger.error(..., exc_info=True)`.
- **WAL Backpressure Check:** When SQLite `-wal` exceeds 32 MB, `JobQueue` executes `PRAGMA wal_checkpoint(PASSIVE)` with a 5.0s bounded wait. If still above 32 MB, write leases are paused and tasks defer by 5.0s.
- **Deduplicated Hybrid Eviction Policy (Cap = 100 pending jobs):**
  - Strict deduplication by `job.name`.
  - When capacity (100 jobs) is reached, recurring jobs are dropped to their next scheduled interval; for one-time/user-requested jobs, the lowest-priority scheduled recurring job is evicted. One-time jobs are never dropped.

### Tenet 5: Native Execution Offload (GIL Protection)
- All computationally intensive DSP (Chromaprint acoustic fingerprinting, audio decoders, waveform generation) must be implemented in native Rust (`echosync_core` via PyO3) or sandboxed WebAssembly (WASM).
- Python workers must only coordinate I/O and orchestration; heavy CPU math must never saturate the Python GIL.

### Tenet 6: Resource Arbiter & Zero Unmanaged Threads
- All background tasks and plugin background threads must be registered with and managed by `JobQueue` and `ProcessSupervisor`.
- Directly spawning detached OS threads (`threading.Thread().start()`) or unmonitored subprocesses (`subprocess.Popen`) without registering in `ProcessSupervisor` is strictly forbidden.
- Background services (`EventBus`, `DBWriter`) must register as `ProcessCategory.CORE_SYSTEM` with `bound_to_general_pool=False`.

### Tenet 7: Unified Task State Machine & Tiered Logger Integration
- Canonical enums are defined in [`core/enums.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/core/enums.py): `TaskStatus`, `TaskCategory`, `TaskPriority`.
- `TaskState` is aliased to `TaskStatus` with legacy compatibility mappings (`IDLE` $\rightarrow$ `QUEUED`, `PENDING` $\rightarrow$ `QUEUED`, `PENDING_BLOCKED` $\rightarrow$ `BLOCKED_WAITING_LEASE`, `FAILED` $\rightarrow$ `FAILED_TERMINAL`).
- State transitions are logged through `core/tiered_logger.py` (`get_logger("core.task_manager")`) with origin taint tags `[TAINT:<plugin_id>]`.

---

## 5. Invariants & Implementation Boundaries

1. **Semaphore Allocation:** `_run_loop` must acquire worker semaphores prior to executing any job thread.
2. **Write Classification:** `is_db_write_heavy_running()` must include `BACKGROUND_METADATA` and `exclusive_db_lease`.
3. **Write Task Tagging:** System jobs performing bulk writes (`retroactive_metadata_enhancement`, `database_update`, `duplicate_scan_job`, `stale_track_scan_job`) must declare `category=TaskCategory.DATABASE_WRITE_HEAVY`.
4. **Buffer Limit:** The queue must enforce a bounded capacity (`max_pending_jobs = 100`) with deduplicated hybrid eviction.
5. **Zero Critical Violations Milestone:** Full codebase compliance is continuously gated by `scripts/audit_task_manager_adoption.py`. As of Phase 3 completion (2026-09-13), the scanner confirms **0 Critical Violations** (zero raw threads/pools) and **0 Medium Violations** (zero unleased SQLite writes).
