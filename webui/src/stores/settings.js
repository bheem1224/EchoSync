import { writable } from 'svelte/store';
import apiClient from '../api/client';

function createSettingsStore() {
  const { subscribe, set, update } = writable({
    loaded: false,
    version: null,
    schema: null,
    data: {},
  });

  async function load() {
    try {
      const response = await apiClient.get('/settings');
      
      // Extract version and schema if backend exposes them
      const version = response.data?.version || response.data?.schema_version || null;
      const schema = response.data?.schema || null;
      const data = response.data?.settings || response.data?.data || response.data;
      
      set({ 
        loaded: true, 
        version,
        schema,
        data 
      });
    } catch (error) {
      console.error('Failed to load settings:', error);
      set({ loaded: false, version: null, schema: null, data: {} });
    }
  }

  async function save(patch) {
    try {
      await apiClient.post('/api/settings', patch);
      update((state) => ({
        ...state,
        data: { ...state.data, ...patch },
      }));
    } catch (error) {
      console.error('Failed to save settings:', error);
    }
  }

  return {
    subscribe,
    load,
    save,
  };
}

export const settings = createSettingsStore();
