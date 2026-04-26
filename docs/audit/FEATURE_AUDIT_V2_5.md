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
