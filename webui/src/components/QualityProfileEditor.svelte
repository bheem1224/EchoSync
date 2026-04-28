<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { providers } from '../stores/providers';

  const { profile = null } = $props();
  const dispatch = createEventDispatcher();

  // Local editable copy as state
  let p = $state({
    id: '',
    name: '',
    formats: [],
    tie_breaker: 'MAX_QUALITY',
    metadataRequired: false
  });
  let selectedFormat = $state('');
  let dragIndex = $state(null);

  const AVAILABLE_FORMATS = [
    'MP3','FLAC','OGG','AAC','ALAC','APE','WAV','DSD'
  ];

  // Derived state from providers store
  const providerList = $derived(Object.values($providers?.items ?? {}));
  const hasMetadataProvider = $derived(providerList.some((p) => p.capabilities?.metadata_richness === 'HIGH' || p.capabilities?.metadata_richness === 'MEDIUM'));
  const hasMatchingProvider = $derived(providerList.some((p) =>
    p.capabilities?.metadata_richness === 'HIGH' ||
    p.capabilities?.search?.tracks ||
    p.capabilities?.search_capabilities?.tracks
  ));
  const hasDownloaderWithSearch = $derived(providerList.some(p => p.capabilities?.search?.tracks));

  onMount(() => {
    if (profile) {
      p = JSON.parse(JSON.stringify(profile));
      if (p.tie_breaker === undefined) p.tie_breaker = 'MAX_QUALITY';
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
    p.formats = [...p.formats, card];
    selectedFormat = '';
  }

  function removeFormat(idx:number) {
    const list = [...p.formats];
    list.splice(idx, 1);
    p.formats = list;
  }

  // Drag and drop handlers
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
    const copy = Array.isArray(arr) ? [...arr] : [];
    const i = copy.indexOf(val);
    if (i === -1) copy.push(val);
    else copy.splice(i,1);
    return copy;
  }

  function toggleFormatField(fmtObj: any, field: string, val: any) {
    fmtObj[field] = toggleArray(fmtObj[field] || [], val);
    // Svelte 5 state is deep by default if initialized correctly, 
    // but re-triggering array updates ensures UI refresh.
    p.formats = [...p.formats];
  }

  function applyPriority(fmtObj: any, e: Event) {
    const raw = (e.target as HTMLInputElement).value;
    let v = parseInt(String(raw));
    if (isNaN(v) || v < 1) v = 1;
    fmtObj.priority = v;

    const list = [...p.formats];
    list.sort((a, b) => (Number(a.priority) || 0) - (Number(b.priority) || 0));
    for (let i = 0; i < list.length; i++) {
      list[i].priority = i + 1;
    }
    p.formats = list;
  }

  function save() {
    if (!p.name || p.name.trim().length === 0) {
      alert('Profile must have a name');
      return;
    }
    dispatch('save', { profile: p });
  }

  function cancel() { dispatch('cancel'); }
</script>

<div class="flex flex-col gap-4">
  <div class="flex">
    <input class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary" bind:value={p.name} placeholder="Profile name (e.g. Audiophile)" />
  </div>

  <div class="editor-body">
    <section class="formats">
      <div class="formats-top">
        <label class="sr-only">Add format</label>
        <select bind:value={selectedFormat} class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary" on:change={() => addFormat(selectedFormat)}>
          <option value="">Add format…</option>
          {#each AVAILABLE_FORMATS as f}
            <option value={f}>{f}</option>
          {/each}
        </select>
      </div>

      {#if p.formats && p.formats.length}
        <div class="flex flex-col gap-2 mt-4">
          {#each p.formats as fmt, idx}
            <div class="bg-background p-4 rounded-global border border-glass-border mb-2" draggable="true" on:dragstart={(e)=>handleDragStart(e, idx)} on:dragover={handleDragOver} on:drop={(e)=>handleDrop(e, idx)}>
              <div class="flex justify-between items-center mb-2">
                <strong>{fmt.type}</strong>
                <div class="card-actions">
                  <button on:click={() => removeFormat(idx)}>Remove</button>
                </div>
              </div>

              <div class="card-body">
                <label>File size (MB)
                  <div class="flex gap-2 items-center">
                      <input type="number" min="0" bind:value={fmt.min_size_mb} class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary" />
                      <span>—</span>
                      <input type="number" min="0" bind:value={fmt.max_size_mb} placeholder="0 = unlimited" class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary" />
                      <label style="margin-left:8px">Priority
                        <input type="number" min="1" value={fmt.priority} on:change={(e) => applyPriority(fmt, e)} class="px-3 py-2 bg-background border border-border rounded-global text-sm text-primary" style="width:80px; margin-left:6px" />
                      </label>
                  </div>
                </label>

                {#if fmt.type === 'MP3' || fmt.type === 'AAC' || fmt.type === 'OGG'}
                  <label>Bitrates</label>
                  <div class="flex gap-2 flex-wrap mb-2">
                    {#each ['320','256','192','V0','V2'] as br}
                      <label><input type="checkbox" checked={fmt.bitrates?.includes(br)} on:change={() => toggleFormatField(fmt, 'bitrates', br)} /> {br}</label>
                    {/each}
                  </div>
                {/if}

                {#if fmt.type === 'FLAC' || fmt.type === 'ALAC' || fmt.type === 'WAV' || fmt.type === 'APE' }
                  <label>Bit depths</label>
                  <div class="flex gap-2 flex-wrap mb-2">
                    {#each ['16','24'] as bd}
                      <label><input type="checkbox" checked={fmt.bit_depths?.includes(bd)} on:change={() => toggleFormatField(fmt, 'bit_depths', bd)} /> {bd}-bit</label>
                    {/each}
                  </div>

                  <label>Sample rates</label>
                  <div class="flex gap-2 flex-wrap mb-2">
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
        <div class="flex flex-col gap-2">
          <div class="flex items-center justify-between gap-2">
            <span>Enforce Duration Match</span>
            <label class="switch">

              <span class="slider"></span>
            </label>
          </div>

          {#if hasDownloaderWithSearch}
            <label class="flex flex-col gap-1 mt-4">
              <span class="text-xs text-secondary font-medium">Tie-Breaker Strategy</span>
              <select
                bind:value={p.tie_breaker}
                class="w-full px-3 py-2 bg-surface border border-glass-border rounded-global text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500/50"
              >
                <option value="MAX_QUALITY" class="bg-black/50 text-white">Max Quality (Largest File)</option>
                <option value="SAVE_STORAGE" class="bg-black/50 text-white">Save Storage (Smallest File)</option>
                <option value="SPEED" class="bg-black/50 text-white">Speed (First Available)</option>
              </select>
            </label>
          {/if}
        </div>
      {/if}

      {#if hasMetadataProvider}
        <div class="flex items-center justify-between gap-2">
          <span>Require MusicBrainz Release ID</span>
          <label class="switch">
            <input type="checkbox" bind:checked={p.metadataRequired} />
            <span class="slider"></span>
          </label>
        </div>
      {/if}

      {#if !hasMetadataProvider && !hasMatchingProvider}
        <p class="muted">Advanced filters available when capable providers are installed.</p>
      {/if}
    </section>
  </div>

  <div class="flex gap-2 justify-end mt-4">
    <button class="btn-primary active:scale-95 transition-all duration-200" on:click={save}>Save</button>
    <button class="button-ghost active:scale-95 transition-all duration-200" on:click={cancel}>Cancel</button>
  </div>
</div>

