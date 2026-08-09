import { writable, derived } from 'svelte/store';
import apiClient from '../api/client';

function createPreferencesStore() {
  const { subscribe, set, update } = writable({ loaded: false, profiles: [] });

  // Local UI preferences persisted to localStorage
  const LOCAL_KEY = 'soulsync.ui.prefs';
  function _loadLocalUi() {
    try {
      const raw = localStorage.getItem(LOCAL_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (e) {
      console.warn('Failed to load local UI prefs', e);
      return {};
    }
  }

  function _saveLocalUi(obj) {
    try {
      localStorage.setItem(LOCAL_KEY, JSON.stringify(obj || {}));
    } catch (e) {
      console.warn('Failed to save local UI prefs', e);
    }
  }

  function getUiPreference(key, defaultValue = undefined) {
    const obj = _loadLocalUi();
    if (Object.prototype.hasOwnProperty.call(obj, key)) return obj[key];
    return defaultValue;
  }

  function setUiPreference(key, value) {
    const obj = _loadLocalUi();
    obj[key] = value;
    _saveLocalUi(obj);
  }

  async function load() {
    try {
      const resp = await apiClient.get('/system/quality-profiles');
      const profiles = resp.data?.profiles || [];
      set({ loaded: true, profiles });
    } catch (e) {
      console.error('Failed to load quality profiles, falling back to settings', e);
      // fallback to settings key
      try {
        const sresp = await apiClient.get('/system/settings');
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
      await apiClient.post('/system/quality-profiles', { profiles });
      update((s) => ({ ...s, profiles }));
    } catch (e) {
      console.error('Failed to save quality profiles via API, falling back to settings.save', e);
      try {
        await apiClient.post('/system/settings', { quality_profiles: profiles });
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
      await apiClient.post('/system/quality-profile', { profile });
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
        const s = await apiClient.get('/system/quality-profiles');
        const profiles = s.data?.profiles || [];
        await apiClient.post('/system/quality-profiles', { profiles });
        update((st) => ({ ...st, profiles }));
      } catch (e2) {
        console.error('Fallback single profile save also failed', e2);
      }
    }
  }

  return { subscribe, load, saveProfiles, saveProfile, setLocalProfiles, updateLocalProfile, getUiPreference, setUiPreference };
}

export const preferences = createPreferencesStore();

// ── Sidebar customization preferences ────────────────────────────────────
// Stored inside the same localStorage key as other UI prefs.
// Shape: { hiddenRoutes: string[], pinnedViews: string[] }

const SIDEBAR_HIDDEN_KEY  = 'sidebar.hiddenRoutes';
const SIDEBAR_PINNED_KEY  = 'sidebar.pinnedViews';

/** Locked routes that are NEVER allowed to be hidden (hard guarantee). */
export const LOCKED_ROUTES = new Set(['/settings', '/sync', '/library']);

function _loadSidebarRaw() {
  try {
    const raw = localStorage.getItem('soulsync.ui.prefs');
    const obj = raw ? JSON.parse(raw) : {};
    return {
      hiddenRoutes: Array.isArray(obj[SIDEBAR_HIDDEN_KEY]) ? obj[SIDEBAR_HIDDEN_KEY] : [],
      pinnedViews:  Array.isArray(obj[SIDEBAR_PINNED_KEY])  ? obj[SIDEBAR_PINNED_KEY]  : [],
    };
  } catch {
    return { hiddenRoutes: [], pinnedViews: [] };
  }
}

function _saveSidebarRaw(hiddenRoutes, pinnedViews) {
  try {
    const raw = localStorage.getItem('soulsync.ui.prefs');
    const obj = raw ? JSON.parse(raw) : {};
    obj[SIDEBAR_HIDDEN_KEY] = hiddenRoutes.filter(r => !LOCKED_ROUTES.has(r));
    obj[SIDEBAR_PINNED_KEY] = pinnedViews;
    localStorage.setItem('soulsync.ui.prefs', JSON.stringify(obj));
  } catch (e) {
    console.warn('[sidebarPrefs] Failed to persist:', e);
  }
}

function createSidebarPrefsStore() {
  const initial = typeof localStorage !== 'undefined' ? _loadSidebarRaw() : { hiddenRoutes: [], pinnedViews: [] };
  const { subscribe, set, update } = writable(initial);

  /** Toggle visibility of a route href (locked routes are silently ignored). */
  function toggleHidden(href) {
    if (LOCKED_ROUTES.has(href)) return; // locked — no-op
    update(s => {
      const set  = new Set(s.hiddenRoutes);
      set.has(href) ? set.delete(href) : set.add(href);
      const next = { ...s, hiddenRoutes: [...set] };
      _saveSidebarRaw(next.hiddenRoutes, next.pinnedViews);
      return next;
    });
  }

  /** Toggle pin state of a plugin view id. */
  function togglePinned(viewId) {
    update(s => {
      const arr = s.pinnedViews.includes(viewId)
        ? s.pinnedViews.filter(id => id !== viewId)
        : [...s.pinnedViews, viewId];
      const next = { ...s, pinnedViews: arr };
      _saveSidebarRaw(next.hiddenRoutes, next.pinnedViews);
      return next;
    });
  }

  /** Move a pinned view up/down in order. */
  function reorderPinned(viewId, direction) {
    update(s => {
      const arr = [...s.pinnedViews];
      const idx = arr.indexOf(viewId);
      if (idx === -1) return s;
      const target = idx + (direction === 'up' ? -1 : 1);
      if (target < 0 || target >= arr.length) return s;
      [arr[idx], arr[target]] = [arr[target], arr[idx]];
      const next = { ...s, pinnedViews: arr };
      _saveSidebarRaw(next.hiddenRoutes, next.pinnedViews);
      return next;
    });
  }

  return { subscribe, toggleHidden, togglePinned, reorderPinned };
}

export const sidebarPrefs = createSidebarPrefsStore();
