# EchoSync Lifecycle Hook Matrix & Frontend Web Component Integration

## 1. Overview & Execution Model

EchoSync uses `HookManager` (`core/hook_manager.py`) to manage hook registration, filter pipeline execution, and UI Web Component extension loading.

Hooks operate in two modes:
1. **Filters (`apply_filters(hook_name, default_value, *args, **kwargs)`):** Pass a value sequentially through registered subscriber callbacks, allowing plugins to inspect, mutate, or override data structures.
2. **Actions (`trigger(hook_name, *args, **kwargs)`):** Dispatch notification events without modifying return values.

---

## 2. Infrastructure & System Hooks

| Hook Name | Type | Arguments (`*args`, `**kwargs`) | Expected Return Type | Description / Intent | File Location |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ON_API_STARTUP` | Action | `app: FastAPI` | `None` | Fired when the main API app starts up. Allows plugins to attach routes. | `web/api_app.py` |
| `AUTHENTICATE_USER` | Filter | `request: Request` | `Optional[Dict[str, Any]]` | Intercepts authentication requests (e.g. for OIDC/SSO bypass). | `web/auth.py` |
| `ON_INBOUND_WEBHOOK` | Filter | `payload: dict, headers: dict` | `Union[str, dict, None]` | Intercepts raw webhook calls. Returning `"SKIP"` bypasses core parsing. | `web/routes/webhooks.py` |
| `RESOLVE_STORAGE_PATH` | Filter | `remote_path: str` | `Optional[Path]` | Translates virtual remote file paths to local filesystem paths. | `core/utils/__init__.py` |

---

## 3. Matching & Metadata Pipeline Hooks

| Hook Name | Type | Arguments (`*args`, `**kwargs`) | Expected Return Type | Description / Intent | File Location |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `pre_normalize_text` | Filter | `text: str` | `str` | Pre-processes string before title/artist normalization. | `core/matching_engine/text_utils.py` |
| `pre_normalize_title` | Filter | `title: str`, `plugin_context: dict` | `str` | Pre-processes song titles before candidate matching. | `core/db/echo_sync_track.py` |
| `ON_SCORING_WEIGHTS_CALCULATE` | Filter | `weights_dict: dict` | `dict` | Overrides matching engine field scoring weights dynamically. | `core/matching_engine/matching_engine.py` |
| `ON_ENGINE_EVALUATE` | Filter | `state: dict, source: dict, candidate: dict` | `dict` | Intercepts matching evaluation and forces match outcome. | `core/matching_engine/matching_engine.py` |
| `ON_MATCH_FAILED` | Filter | `target_track: dict, candidates: list` | `Optional[dict]` | Custom fallback handler when no confidence match meets threshold. | `core/matching_engine/matching_engine.py` |
| `register_metadata_requirements` | Filter | `requirements: list` | `list` | Registers custom metadata fields required before track import. | `services/metadata_enhancer.py` |
| `post_metadata_enrichment` | Filter | `track: Track` | `Track` | Mutates track metadata after enrichment steps complete. | `services/metadata_enhancer.py` |

---

## 4. Download & Media Lifecycle Hooks

| Hook Name | Type | Arguments (`*args`, `**kwargs`) | Expected Return Type | Description / Intent | File Location |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `pre_search_query` | Filter | `query: str, target: dict` | `str` | Mutates download search query terms before sending to providers. | `services/download_manager.py` |
| `ON_DOWNLOAD_DECISION` | Filter | `candidate: dict` | `Optional[dict]` | Approves, rejects, or modifies download candidates in queue. | `services/download_manager.py` |
| `ON_DOWNLOAD_PROGRESS` | Action | `download_id: str, provider_id: str, progress: float, state: str` | `None` | Real-time progress updates during download stream. | `services/download_manager.py` |
| `ON_DOWNLOAD_COMPLETED` | Action | `download_id: str, provider_id: str` | `None` | Fired upon successful download completion before auto-import. | `services/download_manager.py` |
| `ON_CORRUPTION_DETECTED` | Filter | `file_path: str` | `Optional[str]` | Custom handling when corrupt or unreadable audio file is found. | `services/media_manager.py` |

---

## 5. Playlists & Suggestion Engine Hooks

| Hook Name | Type | Arguments (`*args`, `**kwargs`) | Expected Return Type | Description / Intent | File Location |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `BEFORE_SUGGESTION_GENERATION` | Filter | `params: dict` | `dict` | Mutates input parameters before running suggestion algorithms. | `web/routes/suggestions.py` |
| `PROVIDE_VIBE_PROFILE` | Filter | `user_id: str, days: int` | `Optional[dict]` | Provides custom audio vibe profiles (tempo, energy, valence). | `core/suggestion_engine/vibe_profiler.py` |
| `ON_SUGGESTION_READY` | Filter | `pending_tracks: list, account_id: str` | `list` | Filters or re-ranks generated track suggestions before UI return. | `web/routes/suggestions.py` |
| `GENERATE_DYNAMIC_PLAYLIST` | Filter | `playlist_type: str, limit: int` | `Optional[list]` | Generates dynamic playlist track entries from external providers. | `core/personalized_playlists.py` |
| `ON_PLAYLIST_SAVED` | Action | `playlist_name: str, target: str, synced_count: int` | `None` | Fired when a playlist is exported or synced to a media server. | `web/routes/playlists.py` |

---

## 6. Dynamic Frontend UI Integration (`customElement: true`)

Plugins can extend the SvelteKit 2 host shell interface by registering Custom Elements.

### Compilation Requirement
Plugin UI components must be compiled using Svelte with `customElement: true`:
```javascript
// svelte.config.js in plugin UI package
export default {
  compilerOptions: {
    customElement: true
  }
};
```

### Manifest UI Registration
In `manifest.json`:
```json
{
  "ui_components": [
    {
      "tag_name": "echosync-slskd-status",
      "script_url": "/api/v1/plugins/community.slskd/bundle.js",
      "slot": "dashboard_widget"
    }
  ]
}
```

### Host Rendering via `DynamicPluginLoader.svelte`
The host UI uses `webui/src/components/DynamicPluginLoader.svelte` to fetch the registered UI manifest, inject the ES module script tag (`<script type="module">`), and dynamically instantiate the custom web element into the host DOM slot:

```svelte
<!-- DynamicPluginLoader.svelte -->
<script>
  import { onMount } from 'svelte';
  export let slot = 'dashboard_widget';
  let components = [];

  onMount(async () => {
    const res = await fetch(`/api/v1/ui/components?slot=${slot}`);
    components = await res.json();
    for (const comp of components) {
      if (!customElements.get(comp.tag_name)) {
        await import(/* @vite-ignore */ comp.script_url);
      }
    }
  });
</script>

{#each components as comp}
  <svelte:element this={comp.tag_name} />
{/each}
```
