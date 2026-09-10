# Dynamic Plugin UI Web Components

## 1. Overview & Architectural Boundaries

EchoSync UI extensions decouple host application Svelte frontend architecture from plugin UI rendering using **Custom Web Components** (`CustomElements`).

## 2. Dynamic Web Component Rendering

- Web Component bundles compiled by plugins are served via `/api/ui/components/{plugin_id}` (`web/routes/ui_registry.py`).
- Host interface mounts plugin elements dynamically via `DynamicPluginLoader.svelte` in `webui/src/components/`.
- Communication between host SPA and plugin custom elements uses standard CustomEvents (`echosync-action`, `echosync-state-change`).
