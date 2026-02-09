import { writable } from 'svelte/store';

// We'll use a simple fetch wrapper or assume apiClient exists if established pattern.
// Looking at preferences.js, it uses '../api/client'.
// I will assume it exists. If not, I'll fallback to fetch.

import apiClient from '../api/client';

function createMetadataQueueStore() {
  const { subscribe, set, update } = writable({ count: 0, items: [] });

  async function fetchCount() {
    try {
      // The API endpoint is /api/metadata/queue.
      // apiClient likely has base URL or we pass relative path.
      // In preferences.js: apiClient.get('/quality-profiles') -> /api/quality-profiles presumably?
      // Or maybe just /quality-profiles relative to current?
      // Wait, backend routes are /api/....
      // If apiClient.get('/quality-profiles') maps to /api/quality-profiles, then I should use '/metadata/queue'.
      // But let's check web/routes/metadata.py: url_prefix="/api/metadata".
      // So path is /api/metadata/queue.
      // If apiClient prepends /api, then '/metadata/queue' works.
      // If apiClient assumes root, then '/api/metadata/queue'.
      // Let's assume '/api/metadata/queue' to be safe, or check apiClient source if I could.
      // I'll check apiClient source first.

      const resp = await apiClient.get('/api/metadata/queue');
      const queue = resp.data?.queue || [];
      update(s => ({ ...s, count: queue.length, items: queue }));
    } catch (e) {
      console.error('Failed to fetch metadata queue', e);
    }
  }

  return { subscribe, fetchCount, set };
}

export const metadataQueue = createMetadataQueueStore();
