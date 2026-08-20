<script>
  import { onDestroy } from 'svelte';
  import { createEventDispatcher } from 'svelte';
  import apiClient from '../../api/client';
  import { feedback } from '../../stores/feedback';

  export let task = null;

  const dispatch = createEventDispatcher();

  let savingDraft = false;
  let approving = false;
  let rejecting = false;
  let autosavePending = false;
  let autosaveTimer = null;
  let initializedTaskId = null;
  let lastPersistedSignature = '';
  let lastObservedSignature = '';
  let metadataHistory = [];
  let restoringFromUndo = false;
  let showAdvanced = true;
  let isScanningAcoustID = false;
  let isLookingUpMB = false;
  let isLookingUpISRC = false;
  let lookupStatus = null; // { type: 'success'|'warning'|'error'|'info', message: string, timestamp: number }

  let showIsrcPrompt = false;
  let isrcInputValue = '';

  function openIsrcPrompt() {
    isrcInputValue = '';
    showIsrcPrompt = true;
  }

  function closeIsrcPrompt() {
    showIsrcPrompt = false;
  }

  let proposedMetadata = {
    title: '',
    artist: '',
    album: '',
    year: '',
    track_number: '',
    disc_number: '',
    mbid: '',
    acoustid: '',
    acoustid_fingerprint: '',
    acoustid_fingerprint_duration: '',
    isrc: '',
    comments: ''
  };

  function normalizeUnknown(val) {
    if (!val || typeof val !== 'string') return '';
    const lower = val.trim().toLowerCase();
    if (lower === 'unknown artist' || lower === 'unknown title' || lower === 'unknown album') {
      return '';
    }
    return val;
  }

  $: if (task?.id && task.id !== initializedTaskId) {
    const proposed = task?.detected_metadata || {};
    
    proposedMetadata = {
      title: normalizeUnknown(proposed.title) || normalizeUnknown(proposed.raw_title) || '',
      artist: normalizeUnknown(proposed.artist) || normalizeUnknown(proposed.artist_name) || '',
      album: normalizeUnknown(proposed.album) || normalizeUnknown(proposed.album_title) || '',
      year: proposed.year || '',
      track_number: proposed.track_number || '',
      disc_number: proposed.disc_number || '',
      mbid: proposed.mbid || proposed.musicbrainz_id || '',
      acoustid: proposed.acoustid || proposed.acoustid_id || '',
      acoustid_fingerprint: proposed.acoustid_fingerprint || '',
      acoustid_fingerprint_duration: proposed.acoustid_fingerprint_duration || '',
      isrc: proposed.isrc || '',
      comments: proposed.comments || ''
    };

    const initialPayload = buildPayloadFrom(proposedMetadata);
    const initialSignature = JSON.stringify(initialPayload);
    metadataHistory = [initialPayload];
    lastObservedSignature = initialSignature;
    lastPersistedSignature = initialSignature;
    initializedTaskId = task.id;
    lookupStatus = null;
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

  $: noTagsWarning = task?.detected_metadata && 
    !normalizeUnknown(task.detected_metadata.title) && 
    !normalizeUnknown(task.detected_metadata.artist) && 
    !normalizeUnknown(task.detected_metadata.raw_title) && 
    !normalizeUnknown(task.detected_metadata.artist_name);

  $: streamUrl = task?.id ? `/api/v1/core/metadata_review/${task.id}/stream` : '';
  $: coverUrl = task?.current_metadata?._has_embedded_cover ? `/api/v1/core/metadata_review/${task.id}/cover` : '';

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
      mbid: (source.mbid || '').trim(),
      acoustid: (source.acoustid || '').trim(),
      acoustid_fingerprint: (source.acoustid_fingerprint || '').trim(),
      acoustid_fingerprint_duration: source.acoustid_fingerprint_duration
        ? Number(source.acoustid_fingerprint_duration) || source.acoustid_fingerprint_duration
        : '',
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
      await apiClient.put(`/core/metadata_review/${task.id}`, { metadata: payload });
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
    if (!task?.id || approving) return;
    clearAutosaveTimer();
    approving = true;
    dispatch('approvestart', { taskId: task.id });
    try {
      const payload = buildPayload();
      await apiClient.post(`/core/metadata_review/${task.id}/approve`, { metadata: payload }, { timeout: 60000 });
      feedback.addToast('Metadata approved and file imported', 'success');
      dispatch('approved', { taskId: task.id, metadata: payload });
      dispatch('close');
    } catch (error) {
      console.error('Failed to approve and import:', error);
      feedback.addToast(error?.response?.data?.detail || 'Failed to approve and import file', 'error');
    } finally {
      approving = false;
      dispatch('approveend', { taskId: task.id });
    }
  }

  async function rejectAndDelete() {
    if (!task?.id || rejecting || approving || savingDraft) return;
    const filename = getFilename(task?.file_path);
    const confirmDelete = window.confirm(
      `Are you sure you want to reject this track and permanently delete the physical file from disk?\n\nFile: ${filename}`
    );
    if (!confirmDelete) return;

    clearAutosaveTimer();
    rejecting = true;
    try {
      await apiClient.post(`/core/metadata_review/${task.id}/reject`);
      feedback.addToast('Track rejected and file deleted from disk', 'success');
      dispatch('rejected', { taskId: task.id, item: task });
      dispatch('close');
    } catch (error) {
      console.error('Failed to reject and delete file:', error);
      feedback.addToast(error?.response?.data?.detail || 'Failed to reject and delete file', 'error');
    } finally {
      rejecting = false;
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
      return { changed: false, fieldsChanged: [], nextState: proposedMetadata };
    }

    clearAutosaveTimer();

    const normalizedLookupMetadata = {
      ...newMetadata,
      title: newMetadata.title ?? proposedMetadata.title,
      artist: newMetadata.artist ?? proposedMetadata.artist,
      album: newMetadata.album ?? proposedMetadata.album,
      year: newMetadata.year ?? newMetadata.date ?? proposedMetadata.year,
      track_number: newMetadata.track_number ?? proposedMetadata.track_number,
      disc_number: newMetadata.disc_number ?? proposedMetadata.disc_number,
      mbid:
        newMetadata.mbid ??
        newMetadata.musicbrainz_id ??
        newMetadata.recording_id ??
        proposedMetadata.mbid,
      acoustid:
        newMetadata.acoustid ??
        newMetadata.acoustid_id ??
        proposedMetadata.acoustid,
      acoustid_fingerprint:
        newMetadata.acoustid_fingerprint ??
        proposedMetadata.acoustid_fingerprint,
      acoustid_fingerprint_duration:
        newMetadata.acoustid_fingerprint_duration ??
        proposedMetadata.acoustid_fingerprint_duration,
      isrc: newMetadata.isrc ?? proposedMetadata.isrc,
      comments: newMetadata.comments ?? proposedMetadata.comments
    };

    const nextState = {
      ...proposedMetadata,
      ...normalizedLookupMetadata,
      mbid: normalizedLookupMetadata.mbid || '',
      acoustid: normalizedLookupMetadata.acoustid || '',
      acoustid_fingerprint: normalizedLookupMetadata.acoustid_fingerprint || '',
      acoustid_fingerprint_duration: normalizedLookupMetadata.acoustid_fingerprint_duration || '',
      isrc: normalizedLookupMetadata.isrc || ''
    };

    const fieldsChanged = [];
    for (const key of ['title', 'artist', 'album', 'year', 'track_number', 'disc_number', 'mbid', 'acoustid', 'isrc']) {
      if (String(nextState[key] || '').trim() !== String(proposedMetadata[key] || '').trim()) {
        fieldsChanged.push(key);
      }
    }

    proposedMetadata = nextState;
    queueAutosave();
    return { changed: fieldsChanged.length > 0, fieldsChanged, nextState };
  }

  function getLookupMetadata(response) {
    return (
      response?.data?.metadata ||
      response?.data?.detected_metadata ||
      response?.data?.task?.detected_metadata ||
      null
    );
  }

  async function runMusicBrainzLookup() {
    if (!task?.id || isScanningAcoustID || isLookingUpMB || isLookingUpISRC || savingDraft || approving) {
      return;
    }

    clearAutosaveTimer();
    isLookingUpMB = true;
    try {
      const response = await apiClient.post(
        `/core/metadata_review/${task.id}/lookup/musicbrainz`,
        {
          artist: (proposedMetadata.artist || '').trim(),
          title: (proposedMetadata.title || '').trim()
        },
        { timeout: 60000 }
      );

      if (response?.data?.match_found === false) {
        const warnMsg = response?.data?.message || 'MusicBrainz: No matching record found in database.';
        lookupStatus = { type: 'warning', message: warnMsg, timestamp: Date.now() };
        feedback.addToast({
          type: 'warning',
          message: warnMsg
        });
        return;
      }

      const updatedMetadata = getLookupMetadata(response);
      if (updatedMetadata && response?.data?.match_found) {
        const { changed, fieldsChanged } = applyMetadataUpdate(updatedMetadata);
        if (changed && fieldsChanged.length > 0) {
          const changedKeys = fieldsChanged.map(f => f.replace('_', ' '));
          const successMsg = `Matched! Updated: ${changedKeys.join(', ')}`;
          lookupStatus = { type: 'success', message: successMsg, timestamp: Date.now() };
          feedback.addToast({
            type: 'success',
            message: `Match found! Updated: ${changedKeys.join(', ')}`
          });
        } else {
          const infoMsg = 'Match confirmed: Current metadata is already up to date.';
          lookupStatus = { type: 'info', message: infoMsg, timestamp: Date.now() };
          feedback.addToast({
            type: 'info',
            message: infoMsg
          });
        }
      } else if (!updatedMetadata) {
        const noRecordMsg = 'MusicBrainz: No matching record found in database.';
        lookupStatus = { type: 'warning', message: noRecordMsg, timestamp: Date.now() };
        feedback.addToast({
          type: 'warning',
          message: noRecordMsg
        });
      }
    } catch (error) {
      console.error('MusicBrainz lookup failed:', error);
      let errMsg = 'MusicBrainz lookup failed';
      if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
        errMsg = 'MusicBrainz lookup timed out after 60s. The service may be busy.';
      } else {
        const status = error?.response?.status;
        if (status === 404) {
          errMsg = 'No matching records found';
        } else if (status === 500 || status === 503) {
          errMsg = 'Provider lookup failed or is temporarily unavailable.';
        } else if (error?.response?.data?.detail) {
          errMsg = error.response.data.detail;
        }
      }
      lookupStatus = { type: 'error', message: errMsg, timestamp: Date.now() };
      feedback.addToast({
        type: 'error',
        message: errMsg
      });
    } finally {
      isLookingUpMB = false;
    }
  }

  async function runAcoustIDLookup() {
    if (!task?.id || isScanningAcoustID || isLookingUpMB || isLookingUpISRC || savingDraft || approving) {
      return;
    }

    clearAutosaveTimer();
    isScanningAcoustID = true;
    try {
      const response = await apiClient.post(
        `/core/metadata_review/${task.id}/lookup/acoustid`,
        {},
        { timeout: 60000 }
      );

      if (response?.data?.match_found === false) {
        const updatedMetadata = getLookupMetadata(response);
        if (updatedMetadata) {
          applyMetadataUpdate(updatedMetadata);
        }
        const noMatchMsg = 'AcoustID: No acoustic fingerprint match found in database.';
        lookupStatus = { type: 'warning', message: noMatchMsg, timestamp: Date.now() };
        feedback.addToast({
          type: 'warning',
          message: response?.data?.message || noMatchMsg
        });
        return;
      }

      const updatedMetadata = getLookupMetadata(response);
      if (updatedMetadata && response?.data?.match_found) {
        const { changed, fieldsChanged } = applyMetadataUpdate(updatedMetadata);
        if (changed && fieldsChanged.length > 0) {
          const changedKeys = fieldsChanged.map(f => f.replace('_', ' '));
          const successMsg = `Matched! Updated: ${changedKeys.join(', ')}`;
          lookupStatus = { type: 'success', message: successMsg, timestamp: Date.now() };
          feedback.addToast({
            type: 'success',
            message: `Match found! Updated: ${changedKeys.join(', ')}`
          });
        } else {
          const infoMsg = 'Match confirmed: Current metadata is already up to date.';
          lookupStatus = { type: 'info', message: infoMsg, timestamp: Date.now() };
          feedback.addToast({
            type: 'info',
            message: infoMsg
          });
        }
      } else {
        const noMatchMsg = 'AcoustID: No acoustic fingerprint match found in database.';
        lookupStatus = { type: 'warning', message: noMatchMsg, timestamp: Date.now() };
        feedback.addToast({
          type: 'warning',
          message: noMatchMsg
        });
      }
    } catch (error) {
      console.error('AcoustID lookup failed:', error);
      let errMsg = 'AcoustID lookup failed';
      if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
        errMsg = 'AcoustID fingerprinting timed out.';
      } else {
        const status = error?.response?.status;
        if (status === 404) {
          errMsg = 'No matching records found';
        } else if (status === 500 || status === 503) {
          errMsg = 'Provider lookup failed or is temporarily unavailable.';
        } else if (error?.response?.data?.detail) {
          errMsg = error.response.data.detail;
        }
      }
      lookupStatus = { type: 'error', message: errMsg, timestamp: Date.now() };
      feedback.addToast({
        type: 'error',
        message: errMsg
      });
    } finally {
      isScanningAcoustID = false;
    }
  }

  async function runISRCLookup() {
    if (isScanningAcoustID || isLookingUpMB || isLookingUpISRC || savingDraft || approving) {
      return;
    }
    openIsrcPrompt();
  }

  async function doRunISRCLookup(isrc) {
    if (isScanningAcoustID || isLookingUpMB || isLookingUpISRC || savingDraft || approving) {
      return;
    }

    clearAutosaveTimer();
    isLookingUpISRC = true;
    try {
      const response = await apiClient.post(
        `/core/metadata_review/${task.id}/lookup/isrc`,
        { isrc },
        { timeout: 60000 }
      );

      if (response?.data?.match_found === false) {
        const noMatchMsg = 'ISRC: No matching record found in database.';
        lookupStatus = { type: 'warning', message: noMatchMsg, timestamp: Date.now() };
        feedback.addToast({
          type: 'warning',
          message: response?.data?.message || noMatchMsg
        });
        return;
      }

      const updatedMetadata = getLookupMetadata(response);
      if (updatedMetadata && response?.data?.match_found) {
        const { changed, fieldsChanged } = applyMetadataUpdate(updatedMetadata);
        if (changed && fieldsChanged.length > 0) {
          const changedKeys = fieldsChanged.map(f => f.replace('_', ' '));
          const successMsg = `Matched! Updated: ${changedKeys.join(', ')}`;
          lookupStatus = { type: 'success', message: successMsg, timestamp: Date.now() };
          feedback.addToast({
            type: 'success',
            message: `Match found! Updated: ${changedKeys.join(', ')}`
          });
        } else {
          const infoMsg = 'Match confirmed: Current metadata is already up to date.';
          lookupStatus = { type: 'info', message: infoMsg, timestamp: Date.now() };
          feedback.addToast({
            type: 'info',
            message: infoMsg
          });
        }
      } else {
        const noMatchMsg = 'ISRC: No matching record found in database.';
        lookupStatus = { type: 'warning', message: noMatchMsg, timestamp: Date.now() };
        feedback.addToast({
          type: 'warning',
          message: noMatchMsg
        });
      }
    } catch (error) {
      console.error('ISRC lookup failed:', error);
      let errMsg = 'ISRC lookup failed';
      const status = error?.response?.status;
      if (status === 400) {
        errMsg = 'Invalid ISRC format — expected 12 alphanumeric characters';
      } else if (status === 404) {
        errMsg = 'No matching records found';
      } else if (status === 500 || status === 503) {
        errMsg = 'Provider lookup failed or is temporarily unavailable.';
      } else if (error?.response?.data?.detail) {
        errMsg = error.response.data.detail;
      }
      lookupStatus = { type: 'error', message: errMsg, timestamp: Date.now() };
      feedback.addToast({
        type: 'error',
        message: errMsg
      });
    } finally {
      isLookingUpISRC = false;
    }
  }

  function submitIsrcPrompt() {
    const isrc = isrcInputValue.trim();
    if (!isrc) {
      feedback.addToast({
        type: 'error',
        message: 'Please enter an ISRC code'
      });
      return;
    }
    closeIsrcPrompt();
    doRunISRCLookup(isrc);
  }
