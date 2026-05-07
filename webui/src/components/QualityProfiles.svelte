<script>
  import { onMount } from 'svelte';
  import { preferences } from '../stores/preferences';
  import ConfirmDialog from './ConfirmDialog.svelte';
  import { feedback } from '../stores/feedback';
  import { dndzone } from 'svelte-dnd-action';
  import QualityProfileEditor from './QualityProfileEditor.svelte';

  let editingProfile = $state(null);
  let showEditor = $state(false);
  let deletingId = $state(null);
  let showConfirm = $state(false);
  let dragIndex = $state(null);
  let dialogElement = $state();

  onMount(async () => {
    await preferences.load();
  });

  function addProfile() {
    const profiles = $preferences?.profiles || [];
    if (profiles.length >= 6) return;
    const newProfile = {
      id: Date.now().toString(),
      name: `Profile ${profiles.length + 1}`,
      types: []
    };
    const updated = [...profiles, newProfile];
    // local-only until Save All
    preferences.setLocalProfiles(updated);
    // open editor immediately so user can Save the new profile (modal Save will persist)
    openEditor(newProfile);
  }

  function requestDeleteProfile(id) {
    deletingId = id;
    showConfirm = true;
  }

  function deleteProfileConfirmed() {
    const updated = ($preferences?.profiles || []).filter((p) => p.id !== deletingId);
    // delete auto-saves immediately but require confirmation
    preferences.saveProfiles(updated);
    deletingId = null;
    showConfirm = false;
    feedback.addToast('Profile deleted', 'success');
  }

  function cancelDelete() {
    deletingId = null;
    showConfirm = false;
  }

  // Drag and drop handlers
  const flipDurationMs = 200;
  function handleDndConsider(e) {
    preferences.setLocalProfiles(e.detail.items);
  }
  function handleDndFinalize(e) {
    preferences.setLocalProfiles(e.detail.items);
  }

  function openEditor(profile) {
    editingProfile = JSON.parse(JSON.stringify(profile));
    showEditor = true;
    // In Svelte 5, $effect or a small timeout ensures dialog is in DOM
    setTimeout(() => {
      if (dialogElement && typeof dialogElement.showModal === 'function') {
        dialogElement.showModal();
      }
    }, 20);
  }

  function closeEditor() {
    if (dialogElement && typeof dialogElement.close === 'function') {
      dialogElement.close();
    }
    editingProfile = null;
    showEditor = false;
  }

  function saveProfileEdits(e) {
    const updatedProfile = e.detail?.profile ?? e;
    // Persist this single profile immediately (user clicked Save in the modal)
    preferences.saveProfile(updatedProfile).then(() => {
      feedback.addToast('Profile saved', 'success');
    }).catch((err) => {
      console.error('Failed to save profile', err);
      feedback.addToast('Failed to save profile', 'error');
    });
    closeEditor();
  }
</script>

  <section class="p-6 bg-surface backdrop-blur-md border border-glass-border rounded-global mb-4">
    <div class="flex justify-between items-center">
      <h2 class="text-xl font-bold text-primary">Quality Profiles</h2>
      <div class="controls">
        <button class="btn-primary add-btn active:scale-95 transition-all duration-200" on:click={addProfile} disabled={$preferences?.profiles && $preferences.profiles.length >= 6}>+ Add</button>
      </div>
    </div>

      <div 
        class="flex flex-col gap-2 mt-3"
        use:dndzone="{{items: $preferences?.profiles ?? [], flipDurationMs}}"
        on:consider={handleDndConsider}
        on:finalize={handleDndFinalize}
      >
    {#each $preferences?.profiles ?? [] as profile (profile.id)}
      <div
        class="flex justify-between items-center p-2 rounded-global bg-surface-hover outline-none"
      >
        <div class="flex gap-2 items-center">
          <div class="cursor-grab p-1 opacity-50 hover:opacity-100">≡</div>
          <div class="profile-name">{profile.name}</div>
        </div>
        <div class="row-right">
          <button class="ml-2 active:scale-95 transition-all duration-200" on:click={() => openEditor(profile)}>⚙️</button>
          <button class="ml-2 text-error-text hover:bg-error-bg rounded-global p-1 active:scale-95 transition-all duration-200" on:click={() => requestDeleteProfile(profile.id)}>✕</button>
        </div>
      </div>
    {/each}
  </div>

  {#if showConfirm}
    <ConfirmDialog title="Confirm Delete" message="Delete this quality profile? This action will be saved immediately." confirmText="Delete" cancelText="Cancel" danger={true} on:confirm={deleteProfileConfirmed} on:cancel={cancelDelete} />
  {/if}

  {#if showEditor}
    <dialog bind:this={dialogElement} class="bg-transparent m-auto p-0 border-none backdrop:bg-black/60 backdrop:backdrop-blur-md overflow-visible" on:close={closeEditor}>
      <div class="bg-surface border border-glass-border p-6 rounded-global w-[90vw] max-w-[760px] max-h-[90vh] overflow-auto shadow-2xl text-white">
        <QualityProfileEditor
            profile={editingProfile}
            on:save={saveProfileEdits}
            on:cancel={closeEditor}
        />
      </div>
    </dialog>
  {/if}
</section>

