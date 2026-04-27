<script>
  import { createEventDispatcher } from 'svelte';
  import { slide } from 'svelte/transition';
  
  const dispatch = createEventDispatcher();

  export let plugin = {};
  export let globalBetaEnabled = false;
  export let downloading = false;

  let showDropdown = false;
  let openMenuId = null;

  // Logic Aliases for Clarity
  $: installedChannel = plugin.installed_channel || 'release';
  $: installedVersion = plugin.installed_version || '0.0.0';
  $: latestRelease = plugin.version || '0.0.0';
  $: latestBeta = plugin.beta_version || '0.0.0';

  // Version Comparison Helper
  const isNewer = (v1, v2) => {
    if (!v1 || !v2 || v1 === 'Unknown' || v2 === 'Unknown') return false;
    // Simple semver-lite comparison using localeCompare with numeric: true
    return v1.localeCompare(v2, undefined, { numeric: true, sensitivity: 'base' }) > 0;
  };

  $: hasStableUpdate = isNewer(latestRelease, installedVersion);
  $: hasBetaUpdate = isNewer(latestBeta, installedVersion);
  $: isInstalled = !!(plugin.is_installed || plugin._installed);

  // Action Handlers
  function handleMainAction() {
    if (downloading) return;
    
    if (globalBetaEnabled && installedChannel === 'beta') {
      if (hasBetaUpdate) {
        dispatch('install', { ...plugin, channel: 'beta', version: latestBeta });
      }
    } else {
      if (hasStableUpdate || !isInstalled) {
        dispatch('install', { ...plugin, channel: 'release', version: latestRelease });
      }
    }
  }

  function handleSwitch(targetChannel) {
    showDropdown = false;
    dispatch('install', { ...plugin, channel: targetChannel, version: targetChannel === 'beta' ? latestBeta : latestRelease });
  }

  function toggleDropdown(e) {
    e.stopPropagation();
    showDropdown = !showDropdown;
  }

  function closeDropdown() {
    showDropdown = false;
  }

  // Helper for clicking outside (inline implementation)
  function clickOutside(node) {
    const handleClick = (event) => {
      if (node && !node.contains(event.target) && !event.defaultPrevented) {
        closeDropdown();
      }
    };
    document.addEventListener('click', handleClick, true);
    return {
      destroy() {
        document.removeEventListener('click', handleClick, true);
      }
    };
  }
</script>