</script>

<div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
  <div class="relative flex flex-col w-full max-w-5xl max-h-[90vh] bg-slate-900 rounded-xl border border-slate-700 shadow-2xl overflow-hidden">
    <!-- 1. Header (Fixed Height) -->
    <header class="flex shrink-0 items-center justify-between p-4 border-b border-slate-800 bg-slate-900">
      <div>
        <p class="text-xs uppercase tracking-wide text-cyan-300/80 font-semibold">Metadata Editor</p>
        <h3 class="text-xl font-bold text-slate-100">Edit Metadata</h3>
        <p class="text-xs text-slate-400 mt-1">Task #{task?.id} - {getFilename(task?.file_path)}</p>
      </div>
      <button
        class="px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm active:scale-95 transition-all duration-200"
        on:click={closeModal}
        disabled={savingDraft || approving || rejecting}
      >
        Close
      </button>
    </header>

    <!-- 2. Scrollable Body (Takes Remaining Height) -->
    <main class="flex-1 min-h-0 overflow-y-auto p-6 space-y-6">
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section class="rounded-xl border border-slate-800 bg-slate-950/50 p-4">
          <div class="flex items-start gap-4 mb-4">
            {#if coverUrl}
              <div class="w-24 h-24 rounded-lg overflow-hidden border border-slate-700 shadow-lg flex-shrink-0">
                <img src={coverUrl} alt="Album Cover" class="w-full h-full object-cover" />
              </div>
            {:else}
              <div class="w-24 h-24 rounded-lg bg-slate-800 flex items-center justify-center flex-shrink-0 text-slate-500 border border-slate-700">
                <span class="text-2xl">🎵</span>
              </div>
            {/if}
            <div class="flex-1 min-w-0">
              <h4 class="text-sm font-semibold text-slate-100 mb-1">Current File Metadata</h4>
              <p class="text-xs text-slate-400 truncate" title={task?.file_path}>{task?.file_path}</p>
            </div>
          </div>
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
              <span class="text-slate-200 text-right break-all">{displayValue(currentMetadata.mbid || currentMetadata.musicbrainz_id)}</span>
            </div>
            <div class="flex justify-between gap-4">
              <span class="text-slate-400">AcoustID</span>
              <span class="text-slate-200 text-right break-all">{displayValue(currentMetadata.acoustid || currentMetadata.acoustid_id)}</span>
            </div>
            <div class="flex justify-between gap-4">
              <span class="text-slate-400">Comments</span>
              <span class="text-slate-200 text-right break-all">{displayValue(currentMetadata.comments)}</span>
            </div>
          </div>
        </section>

        <section class="rounded-xl border border-cyan-700/40 bg-cyan-950/10 p-4">
          <h4 class="text-sm font-semibold text-cyan-200 mb-3">Proposed Metadata (Editable)</h4>
          
          {#if noTagsWarning}
            <div class="mb-4 px-3 py-2 rounded border border-amber-500/50 bg-amber-950/30 text-amber-200 text-sm flex items-start gap-2">
              <span class="mt-0.5">⚠️</span>
              <span>No embedded tags found. Manual entry required.</span>
            </div>
          {/if}

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
                  <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={proposedMetadata.mbid} on:keydown={handleInputKeydown} />
                </label>

                <label>
                  <span class="block text-xs text-slate-400 mb-1">AcoustID</span>
                  <input class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100" bind:value={proposedMetadata.acoustid} on:keydown={handleInputKeydown} />
                </label>

                <label>
                  <span class="block text-xs text-slate-400 mb-1">Fingerprint Duration (s)</span>
                  <input
                    class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-300"
                    value={proposedMetadata.acoustid_fingerprint_duration || ''}
                    readonly
                  />
                </label>

                <label class="sm:col-span-2">
                  <span class="block text-xs text-slate-400 mb-1">AcoustID Fingerprint (Submission Payload)</span>
                  <textarea
                    class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-300 min-h-[90px]"
                    value={proposedMetadata.acoustid_fingerprint || ''}
                    readonly
                  ></textarea>
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
    </main>

    <!-- Track Preview -->
    {#if streamUrl}
      <div class="px-5 py-2.5 border-t border-slate-800 bg-slate-950/80 shrink-0">
        <p class="text-xs uppercase tracking-wide text-slate-400 mb-1.5 font-medium">Track Preview</p>
        <audio controls src={streamUrl} class="w-full h-8">
          Your browser does not support audio playback.
        </audio>
      </div>
    {/if}

    {#if lookupStatus}
      <div class="absolute bottom-20 left-6 right-6 z-50 pointer-events-auto" style="position: absolute; bottom: 5rem; left: 1.5rem; right: 1.5rem; z-index: 50;">
        <div class="alert alert-{lookupStatus.type} text-xs py-2 px-4 shadow-2xl flex items-center justify-between transition-all rounded-xl border backdrop-blur-md {
          lookupStatus.type === 'success' ? 'bg-emerald-950/90 border-emerald-500/50 text-emerald-200' :
          lookupStatus.type === 'warning' ? 'bg-amber-950/90 border-amber-500/50 text-amber-200' :
          lookupStatus.type === 'error' ? 'bg-rose-950/90 border-rose-500/50 text-rose-200' :
          'bg-cyan-950/90 border-cyan-500/50 text-cyan-200'
        }">
          <div class="flex items-center gap-2.5">
            <span class="text-sm">{lookupStatus.type === 'success' ? '✓' : lookupStatus.type === 'warning' ? '⚠️' : lookupStatus.type === 'error' ? '✕' : 'ℹ'}</span>
            <span class="font-medium">{lookupStatus.message}</span>
          </div>
          <button class="btn btn-ghost btn-xs btn-circle text-slate-400 hover:text-slate-100 hover:bg-slate-800" on:click={() => lookupStatus = null}>✕</button>
        </div>
      </div>
    {/if}

    <!-- 3. Footer Toolbar (Pinned & Always Visible) -->
    <footer class="flex shrink-0 flex-wrap items-center justify-between gap-3 p-4 bg-slate-950 border-t border-slate-800">
      <!-- Left: Destructive Actions -->
      <div class="flex items-center gap-2">
        <button
          class="px-4 py-2 rounded-lg bg-rose-700/80 hover:bg-rose-600 text-white disabled:opacity-60 inline-flex items-center justify-center gap-2 active:scale-95 transition-all duration-200 text-sm font-medium"
          on:click={rejectAndDelete}
          disabled={rejecting || approving || savingDraft}
          title="Reject track candidate and delete physical file from disk"
        >
          {#if rejecting}
            <span class="loading loading-spinner loading-xs animate-spin inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full"></span> Deleting...
          {:else}
            🗑️ Reject & Delete
          {/if}
        </button>
      </div>

      <!-- Right: Search Engines & Import -->
      <div class="flex flex-wrap items-center justify-end gap-2 sm:gap-3">
        <button
          class="px-4 py-2 rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700 disabled:opacity-60 active:scale-95 transition-all duration-200 text-sm"
          on:click={closeModal}
          disabled={savingDraft || approving || rejecting}
        >
          Cancel
        </button>

        <button
          class="px-4 py-2 rounded-lg bg-amber-600 text-white hover:bg-amber-500 disabled:opacity-60 active:scale-95 transition-all duration-200 text-sm"
          on:click={() => saveDraft({ silent: false })}
          disabled={savingDraft || approving || rejecting}
        >
          {savingDraft ? 'Saving...' : 'Save Draft'}
        </button>

        <button
          class="px-4 py-2 rounded-lg bg-slate-700 text-slate-100 hover:bg-slate-600 disabled:opacity-60 active:scale-95 transition-all duration-200 text-sm"
          on:click={undoLastChange}
          disabled={savingDraft || approving || rejecting || metadataHistory.length < 2}
          title="Undo last metadata edit"
        >
          Undo
        </button>

        <button
          class="px-4 py-2 rounded-lg bg-indigo-700 text-white hover:bg-indigo-600 disabled:opacity-60 inline-flex items-center justify-center gap-2 active:scale-95 transition-all duration-200 text-sm"
          on:click={runMusicBrainzLookup}
          disabled={isScanningAcoustID || isLookingUpMB || isLookingUpISRC || approving || savingDraft || rejecting}
        >
          {#if isLookingUpMB}
            <span class="loading loading-spinner loading-xs animate-spin inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full"></span> Looking up...
          {:else}
            🔍 MusicBrainz Lookup
          {/if}
        </button>

        <button
          class="px-4 py-2 rounded-lg bg-emerald-700 text-white hover:bg-emerald-600 disabled:opacity-60 inline-flex items-center justify-center gap-2 active:scale-95 transition-all duration-200 text-sm"
          on:click={runAcoustIDLookup}
          disabled={isScanningAcoustID || isLookingUpMB || isLookingUpISRC || approving || savingDraft || rejecting}
        >
          {#if isScanningAcoustID}
            <span class="loading loading-spinner loading-xs animate-spin inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full"></span> Scanning...
          {:else}
            🧬 AcoustID Scan
          {/if}
        </button>

        <button
          class="px-4 py-2 rounded-lg bg-orange-700 text-white hover:bg-orange-600 disabled:opacity-60 inline-flex items-center justify-center gap-2 active:scale-95 transition-all duration-200 text-sm"
          on:click={runISRCLookup}
          disabled={isScanningAcoustID || isLookingUpMB || isLookingUpISRC || approving || savingDraft || rejecting}
        >
          {#if isLookingUpISRC}
            <span class="loading loading-spinner loading-xs animate-spin inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full"></span> Looking up...
          {:else}
            🎵 ISRC Lookup
          {/if}
        </button>

        <button
          class="px-4 py-2 rounded-lg bg-cyan-600 text-white hover:bg-cyan-500 disabled:opacity-60 inline-flex items-center justify-center gap-2 active:scale-95 transition-all duration-200 text-sm font-medium"
          on:click={approveAndImport}
          disabled={approving || savingDraft || rejecting}
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
    </footer>
  </div>
</div>

{#if showIsrcPrompt}
  <div class="fixed inset-0 z-[200] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
    <div class="w-full max-w-sm bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-6 text-slate-100">
      <h3 class="text-lg font-bold mb-2">Enter ISRC Code</h3>
      <p class="text-xs text-slate-400 mb-4">e.g. USRC12345678 or US-RC1-23-45678</p>
      <input
        type="text"
        class="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-100 focus:outline-none focus:border-cyan-500 transition-colors mb-5"
        bind:value={isrcInputValue}
        on:keydown={(e) => e.key === 'Enter' && submitIsrcPrompt()}
        placeholder="ISRC Code"
        autofocus
      />
      <div class="flex justify-end gap-3">
        <button class="px-4 py-2 rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700 active:scale-95 transition-all" on:click={closeIsrcPrompt}>
          Cancel
        </button>
        <button class="px-4 py-2 rounded-lg bg-cyan-600 text-white hover:bg-cyan-500 active:scale-95 transition-all" on:click={submitIsrcPrompt}>
          Search
        </button>
      </div>
    </div>
  </div>
{/if}
