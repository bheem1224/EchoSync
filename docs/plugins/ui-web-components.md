# Plugin UI & Custom Web Components Integration

## 1. Frontend Architecture Overview

EchoSync's frontend is built with **SvelteKit 2** and **Svelte 5** (`webui/`). To maintain strict micro-frontend decoupling, plugins do not inject Svelte component source code directly into the host repository build. Instead, plugins compile standalone **Custom Elements (Web Components)** (`customElement: true`).

```text
+-----------------------------------------------------------------------------------+
| SvelteKit 2 Host Application Shell (`webui/src/`)                                 |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  | Settings / Dashboard Page                                                   |  |
|  |                                                                             |  |
|  |   +---------------------------------------------------------------------+   |  |
|  |   | `DynamicPluginLoader.svelte`                                        |   |  |
|  |   |                                                                     |   |  |
|  |   |  1. Fetch UI manifest (`/api/v1/plugins/{id}/ui_manifest`)           |   |  |
|  |   |  2. Load JS bundle (`injectPluginBundle()`)                         |   |  |
|  |   |  3. Instantiate Web Component (`<echosync-plex-dashboard>`)         |   |  |
|  |   +---------------------------------------------------------------------+   |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Declaring UI Capabilities (`ui_manifest.json`)

Plugins that expose dashboard widgets, settings screens, or custom media controls must supply a `ui_manifest.json` file in their root plugin directory:

```json
{
  "tag_name": "echosync-plex-dashboard",
  "bundle_path": "ui/plugin-component.js",
  "customElement": true,
  "slot": "dashboard_widget",
  "title": "Plex Server Status",
  "min_width": 4,
  "min_height": 3
}
```

- **`tag_name`**: The custom element HTML tag name (must contain a hyphen).
- **`bundle_path`**: Relative path to the compiled JavaScript web bundle.
- **`customElement`**: Must be set to `true` to indicate standard Web Component registration.
- **`slot`**: Injection target in the UI layout (`dashboard_widget`, `media_details_tab`, `settings_panel`).

---

## 3. Web Component Implementation Standard

Plugin frontend bundles must register standard Custom Elements extending `HTMLElement`:

```javascript
class EchoSyncPlexDashboard extends HTMLElement {
  connectedCallback() {
    this.attachShadow({ mode: 'open' });
    this.shadowRoot.innerHTML = `
      <style>
        .widget-card {
          padding: 1rem;
          background: var(--bg-surface-2, #1e1e2e);
          color: var(--text-main, #cdd6f4);
          border-radius: 8px;
          font-family: system-ui, sans-serif;
        }
      </style>
      <div class="widget-card">
        <h3>Plex Media Server</h3>
        <p>Status: <span id="status">Connected</span></p>
      </div>
    `;
  }
}

if (!customElements.get('echosync-plex-dashboard')) {
  customElements.define('echosync-plex-dashboard', EchoSyncPlexDashboard);
}
```

---

## 4. Host Mounting via `DynamicPluginLoader.svelte`

The host UI component `webui/src/components/DynamicPluginLoader.svelte` handles the dynamic lifecycle of plugin elements:

1. Retrieves active plugin UI manifests from the backend REST endpoint.
2. Calls `injectPluginBundle(bundleUrl)` to asynchronously append the JS script to the document body.
3. Dynamically creates the element (`document.createElement(tagName)`) and appends it to the specified slot container in the DOM.
4. Handles CSS isolation via Shadow DOM to prevent plugin styling leaks into the host shell.