<div class="group relative flex flex-col p-5 bg-black/40 border border-white/10 rounded-2xl hover:border-blue-500/50 transition-all duration-300 shadow-xl backdrop-blur-md overflow-visible">
  <!-- Plugin Header -->
  <div class="flex items-start gap-4 mb-3">
    <div class="w-12 h-12 flex items-center justify-center bg-blue-500/10 text-blue-400 rounded-xl border border-blue-500/20">
      <span class="text-2xl">📦</span>
    </div>
    <div class="flex-1 min-w-0">
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-2 overflow-hidden">
          <h3 class="text-lg font-bold text-white truncate">{plugin.name}</h3>
          {#if plugin.verified_source === 'official'}
            <span class="px-1.5 py-0.5 bg-green-500/20 text-green-400 text-[10px] font-bold uppercase tracking-wider rounded border border-green-500/30 shrink-0">Official</span>
          {/if}
        </div>
        
        {#if isInstalled}
          <div class="relative">
            <button 
              class="text-white opacity-40 hover:opacity-100 p-1 px-2 rounded-lg transition-all"
              on:click={() => openMenuId = (openMenuId === plugin.id ? null : plugin.id)}
            >
              ⋮
            </button>
            {#if openMenuId === plugin.id}
              <div class="absolute right-0 top-8 w-32 bg-slate-900 border border-white/10 shadow-2xl rounded-xl z-[110] overflow-hidden">
                <button 
                  class="w-full text-left px-4 py-2 text-xs text-red-400 hover:bg-red-500/10 border-none bg-transparent cursor-pointer" 
                  on:click={() => { dispatch('uninstall', plugin); openMenuId = null; }}
                >
                  Uninstall
                </button>
              </div>
            {/if}
          </div>
        {/if}
      </div>
      <p class="text-[10px] text-slate-500 font-mono truncate">{plugin.id || 'unknown'}</p>
    </div>
  </div>

  <!-- Description -->
  <p class="text-sm text-slate-400 line-clamp-2 mb-6 h-10 leading-relaxed">
    {plugin.description || 'No description provided.'}
  </p>

  <!-- Metadata Footer -->
  <div class="flex items-center justify-between mt-auto pt-4 border-t border-white/5">
    <div class="flex flex-wrap gap-2">
      <div class="flex items-center gap-1 px-2 py-1 bg-white/5 rounded-md border border-white/10" title="Version">
        <span class="text-[10px] text-slate-500 uppercase font-bold tracking-tight">V</span>
        <span class="text-xs text-slate-300 font-mono">
          {#if isInstalled && (hasStableUpdate || (globalBetaEnabled && hasBetaUpdate))}
            {installedVersion} ➔ {globalBetaEnabled && installedChannel === 'beta' ? latestBeta : latestRelease}
          {:else}
            {isInstalled ? installedVersion : latestRelease}
          {/if}
        </span>
      </div>
      
      {#if isInstalled && installedChannel === 'beta'}
        <span class="px-2 py-1 bg-purple-500/20 text-purple-400 text-[10px] font-bold uppercase rounded border border-purple-500/30">Beta Track</span>
      {/if}
    </div>

    <!-- The Split Button -->
    <div class="relative flex items-stretch" use:clickOutside>
      {#if !globalBetaEnabled}
        <!-- Rule 1: Standard Single Button -->
        <button 
          class="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-white/5 disabled:text-slate-500 disabled:border-white/10 text-white text-xs font-bold rounded-lg transition-all border-none flex items-center gap-2"
          disabled={downloading || (isInstalled && !hasStableUpdate)}
          on:click={handleMainAction}
        >
          {#if downloading}
            <span class="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            <span>{isInstalled ? 'Updating...' : 'Installing...'}</span>
          {:else}
            <span>{!isInstalled ? 'Install' : hasStableUpdate ? 'Update' : 'Up to Date'}</span>
          {/if}
        </button>
      {:else}
        <!-- Split Button Container (ON Channels) -->
        <div class="flex rounded-lg overflow-hidden shadow-lg shadow-blue-900/20">
          <!-- Main Action -->
          <button 
            class="pl-4 pr-3 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-500 text-white text-xs font-bold border-none transition-all flex items-center gap-2 whitespace-nowrap"
            disabled={downloading || (installedChannel === 'release' ? (isInstalled && !hasStableUpdate) : !hasBetaUpdate)}
            on:click={handleMainAction}
          >
            {#if downloading}
              <span class="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
              <span>Processing...</span>
            {:else}
              <span>{!isInstalled ? 'Install' : installedChannel === 'release' ? (hasStableUpdate ? 'Update' : 'Up to Date') : (hasBetaUpdate ? 'Update Beta' : 'Beta Current')}</span>
            {/if}
          </button>

          <!-- Dropdown Arrow -->
          <button 
            class="px-2 py-2 bg-blue-700 hover:bg-blue-600 border-l border-white/10 text-white text-xs transition-all outline-none"
            on:click={toggleDropdown}
          >
            <span class="inline-block transition-transform duration-200 {showDropdown ? 'rotate-180' : ''}">▼</span>
          </button>
        </div>

        <!-- Dropdown Menu -->
        {#if showDropdown}
          <div 
            class="absolute right-0 bottom-full mb-2 w-48 bg-slate-900 border border-white/10 rounded-xl shadow-2xl z-[100] py-1 backdrop-blur-lg"
            transition:slide={{ duration: 150 }}
          >
            {#if !isInstalled || installedChannel === 'release'}
              <button 
                class="w-full text-left px-4 py-2.5 text-xs text-purple-400 hover:bg-white/5 flex items-center gap-2 transition-colors border-none bg-transparent"
                on:click={() => handleSwitch('beta')}
              >
                🚀 Switch to Beta Channel
              </button>
            {:else}
              <button 
                class="w-full text-left px-4 py-2.5 text-xs text-blue-400 hover:bg-white/5 flex items-center gap-2 transition-colors border-none bg-transparent"
                on:click={() => handleSwitch('release')}
              >
                🛡️ Revert to Stable Release
              </button>
            {/if}
          </div>
        {/if}
      {/if}
    </div>
  </div>
</div>
