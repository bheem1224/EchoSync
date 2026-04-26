# EchoSync v2.5.0 Feature Audit Report

## Executive Summary
This document outlines critical logic flaws and discrepancies discovered during the v2.5.0 feature audit. Key issues found:
1. **Plugin Loader Architecture Mismatch:** UI elements for plugins are defined in `ui_manifest.json`, not `manifest.json`, which breaks assumptions if validation strictly checks `manifest.json`.
2. **Download Manager Tie-Breaker Crash / Logic Flaw:** Missing `queue_length` values from plugins default to `0`, making unresponsive or missing peer data appear as the "fastest" source.
3. **Federated Discovery Timeout Risk:** Using `asyncio.gather` with `return_exceptions=True` correctly prevents UI hangs, but a slow plugin will still block the entire response for up to 5 seconds.
4. **Various Artists Overwrite Risk:** "Various Artists" tags can falsely achieve ~41% fuzzy matching scores with certain artists, and the engine fails to definitively bypass "Various Artists" tag pollution when local files misattribute it.

---

## 1. The Nexus Framework (UI/UX) Plugin Loader
**File:** `core/plugin_loader.py`, `web/routes/plugins.py`

**Finding:**
The audit revealed an architectural discrepancy: plugin UI definitions (like `ui_element_tag` and components) are **not** loaded from `manifest.json`. They are loaded from `ui_manifest.json` (see `core/plugin_loader.py:428` and `web/routes/plugins.py:16`).

If a plugin's `manifest.json` is malformed, the `PluginLoader` wraps the JSON parsing in a `try/except` block (e.g. `core/plugin_loader.py:155` for community plugins). It will skip loading the manifest data but will *not* crash the core app. If `ui_manifest.json` is missing or invalid, it gracefully degrades by simply not including the UI components in the `/api/system/plugins/ui-manifest` endpoint.

**Required Fix / Documentation Update:**
No immediate code change is required to prevent a crash, as the error handling is robust. However, documentation and validation tools must be updated to reflect that `ui_manifest.json` is the sole source of truth for UI elements.

---

## 2. Auto-Importer "Various Artists" Defense
**Files:** `core/file_handling/tagging_io.py`, `core/matching_engine/matching_engine.py`

**Finding:**
When comparing "Britney Spears" (TPE1) against "Various Artists" (TPE2), the engine uses Python's `difflib.SequenceMatcher` (`core/matching_engine/matching_engine.py:1159`).

**Mathematical Proof:**
`SequenceMatcher(None, "britney spears", "various artists").ratio()` returns exactly `0.413793` (approx 41.4%).

Because the `tagging_io.py:136` logic forces `TPE1` to always win unless it's completely missing, the metadata parser will extract "Britney Spears" as `track_artist` and "Various Artists" as `album_artist`. During the matching phase, the comparison between the source artist ("Britney Spears") and candidate artist ("Britney Spears" derived from local tags) will yield a 1.0 match.

However, if a compilation track erroneously *lacks* a TPE1 tag, `tagging_io.py:140` will promote `TPE2` ("Various Artists") to `track_artist`. If this candidate is compared against an API source looking for "Britney Spears", the `artist_score` evaluates to `0.413` which is multiplied by the artist weight (typically 30%), yielding an artist contribution of roughly 12.4 points instead of 30.

**Recommendation:**
The reverse "Various Artists" amnesty logic currently only applies when `candidate.artist_name` is exactly "Various Artists" AND a CJK OST marker is present in the title. We need a general penalty for "Various Artists" to prevent it from ever scoring 41% against real artists.

```python
# In core/matching_engine/matching_engine.py:1016 (inside _calculate_fuzzy_text_match)
        if source.artist_name and candidate.artist_name:
            # Prevent "Various Artists" from partially matching real names
            if source.artist_name.lower() != "various artists" and candidate.artist_name.lower() == "various artists":
                 artist_score = 0.0
            else:
                 artist_score = self._fuzzy_match(source.artist_name, candidate.artist_name)
```

---

## 3. Tie-Breaker Strategy & Sorting Logic
**File:** `core/matching_engine/matching_engine.py:1217` (used by `services/download_manager.py`)

**Finding:**
When `tie_breaker` is set to `SPEED`, the sort key returns `(score, -queue_length, upload_speed)`.

If the Soulseek provider returns `None` or an empty string for `queue_length`, the fallback logic is:
`queue_length = cand.identifiers.get('queue_length', 0) or 0`

**Critical Flaw:**
If `queue_length` is missing (`None`), it defaults to `0`. Because the sort orders by `-queue_length` descending (which means highest negative number, i.e., closest to 0), a missing queue length is treated as a queue length of 0. This makes a broken/unresponsive provider look like the *fastest available source* with no queue, prioritizing it over legitimate peers that report a queue of 1 or 2.

**Required Fix:**
Missing `queue_length` must default to infinity (or a very high number) to penalize missing peer data.

```python
# In core/matching_engine/matching_engine.py:1204
            # Safe extraction: missing queue_length means we don't know, so penalize it heavily.
            raw_queue = cand.identifiers.get('queue_length')
            queue_length = int(raw_queue) if raw_queue is not None and str(raw_queue).strip() else 999999

            upload_speed = cand.identifiers.get('upload_speed', 0) or 0
```

