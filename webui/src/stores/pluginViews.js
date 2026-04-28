/**
 * pluginViews.js
 * ──────────────────────────────────────────────────────────────────────
 * Global Svelte store that holds every plugin-declared "custom view"
 * surfaced by GET /api/system/plugins/ui-manifest.
 *
 * Structure of each PluginView:
 *   {
 *     id        : string   – globally unique, e.g. "spotify_analytics"
 *     pluginId  : string   – parent plugin folder_name, e.g. "spotify"
 *     title     : string   – display label, e.g. "Spotify Stats"
 *     icon      : string   – emoji / mdi token, e.g. "♫"
 *     yamlPath  : string   – URL to the view's YAML, e.g. "/api/plugins/spotify/static/dashboard.yaml"
 *     href      : string   – computed SvelteKit route, e.g. "/plugin-views/spotify_analytics"
 *   }
 *
 * The store is populated once at layout load (called from +layout.svelte's
 * onMount) and is read-only from all consumers.
 */

import { writable, derived, get } from 'svelte/store';

// ── Internal writable ─────────────────────────────────────────────────────
const _state = writable({
  loaded: false,
  views:  /** @type {PluginView[]} */ ([]),
  error:  null,
});

// ── Public read-only derived ──────────────────────────────────────────────
/** All registered plugin custom views. */
export const pluginViews = derived(_state, ($s) => $s.views);

/** True once the manifest has been fetched (even if empty or errored). */
export const pluginViewsLoaded = derived(_state, ($s) => $s.loaded);

// ── Loader ────────────────────────────────────────────────────────────────
let _loadPromise = null;

/**
 * Fetch the UI manifest and populate the store.
 * Safe to call multiple times – only performs the network request once.
 */
export async function loadPluginViews() {
  // Return the in-flight promise if already loading / loaded
  if (_loadPromise) return _loadPromise;

  _loadPromise = (async () => {
    try {
      const res = await fetch('/api/system/plugins/ui-manifest', {
        credentials: 'include',
      });

      if (!res.ok) {
        if (res.status === 404) {
          console.warn('[pluginViews] ui-manifest endpoint not found (404). No plugin views registered.');
          _state.update((s) => ({ ...s, loaded: true, views: [] }));
          return;
        }
        throw new Error(`ui-manifest fetch failed: ${res.status} ${res.statusText}`);
      }

      const data = await res.json();
      const plugins = Array.isArray(data?.plugins) ? data.plugins : [];

      /** @type {PluginView[]} */
      const views = [];

      for (const plugin of plugins) {
        const rawViews = Array.isArray(plugin.views) ? plugin.views : [];
        for (const v of rawViews) {
          if (!v.id || !v.title) continue; // Malformed entry – skip

          views.push({
            id:       v.id,
            pluginId: plugin.id,
            title:    v.title,
            icon:     v.icon ?? '🔌',
            yamlPath: v.yaml_path ?? '',
            // Computed SvelteKit href — routed by the catch-all plugin-views page
            href:     `/plugin-views/${v.id}`,
          });
        }
      }

      _state.update((s) => ({ ...s, loaded: true, views, error: null }));
    } catch (err) {
      const msg = err?.message ?? String(err);
      console.warn('[pluginViews] Failed to load plugin views:', msg);
      _state.update((s) => ({ ...s, loaded: true, views: [], error: msg }));
    }
  })();

  return _loadPromise;
}

/**
 * Reset the store (useful in tests or after plugin install).
 * Clears the cached promise so the next loadPluginViews() re-fetches.
 */
export function resetPluginViews() {
  _loadPromise = null;
  _state.set({ loaded: false, views: [], error: null });
}
