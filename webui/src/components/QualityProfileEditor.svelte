<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';

  export let profile: any = null;

  const dispatch = createEventDispatcher();

  // Local editable copy
  let p: any = {
    id: '',
    name: '',
    formats: [],
    // Legacy support for durationMatch object structure if present, otherwise flat fields
    durationMatch: { enabled: false, tolerance_seconds: 3 },
    enforce_duration_match: false,
    duration_tolerance_ms: 3000,
    prefer_max_quality: false,
    metadataRequired: false
  };
  let selectedFormat: string = '';

  const AVAILABLE_FORMATS = [
    'MP3','FLAC','OGG','AAC','ALAC','APE','WAV','DSD'
  ];

  // providers awareness (show advanced options only when supported by installed providers)
  import { providers } from '../stores/providers';
  let providerList: any[] = [];
  let hasMetadataProvider = false;
  let hasMatchingProvider = false;
  const unsubProviders = providers.subscribe((v) => {
    providerList = Object.values(v?.items ?? {});
    // Check for high-quality metadata providers (Spotify, Tidal, etc)
    hasMetadataProvider = providerList.some((p) => p.capabilities?.metadata_richness === 'HIGH' || p.capabilities?.metadata_richness === 'MEDIUM');
    // Check for matching capability (implies we have good metadata to match against duration)
    // Check both 'search' and 'search_capabilities' for robustness
    hasMatchingProvider = providerList.some((p) =>
      p.capabilities?.metadata_richness === 'HIGH' ||
      p.capabilities?.search?.tracks ||
      p.capabilities?.search_capabilities?.tracks
    );
  });

  onMount(() => {
    if (profile) {
      // shallow clone
      p = JSON.parse(JSON.stringify(profile));

      // Initialize new fields if missing
      if (p.enforce_duration_match === undefined) p.enforce_duration_match = false;
      if (p.prefer_max_quality === undefined) p.prefer_max_quality = false;
      if (p.duration_tolerance_ms === undefined) p.duration_tolerance_ms = 3000;
    }
  });

  function addFormat(fmt: string) {
    if (!fmt) return;
    if (!p.formats) p.formats = [];
    const card = {
      id: Date.now().toString() + fmt,
      type: fmt,
      min_size_mb: 0,
      max_size_mb: 0,
      priority: p.formats.length + 1,
      bitrates: [],
      bit_depths: [],
      sample_rates: []
    };
    p.formats.push(card);
    // reset selection (if select is bound)
    selectedFormat = '';
    // ensure Svelte reactivity picks up change
    p = { ...p, formats: [...p.formats] };
  }

  function removeFormat(idx:number) {
    p.formats.splice(idx,1);
    // reassign for reactivity
    p = { ...p, formats: [...p.formats] };
  }

  // Drag and drop handlers
  let dragIndex: number | null = null;
  function handleDragStart(e: DragEvent, idx: number) {
    dragIndex = idx;
    e.dataTransfer!.effectAllowed = 'move';
  }
  function handleDragOver(e: DragEvent) { e.preventDefault(); }
  function handleDrop(e: DragEvent, idx: number) {
    e.preventDefault();
    if (dragIndex === null) return;
    const list = [...p.formats];
    const [moved] = list.splice(dragIndex,1);
    list.splice(idx,0,moved);
    p.formats = list;
    dragIndex = null;
  }

  function toggleArray(arr: any[], val:any) {
    // operate immutably so Svelte picks up nested changes
    const copy = Array.isArray(arr) ? [...arr] : [];
    const i = copy.indexOf(val);
    if (i === -1) copy.push(val);
    else copy.splice(i,1);
    return copy;
  }

  function toggleFormatField(fmtObj: any, field: string, val: any) {
    const updated = toggleArray(fmtObj[field] || [], val);
    fmtObj[field] = updated;
    // force parent-level reassign so Svelte recognizes the change
    p = { ...p, formats: [...(p.formats || [])] };
  }

  function applyPriority(fmtObj: any, e: Event) {
    const raw = (e.target as HTMLInputElement).value;
    let v = parseInt(String(raw));
    if (isNaN(v) || v < 1) v = 1;
    fmtObj.priority = v;

    // Reorder formats by priority and then normalize to sequential priorities
    const list = Array.isArray(p.formats) ? [...p.formats] : [];
    // ensure the object reference in list matches fmtObj (we modified in place)
    list.sort((a, b) => (Number(a.priority) || 0) - (Number(b.priority) || 0));
    for (let i = 0; i < list.length; i++) {
      list[i].priority = i + 1;
    }
    p.formats = list;
    // force reassign
    p = { ...p, formats: [...p.formats] };
  }

  function save() {
    // basic validation
    if (!p.name || p.name.trim().length === 0) {
      alert('Profile must have a name');
      return;
    }
    dispatch('save', { profile: p });
  }

  function cancel() { dispatch('cancel'); }

  import { onDestroy } from 'svelte';
  onDestroy(() => {
    try { unsubProviders && typeof unsubProviders === 'function' && unsubProviders(); } catch (e) {}
  });
</script>

