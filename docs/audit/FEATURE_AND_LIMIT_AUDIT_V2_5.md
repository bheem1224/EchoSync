# Feature & Limit Audit: v2.5.0 "Nexus Framework" Architecture

**Date:** 2026-03-24
**Scope:** v2.5.0 Release Candidate (`main` + Security Hardening Patches)
**Focus:** End-to-End User Workflows (QA), Plugin AST Sandbox Constraints, Database Boundaries, and Core Modularity.

---

## PART 1: The End-to-End User Sanity Check (QA)

The recent introduction of strict Path Jails, DB Session Scoping, and Sandboxes has been empirically verified against core workflows.

| System | Status | Where | How | Why |
| :--- | :--- | :--- | :--- | :--- |
| **Sync & Download Flow (Path Jails)** | **PASS** | `core/file_handling/base_io.py` | Executed a simulated file move. Safe paths executed cleanly. Illegal directory traversal paths correctly threw a `SecurityError` and aborted the operation. | `Path.is_relative_to` correctly validates without crashing the upstream execution chain. |
| **Retroactive Metadata Enhancer** | **PASS** | `services/metadata_enhancer.py` | Evaluated an enhancement batch execution. | Provider/API fetches (e.g., AcoustID/MusicBrainz calls) are correctly staged outside the `db.session_scope()` transaction block, preventing database locks during slow network resolutions. |
| **Media Manager (Duplicate Resolution)** | **PASS** | `services/library_hygiene.py` | Fed the manager duplicate file edge cases. | Detected varying bitrates/qualities and retained the highest quality file. Correctly flagged alternate versions (Live vs Studio) for manual review. Handled files with 1.5s padding delta successfully via `.auto_resolve`. |
| **Suggestion Engine (Fallbacks)** | **PASS** | `core/suggestion_engine/discovery.py` | Executed discovery queries on completely blank and highly obscure library configurations. | Ran successfully without throwing a `ZeroDivisionError` or database exceptions, confirming graceful fallbacks. |
| **Settings Boundary Isolation** | **PASS** | `core/settings.py` | Simulated saving both standard settings and API secrets. | Standard settings route cleanly to `config.json`. API secrets successfully map to the `config.db` database. Neither cross-contaminates. |
| **Operational DB Separation** | **PASS** | SQLite Connections | Evaluated connection URLs for `working.db` and `music_library.db`. | Validated that both databases hold separate connections and are explicitly siloed in memory and on disk. |
| **Download Manager (Queue Fan-Out)** | **PASS** | `services/download_manager.py` | Simulated 1-to-N query expansion via `pre_provider_search` hook. | The waterfall architecture executed the search array across simulated providers cleanly without dropping tasks or queue deadlocks. |

---

## PART 2: The Ultimate Plugin Developer Stress Test (Architecture)

### AST Sandbox Execution

The Zero-Trust AST Sandbox uses static analysis to reject forbidden file I/O operations and restrict application exposure. An execution sweep of our baseline plugins under the **Community Restrictions** yielded the following:

* **Compliant Plugins (Passed AST Scanner):** `outbound_gateway`, `local_player`
* **Non-Compliant Plugins (Failed AST Scanner):** `spotify`, `plex`, `musicbrainz`, `acoustid`, `slskd`, `local_metadata`, `cjk_language_pack`, `listenbrainz`

**Analysis:**
The Zero-Trust AST Scanner correctly identifies and blocks forbidden module imports (`os.unlink`, `database.music_database`, etc.). While official plugins bypass these checks using the `manifest.json` verified signature, any community port of these plugins would instantly hard-fail.
*Community plugins must aggressively transition to using the `LocalFileHandler` for I/O and the `ProviderStorageBox` SDK for data access.*

### Database SDK Constraints (`ProviderStorageBox`)

We stressed the exact boundaries of the `ProviderStorageBox` SQL wrapper given to plugins:
* **Table Creation:** **PASS**. The `create_table()` SDK hook securely and automatically enforces the `prv_{plugin-id}_{table_name}` namespace.
* **Core Interference (DROP/ALTER):** **PASS**. Custom `RestrictedConnection` logic successfully intercepted and blocked `DROP TABLE users` and `ALTER TABLE downloads` execution attempts, throwing a clean `PermissionError`.
* **Plugin Deletion (DROP self):** **PASS**. Plugins can successfully drop their own `prv_`-prefixed tables.

### Hardcoded Bottlenecks & Missing Hooks (Roadmap for v3.0)

Despite significant progress with `core/hook_manager.py`, the core application is not yet 100% modular. The following hardcoded bottlenecks prevent total ecosystem replacement:

#### 1. Core UI Delivery
**Status:** Hardcoded
**Where:** `serve_frontend()` in `web/api_app.py`
**Limit:** The frontend routing explicitly forces a `send_from_directory(app.static_folder, path)`.
**Workaround/Fix:** Requires a new Core Hook (e.g., `ON_FRONTEND_REQUEST`). If a plugin intercepts the path routing, it could return its own SPA artifact or template renderer, allowing full UI replacement.

#### 2. Internal Job Queue
**Status:** Hardcoded
**Where:** `JobQueue` in `core/job_queue.py`
**Limit:** The scheduling engine strictly depends on an internal `threading` lock array and `heapq` instance. A plugin cannot inject an external message broker (like Redis or Celery).
**Workaround/Fix:** Requires a new SDK Function or an `ON_JOB_ENQUEUED` skip hook that bypasses the internal `heapq.heappush` entirely, letting the plugin push the payload to an external server.

#### 3. Matching Engine Bypass
**Status:** Partially Modular
**Where:** `WeightedMatchingEngine` in `core/matching_engine/matching_engine.py`
**Limit:** While plugins can use `scoring_modifier` to boost confidence scores, or `ON_MATCH_FAILED` to salvage a rejected track, there is no top-level skip hook to bypass the engine entirely. The core CPU-heavy fuzzy text comparison algorithm *must* run.
**Workaround/Fix:** Add an `ON_ENGINE_EVALUATE` Skip-Hook at the top of `calculate_match()`. If a plugin (e.g., a pure Acoustic-Fingerprint engine) intercepts it, it can return a final confidence score instantly, skipping the string parsing phase.
