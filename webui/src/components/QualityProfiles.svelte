<script>
  import { onMount } from 'svelte';
  import { preferences } from '../stores/preferences';
  import ConfirmDialog from './ConfirmDialog.svelte';
  import { feedback } from '../stores/feedback';
  import { dndzone } from 'svelte-dnd-action';
  import {
    Plus,
    GripVertical,
    SlidersHorizontal,
    Trash2,
    ArrowRight,
    Layers
  } from 'lucide-svelte';
  import QualityProfileEditor from './QualityProfileEditor.svelte';

  let editingProfile = $state(null);
  let showEditor = $state(false);
  let deletingId = $state(null);
  let showConfirm = $state(false);
  let dialogElement = $state();
  let saving = $state(false);

  const profiles = $derived($preferences?.profiles ?? []);

  onMount(async () => {
    await preferences.load();
  });

  function getProfileNameById(id) {
    if (!id) return null;
    const found = profiles.find((p) => String(p.id) === String(id));
    return found ? found.name : null;
  }

  function getReferencingProfiles(profileId) {
    return profiles.filter(
      (p) => String(p.id) !== String(profileId) && String(p.fallback_profile_id || '') === String(profileId)
    );
  }

  function addProfile() {
    if (profiles.length >= 6) return;
    const newProfile = {
      id: Date.now().toString(),
      name: `Profile ${profiles.length + 1}`,
      formats: [],
      tie_breaker: 'MAX_QUALITY',
      fallback_profile_id: null
    };
    const updated = [...profiles, newProfile];
    preferences.setLocalProfiles(updated);
    openEditor(newProfile);
  }

  function requestDeleteProfile(id) {
    deletingId = id;
    showConfirm = true;
  }

  async function deleteProfileConfirmed() {
    const targetId = String(deletingId);
    // Clear any dangling fallback_profile_id references pointing to the deleted profile
    const updated = profiles
      .filter((p) => String(p.id) !== targetId)
      .map((p) =>
        String(p.fallback_profile_id || '') === targetId
          ? { ...p, fallback_profile_id: null }
          : p
      );
    deletingId = null;
    showConfirm = false;
    try {
      await preferences.saveProfiles(updated);
      feedback.addToast('Profile deleted', 'success');
    } catch (err) {
      console.error('Failed to delete profile', err);
      feedback.addToast(err?.message || 'Failed to delete profile', 'error');
    }
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
    setTimeout(() => {
      if (dialogElement && typeof dialogElement.showModal === 'function' && !dialogElement.open) {
        dialogElement.showModal();
      }
    }, 20);
  }

  function closeEditor() {
    if (dialogElement && typeof dialogElement.close === 'function' && dialogElement.open) {
      dialogElement.close();
    }
    editingProfile = null;
    showEditor = false;
  }

  async function saveProfileEdits(e) {
    const updatedProfile = e.detail?.profile ?? e;
    saving = true;
    try {
      await preferences.saveProfile(updatedProfile);
      feedback.addToast('Profile saved', 'success');
      closeEditor();
    } catch (err) {
      console.error('Failed to save profile', err);
      feedback.addToast(err?.message || 'Failed to save profile', 'error');
    } finally {
      saving = false;
    }
  }
</script>

