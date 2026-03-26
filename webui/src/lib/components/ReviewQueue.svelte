<script>
  import { onMount } from 'svelte';
  import apiClient from '../../api/client';
  import { feedback } from '../../stores/feedback';
  import MetadataReviewModal from './MetadataReviewModal.svelte';
  import { decodeSyncId } from '../utils';

  let loading = true;
  let error = '';
  let tasks = [];
  let rowActionState = {};

  let showReviewModal = false;
  let selectedTask = null;

  function getFilename(filePath) {
    if (!filePath) return 'Unknown file';
    const normalized = String(filePath).replace(/\\/g, '/');
    const parts = normalized.split('/');
    return parts[parts.length - 1] || normalized;
  }

  function confidenceBadgeClass(score) {
    if (score >= 0.85) {
      return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
    }
    if (score >= 0.6) {
      return 'bg-amber-500/20 text-amber-300 border border-amber-500/40';
    }
    return 'bg-rose-500/20 text-rose-300 border border-rose-500/40';
  }

  function confidenceLabel(score) {
    if (score >= 0.85) return 'High';
    if (score >= 0.6) return 'Medium';
    return 'Low';
  }

  function getProposedArtist(task) {
    return task?.detected_metadata?.artist || 'Unknown Artist';
  }

  function getProposedTitle(task) {
    return task?.detected_metadata?.title || 'Unknown Title';
  }

  function getReadableSyncLabel(task) {
    const rawSyncId = task?.sync_id;
    if (!rawSyncId) return '';
    return decodeSyncId(rawSyncId);
  }

  function openReviewModal(task) {
    selectedTask = task;
    showReviewModal = true;
  }

  function setRowState(taskId, state) {
    if (!taskId) return;
    rowActionState = {
      ...rowActionState,
      [taskId]: state
    };
  }

  function clearRowState(taskId) {
    if (!taskId) return;
    const next = { ...rowActionState };
    delete next[taskId];
    rowActionState = next;
  }

  function getStateBadgeClass(state) {
    if (state === 'approving') {
      return 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40';
    }
    if (state === 'saving') {
      return 'bg-amber-500/20 text-amber-300 border border-amber-500/40';
    }
    if (state === 'saved') {
      return 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40';
    }
    return 'bg-slate-700/30 text-slate-300 border border-slate-600/40';
  }

  function getStateLabel(state) {
    if (state === 'approving') return 'Approving...';
    if (state === 'saving') return 'Saving...';
    if (state === 'saved') return 'Saved';
    return '';
  }

  function closeReviewModal() {
    showReviewModal = false;
    selectedTask = null;
  }

  function handleDraftSaved(event) {
    const { taskId, metadata } = event.detail || {};
    if (!taskId || !metadata) return;
    tasks = tasks.map((task) =>
      task.id === taskId
        ? { ...task, detected_metadata: { ...metadata } }
        : task
    );
    setRowState(taskId, 'saved');
    setTimeout(() => {
      clearRowState(taskId);
    }, 1200);
  }

  function handleApproved(event) {
    const { taskId } = event.detail || {};
    if (!taskId) return;
    tasks = tasks.filter((task) => task.id !== taskId);
    clearRowState(taskId);
    closeReviewModal();
  }

  function handleDraftStart(event) {
    const { taskId } = event.detail || {};
    setRowState(taskId, 'saving');
  }

  function handleDraftEnd(event) {
    const { taskId } = event.detail || {};
    if (rowActionState[taskId] === 'saving') {
      clearRowState(taskId);
    }
  }

  function handleApproveStart(event) {
    const { taskId } = event.detail || {};
    setRowState(taskId, 'approving');
  }

  function handleApproveEnd(event) {
    const { taskId } = event.detail || {};
    if (rowActionState[taskId] === 'approving') {
      clearRowState(taskId);
    }
  }

  async function loadQueue() {
    loading = true;
    error = '';
    try {
      const response = await apiClient.get('/review-queue');
      tasks = Array.isArray(response.data?.tasks) ? response.data.tasks : [];
    } catch (err) {
      console.error('Failed to load review queue:', err);
      error = err?.response?.data?.error || err?.message || 'Failed to load review queue';
      feedback.addToast('Failed to load review queue', 'error');
    } finally {
      loading = false;
    }
  }

  onMount(loadQueue);