---

## 4. Federated Omnibar Timeout Behavior
**File:** `web/services/search_service.py:102`

**Finding:**
The federated discovery endpoint utilizes `asyncio.gather(*tasks, return_exceptions=True)`.

Inside `fetch_provider()`, the actual plugin call is executed via:
`await asyncio.wait_for(loop.run_in_executor(None, provider.search, query, "track", 20), timeout=5.0)`

**Conclusion:**
If a plugin (e.g. MusicBrainz) takes 15 seconds to respond, the `asyncio.wait_for` wrapper enforces a strict **5.0 second timeout**. The UI will hang for exactly 5 seconds waiting for the slow provider, after which a `TimeoutError` is raised internally. Because `return_exceptions=True` is used on `asyncio.gather`, the entire application does **not** crash. The slow provider is safely ignored and logged, while the other fast providers' results are returned to the frontend.

**Recommendation:**
The timeout is correctly implemented. However, 5 seconds might be too long for an interactive "Omnibar" search experience. Consider reducing the timeout to `2.5` seconds for search-as-you-type UX.

---

## 5. The Tie-Breaker Data Pipeline (Slskd)
**File:** `plugins/slskd/client.py`

**Finding:**
We investigated whether the Slskd plugin properly hydrates the `identifiers` dictionary required for the `SPEED` tie-breaker.
The code at `plugins/slskd/client.py:463` correctly parses the raw API payload: `upload_speed=response_data.get('uploadSpeed', 0)` and `queue_length=response_data.get('queueLength', 0)`.
Furthermore, inside `_process_and_queue_download` (line 364), the values are successfully injected into the `EchoSyncTrack` instance:
`echo_track.identifiers['upload_speed'] = result.upload_speed`
`echo_track.identifiers['queue_length'] = result.queue_length`

**Conclusion:**
The Slskd data pipeline successfully supports the `SPEED` tie-breaker. The `SPEED` logic relies on these injected identifiers, which are verifiably present.

---

## 6. Web Component State Desync (UI Theme/Profile)
**Files:** `webui/src/routes/settings/preferences/+page.svelte`, plugin UI `.svelte` files.

**Finding:**
EchoSync utilizes an isolated Svelte custom elements (Web Components) architecture.
When the user changes global UI state (like the Light/Dark theme dropdown in preferences), the core SvelteKit application updates its local state and CSS variables.
However, Web Components (`plugins/*/ui/`) do not automatically inherit or observe Svelte's internal state stores unless explicitly passed as reactive attributes. Because the `manifestData.plugins` script injection (`dashboard/+page.svelte`) mounts these components without binding to a global state context, the plugin UI cards do not react to global theme changes.

**Recommendation:**
Standardize on the global App Shell Tailwind CSS variables (`--es-*`) for all Web Components to ensure they inherit the visual state from the DOM tree organically. If explicit JS state is needed, the core dashboard loader must pass state via attributes (e.g., `<svelte:element this={card.type} theme={$currentTheme} />`) and the Web Component must reactively parse it.

---

## 7. The "Chaotic User" Fuzzer (Media Manager Queue System)
**File:** `services/download_manager.py` (triggered via `services/media_manager.py`)

**Finding:**
If a chaotic user rapid-fires the "Approve" button 5 times on the same suggestion, what happens to the database?
The `approve_suggestion` endpoint delegates to `dm.queue_download(track)`.
Inside `queue_download`, before inserting into the database, it calls `_find_existing_download(track_json)`. This function calculates a normalized track signature and queries the `working_db` for any downloads in an active state (`"queued"`, `"searching"`, `"downloading"`).

**Conclusion:**
If an active download matches the signature, it immediately aborts and returns the existing download ID.
The backend strictly enforces idempotency against rapid-fire requests. No duplicate jobs will be queued.

---

## 8. Plugin Router Collisions (Micro-API Mounting)
**Files:** `core/plugin_router.py`, `web/api_app.py`

**Finding:**
If two different plugins accidentally attempt to register identical API routes (e.g., via `PluginRouterRegistry.mount_router`), the behavior depends on the exact `Blueprint` instantiation:
1. **Name Collision (Fatal):** If two plugins instantiate a Flask Blueprint with the exact same name (e.g., `Blueprint('myplugin', ...)`), Flask will raise an Exception during `app.register_blueprint(bp)` inside `api_app.py`. This exception is wrapped in a `try/except` block (`web/api_app.py:108`), which prints an error but **prevents the app from crashing**. The second plugin's routes fail to mount.
2. **URL Route Collision (Silent Failure):** If they use different blueprint names but mount to the exact same URL namespace (e.g., both use `url_prefix='/api/plugins/shared_name'`), Flask will register both without crashing. However, during routing, the first registered plugin will silently hijack all matching requests, and the second plugin's endpoints will be completely unreachable.

**Recommendation:**
Enforce dynamic blueprint naming based on the strict `plugin_id` folder name, rather than letting plugins define their own Blueprint identifiers or URL prefixes.

```python
# In core/plugin_router.py
        # Force the blueprint name to avoid Flask registry collisions
        router.name = f"plugin_router_{plugin_id}"
        prefix = f"/api/plugins/{plugin_id}"
        router.url_prefix = prefix
```
