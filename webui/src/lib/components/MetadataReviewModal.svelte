<script>
  import { createEventDispatcher } from 'svelte';
  import apiClient from '../../api/client';
  import { feedback } from '../../stores/feedback';

  export let task = null;

  const dispatch = createEventDispatcher();

  let savingDraft = false;
  let approving = false;

  let editable = {
    title: '',
    artist: '',
    album: '',
    year: '',
    track_number: '',
    disc_number: '',
    isrc: ''
  };

  $: if (task) {
    const proposed = task?.detected_metadata || {};
    editable = {
      title: proposed.title || '',
      artist: proposed.artist || '',
      album: proposed.album || '',
      year: proposed.year || '',
      track_number: proposed.track_number || '',
      disc_number: proposed.disc_number || '',
      isrc: proposed.isrc || ''
    };
  }

  $: currentMetadata =
    task?.current_metadata ||
    task?.source_metadata ||
    task?.raw_metadata ||
    task?.existing_metadata ||
    {};

  function getFilename(filePath) {
    if (!filePath) return 'Unknown file';
    const normalized = String(filePath).replace(/\\/g, '/');
    const parts = normalized.split('/');
    return parts[parts.length - 1] || normalized;
  }

  function closeModal() {
    if (savingDraft || approving) {
      return;
    }
    dispatch('close');
  }

  function handleGlobalKeydown(event) {
    if (event.key === 'Escape') {
      event.preventDefault();
      closeModal();
    }
  }

  function handleInputKeydown(event) {
    if (event.key !== 'Enter') {
      return;
    }

    const target = event.target;
    const tagName = target?.tagName ? String(target.tagName).toLowerCase() : '';
    if (tagName !== 'input') {
      return;
    }

    event.preventDefault();
    saveDraft();
  }

  function buildPayload() {
    return {
      title: (editable.title || '').trim(),
      artist: (editable.artist || '').trim(),
      album: (editable.album || '').trim(),
      year: editable.year ? Number(editable.year) || editable.year : '',
      track_number: editable.track_number ? Number(editable.track_number) || editable.track_number : '',
      disc_number: editable.disc_number ? Number(editable.disc_number) || editable.disc_number : '',
      isrc: (editable.isrc || '').trim()
    };
  }

  async function saveDraft() {
    if (!task?.id || savingDraft || approving) return;
    savingDraft = true;
    dispatch('draftstart', { taskId: task.id });
    try {
      const payload = buildPayload();
      await apiClient.put(`/review-queue/${task.id}`, { metadata: payload });
      feedback.addToast('Draft metadata saved', 'success');
      dispatch('saved', { taskId: task.id, metadata: payload });
    } catch (error) {
      console.error('Failed to save draft:', error);
      feedback.addToast('Failed to save draft metadata', 'error');
    } finally {
      savingDraft = false;
      dispatch('draftend', { taskId: task.id });
    }
  }

  async function approveAndImport() {
    if (!task?.id || approving || savingDraft) return;
    approving = true;
    dispatch('approvestart', { taskId: task.id });
    try {
      const payload = buildPayload();
      await apiClient.post(`/review-queue/${task.id}/approve`, { metadata: payload });
      feedback.addToast('Metadata approved and file imported', 'success');
      dispatch('approved', { taskId: task.id, metadata: payload });
      dispatch('close');
    } catch (error) {
      console.error('Failed to approve and import:', error);
      feedback.addToast('Failed to approve and import file', 'error');
    } finally {
      approving = false;
      dispatch('approveend', { taskId: task.id });
    }
  }

  function displayValue(value) {
    if (value === undefined || value === null || value === '') {
      return 'Not available';
    }
    return String(value);
  }
</script>

<svelte:window on:keydown={handleGlobalKeydown} />

