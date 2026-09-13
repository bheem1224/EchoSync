# ADR 0003: Container-Aware Native Thread Scaling and GIL-Isolated Execution

- **Status:** Accepted / Implemented
- **Date:** 2026-09-13
- **Authors:** EchoSync Architecture Group
- **Supercedes:** N/A
- **Governing Implementations:**
  - [`src/lib.rs`](file:///c:/Users/bheem/VScode-Projects/EchoSync/src/lib.rs) (`init_native_thread_pool`, `rayon::ThreadPoolBuilder`)
  - [`core/task_manager/task_queue.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/core/task_manager/task_queue.py) (`JobQueue.__init__` native bootstrapping)
  - [`services/library_sync_service.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/services/library_sync_service.py) (Sequential extraction with cooperative cancellation)
  - [`plugins/EchoSync/local_server/client.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/plugins/EchoSync/local_server/client.py) (Sequential crawler)
  - [`tests/core/test_phase_1a_task_manager_integration.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/tests/core/test_phase_1a_task_manager_integration.py)

---

## 1. Context & Problem Statement

EchoSync frequently operates in resource-constrained environments, including Docker and Podman containers, Unraid servers, TrueNAS SCALE apps, and single-board computers (Raspberry Pi 4/5). In these environments, CPU quotas are tightly constrained by cgroups, and excessive thread creation starves neighboring services or triggers kernel OOM kills.

In legacy iterations, service layers frequently spawned Python-level `concurrent.futures.ThreadPoolExecutor` instances:
- `services/library_sync_service.py` spawned `ThreadPoolExecutor(max_workers=min(32, (os.cpu_count() or 1) + 4))` to extract metadata from discovered audio tracks.
- `plugins/EchoSync/local_server/client.py` spawned `ThreadPoolExecutor(max_workers=8)` to scan directory trees.

This architecture suffered from two critical defects:
1. **Python GIL Contention:** Python threads executing audio tag decoding and hashing contended for the Global Interpreter Lock (GIL), freezing WebUI response times and causing playback buffer underruns.
2. **Container Starvation & Thrashing:** Fixed 8-thread or 32-thread pools on a 2-core container generated severe context switching overhead, CPU throttling, and host exhaustion.

---

## 2. Decision Drivers

- **Container & Homelab Friendliness:** Respect host CPU limits dynamically without manual user tuning.
- **True Parallelism via GIL Release:** Execute computationally heavy audio decoding, metadata extraction, and Chromaprint fingerprinting in native Rust (`echosync_core`), completely releasing the Python GIL.
- **Single-Tier Orchestration:** Python services must orchestrate tasks sequentially or via bounded `JobQueue` jobs, eliminating nested `ThreadPoolExecutor` anti-patterns.
- **Idempotent Bootstrapping:** Native thread pool initialization must be safe to call repeatedly across application lifecycles and tests.
- **Cooperative Preemption:** Long-running batch loops must inspect cancellation state at every item boundary.

---

## 3. Considered Options & Trade-offs

### Option A: Unconstrained Python `ThreadPoolExecutor`
- *Pros:* Easy standard library call.
- *Cons:* Heavy GIL contention; bypasses Task Manager supervision; causes CPU starvation on low-core hosts; triggers AST critical violations.

### Option B: Fixed-Capacity Native Thread Pool (e.g., 4 Threads)
- *Pros:* Predictable resource usage.
- *Cons:* Starves 1–2 core single-board hosts; underutilizes high-end homelab servers (e.g., 16–32 core AMD EPYC/Ryzen).

### Option C: Progressive Core-Proportional Native Rayon Scaling with Sequential Python Orchestration (Selected)
- *Pros:*
  1. Implements native thread management via Rayon in `src/lib.rs` exposed through PyO3 (`init_native_thread_pool`).
  2. Dynamically scales worker capacity using a progressive formula:
     - $1 \le \text{cores} \le 4 \implies 1 \text{ worker thread}$ (protects low-end hosts from context-switching overhead).
     - $5 \le \text{cores} \le 8 \implies \lfloor\text{cores} / 2\rfloor \text{ worker threads}$.
     - $\text{cores} > 8 \implies 8 \text{ max worker threads}$ (prevents memory and thread saturation).
  3. Allows explicit override via `ECHOSYNC_NATIVE_THREADS` environment variable or manual parameter.
  4. Bootstraps automatically during `JobQueue.__init__()`.
  5. Python services process items sequentially, passing batches directly to native Rust routines and checking `supervisor.is_current_task_cancelled()` at each iteration.
- *Cons:* Requires native extension build support (`maturin develop` / `uv run maturin`).

---

## 4. Decision Outcome & Invariants

We adopt **Option C**. The operational invariants are:

### Invariant 1: Progressive Core Scaling Formula
The native Rayon global thread pool in `src/lib.rs` must compute thread capacity using:
```rust
let default_threads = match num_cpus {
    1..=4 => 1,
    5..=8 => num_cpus / 2,
    _ => 8,
};
```
An explicit environment variable `ECHOSYNC_NATIVE_THREADS` or an argument to `init_native_thread_pool(threads)` overrides this heuristic, bounded strictly between 1 and 8 threads.

### Invariant 2: Idempotent Bootstrapping in `JobQueue`
`JobQueue.__init__` must initialize native thread scaling upon startup:
```python
try:
    import echosync_core
    if hasattr(echosync_core, "init_native_thread_pool"):
        echosync_core.init_native_thread_pool()
except (ImportError, AttributeError):
    pass
```
Multiple calls to `init_native_thread_pool` are guaranteed idempotent and return the existing active thread count without reinitializing the global Rayon pool.

### Invariant 3: Prohibition of Python `ThreadPoolExecutor`
No service in `core/`, `services/`, or `plugins/` may instantiate `concurrent.futures.ThreadPoolExecutor` or `ProcessPoolExecutor`. CPU-heavy passes (metadata extraction, audio fingerprinting) must be offloaded to native `echosync_core` functions, while the Python caller loops sequentially with cooperative preemption:
```python
for item in batch:
    if supervisor.is_current_task_cancelled():
        logger.info("Batch processing cancelled cooperatively.")
        break
    process_item(item)
```

---

## 5. Verification & Test Evidence

- **Idempotency & Scaling Verification:** [`tests/core/test_phase_1a_task_manager_integration.py::test_native_thread_pool_initialization_and_idempotency`](file:///c:/Users/bheem/VScode-Projects/EchoSync/tests/core/test_phase_1a_task_manager_integration.py) verifies that `init_native_thread_pool()` returns bounded integer worker counts and handles repeat calls idempotently.
- **Sequential Extraction Verification:** [`tests/services/test_phase_1b_task_manager_integration.py::test_library_sync_sequential_extraction_no_thread_pool`](file:///c:/Users/bheem/VScode-Projects/EchoSync/tests/services/test_phase_1b_task_manager_integration.py) confirms that `LibrarySyncService` processes audio files sequentially without invoking `ThreadPoolExecutor`.
- **AST Concurrency Zero-Critical Milestone:** `scripts/audit_task_manager_adoption.py` scans all Python files for `ThreadPoolExecutor` and reports **0 Critical Violations**.

