# Dynamic Plugin UI Web Components

## 1. Overview & Architectural Boundaries

EchoSync UI extensions decouple host application Svelte 5 frontend architecture from plugin UI rendering using **Custom Web Components** (`CustomElements`).

Plugins package custom UI components as standalone JavaScript ES modules compiled with Svelte's `customElement: true` compiler option. The EchoSync SvelteKit host shell renders these custom elements dynamically inside the host DOM using `<DynamicPluginLoader />`.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        EchoSync Host Svelte App                        │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                 DynamicPluginLoader.svelte                     │   │
│   │                                                                │   │
│   │  1. Fetch active UI manifest (/api/system/plugins/ui-manifest) │   │
│   │  2. Inject ES module script tag (<script type="module">)      │   │
│   │  3. Render Custom Element: <svelte:element this="my-plugin">   │   │
│   └────────────────────────────────┬───────────────────────────────┘   │
│                                    │                                   │
│                                    ▼                                   │
│                  ┌──────────────────────────────────┐                  │
│                  │  Custom Web Component Shadow DOM │                  │
│                  │  (Isolated CSS & Custom Logic)   │                  │
│                  └──────────────────────────────────┘                  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Compiling Web Components with Svelte

To build a Web Component for EchoSync:

1. Configure `vite.config.js` or `svelte.config.js` with `customElement: true`:

```javascript
// svelte.config.js
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

export default {
  preprocess: vitePreprocess(),
  compilerOptions: {
    customElement: true,
  },
};
```

2. Declare the custom element tag inside the component header:

```svelte
<svelte:options customElement="echosync-plex-card" />

<script>
  // Props are passed as HTML attributes by DynamicPluginLoader
  export let apiBase = '';
  export let activeTrackId = '';

  async function syncLibrary() {
    await fetch(`${apiBase}/sync`, { method: 'POST' });
  }
</script>

<div class="plex-card">
  <h3>Plex Media Server Integration</h3>
  <button on:click={syncLibrary}>Trigger Full Sync</button>
</div>

<style>
  /* Encapsulated within Shadow DOM */
  .plex-card {
    background: #1e1a23;
    border: 1px solid #3d3741;
    border-radius: 8px;
    padding: 16px;
    color: #eadfed;
  }
</style>
```

---

## 3. Plugin Manifest UI Declaration

Plugins declare UI entry points inside `manifest.json` under the `components` object mapping component categories to Web Component HTML tag names:

```json
{
  "plugin_id": "community.plex.mediaserver",
  "name": "Plex Integration",
  "version": "1.2.0",
  "ui_bundle": "public/bundle.js",
  "components": {
    "media_server": "echosync-plex-card",
    "dashboard_widget": "echosync-plex-status-widget"
  }
}
```

---

## 4. Host Integration: `DynamicPluginLoader.svelte`

The host application loads custom Web Components via `DynamicPluginLoader.svelte`:

### Component Props

| Prop | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `category` | `string` | `""` | Target category key matching `plugin.components[category]` (e.g. `"media_server"`, `"music_service"`). |
| `passProps` | `object` | `{}` | Key-value pairs forwarded as HTML attributes to the rendered Web Component element. |
| `showEmpty` | `boolean` | `true` | Renders fallback slot when no plugins provide components for the category. |

### Usage Example in Host Page

```svelte
<script>
  import DynamicPluginLoader from '$components/DynamicPluginLoader.svelte';
</script>

<!-- Render all active media server plugin components -->
<DynamicPluginLoader
  category="media_server"
  passProps={{ "api-base": "/api/v1/plugins/plex", "user-id": "123" }}
>
  <div slot="default" class="empty-state">
    No media server plugins installed.
  </div>
</DynamicPluginLoader>
```

---

## 5. Security & Shadow DOM Isolation Rules

1. **CSS Encapsulation:** Style rules defined inside Web Components do not leak into the host DOM, protecting host theme styles.
2. **Host Theme Variable Usage:** Components can consume host CSS custom properties (e.g., `var(--color-primary, #ddb7ff)`).
3. **Event Dispatching:** Custom events dispatched from inside custom elements must set `bubbles: true` and `composed: true` to pass through the Shadow DOM boundary into host event listeners:

```javascript
this.dispatchEvent(new CustomEvent('plugin-action', {
  detail: { status: 'complete' },
  bubbles: true,
  composed: true
}));
```
