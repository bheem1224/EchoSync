<svelte:options customElement={{
  tag: 'echosync-review-queue',
  shadow: 'none'
}} />

<script lang="ts">
  import { onMount } from 'svelte';
  import apiClient from '../../api/client';
  import MetadataReviewModal from './MetadataReviewModal.svelte';

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

  function getProposedArtist(task) {
    return task?.detected_metadata?.artist || 'Unknown Artist';
  }

  function getProposedTitle(task) {
    return task?.detected_metadata?.title || 'Unknown Title';
  }

  function getReadableSyncLabel(task) {
    const rawSyncId = task?.sync_id;
    if (!rawSyncId) return '';
    try {
        if (!rawSyncId || typeof rawSyncId !== 'string') return rawSyncId;
        if (rawSyncId.startsWith('ss:track:meta:')) {
            const b64 = rawSyncId.split('?')[0].replace('ss:track:meta:', '');
            const jsonStr = atob(b64);
            const data = JSON.parse(jsonStr);
            return `${data.artist} - ${data.title}`;
        }
        if (rawSyncId.startsWith('ss:track:acoustid:')) {
            return `AcoustID: ${rawSyncId.replace('ss:track:acoustid:', '').split('?')[0]}`;
        }
    } catch(e) {}
    return rawSyncId;
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

  async function handleModalSaveDraft(e) {
      const { proposedMetadata, item } = e.detail || {};
      if (!item) return;
      const taskId = item.id;

      setRowState(taskId, 'saving');
      try {
          const payload = { ...item.proposed_metadata, ...proposedMetadata };
          await apiClient.put(`/review-queue/${taskId}`, payload);

          tasks = tasks.map((task) =>
            task.id === taskId
              ? { ...task, detected_metadata: { ...payload }, proposed_metadata: { ...payload } }
              : task
          );

          setRowState(taskId, 'saved');
          setTimeout(() => clearRowState(taskId), 1200);
      } catch (err) {
          console.error('Failed to save draft:', err);
          clearRowState(taskId);
      }
  }

  async function handleModalApprove(e) {
      const { proposedMetadata, item } = e.detail || {};
      if (!item) return;
      const taskId = item.id;

      setRowState(taskId, 'approving');
      try {
          const payload = { ...item.proposed_metadata, ...proposedMetadata };
          // Save draft first just in case
          await apiClient.put(`/review-queue/${taskId}`, payload);
          // Then approve
          await apiClient.post(`/review-queue/${taskId}/approve`);

          tasks = tasks.filter(t => t.id !== taskId);
          clearRowState(taskId);
          closeReviewModal();
      } catch (err) {
          console.error('Failed to approve task:', err);
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
    } finally {
      loading = false;
    }
  }

  onMount(loadQueue);
</script>

<div class="flex flex-col h-full min-h-0 bg-background">
  <div class="flex items-center justify-between p-4">
    <div>
      <p class="text-xs uppercase tracking-wide text-secondary font-semibold">Metadata Workflow</p>
      <h2 class="text-2xl font-bold text-primary m-0">Review Queue</h2>
    </div>
    <button
      class="px-4 py-2 rounded-global text-sm font-medium bg-surface text-primary border border-global hover:bg-surface-hover transition-colors active:scale-95"
      on:click={loadQueue}
      disabled={loading}
    >
      {loading ? 'Refreshing...' : 'Refresh'}
    </button>
  </div>

  <div class="m-4 mt-0 flex-1 min-h-0 overflow-y-auto rounded-global bg-surface backdrop-blur-md border border-glass-border">
    {#if loading}
      <div class="p-8 text-center text-secondary">Loading review queue...</div>
    {:else if error}
      <div class="p-8 text-center text-error-text bg-error-bg">{error}</div>
    {:else if tasks.length === 0}
      <div class="p-8 text-center text-secondary italic">No pending metadata review tasks.</div>
    {:else}
      <div class="overflow-x-auto">
        <table class="min-w-full text-left border-collapse">
          <thead class="bg-surface-hover">
            <tr class="text-secondary text-xs uppercase tracking-wider border-b border-global">
              <th class="px-4 py-3 font-semibold">File</th>
              <th class="px-4 py-3 font-semibold">Proposed Artist / Title</th>
              <th class="px-4 py-3 font-semibold">Confidence</th>
              <th class="px-4 py-3 font-semibold text-right">Action</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-global bg-background">
            {#each tasks as task (task.id)}
              <tr class="hover:bg-surface-hover transition-colors">
                <td class="px-4 py-3">
                  <div class="text-sm text-primary font-medium">{getFilename(task.file_path)}</div>
                  <div class="text-xs text-secondary truncate max-w-xs">{task.file_path}</div>
                </td>
                <td class="px-4 py-3">
                  <div class="text-sm text-primary">{getProposedArtist(task)}</div>
                  <div class="text-sm text-secondary">{getProposedTitle(task)}</div>
                  {#if task?.sync_id}
                    <div class="text-xs text-accent truncate max-w-xs mt-1" title={task.sync_id}>
                      {getReadableSyncLabel(task)}
                    </div>
                  {/if}
                </td>
                <td class="px-4 py-3">
                  <span class={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${
                      (task.confidence_score || 0) >= 0.85 ? 'bg-success-bg text-success-text border-success-border' :
                      (task.confidence_score || 0) >= 0.6 ? 'bg-warning-bg text-warning-text border-warning-border' :
                      'bg-error-bg text-error-text border-error-border'
                  }`}>
                    {(task.confidence_score || 0) >= 0.85 ? 'High' : (task.confidence_score || 0) >= 0.6 ? 'Medium' : 'Low'}
                    <span class="opacity-80 ml-1">{Math.round((task.confidence_score || 0) * 100)}%</span>
                  </span>
                </td>
                <td class="px-4 py-3 text-right">
                  <div class="inline-flex items-center gap-2 justify-end w-full">
                    {#if rowActionState[task.id]}
                      <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-surface border border-global text-primary">
                        {getStateLabel(rowActionState[task.id])}
                      </span>
                    {/if}
                    <button
                      class="px-3 py-2 rounded-global text-sm font-medium bg-accent text-primary hover:opacity-90 transition-opacity active:scale-95"
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
  <!-- We use the native web component we built earlier -->
    <MetadataReviewModal
      task={selectedTask}
      on:close={() => closeReviewModal()}
      on:saved={(e) => handleModalSaveDraft({ detail: { proposedMetadata: e.detail?.metadata || e.detail?.proposedMetadata, item: selectedTask } })}
      on:approved={(e) => handleModalApprove({ detail: { proposedMetadata: e.detail?.metadata || e.detail?.proposedMetadata, item: selectedTask } })}
    />
{/if}

<style>
  .bg-success-bg { background-color: var(--es-success-bg); }
  .text-success-text { color: var(--es-success-text); }
  .border-success-border { border-color: var(--es-success-bg); }

  .bg-warning-bg { background-color: var(--es-warning-bg); }
  .text-warning-text { color: var(--es-warning-text); }
  .border-warning-border { border-color: var(--es-warning-border); }

  .bg-error-bg { background-color: var(--es-error-bg); }
  .text-error-text { color: var(--es-error-text); }
  .border-error-border { border-color: var(--es-error-border); }
</style>
