import { writable } from 'svelte/store';

// Controls whether the settings side panel is open and which category is active
export const settingsPanel = writable({ open: false, active: 'preferences' });

export function openSettings(category = 'preferences') {
  settingsPanel.set({ open: true, active: category });
}

export function closeSettings() {
  settingsPanel.set({ open: false, active: 'preferences' });
}

export function setActive(category) {
  settingsPanel.update((s) => ({ ...s, active: category }));
}
