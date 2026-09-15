# ADR 0004: Plugin Isolation, Canonical Integer Taint, and Centralized Sidecar Contracts

- **Status:** Accepted / Implemented
- **Date:** 2026-09-13
- **Authors:** EchoSync Architecture Group
- **Supercedes:** N/A
- **Governing Implementations:**
  - [`core/tiered_logger.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/core/tiered_logger.py) (`get_logger`, `[TAINT:<int_id>]` formatting, unsigned 32-bit integer validation)
  - [`core/task_manager/supervisor.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/core/task_manager/supervisor.py) (`spawn_supervised_thread`, `bound_to_general_pool` contract)
  - [`plugins/EchoSync/slskd/plugin.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/plugins/EchoSync/slskd/plugin.py) (Supervised webhook callback threads)
  - [`plugins/EchoSync/tidal/client.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/plugins/EchoSync/tidal/client.py) (Supervised unbounded sidecar with deprecation warning)
  - [`plugins/EchoSync/local_server/`](file:///c:/Users/bheem/VScode-Projects/EchoSync/plugins/EchoSync/local_server/) (Lease-protected database cleanup)
  - [`tests/plugins/test_phase_2b_task_manager_integration.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/tests/plugins/test_phase_2b_task_manager_integration.py)

---

## 1. Context & Problem Statement

Plugins in EchoSync (`slskd`, `tidal`, `listenbrainz`, `spotify`, `cjk_language_pack`, `local_server`) provide critical integration surfaces for third-party streaming services and music servers. Because plugins run in the same process space as core components, unconstrained plugin behavior can jeopardize core system stability in three distinct ways:

1. **Telemetry & Log Taint Inconsistency:** Plugins historically passed arbitrary string namespaces (e.g., `"EchoSync.slskd"`, `"TidalClient"`, `"listenbrainz"`) or booleans to loggers. This created variable-width log formatting, broke telemetry ingestion pipelines that index numeric plugin IDs, and conflicted with `Account.plugin_id` database columns which require integer foreign keys.
2. **Worker Pool Slot Depletion:** Plugins frequently spawned background threads for idle listening (such as OAuth redirect handlers or event webhooks). When bound to the `JobQueue` General Worker Pool, these idle threads permanently occupied worker slots, starving core background tasks (library sync, audio fingerprinting).
3. **Ad-Hoc Port Collisions & Insecure Endpoints:** Individual plugins (such as Tidal OAuth) spun up ad-hoc localhost HTTP servers on hardcoded ports (e.g., port 8080/8888). In containerized environments sharing the host network, this created port collisions and exposed unencrypted redirect tokens.

---

## 2. Decision Drivers

- **Canonical Numeric Identity:** Establish a compact, deterministic, 32-bit unsigned integer identifier for every plugin.
- **Strict Logging Isolation (Zero Fallback Shims):** Log records from plugins must carry origin taint tags in a strictly validated format: `[TAINT:<int_id>]`. Invalid types (strings, booleans, floats) must be rejected immediately.
- **Worker Pool Slot Conservation:** Idle listening services must never consume general worker slots reserved for computational batch jobs.
- **Centralized OAuth Ingress:** Deprecate ad-hoc HTTP port binding in individual plugins in favor of a centralized HTTPS sidecar architecture.

---

## 3. Considered Options & Trade-offs

### Option A: String Namespaces with Optional Supervisor Registration
- *Pros:* Human-readable log prefixes (`[EchoSync.slskd]`).
- *Cons:* Inefficient database indexing; cannot link directly to relational tables; variable string formats complicate log scraping; no protection against rogue threads.

### Option B: Permissive Type Coercion (Auto-Hashing Strings)
- *Pros:* Backward-compatible with legacy plugin code.
- *Cons:* Violates the "No Legacy Shims" rule; masks developer typing bugs; results in non-deterministic IDs if string capitalization varies.

### Option C: Strict CRC32 Integer Tainting + Supervised Pool-Free Sidecars (Selected)
- *Pros:*
  1. Every plugin defines a canonical unsigned 32-bit integer:
     $$\text{PLUGIN\_CRC32} = \text{zlib.crc32}(\text{"author.slug"}.\text{encode}()) \ \& \ \text{0xFFFFFFFF}$$
  2. `core.tiered_logger.get_logger(name, plugin_id=...)` strictly enforces `isinstance(plugin_id, int)` and $0 \le \text{plugin\_id} \le \text{0xFFFFFFFF}$. Strings, booleans, and floats are rejected with `TypeError`. Taint tags format uniformly as `[TAINT:<int_id>]`.
  3. All plugin threads must be spawned via `supervisor.spawn_supervised_thread()` with `owner_type=OwnerType.PLUGIN` and `owner_id=str(PLUGIN_CRC32)`.
  4. Ephemeral background jobs set `bound_to_general_pool=True`; idle listeners (OAuth servers, webhooks) set `bound_to_general_pool=False`, ensuring zero worker slot starvation.
  5. Localhost port-binding HTTP servers are deprecated with runtime warnings urging migration to EchoSync's centralized HTTPS sidecar.
- *Cons:* Requires plugins to compute `PLUGIN_CRC32` and pass explicit integer IDs.

---

## 4. Decision Outcome & Invariants

We adopt **Option C**. The operational invariants are:

### Invariant 1: Canonical 32-Bit Unsigned Integer `plugin_id`
Every plugin module must compute its canonical identifier using standard CRC32:
```python
import zlib

PLUGIN_CRC32: int = zlib.crc32(b"EchoSync.slskd") & 0xFFFFFFFF
```
No string namespaces or arbitrary integer values outside $[0, 2^{32} - 1]$ are permitted.

### Invariant 2: Strict Type Enforcement in `tiered_logger`
`core/tiered_logger.py` enforces integer typing without fallback shims:
```python
if plugin_id is not None:
    if isinstance(plugin_id, bool) or not isinstance(plugin_id, int):
        raise TypeError(f"plugin_id must be an unsigned 32-bit integer, got {type(plugin_id).__name__}")
    if not (0 <= plugin_id <= 0xFFFFFFFF):
        raise ValueError(f"plugin_id must be an unsigned 32-bit integer (0..4294967295), got {plugin_id}")
```
Log output formats the origin taint tag as `[TAINT:<int_id>]`.

### Invariant 3: Supervised Thread Lifecycle & Worker Pool Protection
Plugins must never instantiate raw `threading.Thread`. All plugin threads must register through `ProcessSupervisor`:
- **Active / Ephemeral Workers:** Spawn with `bound_to_general_pool=True` to claim a general worker slot for the duration of the task.
- **Idle Listeners / Sidecars:** Spawn with `bound_to_general_pool=False` so they remain supervised without depleting worker slots.

### Invariant 4: Centralized Zero-Trust OAuth Token Broker & Port Binding Prohibition
Plugins must not bind raw TCP ports on the host (port 8889 in Tidal has been eliminated).
1. External authentication flows route through EchoSync's Centralized Token Broker on port 5001 (`core/oauth/sidecar.py`).
2. **Zero-Trust Direct Caller Return:** The sidecar terminates TLS, manages high-entropy PKCE challenges (`S256`), executes upstream token exchanges, and directly returns credentials in-memory to the initiating plugin's private callback (`OAuthSession.on_token`). Tokens are strictly NEVER emitted over `EventBus`.
3. **Supervisor Burst Dispatch:** In-memory callback execution is dispatched via `supervisor.spawn_supervised_thread(bound_to_general_pool=False, owner_type=OwnerType.PLUGIN, owner_id=str(plugin_id), category=ProcessCategory.CORE_SYSTEM)`.
4. **Lease-Protected Encrypted Persistence:** Plugins persist received tokens into `config.db` using `sdk.accounts.save_token()` wrapped in `with job_queue.db_write_lease():` under AES-256-GCM encryption.

---

## 5. Verification & Test Evidence

- **Type Safety Tests:** [`tests/plugins/test_phase_2b_task_manager_integration.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/tests/plugins/test_phase_2b_task_manager_integration.py) verifies:
  - `test_tiered_logger_integer_plugin_id`: PASSED
  - `test_tiered_logger_rejects_string_plugin_id`: PASSED (`TypeError` raised)
  - `test_tiered_logger_rejects_boolean_plugin_id`: PASSED (`TypeError` raised)
  - `test_tiered_logger_rejects_out_of_range_plugin_id`: PASSED (`ValueError` raised)
- **Supervision & Pool Isolation Tests:**
  - `test_slskd_eventbus_callbacks_spawn_supervised_threads`: PASSED (`bound_to_general_pool=True`)
  - `test_tidal_oauth_sidecar_retired_and_warns`: PASSED (port 8889 retired, delegates to centralized HTTPS sidecar)
- **Centralized OAuth Sidecar Capability Tests:** [`tests/core/test_oauth_sidecar_capability.py`](file:///c:/Users/bheem/VScode-Projects/EchoSync/tests/core/test_oauth_sidecar_capability.py) verifies:
  - Strict unsigned 32-bit integer `plugin_id` enforcement in `OAuthSession` and `sidecar.py`.
  - S256 PKCE challenge and high-entropy state generation.
  - Upstream token exchange execution inside sidecar with direct caller in-memory return.
  - Supervised callback dispatch with `bound_to_general_pool=False`.
  - Zero-Trust EventBus Invariant: 0 tokens leaked to EventBus.
- **Zero Critical Violations:** AST scanner reports **0 Critical Violations** and **0 Unleased Writes** across the entire repository.

