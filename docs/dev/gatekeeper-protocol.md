# IO Gatekeeper & RequestManager Invariant Protocols

## 1. Zero-Trust Filesystem Security: IO Gatekeeper

`core/io_gatekeeper.py` serves as the mandatory security barrier for all physical file mutations (relocations, renames, copies, deletions) in EchoSync. Direct usage of `os.rename`, `os.remove`, `os.unlink`, or `shutil.move` in business logic, services, or controllers is strictly forbidden.

---

## 2. Gatekeeper Architectural Invariants

```text
Service / Controller Call
           │
           ▼
┌──────────────────────────────┐
│  core.io_gatekeeper          │
│  Gatekeeper.authorize(...)   │
└──────────┬───────────────────┘
           │
           ├─► 1. Validate Plugin / Service Permissions
           ├─► 2. Validate Source & Destination Canonical Paths against Allowed Roots
           │
           ▼
┌──────────────────────────────┐
│  echosync_core Native FFI    │
│  safe_move_file / delete_file│
└──────────────────────────────┘
```

1. **Root Boundary Validation:** Paths are canonicalized using `Path.resolve()` and verified against authorized library root directories (`system.library_path`, `system.download_path`).
2. **Native Execution:** File operations are delegated to `echosync_core` native Rust functions (`safe_move_file`, `copy_file`, `delete_file`).
3. **Atomic Rollback:** If a move operation fails mid-transit, destination artifacts are cleaned up and source state is preserved.

---

## 3. Global Outbound HTTP Protocol: RequestManager

`core/request_manager.py` is the centralized HTTP client wrapper governing all outbound network requests.

### RequestManager Invariants

1. **Global Rate Limiting:** Enforces per-domain rate limits (e.g. MusicBrainz 1 req/sec, Discogs 1 req/sec) globally across all concurrent threads and plugins.
2. **Thread-Safe Asynchronous Locks:** Uses `asyncio.Lock` around rate limiter timestamp modifications to prevent race conditions that bypass limits.
3. **Automatic Retries & Backoff:** Implements exponential backoff on HTTP `429 Too Many Requests` and `5xx` server errors.
4. **Prohibition:** Raw `requests.get/post` or `httpx.get/post` calls in plugins or background services are architectural infractions.
