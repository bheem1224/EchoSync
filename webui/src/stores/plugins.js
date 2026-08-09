import { writable, derived } from 'svelte/store';
import apiClient from '../api/client';

function createPluginsStore() {
  const { subscribe, set, update } = writable({
    loaded: false,
    items: {},   // key: plugin_id
  });

  async function load() {
    try {
      const response = await apiClient.get('/system/plugins');
      const list = Array.isArray(response.data)
        ? response.data
        : Array.isArray(response.data?.plugins)
          ? response.data.plugins
          : [];
      const map = {};
      for (const plugin of list) {
        map[plugin.id] = plugin;
      }
      set({ loaded: true, items: map });
    } catch (error) {
      console.error('Failed to load plugins:', error);
    }
  }

  function refresh() {
    return load();
  }

  return {
    subscribe,
    load,
    refresh,
  };
}

export const plugins = createPluginsStore();

/* 🔹 Derived helpers */

// Plugins that are not disabled
export const enabledPlugins = derived(plugins, ($plugins) =>
  Object.values($plugins.items).filter((p) => !p.disabled)
);

export const playlistPlugins = derived(enabledPlugins, ($plugins) =>
  $plugins.filter((p) => p.capabilities.supports_playlists !== 'NONE')
);

export const searchPlugins = derived(enabledPlugins, ($plugins) =>
  $plugins.filter((p) => p.capabilities.search?.tracks)
);