<div class="editor">
  <div class="editor-header">
    <input class="input" bind:value={p.name} placeholder="Profile name (e.g. Audiophile)" />
  </div>

  <div class="editor-body">
    <section class="formats">
      <div class="formats-top">
        <label class="sr-only">Add format</label>
        <select bind:value={selectedFormat} class="input select" on:change={() => addFormat(selectedFormat)}>
          <option value="">Add format…</option>
          {#each AVAILABLE_FORMATS as f}
            <option value={f}>{f}</option>
          {/each}
        </select>
      </div>

      {#if p.formats && p.formats.length}
        <div class="formats-list">
          {#each p.formats as fmt, idx}
            <div class="format-card" draggable="true" on:dragstart={(e)=>handleDragStart(e, idx)} on:dragover={handleDragOver} on:drop={(e)=>handleDrop(e, idx)}>
              <div class="card-head">
                <strong>{fmt.type}</strong>
                <div class="card-actions">
                  <button on:click={() => removeFormat(idx)}>Remove</button>
                </div>
              </div>

              <div class="card-body">
                <label>File size (MB)
                  <div class="size-row">
                      <input type="number" min="0" bind:value={fmt.min_size_mb} class="input" />
                      <span>—</span>
                      <input type="number" min="0" bind:value={fmt.max_size_mb} placeholder="0 = unlimited" class="input" />
                      <label style="margin-left:8px">Priority
                        <input type="number" min="1" value={fmt.priority} on:change={(e) => applyPriority(fmt, e)} class="input" style="width:80px; margin-left:6px" />
                      </label>
                  </div>
                </label>

                {#if fmt.type === 'MP3' || fmt.type === 'AAC' || fmt.type === 'OGG'}
                  <label>Bitrates</label>
                  <div class="chips">
                    {#each ['320','256','192','V0','V2'] as br}
                      <label><input type="checkbox" checked={fmt.bitrates?.includes(br)} on:change={() => toggleFormatField(fmt, 'bitrates', br)} /> {br}</label>
                    {/each}
                  </div>
                {/if}

                {#if fmt.type === 'FLAC' || fmt.type === 'ALAC' || fmt.type === 'WAV' || fmt.type === 'APE' }
                  <label>Bit depths</label>
                  <div class="chips">
                    {#each ['16','24'] as bd}
                      <label><input type="checkbox" checked={fmt.bit_depths?.includes(bd)} on:change={() => toggleFormatField(fmt, 'bit_depths', bd)} /> {bd}-bit</label>
                    {/each}
                  </div>

                  <label>Sample rates</label>
                  <div class="chips">
                    {#each ['44.1','48','88.2','96','192'] as sr}
                      <label><input type="checkbox" checked={fmt.sample_rates?.includes(sr)} on:change={() => toggleFormatField(fmt, 'sample_rates', sr)} /> {sr}kHz</label>
                    {/each}
                  </div>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      {:else}
        <p class="muted">No formats added.</p>
      {/if}
    </section>

    <section class="advanced">
      <h3>Advanced Filters</h3>
      {#if hasMatchingProvider}
        <div class="advanced-options">
          <label class="checkbox-label">
            <input type="checkbox" bind:checked={p.enforce_duration_match} />
            Enforce Duration Match
          </label>

          {#if p.enforce_duration_match}
            <label class="sub-label">Tolerance (seconds)
              <input
                type="number"
                min="0"
                value={(p.duration_tolerance_ms || 3000) / 1000}
                on:input={(e) => p.duration_tolerance_ms = e.currentTarget.value * 1000}
                class="input small-input"
              />
            </label>
          {/if}

          <label class="checkbox-label" style="margin-top:8px">
            <input type="checkbox" bind:checked={p.prefer_max_quality} />
            Prefer Larger Files (Max Quality)
          </label>
        </div>
      {/if}

      {#if hasMetadataProvider}
        <label class="checkbox-label"><input type="checkbox" bind:checked={p.metadataRequired} /> Require MusicBrainz Release ID</label>
      {/if}

      {#if !hasMetadataProvider && !hasMatchingProvider}
        <p class="muted">Advanced filters available when capable providers are installed.</p>
      {/if}
    </section>
  </div>

  <div class="editor-footer">
    <button class="btn-primary" on:click={save}>Save</button>
    <button class="button-ghost" on:click={cancel}>Cancel</button>
  </div>
</div>

<style>
  .editor { display:flex; flex-direction:column; gap:12px }
  .editor-header { display:flex }
  .formats-list { display:flex; flex-direction:column; gap:8px }
  .format-card { background:var(--bg-input); padding:8px; border-radius:8px; border:1px solid var(--border-subtle) }
  .card-head { display:flex; justify-content:space-between; align-items:center }
  .size-row { display:flex; gap:8px; align-items:center }
  .chips { display:flex; gap:8px; flex-wrap:wrap }
  .editor-footer { display:flex; gap:8px; justify-content:flex-end }
  .advanced-options { display:flex; flex-direction:column; gap:8px }
  .checkbox-label { display:flex; align-items:center; gap:8px; cursor:pointer }
  .sub-label { display:flex; align-items:center; gap:8px; margin-left: 28px; font-size: 0.9em }
  .small-input { width: 80px }
</style>
