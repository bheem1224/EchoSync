# ADR 0002: Re-entrant Scoped Write Leases and Universal SQLite WAL Session Enforcement

- **Status:** Accepted / Implemented
- **Date:** 2026-09-13
- **Authors:** EchoSync Architecture Group
- **Supercedes:** N/A
- **Governing Implementations:**
  - [`core/task_manager/task_queue.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/core/task_manager/task_queue.py) (`JobQueue.db_write_lease`, `_lease_holders: dict[int, int]`)
  - [`database/music_database.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/database/music_database.py) (`MusicDatabase.session_scope`)
  - [`database/working_database.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/database/working_database.py) (`WorkingDatabase.session_scope`, `PluginDatabaseFactory.session_scope`)
  - [`tests/core/test_phase_1a_task_manager_integration.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/tests/core/test_phase_1a_task_manager_integration.py)
  - [`tests/database/test_phase_3_task_manager_integration.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/tests/database/test_phase_3_task_manager_integration.py)

---

## 1. Context & Problem Statement

EchoSync utilizes SQLite in Write-Ahead Logging (WAL) mode for its primary databases (`music_library.db`, `working.db`, `config.db`). While SQLite WAL permits arbitrary concurrent readers, it fundamentally restricts write access to a **single writer at any given instant**.

Prior to Phase 1A, background worker threads, plugin hooks, and web endpoints executed concurrent database writes without centralized synchronization. Under load (e.g., simultaneous library synchronization, audio fingerprint backfilling, and user track rating), this caused pervasive `sqlite3.OperationalError: database is locked` exceptions, transaction rollbacks, and potential WAL index corruption.

Initial attempts to gate writes using standard Python non-reentrant locks or dispatch-level task categories failed when:
1. **Nested Service Calls:** High-level workflows (such as `DownloadManager._execute_waterfall_search_and_download`) acquired a write lease, then invoked lower-level repositories (`TrackRepository`, `DownloadRepository`) which also attempted to acquire write leases. Non-reentrant locks resulted in immediate self-deadlock on the worker thread.
2. **Uncoordinated Commit Sites:** Direct calls to `session.commit()` scattered across plugins, background services, and web routes bypassed queue-level gates.
3. **Granularity Mismatch:** Holding an exclusive database lock across an entire ingestion pass blocked concurrent readers and stalled fast metadata searches while the worker performed slow network I/O or native audio DSP.

---

## 2. Decision Drivers

- **Deterministic Write Mutual Exclusion:** Guarantee that at most one thread executes a write transaction against any SQLite database file at any instant.
- **Transparent Re-entrancy:** Allow nested function calls, repository methods, and session contexts on the same thread to acquire leases recursively without deadlocking or releasing the lease prematurely.
- **Universal Session Scope Protection:** Ensure all database mutations performed via standard SQLAlchemy `session_scope()` automatically acquire write leases, eliminating developer error at leaf commit sites.
- **Cross-Thread Blocking & Timeout Protection:** Enforce bounded FIFO waiting with configurable timeouts (default 30.0s) for distinct competing threads.
- **Zero Performance Penalty for Readers:** Read-only queries must never acquire write leases or block on concurrent read operations.

---

## 3. Considered Options & Trade-offs

### Option A: Coarse Global Process-Wide Mutex (`threading.Lock`)
- *Pros:* Simple single mutex across all operations.
- *Cons:* Blocks concurrent read queries; non-reentrant across composed workflows; forces slow network requests and CPU DSP to hold the database lock.

### Option B: Non-Reentrant Leaf-Only Write Leases
- *Pros:* Locks held only during the immediate `session.commit()` invocation.
- *Cons:* Multi-statement atomic transactions cannot span multiple repository calls; any nested lease acquisition causes immediate thread self-deadlock.

### Option C: Per-Thread Depth-Tracked Write Lease Embedded into `session_scope()` (Selected)
- *Pros:*
  1. `JobQueue` maintains an internal dictionary `_lease_holders: dict[int, int]` mapping `threading.get_ident()` to active lease recursion depth.
  2. The initial lease acquisition by thread $T$ claims the underlying write semaphore (`_db_write_semaphore.acquire(timeout=timeout)`).
  3. Subsequent nested acquisitions on thread $T$ immediately increment the depth counter without blocking.
  4. Nested exits decrement the depth counter; only when depth reaches 0 is the underlying write semaphore released.
  5. `session_scope()` in `music_database.py` and `working_database.py` wraps `session.commit()` inside `with db_write_lease():`, guaranteeing universal write lease coverage for all database writes across the entire codebase.
- *Cons:* Requires disciplined session scoping; raw `session.commit()` outside `session_scope()` must be wrapped manually or migrated.

---

## 4. Decision Outcome & Invariants

We adopt **Option C** across all database interactions. The operational invariants are:

### Invariant 1: Thread-Aware Depth Tracking
`JobQueue.db_write_lease(task_name, timeout)` must enforce per-thread depth tracking:
```python
tid = threading.get_ident()
with self._lease_state_lock:
    if tid in self._lease_holders:
        self._lease_holders[tid] += 1
        is_reentrant = True
    else:
        is_reentrant = False

if not is_reentrant:
    acquired = self._db_write_semaphore.acquire(timeout=timeout)
    if not acquired:
        raise TimeoutError(f"Database write lease timed out after {timeout}s for task '{task_name}'")
    with self._lease_state_lock:
        self._lease_holders[tid] = 1
try:
    yield
finally:
    with self._lease_state_lock:
        self._lease_holders[tid] -= 1
        if self._lease_holders[tid] <= 0:
            del self._lease_holders[tid]
            self._db_write_semaphore.release()
```

### Invariant 2: Universal `session_scope()` Enforcement
All session contexts created via `MusicDatabase.session_scope()` and `WorkingDatabase.session_scope()` must wrap `session.commit()` inside `with db_write_lease():`:
```python
@contextmanager
def session_scope(self) -> Generator[Session, None, None]:
    session = self.SessionLocal()
    try:
        yield session
        from core.task_manager import db_write_lease
        with db_write_lease(task_name="music_database_session"):
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

### Invariant 3: Safe Compound Context Managers
Top-level workflows may explicitly declare named write leases for audit tracing without conflicting with internal session commits:
```python
with db_write_lease(task_name="user_sync"), db.session_scope() as session:
    # Outer lease depth = 1
    # Inner session_scope commit re-enters at depth = 2
    session.add(entity)
```

### Invariant 4: Zero Unleased Database Writes
No runtime code in `core/`, `services/`, `database/`, `web/`, or `plugins/` may execute a database commit outside `db_write_lease()`. Compliance is strictly validated by `scripts/audit_task_manager_adoption.py` (0 Medium Violations).

---

## 5. Verification & Test Evidence

- **Re-entrancy Verification:** [`tests/core/test_phase_1a_task_manager_integration.py::test_reentrant_db_write_lease_nesting`](file:///c:/Users/bheem/VScode-Projects/EchoSync/tests/core/test_phase_1a_task_manager_integration.py) confirms depth increments from 1 to 3 and safely unwinds to 0 without deadlock.
- **Mutual Exclusion Verification:** [`tests/core/test_phase_1a_task_manager_integration.py::test_reentrant_db_write_lease_blocks_distinct_threads`](file:///c:/Users/bheem/VScode-Projects/EchoSync/tests/core/test_phase_1a_task_manager_integration.py) confirms distinct threads are blocked while a lease is active.
- **Nested Scope Integration:** [`tests/database/test_phase_3_task_manager_integration.py::test_reentrant_db_write_lease_across_nested_scopes`](file:///c:/Users/bheem/VScode-Projects/EchoSync/tests/database/test_phase_3_task_manager_integration.py) confirms nested `session_scope()` commits within outer leases succeed across both `music_library.db` and `working.db`.

