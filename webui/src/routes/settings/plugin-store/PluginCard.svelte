<script>
  import { createEventDispatcher } from 'svelte';
  import { slide } from 'svelte/transition';
  import apiClient from '../../../api/client';
  
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

  const getRepoLabel = (url) => {
    if (!url) return '';
    try {
      const u = new URL(url);
      return u.hostname.replace('www.', '');
    } catch (e) {
      return url.split('/').slice(0, 3).join('/'); // Fallback to start of string
    }
  };

  // Version Comparison Helper
  const isNewer = (v1, v2) => {
    // Clean versions of common prefixes
    const clean = (v) => (v || '').replace(/^v/, '').trim();
    const cv1 = clean(v1);
    const cv2 = clean(v2);

    if (!cv1 || cv1 === 'Unknown' || cv1 === '0.0.0') return false;
    if (!cv2 || cv2 === 'Unknown' || cv2 === '0.0.0') return true;
    if (cv1 === cv2) return false;
    
    try {
      // Use numeric comparison for semver-like strings
      const parts1 = cv1.split(/[.-]/).map(p => isNaN(p) ? p : parseInt(p));
      const parts2 = cv2.split(/[.-]/).map(p => isNaN(p) ? p : parseInt(p));
      
      for (let i = 0; i < Math.max(parts1.length, parts2.length); i++) {
        const p1 = parts1[i] ?? 0;
        const p2 = parts2[i] ?? 0;
        if (p1 > p2) return true;
        if (p1 < p2) return false;
      }
      return false;
    } catch (e) {
      return cv1.localeCompare(cv2, undefined, { numeric: true }) > 0;
    }
  };

  $: hasStableUpdate = isNewer(latestRelease, installedVersion);
  $: hasBetaUpdate = isNewer(latestBeta, installedVersion);
  $: isInstalled = !!(plugin.is_installed || plugin._installed);
  $: useBeta = globalBetaEnabled || installedChannel === 'beta';

  // Action Handlers
  function handleMainAction() {
    console.log(`[PluginCard] handleMainAction for ${plugin.id}. Channel: ${installedChannel}, StableUpdate: ${hasStableUpdate}, BetaUpdate: ${hasBetaUpdate}`);
    if (downloading) return;
    
    if (useBeta) {
      console.log(`[PluginCard] Dispatching beta install dispatch for ${plugin.id}`);
      dispatch('install', { ...plugin, channel: 'beta', version: latestBeta, isUpdate: isInstalled, isRollback: false });
    } else {
      console.log(`[PluginCard] Dispatching release install dispatch for ${plugin.id}`);
      dispatch('install', { ...plugin, channel: 'release', version: latestRelease, isUpdate: isInstalled, isRollback: false });
    }
  }

  function handleSwitch(targetChannel) {
    console.log(`[PluginCard] handleSwitch to ${targetChannel} for ${plugin.id}`);
    showDropdown = false;
    const isRollback = isInstalled && targetChannel === 'release' && installedChannel === 'beta';
    dispatch('install', { ...plugin, channel: targetChannel, version: targetChannel === 'beta' ? latestBeta : latestRelease, isUpdate: isInstalled, isRollback });
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

  // Grace Period Logic
  function getRemainingHours(expiryTimestamp) {
    if (!expiryTimestamp) return 0;
    const remainingMs = new Date(expiryTimestamp) - new Date();
    return Math.max(0, Math.floor(remainingMs / (1000 * 60 * 60)));
  }

  async function handleUndoUpdate() {
    if (confirm("Are you sure you want to restore the previous stable version? Your current beta settings and state will be replaced by the snapshot taken before the update.")) {
      try {
        await apiClient.post(`/plugins/${plugin.id}/rollback`);
        window.location.reload();
      } catch (err) {
        console.error("Rollback failed:", err);
        const errorMsg = err.response?.data?.error || "Failed to restore stable version. The snapshot might have expired.";
        alert(`Rollback failed: ${errorMsg}`);
      }
    }
  }

  async function handleRevertToStable() {
    try {
      await apiClient.post(`/plugins/${plugin.id}/beta-opt`, { beta_opt_in: false });
      window.location.reload();
    } catch (err) {
      console.error("Revert to stable failed:", err);
      alert(`Failed to revert to stable: ${err.response?.data?.error || err.message}`);
    }
  }

  async function handleOptInBeta() {
    try {
      await apiClient.post(`/plugins/${plugin.id}/beta-opt`, { beta_opt_in: true });
      if (confirm("Successfully opted-in to Beta. Would you like to check and download the Beta update now?")) {
        dispatch('install', { ...plugin, channel: 'beta', version: latestBeta, isUpdate: true, isRollback: false });
      } else {
        window.location.reload();
      }
    } catch (err) {
      console.error("Opt-in to beta failed:", err);
      alert(`Failed to opt-in to beta: ${err.response?.data?.error || err.message}`);
    }
  }

  async function handleClearLocalBeta() {
    try {
      await apiClient.post(`/plugins/${plugin.id}/beta-opt`, { beta_opt_in: null });
      window.location.reload();
    } catch (err) {
      console.error("Clearing local beta failed:", err);
      alert(`Failed to reset channel: ${err.response?.data?.error || err.message}`);
    }
  }

  $: targetVersion = (useBeta && hasBetaUpdate) 
    ? latestBeta 
    : (hasStableUpdate ? latestRelease : installedVersion);
  
  $: showArrow = isInstalled && targetVersion !== installedVersion && targetVersion !== '0.0.0';
</script>

<div class="group relative flex flex-col p-5 bg-black/40 border border-white/10 rounded-2xl hover:border-blue-500/50 transition-all duration-300 shadow-xl backdrop-blur-md overflow-visible">
  <!-- Plugin Header -->
  <div class="flex items-start gap-4 mb-3">
    <div class="w-12 h-12 flex items-center justify-center bg-blue-500/10 text-blue-400 rounded-xl border border-blue-500/20">
      <span class="text-2xl">📦</span>
    </div>
    <div class="flex-1 min-w-0">
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-1.5 flex-nowrap shrink-0 overflow-visible">
          <h3 class="text-lg font-bold text-white truncate max-w-[150px] lg:max-w-[200px]" title={plugin.name}>{plugin.name}</h3>
          {#if plugin.verified_source === 'official'}
            <span class="px-1.5 py-0.5 bg-green-500/20 text-green-400 text-[10px] font-bold uppercase tracking-wider rounded border border-green-500/30 shrink-0 whitespace-nowrap">Official</span>
          {:else if plugin._source_repo}
            <span class="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 text-[10px] font-bold uppercase tracking-wider rounded border border-blue-500/30 shrink-0 truncate max-w-[120px] whitespace-nowrap" title={plugin._source_repo}>
              {getRepoLabel(plugin._source_repo)}
            </span>
          {/if}
        </div>
        
        {#if isInstalled}
          <div class="relative">
            <button 
              class="text-white opacity-40 hover:opacity-100 p-1 px-2 rounded-lg transition-all border-none bg-transparent cursor-pointer"
              on:click={() => openMenuId = (openMenuId === plugin.id ? null : plugin.id)}
            >
              ⋮
            </button>
            {#if openMenuId === plugin.id}
              <div class="absolute right-0 top-8 w-44 bg-slate-900 border border-white/10 shadow-2xl rounded-xl z-[110] overflow-hidden py-1">
                {#if installedChannel === 'stable'}
                  <button 
                    class="w-full text-left px-4 py-2.5 text-xs text-purple-400 hover:bg-purple-500/10 border-none bg-transparent cursor-pointer whitespace-nowrap" 
                    on:click={() => { handleOptInBeta(); openMenuId = null; }}
                  >
                    🚀 Opt-in to Beta Channel
                  </button>
                {/if}
                
                {#if plugin.beta_opt_in !== null}
                  <button 
                    class="w-full text-left px-4 py-2.5 text-xs text-slate-300 hover:bg-white/5 border-none bg-transparent cursor-pointer whitespace-nowrap" 
                    on:click={() => { handleClearLocalBeta(); openMenuId = null; }}
                  >
                    ⚙️ Use Global Channel
                  </button>
                {/if}

                <button 
                  class="w-full text-left px-4 py-2.5 text-xs text-red-400 hover:bg-red-500/10 border-none bg-transparent cursor-pointer whitespace-nowrap" 
                  on:click={() => { dispatch('uninstall', plugin); openMenuId = null; }}
                >
                  🗑️ Uninstall
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

  <!-- Local Management Buttons -->
  {#if isInstalled && (installedChannel === 'beta' || plugin.previous_version_path)}
    <div class="flex flex-wrap gap-2 mb-4 p-3 bg-white/5 rounded-xl border border-white/10">
      {#if installedChannel === 'beta'}
        <button 
          on:click={handleRevertToStable}
          class="flex-1 px-3 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 font-bold rounded-lg text-[10px] uppercase tracking-wider transition-all border border-red-500/20 cursor-pointer whitespace-nowrap text-center">
          Revert to Stable Channel
        </button>
      {/if}
      
      {#if plugin.previous_version_path}
        <button 
          on:click={handleUndoUpdate}
          class="flex-1 px-3 py-2 bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400 font-bold rounded-lg text-[10px] uppercase tracking-wider transition-all border border-yellow-500/20 cursor-pointer whitespace-nowrap text-center">
          Rollback
        </button>
      {/if}
    </div>
  {/if}

  <!-- Grace Period Block -->
  {#if plugin.archive_expiry_date && getRemainingHours(plugin.archive_expiry_date) > 0}
    <div class="mb-4 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg flex items-center justify-between" transition:slide>
        <div class="pr-2">
            <h4 class="text-yellow-400 font-bold text-sm">Grace Period Active</h4>
            <p class="text-gray-300 text-[10px] mt-1 leading-tight">
                Your previous data snapshot expires in {getRemainingHours(plugin.archive_expiry_date)} hours.
            </p>
        </div>
        <button 
            on:click={handleUndoUpdate}
            class="px-3 py-1.5 bg-yellow-500 hover:bg-yellow-600 text-black font-bold rounded text-[10px] uppercase tracking-wider transition-colors border-none cursor-pointer whitespace-nowrap">
            Undo Update
        </button>
    </div>
  {/if}

  <!-- Metadata Footer -->
  <div class="flex items-center justify-between mt-auto pt-4 border-t border-white/5">
    <div class="flex flex-wrap gap-2">
      <div class="flex items-center gap-1 px-2 py-1 bg-white/5 rounded-md border border-white/10" title="Version">
        <span class="text-[10px] text-slate-500 uppercase font-bold tracking-tight">V</span>
        <span class="text-xs text-slate-300 font-mono">
          {#if showArrow}
            {installedVersion} ➔ {targetVersion}
          {:else}
            {isInstalled ? installedVersion : (useBeta ? latestBeta : latestRelease)}
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
          class="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-white/5 disabled:text-slate-500 disabled:border-white/10 text-white text-xs font-bold rounded-lg transition-all border-none flex items-center gap-2 cursor-pointer"
          disabled={downloading}
          on:click={handleMainAction}
        >
          {#if downloading}
            <span class="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
            <span>{isInstalled ? 'Updating...' : 'Installing...'}</span>
          {:else}
            <span>{!isInstalled ? 'Install' : useBeta ? (hasBetaUpdate ? 'Update' : 'Up to Date') : (hasStableUpdate ? 'Update' : 'Up to Date')}</span>
          {/if}
        </button>
      {:else}
        <!-- Split Button Container (ON Channels) -->
        <div class="flex rounded-lg overflow-hidden shadow-lg shadow-blue-900/20">
          <!-- Main Action -->
          <button 
            class="pl-4 pr-3 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 disabled:text-slate-500 text-white text-xs font-bold border-none transition-all flex items-center gap-2 whitespace-nowrap cursor-pointer"
            disabled={downloading}
            on:click={handleMainAction}
          >
            {#if downloading}
              <span class="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
              <span>Processing...</span>
            {:else}
              <span>{!isInstalled ? 'Install' : useBeta ? (hasBetaUpdate ? 'Update' : 'Up to Date') : (hasStableUpdate ? 'Update' : 'Up to Date')}</span>
            {/if}
          </button>

          <!-- Dropdown Arrow -->
          <button 
            class="px-2 py-2 bg-blue-700 hover:bg-blue-600 border-l border-white/10 text-white text-xs transition-all outline-none cursor-pointer"
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
