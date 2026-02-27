<script>
  import { onMount } from 'svelte';
  import { preferences } from '../stores/preferences';
  import ConfirmDialog from './ConfirmDialog.svelte';
  import { feedback } from '../stores/feedback';

  let prefs;
  const unsub = preferences.subscribe((v) => (prefs = v));
  import { onDestroy } from 'svelte';
  onDestroy(() => unsub && typeof unsub === 'function' && unsub());

  let editingProfile = null;
  let showEditor = false;
  import QualityProfileEditor from './QualityProfileEditor.svelte';

  onMount(async () => {
    await preferences.load();
  });

  function addProfile() {
    const profiles = prefs?.profiles || [];
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

  let deletingId = null;
  let showConfirm = false;

  function requestDeleteProfile(id) {
    deletingId = id;
    showConfirm = true;
  }

  function deleteProfileConfirmed() {
    const updated = (prefs?.profiles || []).filter((p) => p.id !== deletingId);
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
  let dragIndex = null;
  function handleDragStart(e, idx) {
    dragIndex = idx;
    e.dataTransfer.effectAllowed = 'move';
  }
  function handleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  }
  function handleDrop(e, idx) {
    e.preventDefault();
    if (dragIndex === null) return;
    const list = [...(prefs?.profiles || [])];
    const [moved] = list.splice(dragIndex, 1);
    list.splice(idx, 0, moved);
    // reordering is local-only until Save All
    preferences.setLocalProfiles(list);
    dragIndex = null;
  }

  function openEditor(profile) {
    editingProfile = JSON.parse(JSON.stringify(profile));
    showEditor = true;
  }

  function closeEditor() {
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

  <section class="quality-profiles card">
    <div class="section-heading">
      <h2>Quality Profiles</h2>
      <div class="controls">
        <button class="btn-primary add-btn" on:click={addProfile} disabled={prefs?.profiles && prefs.profiles.length >= 6}>+ Add</button>
      </div>
    </div>

      <div class="profiles-list">
    {#each prefs?.profiles ?? [] as profile, idx}
      <div
        class="profile-row"
        draggable="true"
        on:dragstart={(e) => handleDragStart(e, idx)}
        on:dragover={handleDragOver}
        on:drop={(e) => handleDrop(e, idx)}
      >
        <div class="row-left">
          <div class="drag-handle">≡</div>
          <div class="profile-name">{profile.name}</div>
        </div>
        <div class="row-right">
          <button class="settings-btn" on:click={() => openEditor(profile)}>⚙️</button>
          <button class="delete" on:click={() => requestDeleteProfile(profile.id)}>✕</button>
        </div>
      </div>
    {/each}
  </div>

  {#if showConfirm}
    <ConfirmDialog title="Confirm Delete" message="Delete this quality profile? This action will be saved immediately." confirmText="Delete" cancelText="Cancel" danger={true} on:confirm={deleteProfileConfirmed} on:cancel={cancelDelete} />
  {/if}

  {#if showEditor}
    <div class="modal-backdrop" on:click={closeEditor}>
      <div class="modal" on:click|stopPropagation>
        <QualityProfileEditor profile={editingProfile} on:save={saveProfileEdits} on:cancel={closeEditor} />
      </div>
    </div>
  {/if}
</section>

<style>
  .quality-profiles { padding: 12px; }
  .profiles-list { display:flex; flex-direction:column; gap:8px; margin-top:12px }
  .profile-row { display:flex; justify-content:space-between; align-items:center; padding:8px; border-radius:8px; background:var(--card-bg); }
  .row-left { display:flex; gap:8px; align-items:center }
  .drag-handle { cursor:grab }
  .settings-btn, .delete { margin-left:8px }
  .modal-backdrop { position:fixed; inset:0; background:rgba(0,0,0,0.7); display:flex; align-items:center; justify-content:center; z-index:2000; backdrop-filter: blur(6px); }
  .modal { background:var(--bg-card); padding:16px; border-radius:12px; width:90%; max-width:760px; max-height: 85vh; overflow-y: auto; box-shadow: 0 20px 60px rgba(0,0,0,0.6); color:var(--text-main) }
</style>