<div class="fixed inset-0 z-50 bg-black/50 overflow-y-auto">
  <button
    class="absolute inset-0 w-full h-full cursor-default"
    aria-label="Close metadata review modal"
    on:click={closeModal}
  ></button>
  <div class="relative min-h-full flex items-start md:items-center justify-center p-4 md:p-6">
    <div
      class="w-full max-w-5xl rounded-2xl border border-slate-700 bg-slate-900 text-slate-100 shadow-2xl"
    >
      <div class="px-5 py-4 border-b border-slate-800 flex items-start justify-between gap-4">
        <div>
          <p class="text-xs uppercase tracking-wide text-cyan-300/80 font-semibold">Picard-style Review</p>
          <h3 class="text-xl font-bold">Edit Metadata</h3>
          <p class="text-xs text-slate-400 mt-1">Task #{task?.id} - {getFilename(task?.file_path)}</p>
        </div>
        <button
          class="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm"
          on:click={closeModal}
          disabled={savingDraft || approving}
        >
          Close
        </button>
      </div>

      <div class="p-5 md:p-6 max-h-[70vh] overflow-y-auto">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section class="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
            <h4 class="text-sm font-semibold text-slate-100 mb-3">Current File Metadata</h4>
            <div class="space-y-2 text-sm">
              <div class="flex justify-between gap-4">
                <span class="text-slate-400">Title</span>
                <span class="text-slate-200 text-right">{displayValue(currentMetadata.title)}</span>
              </div>
              <div class="flex justify-between gap-4">
                <span class="text-slate-400">Artist</span>
                <span class="text-slate-200 text-right">{displayValue(currentMetadata.artist)}</span>
              </div>
              <div class="flex justify-between gap-4">
                <span class="text-slate-400">Album</span>
                <span class="text-slate-200 text-right">{displayValue(currentMetadata.album)}</span>
              </div>
              <div class="flex justify-between gap-4">
                <span class="text-slate-400">Year</span>
                <span class="text-slate-200 text-right">{displayValue(currentMetadata.year || currentMetadata.date)}</span>
              </div>
              <div class="flex justify-between gap-4">
                <span class="text-slate-400">Track #</span>
                <span class="text-slate-200 text-right">{displayValue(currentMetadata.track_number)}</span>
              </div>
              <div class="flex justify-between gap-4">
                <span class="text-slate-400">Disc #</span>
                <span class="text-slate-200 text-right">{displayValue(currentMetadata.disc_number)}</span>
              </div>
              <div class="flex justify-between gap-4">
                <span class="text-slate-400">ISRC</span>
                <span class="text-slate-200 text-right break-all">{displayValue(currentMetadata.isrc)}</span>
              </div>
            </div>
          </section>

          <section class="rounded-xl border border-cyan-700/40 bg-cyan-950/10 p-4">
            <h4 class="text-sm font-semibold text-cyan-200 mb-3">Proposed Metadata (Editable)</h4>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label class="sm:col-span-2">
                <span class="block text-xs text-slate-400 mb-1">Title</span>
                <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={editable.title} on:keydown={handleInputKeydown} />
              </label>

              <label class="sm:col-span-2">
                <span class="block text-xs text-slate-400 mb-1">Artist</span>
                <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={editable.artist} on:keydown={handleInputKeydown} />
              </label>

              <label class="sm:col-span-2">
                <span class="block text-xs text-slate-400 mb-1">Album</span>
                <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={editable.album} on:keydown={handleInputKeydown} />
              </label>

              <label>
                <span class="block text-xs text-slate-400 mb-1">Year</span>
                <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={editable.year} on:keydown={handleInputKeydown} />
              </label>

              <label>
                <span class="block text-xs text-slate-400 mb-1">Track Number</span>
                <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={editable.track_number} on:keydown={handleInputKeydown} />
              </label>

              <label>
                <span class="block text-xs text-slate-400 mb-1">Disc Number</span>
                <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={editable.disc_number} on:keydown={handleInputKeydown} />
              </label>

              <label>
                <span class="block text-xs text-slate-400 mb-1">ISRC</span>
                <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={editable.isrc} on:keydown={handleInputKeydown} />
              </label>
            </div>
          </section>
        </div>
      </div>

      <div class="px-5 py-4 border-t border-slate-800 flex flex-col-reverse sm:flex-row justify-end gap-2 sm:gap-3 bg-slate-900/80">
        <button
          class="px-4 py-2 rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700 disabled:opacity-60"
          on:click={closeModal}
          disabled={savingDraft || approving}
        >
          Cancel
        </button>

        <button
          class="px-4 py-2 rounded-lg bg-amber-600 text-white hover:bg-amber-500 disabled:opacity-60"
          on:click={saveDraft}
          disabled={savingDraft || approving}
        >
          {savingDraft ? 'Saving...' : 'Save Draft'}
        </button>

        <button
          class="px-4 py-2 rounded-lg bg-cyan-600 text-white hover:bg-cyan-500 disabled:opacity-60 inline-flex items-center justify-center gap-2"
          on:click={approveAndImport}
          disabled={approving || savingDraft}
        >
          {#if approving}
            <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            Approving...
          {:else}
            Approve & Import
          {/if}
        </button>
      </div>
    </div>
  </div>
</div>
