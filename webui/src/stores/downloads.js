import { writable, derived } from 'svelte/store';
import apiClient from '../api/client';

export const downloadQueue = writable([]);
export const activeDownloads = writable([]);
export const downloadHistory = writable([]);
export const activeDownloadCount = writable(0);
export const downloadStats = writable({
  totalSpeed: 0,
  activeCount: 0,
  queuedCount: 0,
  completedCount: 0,
  failedCount: 0,
  isRunning: false
});

let pollingTimer = null;

export async function fetchDownloads() {
  try {
    const [queueRes, jobsRes] = await Promise.allSettled([
      apiClient.get('/core/downloads/queue').catch(() => apiClient.get('/system/downloads/queue')),
      apiClient.get('/system/jobs').catch(() => null)
    ]);

    let allItems = [];
    if (queueRes.status === 'fulfilled' && queueRes.value?.data?.items) {
      allItems = queueRes.value.data.items;
      downloadQueue.set(allItems);
    }

    const activeStatuses = new Set(['DOWNLOADING', 'SEARCHING', 'QUEUED', 'PAUSED', 'downloading', 'searching', 'queued', 'paused']);
    const activeItems = allItems.filter(i => activeStatuses.has(i.status));
    activeDownloads.set(activeItems);

    const activelyRunningCount = allItems.filter(i => 
      ['DOWNLOADING', 'SEARCHING', 'QUEUED', 'downloading', 'searching', 'queued'].includes(i.status)
    ).length;
    activeDownloadCount.set(activelyRunningCount);

    const historyItems = allItems.filter(i => !activeStatuses.has(i.status));
    downloadHistory.set(historyItems);

    let totalSpeed = 0;
    for (const item of activeItems) {
      if (item.current_speed) {
        totalSpeed += Number(item.current_speed) || 0;
      }
    }

    let isJobRunning = false;
    if (jobsRes.status === 'fulfilled' && jobsRes.value?.data?.items) {
      const job = jobsRes.value.data.items.find(j => j.name === 'download_manager');
      isJobRunning = job ? !!job.running : false;
    }

    downloadStats.set({
      totalSpeed,
      activeCount: allItems.filter(i => ['DOWNLOADING', 'SEARCHING', 'downloading', 'searching'].includes(i.status)).length,
      queuedCount: allItems.filter(i => ['QUEUED', 'queued'].includes(i.status)).length,
      completedCount: allItems.filter(i => ['COMPLETED', 'completed'].includes(i.status)).length,
      failedCount: allItems.filter(i => ['FAILED', 'NOT_FOUND', 'failed', 'not_found'].includes(i.status)).length,
      isRunning: isJobRunning
    });
  } catch (err) {
    console.error('Failed to fetch downloads:', err);
  }
}

export function startDownloadsPolling(intervalMs = 4000) {
  fetchDownloads();
  if (pollingTimer) clearInterval(pollingTimer);
  pollingTimer = setInterval(fetchDownloads, intervalMs);
}

export function stopDownloadsPolling() {
  if (pollingTimer) {
    clearInterval(pollingTimer);
    pollingTimer = null;
  }
}
