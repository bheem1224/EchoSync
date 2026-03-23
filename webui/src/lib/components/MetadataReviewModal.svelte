<script>
  import { onDestroy } from 'svelte';
  import { createEventDispatcher } from 'svelte';
  import apiClient from '../../api/client';
  import { feedback } from '../../stores/feedback';

  export let task = null;

  const dispatch = createEventDispatcher();

  let savingDraft = false;
  let approving = false;
  let autosavePending = false;
  let autosaveTimer = null;
  let initializedTaskId = null;
  let lastPersistedSignature = '';
  let lastObservedSignature = '';
  let metadataHistory = [];
  let restoringFromUndo = false;
  let showAdvanced = true;
  let musicbrainzLookupLoading = false;
  let acoustidLookupLoading = false;

  let proposedMetadata = {
    title: '',
    artist: '',
    album: '',
    year: '',
    track_number: '',
    disc_number: '',
    musicbrainz_id: '',
    acoustid_id: '',
    isrc: '',
    comments: ''
  };

  $: if (task?.id && task.id !== initializedTaskId) {
    const proposed = task?.detected_metadata || {};
    proposedMetadata = {
      title: proposed.title || '',
      artist: proposed.artist || '',
      album: proposed.album || '',
      year: proposed.year || '',
      track_number: proposed.track_number || '',
      disc_number: proposed.disc_number || '',
      musicbrainz_id: proposed.musicbrainz_id || '',
      acoustid_id: proposed.acoustid_id || '',
      isrc: proposed.isrc || '',
      comments: proposed.comments || ''
    };

    const initialPayload = buildPayloadFrom(proposedMetadata);
    const initialSignature = JSON.stringify(initialPayload);
    metadataHistory = [initialPayload];
    lastObservedSignature = initialSignature;
    lastPersistedSignature = initialSignature;
    initializedTaskId = task.id;
    clearAutosaveTimer();
    autosavePending = false;
  }

  $: proposedSignature = JSON.stringify(buildPayloadFrom(proposedMetadata));

  $: if (task?.id && proposedSignature && proposedSignature !== lastObservedSignature) {
    if (!restoringFromUndo) {
      const snapshot = JSON.parse(proposedSignature);
      const previous = metadataHistory[metadataHistory.length - 1];
      if (!previous || JSON.stringify(previous) !== proposedSignature) {
        metadataHistory = [...metadataHistory, snapshot].slice(-50);
      }
    }

    lastObservedSignature = proposedSignature;
    queueAutosave();
  }

  $: currentMetadata =
    task?.current_metadata ||
    task?.source_metadata ||
    task?.raw_metadata ||
    task?.existing_metadata ||
    {};

  $: streamUrl = task?.id ? `/api/review-queue/${task.id}/stream` : '';

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
    return buildPayloadFrom(proposedMetadata);
  }

  function buildPayloadFrom(source) {
    return {
      title: (source.title || '').trim(),
      artist: (source.artist || '').trim(),
      album: (source.album || '').trim(),
      year: source.year ? Number(source.year) || source.year : '',
      track_number: source.track_number ? Number(source.track_number) || source.track_number : '',
      disc_number: source.disc_number ? Number(source.disc_number) || source.disc_number : '',
      musicbrainz_id: (source.musicbrainz_id || '').trim(),
      acoustid_id: (source.acoustid_id || '').trim(),
      isrc: (source.isrc || '').trim(),
      comments: (source.comments || '').trim()
    };
  }

  function clearAutosaveTimer() {
    if (autosaveTimer) {
      clearTimeout(autosaveTimer);
      autosaveTimer = null;
    }
  }

  function queueAutosave() {
    if (!task?.id || savingDraft || approving) return;
    clearAutosaveTimer();
    autosavePending = true;
    autosaveTimer = setTimeout(() => {
      saveDraft({ silent: true });
    }, 1000);
  }

  function undoLastChange() {
    if (metadataHistory.length < 2 || savingDraft || approving) {
      return;
    }

    const nextHistory = metadataHistory.slice(0, -1);
    const previousState = nextHistory[nextHistory.length - 1];
    metadataHistory = nextHistory;

    restoringFromUndo = true;
    proposedMetadata = {
      ...proposedMetadata,
      ...previousState
    };
    restoringFromUndo = false;

    lastObservedSignature = JSON.stringify(buildPayloadFrom(proposedMetadata));
    queueAutosave();
  }

  async function saveDraft(options = {}) {
    const { silent = false } = options;
    if (!task?.id || savingDraft || approving) return;
    const payload = buildPayload();
    const payloadSignature = JSON.stringify(payload);

    if (payloadSignature === lastPersistedSignature && silent) {
      autosavePending = false;
      return;
    }

    savingDraft = true;
    dispatch('draftstart', { taskId: task.id });
    try {
      await apiClient.put(`/review-queue/${task.id}`, { metadata: payload });
      lastPersistedSignature = payloadSignature;
      if (!silent) {
        feedback.addToast('Draft metadata saved', 'success');
      }
      dispatch('saved', { taskId: task.id, metadata: payload });
    } catch (error) {
      console.error('Failed to save draft:', error);
      feedback.addToast('Failed to save draft metadata', 'error');
    } finally {
      savingDraft = false;
      autosavePending = false;
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

  onDestroy(() => {
    clearAutosaveTimer();
  });
  
  function applyMetadataUpdate(newMetadata) {
    if (!newMetadata || typeof newMetadata !== 'object') {
      return;
    }

    const normalizedLookupMetadata = {
      ...newMetadata,
      title: newMetadata.title ?? proposedMetadata.title,
      artist: newMetadata.artist ?? proposedMetadata.artist,
      album: newMetadata.album ?? proposedMetadata.album,
      year: newMetadata.year ?? newMetadata.date ?? proposedMetadata.year,
      track_number: newMetadata.track_number ?? proposedMetadata.track_number,
      disc_number: newMetadata.disc_number ?? proposedMetadata.disc_number,
      musicbrainz_id:
        newMetadata.musicbrainz_id ??
        newMetadata.recording_id ??
        newMetadata.mbid ??
        proposedMetadata.musicbrainz_id,
      acoustid_id:
        newMetadata.acoustid_id ??
        newMetadata.acoustid ??
        proposedMetadata.acoustid_id,
      isrc: newMetadata.isrc ?? proposedMetadata.isrc,
      comments: newMetadata.comments ?? proposedMetadata.comments
    };

    proposedMetadata = {
      ...proposedMetadata,
      ...normalizedLookupMetadata,
      musicbrainz_id: normalizedLookupMetadata.musicbrainz_id || '',
      acoustid_id: normalizedLookupMetadata.acoustid_id || '',
      isrc: normalizedLookupMetadata.isrc || ''
    };

    queueAutosave();
  }

  function getLookupMetadata(response) {
    const payload = response?.data || {};
    const taskPayload = payload?.task || {};
    return taskPayload?.detected_metadata || payload?.detected_metadata || payload?.metadata || null;
  }

  async function runMusicBrainzLookup() {
    if (!task?.id || musicbrainzLookupLoading || acoustidLookupLoading || approving) {
      return;
    }

    musicbrainzLookupLoading = true;
    try {
      const response = await apiClient.post(`/review-queue/${task.id}/lookup/musicbrainz`, {
        artist: (proposedMetadata.artist || '').trim(),
        title: (proposedMetadata.title || '').trim()
      });
      const updatedMetadata = getLookupMetadata(response);
      if (updatedMetadata) {
        applyMetadataUpdate(updatedMetadata);
        feedback.addToast('MusicBrainz metadata loaded', 'success');
      } else {
        feedback.addToast('MusicBrainz lookup returned no metadata', 'error');
      }
    } catch (error) {
      console.error('MusicBrainz lookup failed:', error);
      feedback.addToast('MusicBrainz lookup failed', 'error');
    } finally {
      musicbrainzLookupLoading = false;
    }
  }

  async function runAcoustIDLookup() {
    if (!task?.id || acoustidLookupLoading || musicbrainzLookupLoading || approving) {
      return;
    }

    acoustidLookupLoading = true;
    try {
      const response = await apiClient.post(`/review-queue/${task.id}/lookup/acoustid`);
      const updatedMetadata = getLookupMetadata(response);
      if (updatedMetadata) {
        applyMetadataUpdate(updatedMetadata);
        feedback.addToast('AcoustID metadata loaded', 'success');
      } else {
        feedback.addToast('AcoustID scan returned no metadata', 'error');
      }
    } catch (error) {
      console.error('AcoustID lookup failed:', error);
      feedback.addToast('AcoustID lookup failed', 'error');
    } finally {
      acoustidLookupLoading = false;
    }
  }

  onDestroy(() => {
    clearAutosaveTimer();
  });
</script>

<div class="fixed inset-0 z-[100] w-screen h-screen flex items-center justify-center bg-black/75 overflow-hidden">
  <div class="relative w-full h-full flex items-center justify-center p-4 md:p-6">
    <div
      class="w-full max-w-5xl rounded-2xl border border-slate-700 bg-slate-900 text-slate-100 shadow-2xl max-h-[90vh]"
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
              <div class="flex justify-between gap-4">
                <span class="text-slate-400">MusicBrainz ID</span>
                <span class="text-slate-200 text-right break-all">{displayValue(currentMetadata.musicbrainz_id)}</span>
              </div>
              <div class="flex justify-between gap-4">
                <span class="text-slate-400">AcoustID</span>
                <span class="text-slate-200 text-right break-all">{displayValue(currentMetadata.acoustid_id)}</span>
              </div>
              <div class="flex justify-between gap-4">
                <span class="text-slate-400">Comments</span>
                <span class="text-slate-200 text-right break-all">{displayValue(currentMetadata.comments)}</span>
              </div>
            </div>
          </section>

          <section class="rounded-xl border border-cyan-700/40 bg-cyan-950/10 p-4">
            <h4 class="text-sm font-semibold text-cyan-200 mb-3">Proposed Metadata (Editable)</h4>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label class="sm:col-span-2">
                <span class="block text-xs text-slate-400 mb-1">Title</span>
                <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={proposedMetadata.title} on:keydown={handleInputKeydown} />
              </label>

              <label class="sm:col-span-2">
                <span class="block text-xs text-slate-400 mb-1">Artist</span>
                <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={proposedMetadata.artist} on:keydown={handleInputKeydown} />
              </label>

              <label class="sm:col-span-2">
                <span class="block text-xs text-slate-400 mb-1">Album</span>
                <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={proposedMetadata.album} on:keydown={handleInputKeydown} />
              </label>

              <label>
                <span class="block text-xs text-slate-400 mb-1">Year</span>
                <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={proposedMetadata.year} on:keydown={handleInputKeydown} />
              </label>

              <label>
                <span class="block text-xs text-slate-400 mb-1">Track Number</span>
                <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={proposedMetadata.track_number} on:keydown={handleInputKeydown} />
              </label>

              <label>
                <span class="block text-xs text-slate-400 mb-1">Disc Number</span>
                <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={proposedMetadata.disc_number} on:keydown={handleInputKeydown} />
              </label>

              <details class="sm:col-span-2 rounded-lg border border-slate-700 bg-slate-900/50 p-3" bind:open={showAdvanced}>
                <summary class="cursor-pointer text-sm font-medium text-slate-200">Advanced Tagging</summary>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
                  <label>
                    <span class="block text-xs text-slate-400 mb-1">MusicBrainz ID (MBID)</span>
                    <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={proposedMetadata.musicbrainz_id} on:keydown={handleInputKeydown} />
                  </label>

                  <label>
                    <span class="block text-xs text-slate-400 mb-1">AcoustID</span>
                    <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={proposedMetadata.acoustid_id} on:keydown={handleInputKeydown} />
                  </label>

                  <label class="sm:col-span-2">
                    <span class="block text-xs text-slate-400 mb-1">ISRC</span>
                    <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={proposedMetadata.isrc} on:keydown={handleInputKeydown} />
                  </label>

                  <label class="sm:col-span-2">
                    <span class="block text-xs text-slate-400 mb-1">Comments</span>
                    <textarea class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100 min-h-[90px]" bind:value={proposedMetadata.comments}></textarea>
                  </label>
                </div>
              </details>
            </div>
            <p class="mt-3 text-xs text-slate-400">
              {#if autosavePending}
                Autosave pending...
              {:else if savingDraft}
                Saving draft...
              {:else}
                Changes are autosaved 1s after typing stops.
              {/if}
            </p>
          </section>
        </div>
      </div>

      <div class="px-5 py-3 border-t border-slate-800 bg-slate-950/60">
        <p class="text-xs uppercase tracking-wide text-slate-400 mb-2">Track Preview</p>
        {#if streamUrl}
          <audio controls src={streamUrl} class="w-full h-10">
            Your browser does not support audio playback.
          </audio>
        {/if}
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
          on:click={() => saveDraft({ silent: false })}
          disabled={savingDraft || approving}
        >
          {savingDraft ? 'Saving...' : 'Save Draft'}
        </button>

        <button
          class="px-4 py-2 rounded-lg bg-slate-700 text-slate-100 hover:bg-slate-600 disabled:opacity-60"
          on:click={undoLastChange}
          disabled={savingDraft || approving || metadataHistory.length < 2}
          title="Undo last metadata edit"
        >
          Undo
        </button>

        <button
          class="px-4 py-2 rounded-lg bg-indigo-700 text-white hover:bg-indigo-600 disabled:opacity-60"
          on:click={runMusicBrainzLookup}
          disabled={musicbrainzLookupLoading || acoustidLookupLoading || approving || savingDraft}
        >
          {musicbrainzLookupLoading ? 'Looking up MusicBrainz...' : '🔍 MusicBrainz Lookup'}
        </button>

        <button
          class="px-4 py-2 rounded-lg bg-emerald-700 text-white hover:bg-emerald-600 disabled:opacity-60"
          on:click={runAcoustIDLookup}
          disabled={acoustidLookupLoading || musicbrainzLookupLoading || approving || savingDraft}
        >
          {acoustidLookupLoading ? 'Scanning AcoustID...' : '🧬 AcoustID Scan'}
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
