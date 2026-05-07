<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { dndzone } from 'svelte-dnd-action';
  import { providers } from '../stores/providers';

  const { profile = null } = $props();
  const dispatch = createEventDispatcher();

  // Local editable copy as state
  let p = $state({
    id: '',
    name: '',
    formats: [],
    tie_breaker: 'MAX_QUALITY',
    metadataRequired: false,
    plugin_options: []
  });
  let selectedFormat = $state('');
  const flipDurationMs = 200;

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
  function handleDndConsider(e: any) {
    p.formats = e.detail.items;
  }
  function handleDndFinalize(e: any) {
    p.formats = e.detail.items;
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
        <div 
          class="flex flex-col gap-2 mt-4"
          use:dndzone="{{items: p.formats, flipDurationMs}}"
          on:consider={handleDndConsider}
          on:finalize={handleDndFinalize}
        >
          {#each p.formats as fmt (fmt.id)}
            <div class="bg-background p-4 rounded-global border border-glass-border mb-2 outline-none">
              <div class="flex justify-between items-center mb-2">
                <div class="flex items-center gap-2">
                  <div class="cursor-grab opacity-50">≡</div>
                  <strong>{fmt.type}</strong>
                </div>
                <div class="card-actions">
                  <button class="text-xs text-error-text opacity-70 hover:opacity-100" on:click={() => removeFormat(p.formats.indexOf(fmt))}>Remove</button>
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
      <h3 class="text-base font-semibold mb-3">Tie-Breaker Strategy</h3>
      {#if hasMatchingProvider && hasDownloaderWithSearch}
        <label class="flex flex-col gap-1">
          <span class="text-xs text-secondary font-medium mb-1">Select priority when multiple high-quality matches are found:</span>
          <select
            bind:value={p.tie_breaker}
            class="w-full px-3 py-2 bg-surface border border-glass-border rounded-global text-sm text-white focus:outline-none focus:ring-1 focus:ring-teal-500/50"
          >
            <option value="MAX_QUALITY" class="bg-black/50 text-white">Max Quality (Largest)</option>
            <option value="SAVE_STORAGE" class="bg-black/50 text-white">Save Storage (Smallest)</option>
            <option value="SPEED" class="bg-black/50 text-white">Speed (Fastest)</option>
          </select>
        </label>
      {:else if !hasMatchingProvider}
        <p class="muted">Tie-breaker options available when capable providers are installed.</p>
      {/if}
    </section>

    <!-- Task 4: Dynamic Plugin Options Loop -->
    <section class="plugin-options mt-6">
      {#if p.plugin_options && p.plugin_options.length > 0}
        <h3 class="text-base font-semibold mb-3">Plugin Specific Options</h3>
        <div class="flex flex-col gap-4">
          {#each p.plugin_options as option (option.id || option.name)}
            <div class="flex flex-col gap-1.5">
              <label class="text-xs text-secondary font-medium" for={option.id}>{option.label || option.name}</label>
              
              {#if option.type === 'boolean'}
                <div class="flex items-center gap-2">
                  <input 
                    type="checkbox" 
                    id={option.id} 
                    bind:checked={option.value} 
                    class="w-4 h-4 rounded border-glass-border bg-surface accent-teal-500"
                  />
                  <span class="text-sm text-white/70">{option.description || ''}</span>
                </div>
              {:else if option.type === 'dropdown'}
                <select 
                  id={option.id} 
                  bind:value={option.value} 
                  class="w-full px-3 py-2 bg-surface border border-glass-border rounded-global text-sm text-white focus:outline-none focus:ring-1 focus:ring-teal-500/50"
                >
                  {#each option.choices || [] as choice}
                    <option value={choice}>{choice}</option>
                  {/each}
                </select>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </section>
  </div>

  <div class="flex gap-2 justify-end mt-4">
    <button class="btn-primary active:scale-95 transition-all duration-200" on:click={save}>Save</button>
    <button class="button-ghost active:scale-95 transition-all duration-200" on:click={cancel}>Cancel</button>
  </div>
</div>

