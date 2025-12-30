import { writable, derived } from 'svelte/store';
import apiClient from '../api/client';

function createProvidersStore() {
  const { subscribe, set, update } = writable({
    loaded: false,
    items: {},   // key: provider_id
  });

  async function load() {
    try {
      const response = await apiClient.get('/providers');
      const list = Array.isArray(response.data)
        ? response.data
        : Array.isArray(response.data?.plugins)
          ? response.data.plugins
          : [];
      const map = {};
      for (const provider of list) {
        map[provider.id] = provider;
      }
      set({ loaded: true, items: map });
    } catch (error) {
      console.error('Failed to load providers:', error);
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

export const providers = createProvidersStore();

/* 🔹 Derived helpers */

export const playlistProviders = derived(providers, ($providers) =>
  Object.values($providers.items).filter((p) => p.capabilities.supports_playlists !== 'NONE')
);

export const searchProviders = derived(providers, ($providers) =>
  Object.values($providers.items).filter((p) => p.capabilities.search?.tracks)
);