</script>

<div class="flex flex-col h-full min-h-0">
  <div class="flex items-center justify-between">
    <div>
      <p class="text-xs uppercase tracking-wide text-cyan-300/80 font-semibold">Metadata Workflow</p>
      <h2 class="text-2xl font-bold text-white">Review Queue</h2>
    </div>
    <button
      class="px-3 py-2 rounded-lg text-sm font-medium bg-slate-800 text-slate-200 border border-slate-700 hover:bg-slate-700"
      on:click={loadQueue}
      disabled={loading}
    >
      {loading ? 'Refreshing...' : 'Refresh'}
    </button>
  </div>

  <div class="mt-4 flex-1 min-h-0 overflow-y-auto rounded-xl border border-slate-700/60 bg-slate-900/70">
    {#if loading}
      <div class="p-8 text-center text-slate-300">Loading review queue...</div>
    {:else if error}
      <div class="p-8 text-center text-rose-300">{error}</div>
    {:else if tasks.length === 0}
      <div class="p-8 text-center text-slate-300">No pending metadata review tasks.</div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-full text-left">
          <thead class="bg-slate-800/80">
            <tr class="text-slate-300 text-xs uppercase tracking-wider">
              <th class="px-4 py-3 font-semibold">File</th>
              <th class="px-4 py-3 font-semibold">Proposed Artist / Title</th>
              <th class="px-4 py-3 font-semibold">Confidence</th>
              <th class="px-4 py-3 font-semibold text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800">
            {#each tasks as task (task.id)}
              <tr class="hover:bg-slate-800/40 transition-colors">
                <td class="px-4 py-3">
                  <div class="text-sm text-slate-100 font-medium">{getFilename(task.file_path)}</div>
                  <div class="text-xs text-slate-400 truncate max-w-[320px]">{task.file_path}</div>
                </td>
                <td class="px-4 py-3">
                  <div class="text-sm text-slate-100">{getProposedArtist(task)}</div>
                  <div class="text-sm text-slate-300">{getProposedTitle(task)}</div>
                  {#if task?.sync_id}
                    <div class="text-xs text-cyan-200/90 truncate max-w-[320px]" title={task.sync_id}>
                      {getReadableSyncLabel(task)}
                    </div>
                  {/if}
                </td>
                <td class="px-4 py-3">
                  <span class={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-semibold ${confidenceBadgeClass(task.confidence_score || 0)}`}>
                    {confidenceLabel(task.confidence_score || 0)}
                    <span class="opacity-80">{Math.round((task.confidence_score || 0) * 100)}%</span>
                  </span>
                </td>
                <td class="px-4 py-3 text-right">
                  <div class="inline-flex items-center gap-2">
                    {#if rowActionState[task.id]}
                      <span class={`inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold ${getStateBadgeClass(rowActionState[task.id])}`}>
                        {getStateLabel(rowActionState[task.id])}
                      </span>
                    {/if}
                    <button
                      class="px-3 py-2 rounded-lg text-sm font-medium bg-cyan-600 text-white hover:bg-cyan-500"
                      on:click={() => openReviewModal(task)}
                    >
                      Review & Edit
                    </button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>

{#if showReviewModal && selectedTask}
  <MetadataReviewModal
    task={selectedTask}
    on:close={closeReviewModal}
    on:saved={handleDraftSaved}
    on:approved={handleApproved}
    on:draftstart={handleDraftStart}
    on:draftend={handleDraftEnd}
    on:approvestart={handleApproveStart}
    on:approveend={handleApproveEnd}
  />
{/if}
