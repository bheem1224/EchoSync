<script>
  import { createEventDispatcher } from 'svelte';
  import apiClient from '../../api/client';
  
  export let forcedPrefix = "";
  export let placeholder = "Search library, settings, or type ? for web search...";

  const dispatch = createEventDispatcher();

  export let query = "";
  let isFocused = false;
  let inputRef;
  let searchTimer;
  let isSearching = false;

  let results = {
    settings: [],
    plugins: [],
    external: [],
    library: {
      artists: [],
      albums: [],
      tracks: []
    }
  };

  const SETTINGS_ROUTES = [
    { label: "Settings: Preferences", path: "/settings/preferences" },
    { label: "Settings: Music Services", path: "/settings/music-services" },
    { label: "Settings: Servers", path: "/settings/servers" },
    { label: "Settings: Download Clients", path: "/settings/download-clients" },
    { label: "Settings: Plugin Store", path: "/settings/plugin-store" },
    { label: "Settings: System", path: "/settings/system" },
    { label: "Dashboard", path: "/dashboard" },
    { label: "Sync Queue", path: "/sync" },
    { label: "Library Manager", path: "/library/manager" },
    { label: "Review Queue", path: "/library/review-queue" },
    { label: "Search", path: "/search" },
    { label: "Discover", path: "/discover" }
  ];

  const GUIDE_ITEMS = [
    { prefix: "> ", label: ">", desc: "Search Settings & Commands" },
    { prefix: "! ", label: "!", desc: "Search & Manage Plugins" },
    { prefix: "? ", label: "?", desc: "Search Web to Download New Music" }
  ];

  // Evaluate the query silently injecting the forcedPrefix
  $: evaluatedQuery = (forcedPrefix + query).trimStart();
  $: showGuide = isFocused && query === "" && forcedPrefix === "";
  $: showResults = isFocused && evaluatedQuery.length > 0;

  function applyPrefix(prefix) {
    query = prefix;
    inputRef.focus();
  }

  function handleInput() {
    clearTimeout(searchTimer);
    if (!evaluatedQuery) {
      clearResults();
      return;
    }

    // Settings search is local and fast
    if (evaluatedQuery.startsWith(">") || (!evaluatedQuery.match(/^[>!?#]/) && !forcedPrefix)) {
      const searchTerm = evaluatedQuery.startsWith(">") ? evaluatedQuery.replace(/^>\s*/, '').toLowerCase() : evaluatedQuery.toLowerCase();
      if (searchTerm) {
        results.settings = SETTINGS_ROUTES.filter(route => 
          route.label.toLowerCase().includes(searchTerm)
        );
      } else {
        results.settings = SETTINGS_ROUTES; // Show all if just '>'
      }
    } else {
      results.settings = [];
    }

    isSearching = true;
    searchTimer = setTimeout(async () => {
      await performSearch();
    }, 300);
  }

  async function performSearch() {
    try {
      const prefixMatch = evaluatedQuery.match(/^([>!?#])\s*(.*)/);
      const prefix = prefixMatch ? prefixMatch[1] : null;
      const term = prefixMatch ? prefixMatch[2] : evaluatedQuery;

      if (!term.trim() && !prefix) {
         clearResults();
         return;
      }

      // 1. Settings (Synchronously handled in handleInput)
      if (prefix === '>') {
        results.plugins = [];
        results.external = [];
        clearLibrary();
      }
      // 2. Plugins
      else if (prefix === '!') {
        if (term.trim()) {
            const res = await apiClient.get(`/plugins/search?q=${encodeURIComponent(term)}`);
            results.plugins = res.data?.results || res.data?.plugins || [];
        } else {
            results.plugins = [];
        }
        results.external = [];
        clearLibrary();
      }
      // 3. External (Discovery / Federated)
      else if (prefix === '?') {
        if (term.trim()) {
            const res = await apiClient.get(`/search/discovery?q=${encodeURIComponent(term)}`);
            results.external = res.data?.results || [];
        } else {
            results.external = [];
        }
        results.plugins = [];
        clearLibrary();
        results.settings = [];
      }
      // 4. Library Only (#)
      else if (prefix === '#') {
        if (term.trim()) {
            const res = await apiClient.get(`/library/search?q=${encodeURIComponent(term)}`);
            results.library.tracks = res.data?.tracks || [];
            results.library.albums = res.data?.albums || [];
            results.library.artists = res.data?.artists || [];
        } else {
            clearLibrary();
        }
        results.plugins = [];
        results.external = [];
        results.settings = [];
      }
      // 5. Default (Library + Settings)
      else {
        if (term.trim()) {
            const res = await apiClient.get(`/library/search?q=${encodeURIComponent(term)}`);
            results.library.tracks = res.data?.tracks || [];
            results.library.albums = res.data?.albums || [];
            results.library.artists = res.data?.artists || [];
        } else {
            clearLibrary();
        }
        results.plugins = [];
        results.external = [];
      }
    } catch (err) {
      console.error("Omnibar search error:", err);
    } finally {
      isSearching = false;
      results = { ...results }; // trigger reactivity
    }
  }

  function clearResults() {
    results = {
      settings: [],
      plugins: [],
      external: [],
      library: { artists: [], albums: [], tracks: [] }
    };
  }

  function clearLibrary() {
    results.library = { artists: [], albums: [], tracks: [] };
  }

  function handleKeydown(e) {
    if (e.key === 'Escape') {
      inputRef.blur();
      isFocused = false;
    }
  }

  function handleSelect(item, type) {
    dispatch('select', { item, type });
    inputRef.blur();
    isFocused = false;
    query = "";
    clearResults();
  }
</script>

<div class="relative w-full z-50" on:focusout={(e) => { if (!e.currentTarget.contains(e.relatedTarget)) isFocused = false; }}>
  <div class="relative flex items-center">
    <div class="absolute left-3 text-muted pointer-events-none">
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="11" cy="11" r="8"></circle>
        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
      </svg>
    </div>
    
    <input 
      bind:this={inputRef}
      bind:value={query}
      on:input={handleInput}
      on:focus={() => { isFocused = true; handleInput(); }}
      on:keydown={handleKeydown}
      type="text" 
      {placeholder}
      class="w-full pl-10 pr-10 py-2.5 text-sm bg-surface border border-glass-border rounded-global text-white focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/50 transition-all placeholder:text-muted"
    />

    {#if isSearching}
      <div class="absolute right-3 w-4 h-4 border-2 border-white/10 border-t-accent rounded-full animate-spin"></div>
    {/if}
  </div>

  {#if showGuide}
    <div class="absolute top-full left-0 right-0 mt-2 bg-surface border border-glass-border shadow-2xl rounded-global overflow-hidden backdrop-blur-md">
      <div class="flex flex-col py-1">
        {#each GUIDE_ITEMS as item}
          <button class="flex items-center gap-3 px-4 py-2.5 text-left bg-transparent border-none cursor-pointer hover:bg-white/5 active:bg-white/10 transition-colors" on:click={() => applyPrefix(item.prefix)}>
            <span class="bg-white/10 text-white font-mono px-2 py-0.5 rounded text-xs min-w-[24px] text-center">{item.label}</span>
            <span class="text-slate-300 text-sm">{item.desc}</span>
          </button>
        {/each}
      </div>
    </div>
  {/if}

  {#if showResults && !showGuide}
    <div class="absolute top-full left-0 right-0 mt-2 bg-surface border border-glass-border shadow-2xl rounded-global overflow-y-auto max-h-[60vh] backdrop-blur-md pb-2">
      {#if !isSearching && results.settings.length === 0 && results.plugins.length === 0 && results.external.length === 0 && results.library.artists.length === 0 && results.library.albums.length === 0 && results.library.tracks.length === 0}
        <div class="text-muted text-sm p-4 text-center">No results found.</div>
      {/if}

      {#if results.settings.length > 0}
        <div class="mb-1">
          <div class="text-muted text-[10px] font-bold px-4 py-2 uppercase tracking-widest bg-black/20">Settings</div>
          {#each results.settings as setting}
            <button class="w-full text-left px-4 py-2 text-sm text-slate-200 hover:bg-white/10 transition-colors border-none bg-transparent cursor-pointer" on:click={() => handleSelect(setting, 'setting')}>
              {setting.label}
            </button>
          {/each}
        </div>
      {/if}

      {#if results.library.artists.length > 0}
        <div class="mb-1">
          <div class="text-muted text-[10px] font-bold px-4 py-2 uppercase tracking-widest bg-black/20">Library Artists</div>
          {#each results.library.artists as artist}
            <button class="w-full text-left px-4 py-2 text-sm text-slate-200 hover:bg-white/10 transition-colors border-none bg-transparent cursor-pointer" on:click={() => handleSelect(artist, 'artist')}>
              {artist.name}
            </button>
          {/each}
        </div>
      {/if}

      {#if results.library.albums.length > 0}
        <div class="mb-1">
          <div class="text-muted text-[10px] font-bold px-4 py-2 uppercase tracking-widest bg-black/20">Library Albums</div>
          {#each results.library.albums as album}
            <button class="w-full text-left px-4 py-2 text-sm text-slate-200 hover:bg-white/10 transition-colors border-none bg-transparent cursor-pointer" on:click={() => handleSelect(album, 'album')}>
              {album.title} <span class="text-xs text-muted ml-2">{album.artist_name || ''}</span>
            </button>
          {/each}
        </div>
      {/if}

      {#if results.library.tracks.length > 0}
        <div class="mb-1">
          <div class="text-muted text-[10px] font-bold px-4 py-2 uppercase tracking-widest bg-black/20">Library Tracks</div>
          {#each results.library.tracks as track}
            <button class="w-full text-left px-4 py-2 text-sm text-slate-200 hover:bg-white/10 transition-colors border-none bg-transparent cursor-pointer" on:click={() => handleSelect(track, 'track')}>
              {track.title} <span class="text-xs text-muted ml-2">{track.artist_name || ''}</span>
            </button>
          {/each}
        </div>
      {/if}

      {#if results.plugins.length > 0}
        <div class="mb-1">
          <div class="text-muted text-[10px] font-bold px-4 py-2 uppercase tracking-widest bg-black/20">Plugins</div>
          {#each results.plugins as plugin}
            <button class="w-full text-left px-4 py-2 text-sm text-slate-200 hover:bg-white/10 transition-colors border-none bg-transparent cursor-pointer" on:click={() => handleSelect(plugin, 'plugin')}>
              {plugin.name} <span class="text-xs text-muted ml-2">v{plugin.version}</span>
            </button>
          {/each}
        </div>
      {/if}

      {#if results.external.length > 0}
        <div class="mb-1">
          <div class="text-muted text-[10px] font-bold px-4 py-2 uppercase tracking-widest bg-black/20">Discovery Results</div>
          {#each results.external as ext}
            <div class="w-full text-left px-4 py-2 text-sm text-slate-200 hover:bg-white/10 transition-colors border-none bg-transparent flex items-center justify-between">
              <button class="flex-1 text-left border-none bg-transparent cursor-pointer flex items-center gap-3" on:click={() => handleSelect(ext, 'external')}>
                  {#if ext.cover_art}
                    <img src={ext.cover_art} alt={ext.title} class="w-8 h-8 rounded object-cover shadow" />
                  {:else}
                    <div class="w-8 h-8 rounded bg-white/5 flex items-center justify-center text-xs">🎵</div>
                  {/if}
                  <div class="flex flex-col">
                    <span>{ext.title || ext.name} <span class="text-xs text-muted ml-1">— {ext.artist || ext.artist_name || ''}</span></span>
                    <span class="text-[10px] text-muted flex gap-1 mt-0.5">
                      {#each ext.sources || [] as source}
                        <span class="bg-white/5 px-1 py-0.5 rounded">{source}</span>
                      {/each}
                    </span>
                  </div>
              </button>
              
              {#if ext.ownership_state === 'missing'}
                <button class="ml-4 px-3 py-1.5 text-[10px] font-bold bg-accent text-black rounded hover:scale-105 active:scale-95 transition-all shadow-lg flex items-center gap-1 border-none cursor-pointer" on:click|stopPropagation={() => handleSelect(ext, 'download')}>
                  📥 Download
                </button>
              {/if}
            </div>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>
