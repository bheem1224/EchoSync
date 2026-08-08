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
import apiClient from '../api/client';

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
      const res = await apiClient.get('/v1/system/ui-registry');

      if (res.status !== 200) {
        if (res.status === 404) {
          console.warn('[pluginViews] registry endpoint not found (404). No plugin views registered.');
          _state.update((s) => ({ ...s, loaded: true, views: [] }));
          return;
        }
        throw new Error(`registry fetch failed: ${res.status} ${res.statusText}`);
      }

      const data = await res.json();
      const rawViews = Array.isArray(data?.views) ? data.views : [];

      /** @type {PluginView[]} */
      const views = [];

      for (const v of rawViews) {
        const id = v.tag_name ? v.tag_name.replace("es-view-", "") : "";
        if (!id) continue; // Malformed entry – skip

        views.push({
          id:       id,
          pluginId: v.plugin_name || String(v.plugin_id),
          title:    v.tag_name,
          icon:     v.icon ?? '🔌',
          yamlPath: v.entry ?? '',
          // Computed SvelteKit href — routed by the catch-all plugin-views page
          href:     `/plugin-views/${id}`,
        });
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
