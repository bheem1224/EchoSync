# Core System Architectural Invariants for Autonomous Coding Agents

## 1. Executive Directive

Autonomous coding agents (e.g. Jules, AI assistants) contributing code to EchoSync must adhere strictly to these non-negotiable architectural invariants.

---

## 2. Invariant Rules Matrix

### Rule 1: Audio Tagging & Mutagen Prohibition
- Tag reading, writing, and Chromaprint extraction MUST route strictly through native `lofty` in `echosync_core` (`src/metadata/`).
- Direct imports of `mutagen`, `tinytag`, or `taglib` in runtime Python code are critical violations.
- Verification command: `uv run python tools/lint_audio_calls.py`.

### Rule 2: Zero-Trust Filesystem Mutations (Gatekeeper Protocol)
- All physical file relocations, renames, and deletions MUST route through `core/io_gatekeeper.py`, invoking `echosync_core.safe_move_file`, `copy_file`, or `delete_file`.
- Raw `os.rename`, `os.remove`, or `shutil.move` calls within services or route controllers violate the Gatekeeper boundary.

### Rule 3: Three-Database Partitioning & Concurrency
- `config.db`: Read-heavy system configuration, credentials, and encrypted tokens.
- `working.db`: Ephemeral task state, ingestion buffers (`VirtualTrackCache`), review queues.
- `library.db`: Pristine canonical entity graph (`Track`, `LocalMedia`).
- Direct `sqlite3.connect()` calls and synchronous N+1 write loops are forbidden. All operations must use batched SQLAlchemy sessions via `session_scope()`.

### Rule 4: Lightweight Event Bus Identity
- Events published via `core/event_bus.py` MUST transmit lightweight entity identifiers (`sync_id`, `media_id`), never monolithic serialized track dictionaries.
- Serialization MUST occur in the caller thread before pushing payload to queue to prevent race conditions.

### Rule 5: Backend Primitive Payloads & Frontend Formatting Boundary
- Backend API endpoints must return raw primitive values (e.g. rounded integer seconds for duration/uptime).
- String formatting, humanization, and localization are strictly responsibilities of the decoupled Svelte frontend.

### Rule 6: No Legacy Shims
- When a method or pattern is deprecated, remove it completely instead of writing backward-compatibility wrapper shims.

### Rule 7: Invariant: Concurrency, Worker Pool Isolation & Progressive Scaling
- Background workers, system jobs, and plugins MUST NOT spawn unmanaged native OS threads (`threading.Thread().start()`), `multiprocessing.Process`, or unconstrained `ThreadPoolExecutor` instances.
- All execution must be arbitrated by `JobQueue` using the two-tier worker pool (ADR 0001, ADR 0003):
  - **Pool 1 (Critical):** 2 reserved slots strictly for `TaskCategory.CRITICAL` and interactive API operations (streaming playback, search queries, manual user interactions, system power lifecycle). Background ingestion or reconciliation tasks are forbidden from acquiring Critical slots. During system shutdown or restart pending, critical tasks can still execute to cleanly flush buffers.
  - **Pool 2 (General):** Bounded pool ($N$ slots, default 2, configurable up to host core quotas) for bulk processing (`DATABASE_WRITE_HEAVY`, `BACKGROUND_METADATA`, `GENERAL`).
- The in-memory job buffer must enforce bounded capacity limits (`max_pending_jobs = 100`) with deduplicated hybrid eviction to prevent memory exhaustion during massive library ingestion passes.
- Computationally heavy tasks (audio tag decoding, audio fingerprinting) must be offloaded to native Rust (`echosync_core`), which scales progressively with host CPU quotas (1–4 cores: 1 thread, 5–8 cores: $\lfloor\text{cores}/2\rfloor$, $>8$ cores: max 8) and releases the Python GIL. Python orchestrators must process batches sequentially without nested thread pools.

