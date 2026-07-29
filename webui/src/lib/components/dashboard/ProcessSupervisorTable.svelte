<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import {
    fetchProcesses,
    terminateProcess,
    type ProcessOwner,
    type ProcessListResponse
  } from '../../api/systemTasks';

  let processes: ProcessOwner[] = [];
  let total = 0;
  let loading = true;
  let terminatingIds = new Set<string>();
  let toastMessage = '';
  let toastType: 'success' | 'error' = 'success';
  let pollInterval: ReturnType<typeof setInterval> | null = null;

  async function loadProcesses() {
    try {
      const data: ProcessListResponse = await fetchProcesses();
      processes = data.processes || [];
      total = data.total || 0;
    } catch (err: any) {
      showToast(err?.message || 'Failed to load active processes', 'error');
    } finally {
      loading = false;
    }
  }

  function showToast(msg: string, type: 'success' | 'error' = 'success') {
    toastMessage = msg;
    toastType = type;
    setTimeout(() => {
      if (toastMessage === msg) toastMessage = '';
    }, 4000);
  }

  async function handleTerminate(proc: ProcessOwner) {
    const regId = proc.registration_id || proc.owner_id;
    if (!regId) return;

    if (!confirm(`Are you sure you want to terminate process '${proc.task_name}' (${proc.owner_id})?`)) {
      return;
    }

    terminatingIds.add(regId);
    terminatingIds = terminatingIds;

    try {
      const res = await terminateProcess(regId);
      showToast(res.message || `Terminated process '${proc.task_name}'`, 'success');
      await loadProcesses();
    } catch (err: any) {
      showToast(err?.response?.data?.error || err?.message || 'Failed to terminate process', 'error');
    } finally {
      terminatingIds.delete(regId);
      terminatingIds = terminatingIds;
    }
  }

  onMount(() => {
    loadProcesses();
    pollInterval = setInterval(loadProcesses, 5000);
  });

  onDestroy(() => {
    if (pollInterval) clearInterval(pollInterval);
  });

  function formatDate(isoStr: string): string {
    if (!isoStr) return '-';
    try {
      return new Date(isoStr).toLocaleTimeString();
    } catch {
      return isoStr;
    }
  }
</script>

<div class="bg-gray-900/90 border border-gray-800 rounded-xl p-5 shadow-lg backdrop-blur-sm">
  <div class="flex items-center justify-between mb-4">
    <div class="flex items-center space-x-3">
      <h3 class="text-lg font-semibold text-gray-100">Process Supervisor</h3>
      <span class="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-800 text-gray-300 border border-gray-700">
        {total} Active Registered
      </span>
    </div>
    <button
      on:click={loadProcesses}
      class="px-3 py-1.5 text-xs font-medium text-gray-300 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg transition-colors"
    >
      Refresh
    </button>
  </div>

  {#if toastMessage}
    <div
      class={`p-3 mb-4 rounded-lg text-xs font-medium flex items-center justify-between transition-all ${
        toastType === 'error'
          ? 'bg-rose-500/10 border border-rose-500/30 text-rose-400'
          : 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
      }`}
    >
      <span>{toastMessage}</span>
      <button on:click={() => (toastMessage = '')} class="text-xs opacity-70 hover:opacity-100">&times;</button>
    </div>
  {/if}

  {#if loading && processes.length === 0}
    <div class="py-8 text-center text-xs text-gray-400">Loading active process registrations...</div>
  {:else if processes.length === 0}
    <div class="py-8 text-center text-xs text-gray-500 italic bg-gray-800/30 rounded-lg border border-gray-800">
      No active worker processes or threads registered in supervisor.
    </div>
  {:else}
    <div class="overflow-x-auto">
      <table class="w-full text-left text-xs text-gray-300 border-collapse">
        <thead>
          <tr class="border-b border-gray-800 text-gray-400 font-medium uppercase tracking-wider text-[10px]">
            <th class="py-2.5 px-3">Owner ID</th>
            <th class="py-2.5 px-3">Type</th>
            <th class="py-2.5 px-3">Task Name</th>
            <th class="py-2.5 px-3">PID</th>
            <th class="py-2.5 px-3">Thread ID</th>
            <th class="py-2.5 px-3">Started At</th>
            <th class="py-2.5 px-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-800/60">
          {#each processes as proc (proc.registration_id || `${proc.owner_id}_${proc.pid}_${proc.thread_id}`)}
            {@const regId = proc.registration_id || proc.owner_id}
            <tr class="hover:bg-gray-800/40 transition-colors">
              <td class="py-2.5 px-3 font-mono font-medium text-gray-200">{proc.owner_id}</td>
              <td class="py-2.5 px-3">
                <span class="px-2 py-0.5 rounded text-[10px] uppercase font-semibold bg-gray-800 text-gray-300 border border-gray-700">
                  {proc.owner_type}
                </span>
              </td>
              <td class="py-2.5 px-3 font-medium text-gray-100">{proc.task_name}</td>
              <td class="py-2.5 px-3 font-mono text-gray-400">{proc.pid ?? '-'}</td>
              <td class="py-2.5 px-3 font-mono text-gray-400">{proc.thread_id ?? '-'}</td>
              <td class="py-2.5 px-3 text-gray-400">{formatDate(proc.started_at)}</td>
              <td class="py-2.5 px-3 text-right">
                <button
                  on:click={() => handleTerminate(proc)}
                  disabled={terminatingIds.has(regId)}
                  class="px-2.5 py-1 text-[11px] font-medium text-rose-400 hover:text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 rounded transition-colors disabled:opacity-50"
                >
                  {terminatingIds.has(regId) ? 'Terminating...' : 'Terminate'}
                </button>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
</div>