<section class="p-6 bg-slate-900/80 backdrop-blur-md border border-white/[0.08] rounded-xl mb-4 shadow-lg">
  <div class="flex flex-wrap justify-between items-start gap-4 pb-4 border-b border-white/[0.06]">
    <div>
      <div class="flex items-center gap-2.5">
        <Layers class="w-5 h-5 text-teal-400" />
        <h2 class="text-lg font-bold text-slate-50 tracking-tight">Quality Profiles</h2>
        <span class="text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-white/[0.06]">
          {profiles.length} / 6
        </span>
      </div>
      <p class="text-xs text-slate-400 mt-1">
        Define preferred audio format tiers, size floors, and optional 1-hop fallback profiles.
      </p>
    </div>

    <button
      type="button"
      class="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-teal-500 hover:bg-teal-400 text-slate-950 transition-all duration-150 active:scale-95 disabled:opacity-40 disabled:pointer-events-none shadow-sm shadow-teal-500/20"
      onclick={addProfile}
      disabled={profiles.length >= 6}
    >
      <Plus class="w-3.5 h-3.5 stroke-[2.5]" />
      Add Profile
    </button>
  </div>

  {#if profiles.length === 0}
    <div class="mt-4 py-8 px-4 rounded-xl border border-dashed border-white/10 bg-slate-950/40 text-center">
      <p class="text-sm text-slate-300 font-medium">No quality profiles configured yet</p>
      <p class="text-xs text-slate-500 mt-1">Create a profile to control lossless/lossy format preferences and fallbacks.</p>
    </div>
  {:else}
    <div
      class="flex flex-col gap-2.5 mt-4"
      use:dndzone={{ items: profiles, flipDurationMs }}
      onconsider={handleDndConsider}
      onfinalize={handleDndFinalize}
    >
      {#each profiles as profile (profile.id)}
        {@const fallbackName = getProfileNameById(profile.fallback_profile_id)}
        {@const usedBy = getReferencingProfiles(profile.id)}
        {@const formatList = Array.isArray(profile.formats) ? profile.formats : []}
        <div
          class="group flex justify-between items-center gap-3 px-3.5 py-3 rounded-xl bg-slate-950/60 hover:bg-slate-800/70 border border-white/[0.06] hover:border-white/[0.12] transition-all duration-150 outline-none"
        >
          <div class="flex items-center gap-3 min-w-0">
            <div
              class="cursor-grab active:cursor-grabbing p-1 text-slate-500 hover:text-slate-300 transition-colors shrink-0"
              title="Drag to reorder"
            >
              <GripVertical class="w-4 h-4" />
            </div>

            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-sm font-semibold text-slate-100 truncate">{profile.name}</span>

                {#if fallbackName}
                  <span
                    class="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/25"
                    title={`Falls back to "${fallbackName}" if preferred formats aren't found`}
                  >
                    <ArrowRight class="w-3 h-3" />
                    Fallback: {fallbackName}
                  </span>
                {/if}

                {#if usedBy.length > 0}
                  <span
                    class="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/25"
                    title={`Used as fallback by ${usedBy.map((u) => u.name).join(', ')}`}
                  >
                    Fallback target
                  </span>
                {/if}
              </div>

              {#if formatList.length > 0}
                <div class="flex flex-wrap items-center gap-1.5 mt-1.5">
                  {#each formatList.slice(0, 5) as fmt, idx}
                    <span class="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-slate-800/90 text-slate-300 border border-white/[0.06]">
                      {idx + 1}. {fmt.type}
                    </span>
                  {/each}
                  {#if formatList.length > 5}
                    <span class="text-[10px] text-slate-500 font-medium">+{formatList.length - 5} more</span>
                  {/if}
                </div>
              {:else}
                <p class="text-[11px] text-slate-500 mt-0.5">No formats configured</p>
              {/if}
            </div>
          </div>

          <div class="flex items-center gap-1.5 shrink-0">
            <button
              type="button"
              class="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-800/70 hover:bg-slate-700/80 border border-white/[0.06] transition-all duration-150 active:scale-95"
              aria-label={`Edit ${profile.name} profile`}
              title="Edit profile"
              onclick={() => openEditor(profile)}
            >
              <SlidersHorizontal class="w-3.5 h-3.5 text-teal-400" />
              <span class="hidden sm:inline">Edit</span>
            </button>

            <button
              type="button"
              class="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 border border-transparent hover:border-red-500/20 transition-all duration-150 active:scale-95"
              aria-label={`Delete ${profile.name} profile`}
              title="Delete profile"
              onclick={() => requestDeleteProfile(profile.id)}
            >
              <Trash2 class="w-4 h-4" />
            </button>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  {#if showConfirm}
    <ConfirmDialog
      title="Confirm Delete"
      message="Delete this quality profile? Any profile referencing it as a fallback will have its fallback cleared. This action saves immediately."
      confirmText="Delete"
      cancelText="Cancel"
      danger={true}
      on:confirm={deleteProfileConfirmed}
      on:cancel={cancelDelete}
    />
  {/if}

  {#if showEditor}
    <dialog
      bind:this={dialogElement}
      class="bg-transparent m-auto p-0 border-none backdrop:bg-slate-950/75 backdrop:backdrop-blur-sm overflow-visible"
      onclose={closeEditor}
    >
      <div class="bg-slate-900 border border-white/[0.1] rounded-2xl w-[92vw] max-w-[760px] max-h-[88vh] flex flex-col overflow-hidden shadow-2xl shadow-black/70 text-slate-100">
        <QualityProfileEditor
          profile={editingProfile}
          allProfiles={profiles}
          {saving}
          on:save={saveProfileEdits}
          on:cancel={closeEditor}
        />
      </div>
    </dialog>
  {/if}
</section>