### Rule 8: Invariant: Universal SQLite Write Mutual Exclusion & Re-entrant Leases
- EchoSync operates against SQLite in WAL mode where write concurrency is strictly single-writer.
- All database mutations MUST acquire `db_write_lease` (ADR 0002).
- All SQLAlchemy writes route through `session_scope()` in `database/music_database.py` and `database/working_database.py`, which internally wrap `session.commit()` inside `with db_write_lease():`.
- `db_write_lease` enforces thread-aware re-entrancy depth tracking (`_lease_holders: dict[int, int]`), allowing nested workflows and repository transactions to execute safely without self-deadlock while strictly serializing writes across distinct threads.
- Direct or unleased database commits are strictly forbidden. System jobs performing bulk writes (`retroactive_metadata_enhancement`, `database_update`, `library_sync`, `duplicate_scan`) MUST declare `TaskCategory.DATABASE_WRITE_HEAVY`.

### Rule 9: Invariant: Three-Stage Escalation & Cooperative Cancellation Contract
- All background tasks, worker threads, and plugin processes must register with `ProcessSupervisor` (`core/task_manager/supervisor.py`).
- Termination follows the three-stage escalation protocol (ADR 0001):
  1. **Cooperative Yield & Sliced Wait:** Tasks, polling loops, retry backoffs (`ErrorHandler.handle_exception`), and rate limiters (`TokenBucketRateLimiter.wait`) must periodically check `supervisor.is_current_task_cancelled()` or `job_queue.should_yield()`. Long sleeps must be sliced into cooperative increments ($\le 0.2\text{s}$) or use `Event.wait(timeout)` rather than un-interruptible `time.sleep()`.
  2. **Graceful Thread Cancellation:** Signaling `cancellation_event` or FFI cancellation tokens with a bounded grace period (default 3.0s) to abort cleanly, roll back partial transactions, and exit.
  3. **Process/PID Termination:** Forced OS process termination (`os.kill`) or WASM epoch interruption via `ProcessSupervisor` is reserved strictly for detached worker processes and sandboxed WASM runtimes. Production Python threads must never be forcefully aborted via unsafe C-API calls (`PyThreadState_SetAsyncExc`).

### Rule 10: Invariant: Strict Integer Plugin-ID Tainting
- Plugin identifiers across runtime, database records, and telemetry MUST be canonical unsigned 32-bit integers computed as `zlib.crc32(f"{author}.{slug}".encode()) & 0xFFFFFFFF` (ADR 0004).
- `core.tiered_logger.get_logger(..., plugin_id=...)` strictly enforces `isinstance(plugin_id, int)` and $0 \le \text{plugin\_id} \le \text{0xFFFFFFFF}$. Dotted string namespaces, floats, booleans, and out-of-range integers are rejected with `TypeError`/`ValueError` without fallback shims.
- Taint tags MUST format uniformly in log streams as `[TAINT:<int_id>]`.

### Rule 11: Invariant: Centralized Zero-Trust OAuth Token Broker & Port Isolation
- Individual plugins MUST NOT bind raw host TCP ports (e.g. ad-hoc HTTP callback listeners on port 8080/8888/8889) (ADR 0004).
- External authentication redirects (OAuth) route through EchoSync's centralized HTTPS Token Broker on port 5001 (`core/oauth/sidecar.py`).
- **Zero-Trust Direct Caller Return:** The sidecar terminates TLS, verifies high-entropy PKCE challenges (`S256`), executes upstream token exchange directly on port 5001, and resolves credentials directly to the calling plugin in-memory via private SDK callback hooks (`OAuthSession.on_token`). Tokens MUST NEVER be emitted over `EventBus` to prevent lateral credential sniffing.
- **Supervised Dispatch:** Callback execution is dispatched via `supervisor.spawn_supervised_thread(bound_to_general_pool=False, owner_type=OwnerType.PLUGIN, owner_id=str(plugin_id), category=ProcessCategory.CORE_SYSTEM)`, ensuring credential resolution never blocks or consumes General Pool slots.
- **Lease-Protected Encrypted Persistence:** Calling plugins persist received tokens immediately into `config.db` using `sdk.accounts.save_token()` wrapped within `with job_queue.db_write_lease():` using AES-256-GCM encryption.
