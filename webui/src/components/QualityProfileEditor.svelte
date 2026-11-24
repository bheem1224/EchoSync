<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import { dndzone } from 'svelte-dnd-action';
  import {
    GripVertical,
    Plus,
    Trash2,
    X,
    Lock,
    GitBranch,
    Sparkles,
    HardDrive,
    Zap
  } from 'lucide-svelte';
  import { plugins } from '../stores/plugins';

  const { profile = null, allProfiles = [], saving = false } = $props();
  const dispatch = createEventDispatcher();

  // Local editable copy as state
  let p = $state<any>({
    id: '',
    name: '',
    formats: [],
    tie_breaker: 'MAX_QUALITY',
    fallback_profile_id: null,
    metadataRequired: false,
    plugin_options: []
  });
  let selectedFormat = $state('');
  let nameError = $state('');
  const flipDurationMs = 200;

  const AVAILABLE_FORMATS = [
    'FLAC',
    'WAV',
    'DSD',
    'ALAC',
    'AIFF',
    'APE',
    'MP3',
    'M4A',
    'AAC',
    'OGG',
    'OPUS'
  ];

  const LOSSLESS_FORMATS = new Set(['FLAC', 'WAV', 'DSD', 'ALAC', 'AIFF', 'APE']);
  const LOSSY_FORMATS = new Set(['MP3', 'M4A', 'AAC', 'OGG', 'OPUS']);

  const TIE_BREAKERS = [
    {
      value: 'MAX_QUALITY',
      label: 'Max Quality',
      desc: 'Prefer largest file / highest fidelity',
      icon: Sparkles
    },
    {
      value: 'SAVE_STORAGE',
      label: 'Save Storage',
      desc: 'Prefer smallest compliant file',
      icon: HardDrive
    },
    {
      value: 'SPEED',
      label: 'Fastest Peer',
      desc: 'Prefer highest upload speed',
      icon: Zap
    }
  ];

  // Derived state from plugins store
  const pluginList = $derived(Object.values($plugins?.items ?? {}));
  const hasMatchingPlugin = $derived(
    pluginList.some(
      (pl: any) =>
        pl.capabilities?.metadata_richness === 'HIGH' ||
        pl.capabilities?.search?.tracks ||
        pl.capabilities?.search_capabilities?.tracks
    )
  );
  const hasDownloaderWithSearch = $derived(
    pluginList.some((pl: any) => pl.capabilities?.search?.tracks)
  );

  // 1-Hop Fallback Profile DAG rules:
  // 1. If >= 1 other profile already names THIS profile as its fallback,
  //    THIS profile cannot name a fallback itself (prevents chaining / cycles).
  const usedAsFallbackBy = $derived(
    (Array.isArray(allProfiles) ? allProfiles : []).filter(
      (other: any) =>
        String(other.id) !== String(p.id) &&
        String(other.fallback_profile_id || '') === String(p.id)
    )
  );

  // 2. Eligible fallback targets: any other profile that does NOT itself have a fallback.
  const eligibleFallbacks = $derived(
    (Array.isArray(allProfiles) ? allProfiles : []).filter(
      (other: any) =>
        String(other.id) !== String(p.id) &&
        !other.fallback_profile_id
    )
  );

  onMount(() => {
    if (profile) {
      const cloned = JSON.parse(JSON.stringify(profile));
      if (!Array.isArray(cloned.formats)) cloned.formats = [];
      if (!cloned.tie_breaker) cloned.tie_breaker = 'MAX_QUALITY';
      cloned.fallback_profile_id = cloned.fallback_profile_id
        ? String(cloned.fallback_profile_id)
        : null;
      if (!Array.isArray(cloned.plugin_options)) cloned.plugin_options = [];
      // Ensure every format card has a stable id for dndzone
      cloned.formats = cloned.formats.map((f: any, i: number) => ({
        ...f,
        id: f.id || `${Date.now()}-${i}-${f.type || 'FMT'}`,
        priority: Number(f.priority) || i + 1,
        bitrates: Array.isArray(f.bitrates) ? f.bitrates : [],
        bit_depths: Array.isArray(f.bit_depths) ? f.bit_depths : [],
        sample_rates: Array.isArray(f.sample_rates) ? f.sample_rates : []
      }));
      p = cloned;
    }
  });

  function syncPriorities(list: any[]) {
    return list.map((item, idx) => ({
      ...item,
      priority: idx + 1
    }));
  }

  function addFormat(fmt: string) {
    if (!fmt) return;
    const current = Array.isArray(p.formats) ? p.formats : [];
    const card = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 6)}-${fmt}`,
      type: fmt,
      min_size_mb: 0,
      max_size_mb: 0,
      priority: current.length + 1,
      bitrates: [],
      bit_depths: [],
      sample_rates: []
    };
    p.formats = [...current, card];
    selectedFormat = '';
  }

  function removeFormat(idx: number) {
    const list = [...p.formats];
    list.splice(idx, 1);
    p.formats = syncPriorities(list);
  }

  // Drag and drop handlers
  function handleDndConsider(e: any) {
    p.formats = e.detail.items;
  }
  function handleDndFinalize(e: any) {
    p.formats = syncPriorities(e.detail.items);
  }

  function toggleArray(arr: any[], val: any) {
    const copy = Array.isArray(arr) ? [...arr] : [];
    const i = copy.indexOf(val);
    if (i === -1) copy.push(val);
    else copy.splice(i, 1);
    return copy;
  }

  function toggleFormatField(fmtObj: any, field: string, val: any) {
    fmtObj[field] = toggleArray(fmtObj[field] || [], val);
    p.formats = [...p.formats];
  }

  function applyPriority(fmtObj: any, e: Event) {
    const raw = (e.target as HTMLInputElement).value;
    let v = parseInt(String(raw), 10);
    if (isNaN(v) || v < 1) v = 1;
    fmtObj.priority = v;

    const list = [...p.formats];
    list.sort((a, b) => (Number(a.priority) || 0) - (Number(b.priority) || 0));
    p.formats = syncPriorities(list);
  }

  function handleFallbackChange(e: Event) {
    const val = (e.target as HTMLSelectElement).value;
    p.fallback_profile_id = val ? String(val) : null;
  }

  function save() {
    if (!p.name || p.name.trim().length === 0) {
      nameError = 'Profile name is required';
      return;
    }
    nameError = '';
    const payload = {
      ...p,
      name: p.name.trim(),
      fallback_profile_id: usedAsFallbackBy.length > 0 ? null : (p.fallback_profile_id || null)
    };
    dispatch('save', { profile: payload });
  }

  function cancel() {
    dispatch('cancel');
  }
</script>

<!-- Modal Header (Pinned) -->
<div class="flex items-center justify-between px-6 py-4 border-b border-white/[0.08] bg-slate-900/95 shrink-0">
  <div>
    <h3 class="text-base font-bold text-slate-50 tracking-tight">
      {profile?.name ? `Edit Quality Profile` : 'New Quality Profile'}
    </h3>
    <p class="text-xs text-slate-400 mt-0.5">
      Ordered top-to-bottom by priority. Drag cards to reorder tiers.
    </p>
  </div>
  <button
    type="button"
    class="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
    aria-label="Close editor"
    onclick={cancel}
  >
    <X class="w-4 h-4" />
  </button>
</div>

<!-- Scrollable Body -->
<div class="flex-1 overflow-y-auto px-6 py-5 space-y-6">
  <!-- Profile Name + Add Format Bar -->
  <div class="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
    <div class="sm:col-span-7 flex flex-col gap-1.5">
      <label for="qp-name-input" class="text-xs font-semibold uppercase tracking-wider text-slate-400">
        Profile Name
      </label>
      <input
        id="qp-name-input"
        type="text"
        bind:value={p.name}
        oninput={() => { if (nameError) nameError = ''; }}
        placeholder="e.g. Audiophile Lossless, MP3 320 Fallback"
        class="w-full px-3.5 py-2.5 bg-slate-950/90 border {nameError ? 'border-red-500/70' : 'border-white/10'} rounded-xl text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-teal-500/40 focus:border-teal-500/60 transition-all"
      />
      {#if nameError}
        <span class="text-xs text-red-400">{nameError}</span>
      {/if}
    </div>

    <div class="sm:col-span-5 flex flex-col gap-1.5">
      <label for="qp-add-format" class="text-xs font-semibold uppercase tracking-wider text-slate-400">
        Add Audio Format
      </label>
      <div class="relative">
        <select
          id="qp-add-format"
          bind:value={selectedFormat}
          onchange={() => addFormat(selectedFormat)}
          class="w-full px-3.5 py-2.5 bg-slate-950/90 border border-teal-500/30 hover:border-teal-500/50 rounded-xl text-sm font-medium text-teal-300 focus:outline-none focus:ring-2 focus:ring-teal-500/40 transition-all cursor-pointer"
        >
          <option value="" class="bg-slate-900 text-slate-300">+ Add format tier…</option>
          <optgroup label="Lossless" class="bg-slate-900 text-slate-300">
            {#each AVAILABLE_FORMATS.filter((f) => LOSSLESS_FORMATS.has(f)) as f}
              <option value={f} class="bg-slate-900 text-slate-100">{f}</option>
            {/each}
          </optgroup>
          <optgroup label="Lossy" class="bg-slate-900 text-slate-300">
            {#each AVAILABLE_FORMATS.filter((f) => LOSSY_FORMATS.has(f)) as f}
              <option value={f} class="bg-slate-900 text-slate-100">{f}</option>
            {/each}
          </optgroup>
        </select>
      </div>
    </div>
  </div>

  <!-- Format Cards -->
  <section>
    <div class="flex items-center justify-between mb-2.5">
      <span class="text-xs font-semibold uppercase tracking-wider text-slate-400">
        Format Tiers ({p.formats?.length ?? 0})
      </span>
      {#if p.formats?.length > 1}
        <span class="text-[11px] text-slate-500">Drag handle or edit priority to reorder</span>
      {/if}
    </div>

    {#if p.formats && p.formats.length > 0}
      <div
        class="flex flex-col gap-3"
        use:dndzone={{ items: p.formats, flipDurationMs }}
        onconsider={handleDndConsider}
        onfinalize={handleDndFinalize}
      >
        {#each p.formats as fmt, idx (fmt.id)}
          {@const isLossless = LOSSLESS_FORMATS.has(fmt.type)}
          <div class="bg-slate-950/75 rounded-xl border border-white/[0.08] hover:border-white/[0.14] p-4 transition-colors outline-none">
            <!-- Card Header -->
            <div class="flex justify-between items-center pb-3 mb-3 border-b border-white/[0.06]">
              <div class="flex items-center gap-2.5">
                <div class="cursor-grab active:cursor-grabbing text-slate-500 hover:text-slate-300 transition-colors">
                  <GripVertical class="w-4 h-4" />
                </div>
                <span class="text-xs font-mono font-bold px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-white/[0.06]">
                  #{fmt.priority}
                </span>
                <span class="text-sm font-bold text-slate-100 tracking-wide">{fmt.type}</span>
                <span
                  class="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full {isLossless
                    ? 'bg-teal-500/10 text-teal-300 border border-teal-500/25'
                    : 'bg-sky-500/10 text-sky-300 border border-sky-500/25'}"
                >
                  {isLossless ? 'Lossless' : 'Lossy'}
                </span>
              </div>

              <button
                type="button"
                class="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-red-400 px-2 py-1 rounded-lg hover:bg-red-500/10 transition-colors"
                onclick={() => removeFormat(idx)}
              >
                <Trash2 class="w-3.5 h-3.5" />
                Remove
              </button>
            </div>

            <!-- Size & Priority Grid -->
            <div class="grid grid-cols-3 gap-3 mb-3.5">
              <div class="flex flex-col gap-1">
                <label class="text-[11px] font-medium text-slate-400">Min Size (MB)</label>
                <input
                  type="number"
                  min="0"
                  bind:value={fmt.min_size_mb}
                  class="w-full px-3 py-2 bg-slate-900 border border-white/10 rounded-lg text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-teal-500/50 focus:border-teal-500/50"
                />
              </div>

              <div class="flex flex-col gap-1">
                <label class="text-[11px] font-medium text-slate-400">Max Size (MB)</label>
                <input
                  type="number"
                  min="0"
                  bind:value={fmt.max_size_mb}
                  placeholder="0 = unlimited"
                  class="w-full px-3 py-2 bg-slate-900 border border-white/10 rounded-lg text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-teal-500/50 focus:border-teal-500/50"
                />
              </div>

              <div class="flex flex-col gap-1">
                <label class="text-[11px] font-medium text-slate-400">Priority</label>
                <input
                  type="number"
                  min="1"
                  value={fmt.priority}
                  onchange={(e) => applyPriority(fmt, e)}
                  class="w-full px-3 py-2 bg-slate-900 border border-white/10 rounded-lg text-sm text-slate-100 focus:outline-none focus:ring-1 focus:ring-teal-500/50 focus:border-teal-500/50"
                />
              </div>
            </div>

            <!-- Lossy Bitrate Pill Toggles -->
            {#if LOSSY_FORMATS.has(fmt.type)}
              <div class="flex flex-col gap-1.5">
                <span class="text-[11px] font-medium text-slate-400">Allowed Bitrates (leave empty for any)</span>
                <div class="flex gap-1.5 flex-wrap">
                  {#each ['320', '256', '192', 'V0', 'V2'] as br}
                    {@const active = fmt.bitrates?.includes(br)}
                    <button
                      type="button"
                      onclick={() => toggleFormatField(fmt, 'bitrates', br)}
                      class="px-2.5 py-1 rounded-lg text-xs font-medium border transition-all duration-150 {active
                        ? 'bg-teal-500/20 text-teal-200 border-teal-400/50 shadow-sm shadow-teal-500/10'
                        : 'bg-slate-900 text-slate-400 border-white/[0.08] hover:border-white/20 hover:text-slate-200'}"
                    >
                      {br}{br.startsWith('V') ? '' : ' kbps'}
                    </button>
                  {/each}
                </div>
              </div>
            {/if}

            <!-- Lossless Bit Depth & Sample Rate Pill Toggles -->
            {#if fmt.type === 'FLAC' || fmt.type === 'ALAC' || fmt.type === 'WAV' || fmt.type === 'AIFF' || fmt.type === 'APE'}
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div class="flex flex-col gap-1.5">
                  <span class="text-[11px] font-medium text-slate-400">Bit Depths</span>
                  <div class="flex gap-1.5 flex-wrap">
                    {#each ['16', '24'] as bd}
                      {@const active = fmt.bit_depths?.includes(bd)}
                      <button
                        type="button"
                        onclick={() => toggleFormatField(fmt, 'bit_depths', bd)}
                        class="px-2.5 py-1 rounded-lg text-xs font-medium border transition-all duration-150 {active
                          ? 'bg-teal-500/20 text-teal-200 border-teal-400/50 shadow-sm shadow-teal-500/10'
                          : 'bg-slate-900 text-slate-400 border-white/[0.08] hover:border-white/20 hover:text-slate-200'}"
                      >
                        {bd}-bit
                      </button>
                    {/each}
                  </div>
                </div>

                <div class="flex flex-col gap-1.5">
                  <span class="text-[11px] font-medium text-slate-400">Sample Rates</span>
                  <div class="flex gap-1.5 flex-wrap">
                    {#each ['44.1', '48', '88.2', '96', '192'] as sr}
                      {@const active = fmt.sample_rates?.includes(sr)}
                      <button
                        type="button"
                        onclick={() => toggleFormatField(fmt, 'sample_rates', sr)}
                        class="px-2.5 py-1 rounded-lg text-xs font-medium border transition-all duration-150 {active
                          ? 'bg-teal-500/20 text-teal-200 border-teal-400/50 shadow-sm shadow-teal-500/10'
                          : 'bg-slate-900 text-slate-400 border-white/[0.08] hover:border-white/20 hover:text-slate-200'}"
                      >
                        {sr}kHz
                      </button>
                    {/each}
                  </div>
                </div>
              </div>
            {:else if fmt.type === 'DSD'}
              <p class="text-[11px] text-slate-500">
                Native DSD bitstream — validated against container bitrate floor and spectral integrity checks.
              </p>
            {/if}
          </div>
        {/each}
      </div>
    {:else}
      <div class="py-8 px-4 rounded-xl border border-dashed border-white/10 bg-slate-950/40 text-center">
        <p class="text-sm text-slate-300 font-medium">No format tiers added yet</p>
        <p class="text-xs text-slate-500 mt-1">Select a format from the dropdown above to start building this profile.</p>
      </div>
    {/if}
  </section>

  <!-- 1-Hop Fallback ("Good Enough") Profile -->
  <section class="p-4 rounded-xl bg-slate-950/60 border border-white/[0.08]">
    <div class="flex items-center gap-2 mb-1">
      <GitBranch class="w-4 h-4 text-amber-400" />
      <h4 class="text-sm font-semibold text-slate-100">Fallback Profile (Last Resort)</h4>
    </div>
    <p class="text-xs text-slate-400 mb-3">
      If no preferred-tier candidates match, Download Manager automatically falls back to this profile in the same search pass without triggering extra searches.
    </p>

    {#if usedAsFallbackBy.length > 0}
      <div class="flex items-start gap-2.5 p-3 rounded-lg bg-indigo-500/10 border border-indigo-500/25 text-xs text-indigo-200">
        <Lock class="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
        <div>
          <span class="font-semibold">Fallback chaining disabled:</span>
          This profile is already used as a fallback by
          <span class="font-semibold text-white">{usedAsFallbackBy.map((u: any) => u.name).join(', ')}</span>.
          To prevent loops, a fallback target cannot define its own fallback.
        </div>
      </div>
    {:else}
      <select
        aria-label="Fallback quality profile"
        value={p.fallback_profile_id || ''}
        onchange={handleFallbackChange}
        class="w-full px-3.5 py-2.5 bg-slate-900 border border-white/10 rounded-xl text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500/40 focus:border-teal-500/60 transition-all"
      >
        <option value="" class="bg-slate-900 text-slate-300">
          None (strict — only accept formats in this profile)
        </option>
        {#each eligibleFallbacks as fb (fb.id)}
          <option value={String(fb.id)} class="bg-slate-900 text-slate-100">
            {fb.name} ({Array.isArray(fb.formats) ? fb.formats.map((f: any) => f.type).join(', ') || 'No formats' : 'No formats'})
          </option>
        {/each}
      </select>
      {#if eligibleFallbacks.length === 0}
        <p class="text-[11px] text-slate-500 mt-1.5">
          Create a second standalone quality profile (e.g. MP3 320) to select it here as a fallback.
        </p>
      {/if}
    {/if}
  </section>

  <!-- Tie-Breaker Strategy (Segmented Cards — Never Overflows Footer!) -->
  <section class="p-4 rounded-xl bg-slate-950/60 border border-white/[0.08]">
    <h4 class="text-sm font-semibold text-slate-100 mb-1">Tie-Breaker Strategy</h4>
    {#if hasMatchingPlugin && hasDownloaderWithSearch}
      <p class="text-xs text-slate-400 mb-3">
        Choose how to rank candidates when multiple matches satisfy the same format tier.
      </p>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
        {#each TIE_BREAKERS as tb}
          {@const selected = p.tie_breaker === tb.value}
          {@const Icon = tb.icon}
          <button
            type="button"
            onclick={() => { p.tie_breaker = tb.value; }}
            class="flex flex-col items-start text-left p-3 rounded-xl border transition-all duration-150 {selected
              ? 'bg-teal-500/15 border-teal-400/60 text-slate-50 shadow-sm shadow-teal-500/10'
              : 'bg-slate-900/80 border-white/[0.07] text-slate-300 hover:border-white/20 hover:bg-slate-800/70'}"
          >
            <div class="flex items-center gap-1.5 font-semibold text-xs {selected ? 'text-teal-300' : 'text-slate-200'}">
              <Icon class="w-3.5 h-3.5" />
              {tb.label}
            </div>
            <span class="text-[11px] text-slate-400 mt-1 leading-snug">{tb.desc}</span>
          </button>
        {/each}
      </div>
    {:else if !hasMatchingPlugin}
      <p class="text-xs text-slate-500">Tie-breaker options become available when a download provider with search is enabled.</p>
    {/if}
  </section>

  <!-- Dynamic Plugin Options -->
  {#if p.plugin_options && p.plugin_options.length > 0}
    <section class="p-4 rounded-xl bg-slate-950/60 border border-white/[0.08]">
      <h4 class="text-sm font-semibold text-slate-100 mb-3">Plugin Specific Options</h4>
      <div class="flex flex-col gap-3.5">
        {#each p.plugin_options as option (option.id || option.name)}
          <div class="flex flex-col gap-1.5">
            <label class="text-xs text-slate-300 font-medium" for={option.id}>
              {option.label || option.name}
            </label>

            {#if option.type === 'boolean'}
              <label class="inline-flex items-center gap-2.5 cursor-pointer">
                <input
                  type="checkbox"
                  id={option.id}
                  bind:checked={option.value}
                  class="w-4 h-4 rounded border-white/20 bg-slate-900 accent-teal-500"
                />
                <span class="text-xs text-slate-400">{option.description || ''}</span>
              </label>
            {:else if option.type === 'dropdown'}
              <select
                id={option.id}
                bind:value={option.value}
                class="w-full px-3.5 py-2 bg-slate-900 border border-white/10 rounded-xl text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500/40"
              >
                {#each option.choices || [] as choice}
                  <option value={choice} class="bg-slate-900 text-slate-100">{choice}</option>
                {/each}
              </select>
            {/if}
          </div>
        {/each}
      </div>
    </section>
  {/if}
</div>

<!-- Sticky Modal Footer -->
<div class="flex items-center justify-end gap-2.5 px-6 py-4 border-t border-white/[0.08] bg-slate-900/95 shrink-0">
  <button
    type="button"
    class="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700/80 border border-white/[0.08] transition-all duration-150 active:scale-95"
    onclick={cancel}
    disabled={saving}
  >
    Cancel
  </button>
  <button
    type="button"
    class="px-5 py-2 rounded-xl text-xs font-semibold bg-teal-500 hover:bg-teal-400 text-slate-950 transition-all duration-150 active:scale-95 disabled:opacity-50 shadow-sm shadow-teal-500/20"
    onclick={save}
    disabled={saving}
  >
    {saving ? 'Saving…' : 'Save Profile'}
  </button>
</div>
