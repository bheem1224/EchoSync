import { writable } from 'svelte/store';

export const isDownloadDrawerOpen = writable(false);
export const toggleDownloadDrawer = () => isDownloadDrawerOpen.update(v => !v);
export const openDownloadDrawer = () => isDownloadDrawerOpen.set(true);
export const closeDownloadDrawer = () => isDownloadDrawerOpen.set(false);
