import { writable } from 'svelte/store';

// Placeholder stores for GlobalHeader badges.
// Hook these up to backend polling/actions from layout or page-level logic later.
export const unreadAlerts = writable(0);
export const activeDownloads = writable(0);
