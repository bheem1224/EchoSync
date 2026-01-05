import { writable } from 'svelte/store';
import apiClient from '../api/client';

function createPreferencesStore() {
  const { subscribe, set, update } = writable({ loaded: false, profiles: [] });

  async function load() {
    try {
      const resp = await apiClient.get('/quality-profiles');
      const profiles = resp.data?.profiles || [];
      set({ loaded: true, profiles });
    } catch (e) {
      console.error('Failed to load quality profiles, falling back to settings', e);
      // fallback to settings key
      try {
        const sresp = await apiClient.get('/settings');
        const data = sresp.data?.settings || {};
        const profiles = Array.isArray(data.quality_profiles) ? data.quality_profiles : [];
        set({ loaded: true, profiles });
      } catch (e2) {
        console.error('Fallback load failed', e2);
        set({ loaded: true, profiles: [] });
      }
    }
  }

  async function saveProfiles(profiles) {
    try {
      await apiClient.post('/quality-profiles', { profiles });
      update((s) => ({ ...s, profiles }));
    } catch (e) {
      console.error('Failed to save quality profiles via API, falling back to settings.save', e);
      try {
        await apiClient.post('/settings', { quality_profiles: profiles });
        update((s) => ({ ...s, profiles }));
      } catch (e2) {
        console.error('Fallback save also failed', e2);
      }
    }
  }

  // Local-only mutations (do not persist) used by the UI until user clicks Save All
  function setLocalProfiles(profiles) {
    update((s) => ({ ...s, profiles }));
  }

  function updateLocalProfile(profile) {
    update((s) => {
      const list = Array.isArray(s.profiles) ? [...s.profiles] : [];
      const idx = list.findIndex((p) => String(p.id) === String(profile.id));
      if (idx >= 0) list[idx] = profile; else list.push(profile);
      return { ...s, profiles: list };
    });
  }

  async function saveProfile(profile) {
    try {
      await apiClient.post('/quality-profile', { profile });
      // merge into existing store
      update((s) => {
        const list = Array.isArray(s.profiles) ? [...s.profiles] : [];
        const idx = list.findIndex((p) => String(p.id) === String(profile.id));
        if (idx >= 0) list[idx] = profile; else list.push(profile);
        return { ...s, profiles: list };
      });
    } catch (e) {
      console.error('Failed to save single profile via API, falling back to full save', e);
      try {
        const s = await apiClient.get('/quality-profiles');
        const profiles = s.data?.profiles || [];
        await apiClient.post('/quality-profiles', { profiles });
        update((st) => ({ ...st, profiles }));
      } catch (e2) {
        console.error('Fallback single profile save also failed', e2);
      }
    }
  }

  return { subscribe, load, saveProfiles, saveProfile, setLocalProfiles, updateLocalProfile };
}

export const preferences = createPreferencesStore();
