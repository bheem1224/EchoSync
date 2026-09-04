# Plugin Hook Matrix & Event Directory

## 1. Overview

EchoSync plugins interact with the core application through two distinct messaging patterns:
1. **Hook Filters (`HookManager`)**: Synchronous mutator or interceptor callbacks registered via `hook_manager.add_filter()` that inspect, transform, or reject domain data during execution pipelines.
2. **Event Subscriptions (`EventBus`)**: Asynchronous, lightweight event notifications fired via `event_bus.publish()` carrying scalar entity references (`sync_id`, `media_id`).

---

## 2. Core Hook Filter Matrix

| Hook Name | Type | Invocation Location | Context / Arguments | Expected Return Type | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ON_API_STARTUP` | Mutator | `web/api_app.py` | `app` (FastAPI instance) | `None` | Fires right before application web routes spin up. Used to register custom API routes. |
| `AUTHENTICATE_USER` | Interceptor | `web/routes/auth.py` | `credentials` (dict) | `dict` or `None` | Allows plugins to intercept login requests and perform external OIDC/SAML authentication. |
| `ON_INBOUND_WEBHOOK` | Interceptor | `web/routes/webhooks.py` | `payload` (dict), `source` (str) | `"SKIP"` or `None` | Intercepts raw webhook requests before media server parsing. Returning `"SKIP"` handles the webhook. |
| `ON_JOB_ENQUEUED` | Mutator | `core/job_queue.py` | `job_spec` (dict) | `dict` | Fired when a job is enqueued; allows altering execution priority, interval, or retries. |
| `ON_JOB_FAILED` | Event | `core/job_queue.py` | `job_id` (str), `error` (str) | `None` | Fired when a background job exhausts all retries. |
| `pre_normalize_text` | Mutator | `core/matching_engine/text_utils.py` | `text` (str) | `str` | Applied to text strings prior to matching engine normalization. |
| `pre_normalize_title` | Mutator | `core/matching_engine/text_utils.py` | `title` (str), `plugin_context` (dict) | `str` | Fired before title matching to transform script (e.g. CJK Romaji conversion). |
| `ON_SCORING_WEIGHTS_CALCULATE` | Mutator | `core/matching_engine/matching_engine.py` | `weights_dict` (dict) | `dict` | Dynamically overrides metadata confidence scoring weights in Tier 1 engine. |
| `ON_ENGINE_EVALUATE` | Interceptor | `core/matching_engine/matching_engine.py` | `eval_spec` (dict), `source`, `candidate` | `dict` with `{'skip': bool, 'result': MatchResult}` | Intercepts track evaluation; allows short-circuiting match decisions. |
| `ON_MATCH_FAILED` | Event | `core/matching_engine/matching_engine.py` | `target_track` (dict), `candidates` (list) | `None` | Fired when no candidates pass the confidence threshold. |
| `PROVIDE_VIBE_PROFILE` | Interceptor | `core/suggestion_engine/vibe_profiler.py` | `user_id` (str), `days` (int) | `dict` or `None` | Allows plugins to supply custom audio feature vectors for recommendation scoring. |
| `register_metadata_requirements` | Mutator | `core/database/repositories/track_repo.py` | `required_keys` (list) | `list` | Allows plugins to declare mandatory metadata fields required for track sync. |
| `RESOLVE_STORAGE_PATH` | Interceptor | `core/utils.py` | `remote_path` (str) | `str` or `None` | Intercepts remote media path translations (e.g. mapping Plex virtual paths to local mounts). |
| `GENERATE_DYNAMIC_PLAYLIST` | Interceptor | `core/personalized_playlists.py` | `playlist_type` (str), `limit` (int) | `list` of track dicts | Generates dynamic recommendations for personalized playlists. |

---

## 3. Event Bus Subscriptions

Plugins subscribe to application events using `event_bus.subscribe("EVENT_NAME", handler)`:

| Event Name | Transmitted Payload Signature | Description |
| :--- | :--- | :--- |
| `DOWNLOAD_INTENT` | `{"sync_id": str, "artist": str, "title": str, "mbid": str}` | Published when missing media is queued for acquisition. |
| `TRACK_ACQUIRED` | `{"sync_id": str, "media_id": int, "file_path": str}` | Published when physical media is successfully downloaded and tagged. |
| `METADATA_ENHANCED` | `{"media_id": int, "fields_updated": list}` | Published when retroactive metadata enrichment completes. |
| `LIFECYCLE_ACTION` | `{"track_id": int, "action": "DELETE" \| "UPGRADE"}` | Published when suggestion engine consensus triggers track deletion or upgrade. |

---

## 4. Frontend Custom Element Web Components (`customElement: true`)

Plugin UI components render dynamically into the host SvelteKit SPA without modifying core web bundle assets.

- **Manifest Declaration (`ui_manifest.json`):**
  ```json
  {
    "tag_name": "echosync-plex-dashboard",
    "bundle_path": "ui/plugin-component.js",
    "customElement": true,
    "slot": "dashboard_widget"
  }
  ```
- **Rendering Mechanism:** `DynamicPluginLoader.svelte` in `webui/src/components/DynamicPluginLoader.svelte` fetches the JS bundle, executes `customElements.define('echosync-plex-dashboard', CustomClass)`, and injects the Web Component element directly into the DOM slot.
