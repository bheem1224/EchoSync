<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import {
    fetchSystemHealth,
    fetchTaskQueue,
    type SystemHealthResponse,
    type TaskQueueSummaryResponse
  } from '../../api/systemTasks';

  let health: SystemHealthResponse | null = null;
  let queue: TaskQueueSummaryResponse | null = null;
  let loading = true;
  let errorMsg = '';
  let pollInterval: ReturnType<typeof setInterval> | null = null;

  async function loadData() {
    try {
      const [hData, qData] = await Promise.all([
        fetchSystemHealth(),
        fetchTaskQueue()
      ]);
      health = hData;
      queue = qData;
      errorMsg = '';
    } catch (err: any) {
      errorMsg = err?.message || 'Failed to update system metrics';
    } finally {
      loading = false;
    }
  }

  onMount(() => {
    loadData();
    pollInterval = setInterval(loadData, 5000);
  });

  onDestroy(() => {
    if (pollInterval) clearInterval(pollInterval);
  });

  function getStatusColor(status: string | undefined): { bg: string; text: string; dot: string } {
    const s = (status || 'healthy').toLowerCase();
    if (s === 'error') {
      return { bg: 'bg-red-500/10 border-red-500/30', text: 'text-red-400', dot: 'bg-red-500' };
    }
    if (s === 'degraded') {
      return { bg: 'bg-yellow-500/10 border-yellow-500/30', text: 'text-yellow-400', dot: 'bg-yellow-500' };
    }
    return { bg: 'bg-emerald-500/10 border-emerald-500/30', text: 'text-emerald-400', dot: 'bg-emerald-500' };
  }
</script>

<div class="bg-gray-900/90 border border-gray-800 rounded-xl p-5 shadow-lg backdrop-blur-sm">
  <div class="flex items-center justify-between mb-4">
    <div class="flex items-center space-x-3">
      <h3 class="text-lg font-semibold text-gray-100">System Health & Job Queue</h3>
      {#if health}
        {@const color = getStatusColor(health.status)}
        <span class={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${color.bg} ${color.text}`}>
          <span class={`w-2 h-2 rounded-full ${color.dot} animate-pulse`}></span>
          {health.status.toUpperCase()}
        </span>
      {/if}
    </div>
    {#if loading && !health}
      <span class="text-xs text-gray-400">Loading...</span>
    {/if}
  </div>

  {#if errorMsg && !health}
    <div class="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400 mb-3">
      {errorMsg}
    </div>
  {/if}

  {#if queue}
    <div class="grid grid-cols-4 gap-3 my-4">
      <div class="bg-gray-800/50 border border-gray-700/50 rounded-lg p-3 text-center">
        <div class="text-2xl font-bold text-gray-100">{queue.stats.total || 0}</div>
        <div class="text-xs font-medium text-gray-400 mt-1">Total Jobs</div>
      </div>
      <div class="bg-blue-500/10 border border-blue-500/20 rounded-lg p-3 text-center">
        <div class="text-2xl font-bold text-blue-400">{queue.stats.running || 0}</div>
        <div class="text-xs font-medium text-blue-300 mt-1">Running</div>
      </div>
      <div class="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 text-center">
        <div class="text-2xl font-bold text-amber-400">{queue.stats.pending || 0}</div>
        <div class="text-xs font-medium text-amber-300 mt-1">Pending</div>
      </div>
      <div class="bg-rose-500/10 border border-rose-500/20 rounded-lg p-3 text-center">
        <div class="text-2xl font-bold text-rose-400">{queue.stats.blocked || 0}</div>
        <div class="text-xs font-medium text-rose-300 mt-1">Pending Blocked</div>
      </div>
    </div>
  {/if}

  {#if health && health.plugin_states && Object.keys(health.plugin_states).length > 0}
    <div class="mt-4 pt-3 border-t border-gray-800">
      <div class="text-xs font-semibold text-gray-400 mb-2 uppercase tracking-wider">Plugin Lifecycle States</div>
      <div class="flex flex-wrap gap-2">
        {#each Object.entries(health.plugin_states) as [pluginId, status]}
          {@const color = getStatusColor(status.state)}
          <div class="flex items-center space-x-1.5 px-2.5 py-1 bg-gray-800/80 border border-gray-700/60 rounded-md text-xs">
            <span class="font-medium text-gray-200">{pluginId}</span>
            <span class={`px-1.5 py-0.5 text-[10px] uppercase font-semibold rounded ${color.bg} ${color.text}`}>
              {status.state}
            </span>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>
