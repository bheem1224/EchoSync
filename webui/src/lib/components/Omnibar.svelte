<script>
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import apiClient from '../../api/client';
  
  let { 
    forcedPrefix = "", 
    placeholder = "Search library, settings, or type ? for web search...", 
    mode = "inline",
    onselect = null
  } = $props();

  let query = $state("");
  let isFocused = $state(false);
  let isOpen = $state(false); // Only used in modal mode
  let inputRef = $state();
  let searchTimer;
  let isSearching = $state(false);

  let results = $state({
    settings: [],
    plugins: [],
    external: [],
    library: {
      artists: [],
      albums: [],
      tracks: []
    }
  });

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
    { prefix: "? ", label: "?", desc: "Search Web to Download New Music" },
    { prefix: "# ", label: "#", desc: "Search Library Only" },
    { prefix: "@ ", label: "@", desc: "Search Artists Only" }
  ];

  const evaluatedQuery = $derived((forcedPrefix + query).trimStart());
  const showGuide = $derived((isFocused || (mode === 'modal' && isOpen)) && query === "" && forcedPrefix === "");
  const showResults = $derived((isFocused || (mode === 'modal' && isOpen)) && evaluatedQuery.length > 0);

  function applyPrefix(prefix) {
    query = prefix;
    inputRef?.focus();
  }

  function handleInput() {
    activeIndex = -1;
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
        results.settings = SETTINGS_ROUTES;
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
      const prefixMatch = evaluatedQuery.match(/^([>!?#@])\s*(.*)/);
      const prefix = prefixMatch ? prefixMatch[1] : null;
      const term = prefixMatch ? prefixMatch[2] : evaluatedQuery;

      if (!term.trim() && !prefix) {
         clearResults();
         return;
      }

      if (prefix === '>') {
        results.plugins = [];
        results.external = [];
        clearLibrary();
      }
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
      else if (prefix === '@') {
        if (term.trim()) {
            const res = await apiClient.get(`/library/search?q=${encodeURIComponent(term)}&types=artists`);
            results.library.artists = res.data?.artists || [];
            results.library.albums = [];
            results.library.tracks = [];
        } else {
            clearLibrary();
        }
        results.plugins = [];
        results.external = [];
        results.settings = [];
      }
      else if (term.includes(':')) {
        const [key, ...valueParts] = term.split(':');
        const value = valueParts.join(':').trim();
        if (key && value) {
            if (key.toLowerCase() === 'isrc') {
                const res = await apiClient.get(`/metadata/isrc/${encodeURIComponent(value)}`);
                if (res.data?.result) {
                    results.external = [{
                        ...res.data.result,
                        title: res.data.result.title,
                        artist: res.data.result.artist,
                        sources: ['isrc-lookup'],
                        ownership_state: 'missing'
                    }];
                }
            } else {
                const res = await apiClient.get(`/library/search?q=${encodeURIComponent(value)}&field=${encodeURIComponent(key)}`);
                results.library.tracks = res.data?.tracks || [];
                results.library.albums = res.data?.albums || [];
                results.library.artists = res.data?.artists || [];
            }
        }
        results.plugins = [];
        results.settings = [];
      }
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

  let activeIndex = $state(-1);
  const flattenedResults = $derived([
    ...results.settings.map(r => ({ ...r, type: 'setting' })),
    ...results.library.artists.map(r => ({ ...r, type: 'artist' })),
    ...results.library.albums.map(r => ({ ...r, type: 'album' })),
    ...results.library.tracks.map(r => ({ ...r, type: 'track' })),
    ...results.plugins.map(r => ({ ...r, type: 'plugin' })),
    ...results.external.map(r => ({ ...r, type: 'external' }))
  ]);

  function handleKeydown(e) {
    if (e.key === 'Escape') {
      if (mode === 'modal') {
        closeModal();
      } else {
        inputRef.blur();
        isFocused = false;
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIndex = (activeIndex + 1) % (flattenedResults.length || 1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIndex = (activeIndex - 1 + (flattenedResults.length || 1)) % (flattenedResults.length || 1);
    } else if (e.key === 'Enter') {
      if (activeIndex >= 0 && activeIndex < flattenedResults.length) {
        handleSelect(flattenedResults[activeIndex], flattenedResults[activeIndex].type);
      }
    }
  }

  const getFlattenedIndex = (type, index) => {
    let offset = 0;
    const types = ['setting', 'artist', 'album', 'track', 'plugin', 'external'];
    for (const t of types) {
      if (t === type) return offset + index;
      if (t === 'setting') offset += results.settings.length;
      else if (t === 'artist') offset += results.library.artists.length;
      else if (t === 'album') offset += results.library.albums.length;
      else if (t === 'track') offset += results.library.tracks.length;
      else if (t === 'plugin') offset += results.plugins.length;
      else if (t === 'external') offset += results.external.length;
    }
    return -1;
  };

  function handleSelect(item, type) {
    if (type === 'setting') {
      goto(item.path);
    } else if (type === 'artist') {
      goto(`/library?artist_id=${item.id}`);
    } else if (type === 'album') {
      goto(`/library?artist_id=${item.artist_id}&highlight_album=${item.id}`);
    } else if (type === 'track') {
      goto(`/library?artist_id=${item.artist_id}&highlight_track=${item.id}`);
    }

    if (onselect) onselect({ item, type });
    
    if (mode === 'modal') {
      closeModal();
    } else {
      inputRef.blur();
      isFocused = false;
      query = "";
      clearResults();
    }
  }

  function openModal() {
    isOpen = true;
    query = "";
    clearResults();
    setTimeout(() => inputRef?.focus(), 50);
  }

  function closeModal() {
    isOpen = false;
    isFocused = false;
    query = "";
    clearResults();
  }

  function handleGlobalKeydown(e) {
    const isInput = ['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName) || document.activeElement.isContentEditable;
    
    if ((e.ctrlKey && e.key === 'k') || (e.key === '/' && !isInput)) {
      e.preventDefault();
      if (mode === 'modal') {
        if (isOpen) closeModal();
        else openModal();
      } else if (mode === 'inline' && inputRef) {
        inputRef.focus();
      }
    }
  }

  onMount(() => {
    if (typeof window !== 'undefined') window.addEventListener('keydown', handleGlobalKeydown);
    if (typeof window !== 'undefined') window.addEventListener('es-omnibar-toggle', openModal);
  });

  onDestroy(() => {
    if (typeof window !== 'undefined') window.removeEventListener('keydown', handleGlobalKeydown);
    if (typeof window !== 'undefined') window.removeEventListener('es-omnibar-toggle', openModal);
  });
</script>

<div class="relative w-full z-50" on:focusout={(e) => { if (!e.currentTarget.contains(e.relatedTarget)) isFocused = false; }}>
  {#if mode === 'modal'}
    {#if isOpen}
      <div 
        class="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-start justify-center pt-[15vh] px-4"
        on:click|self={closeModal}
      >
        <div class="w-full max-w-2xl bg-surface border border-glass-border shadow-2xl rounded-2xl overflow-hidden animate-in fade-in zoom-in duration-200">
          <div class="relative flex items-center p-4 border-b border-glass-border">
            <div class="absolute left-7 text-muted pointer-events-none">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              </svg>
            </div>
            
            <input 
              bind:this={inputRef}
              bind:value={query}
              on:input={handleInput}
              on:keydown={handleKeydown}
              type="text" 
              placeholder="Search library, settings, plugins... (Esc to close)"
              class="w-full pl-14 pr-10 py-3 text-lg bg-transparent text-white focus:outline-none transition-all placeholder:text-muted/60"
            />

            {#if isSearching}
              <div class="absolute right-7 w-5 h-5 border-2 border-white/10 border-t-accent rounded-full animate-spin"></div>
            {/if}
          </div>

          <div class="max-h-[60vh] overflow-y-auto pb-2 custom-scrollbar">
            {#if !query && forcedPrefix === ""}
              <div class="flex flex-col py-2">
                <div class="text-muted text-[10px] font-bold px-5 py-2 uppercase tracking-widest opacity-60">Shortcuts</div>
                {#each GUIDE_ITEMS as item}
                  <button class="flex items-center gap-4 px-5 py-3 text-left bg-transparent border-none cursor-pointer hover:bg-white/5 active:bg-white/10 transition-colors" on:click={() => applyPrefix(item.prefix)}>
                    <span class="bg-white/10 text-white font-mono px-2 py-0.5 rounded text-xs min-w-[24px] text-center border border-white/5">{item.label}</span>
                    <span class="text-slate-300 text-sm font-medium">{item.desc}</span>
                  </button>
                {/each}
              </div>
            {:else if query || forcedPrefix}
               <!-- Reuse results rendering below -->
               <div class="results-content">
                  {#if !isSearching && results.settings.length === 0 && results.plugins.length === 0 && results.external.length === 0 && results.library.artists.length === 0 && results.library.albums.length === 0 && results.library.tracks.length === 0}
                    <div class="text-muted text-sm p-8 text-center">No results found for "{query}"</div>
                  {/if}

                  {#if results.settings.length > 0}
                    <div class="mb-1">
                      <div class="text-muted text-[10px] font-bold px-5 py-2 uppercase tracking-widest bg-black/20">Settings</div>
                      {#each results.settings as setting, i}
                        <button 
                          class="w-full text-left px-5 py-3 text-sm text-slate-200 hover:bg-white/10 transition-colors border-none bg-transparent cursor-pointer flex items-center justify-between group" 
                          class:active-item={activeIndex === getFlattenedIndex('setting', i)}
                          on:click={() => handleSelect(setting, 'setting')}
                        >
                          <span>{setting.label}</span>
                          <span class="text-xs text-muted opacity-0 group-hover:opacity-100 transition-opacity" class:opacity-100={activeIndex === getFlattenedIndex('setting', i)}>Go to Page ↵</span>
                        </button>
                      {/each}
                    </div>
                  {/if}

                  {#if results.library.artists.length > 0}
                    <div class="mb-1">
                      <div class="text-muted text-[10px] font-bold px-5 py-2 uppercase tracking-widest bg-black/20">Library Artists</div>
                      {#each results.library.artists as artist, i}
                        <button 
                          class="w-full text-left px-5 py-3 text-sm text-slate-200 hover:bg-white/10 transition-colors border-none bg-transparent cursor-pointer flex items-center gap-3 group" 
                          class:active-item={activeIndex === getFlattenedIndex('artist', i)}
                          on:click={() => handleSelect(artist, 'artist')}
                        >
                          <div class="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center text-xs shrink-0 border border-white/5 group-hover:border-accent/30 transition-colors" class:active-border={activeIndex === getFlattenedIndex('artist', i)}>👤</div>
                          <span class="flex-1">{artist.name}</span>
                          <span class="text-xs text-muted opacity-0 group-hover:opacity-100 transition-opacity" class:opacity-100={activeIndex === getFlattenedIndex('artist', i)}>View Artist ↵</span>
                        </button>
                      {/each}
                    </div>
                  {/if}

                  {#if results.library.albums.length > 0}
                    <div class="mb-1">
                      <div class="text-muted text-[10px] font-bold px-5 py-2 uppercase tracking-widest bg-black/20">Library Albums</div>
                      {#each results.library.albums as album, i}
                        <button 
                          class="w-full text-left px-5 py-3 text-sm text-slate-200 hover:bg-white/10 transition-colors border-none bg-transparent cursor-pointer flex items-center gap-3 group" 
                          class:active-item={activeIndex === getFlattenedIndex('album', i)}
                          on:click={() => handleSelect(album, 'album')}
                        >
                          <div class="w-8 h-8 rounded bg-white/5 flex items-center justify-center text-xs shrink-0 border border-white/5 group-hover:border-accent/30 transition-colors" class:active-border={activeIndex === getFlattenedIndex('album', i)}>💿</div>
                          <div class="flex-1 min-w-0">
                            <div class="truncate">{album.title}</div>
                            <div class="text-xs text-muted truncate">{album.artist_name || ''}</div>
                          </div>
                          <span class="text-xs text-muted opacity-0 group-hover:opacity-100 transition-opacity" class:opacity-100={activeIndex === getFlattenedIndex('album', i)}>View Album ↵</span>
                        </button>
                      {/each}
                    </div>
                  {/if}

                  {#if results.library.tracks.length > 0}
                    <div class="mb-1">
                      <div class="text-muted text-[10px] font-bold px-5 py-2 uppercase tracking-widest bg-black/20">Library Tracks</div>
                      {#each results.library.tracks as track, i}
                        <button 
                          class="w-full text-left px-5 py-3 text-sm text-slate-200 hover:bg-white/10 transition-colors border-none bg-transparent cursor-pointer flex items-center gap-3 group" 
                          class:active-item={activeIndex === getFlattenedIndex('track', i)}
                          on:click={() => handleSelect(track, 'track')}
                        >
                          <div class="w-8 h-8 rounded bg-white/5 flex items-center justify-center text-xs shrink-0 border border-white/5 group-hover:border-accent/30 transition-colors" class:active-border={activeIndex === getFlattenedIndex('track', i)}>🎵</div>
                          <div class="flex-1 min-w-0">
                            <div class="truncate">{track.title}</div>
                            <div class="text-xs text-muted truncate">{track.artist_name || ''}</div>
                          </div>
                          <span class="text-xs text-muted opacity-0 group-hover:opacity-100 transition-opacity" class:opacity-100={activeIndex === getFlattenedIndex('track', i)}>Jump to Track ↵</span>
                        </button>
                      {/each}
                    </div>
                  {/if}

                  {#if results.plugins.length > 0}
                    <div class="mb-1">
                      <div class="text-muted text-[10px] font-bold px-5 py-2 uppercase tracking-widest bg-black/20">Plugins</div>
                      {#each results.plugins as plugin, i}
                        <button 
                          class="w-full text-left px-5 py-3 text-sm text-slate-200 hover:bg-white/10 transition-colors border-none bg-transparent cursor-pointer" 
                          class:active-item={activeIndex === getFlattenedIndex('plugin', i)}
                          on:click={() => handleSelect(plugin, 'plugin')}
                        >
                          {plugin.name} <span class="text-xs text-muted ml-2">v{plugin.version}</span>
                        </button>
                      {/each}
                    </div>
                  {/if}

                  {#if results.external.length > 0}
                    <div class="mb-1">
                      <div class="text-muted text-[10px] font-bold px-5 py-2 uppercase tracking-widest bg-black/20">Discovery Results</div>
                      {#each results.external as ext, i}
                        <div 
                          class="w-full text-left px-5 py-3 text-sm text-slate-200 hover:bg-white/10 transition-colors border-none bg-transparent flex items-center justify-between group"
                          class:active-item={activeIndex === getFlattenedIndex('external', i)}
                        >
                          <button class="flex-1 text-left border-none bg-transparent cursor-pointer flex items-center gap-4 min-w-0" on:click={() => handleSelect(ext, 'external')}>
                              {#if ext.cover_art}
                                <img src={ext.cover_art} alt={ext.title} class="w-10 h-10 rounded object-cover shadow-lg border border-white/5 group-hover:border-accent/40" class:active-border={activeIndex === getFlattenedIndex('external', i)} />
                              {:else}
                                <div class="w-10 h-10 rounded bg-white/5 flex items-center justify-center text-xs border border-white/5 group-hover:border-accent/40" class:active-border={activeIndex === getFlattenedIndex('external', i)}>🎵</div>
                              {/if}
                              <div class="flex flex-col min-w-0 flex-1">
                                <span class="font-medium truncate group-hover:text-accent transition-colors" class:active-text={activeIndex === getFlattenedIndex('external', i)}>{ext.title || ext.name}</span>
                                <span class="text-xs text-muted truncate">{ext.artist || ext.artist_name || ''}</span>
                                <span class="text-[9px] text-muted flex gap-1 mt-1">
                                  {#each ext.sources || [] as source}
                                    <span class="bg-white/5 px-1.5 py-0.5 rounded border border-white/5 font-mono uppercase tracking-tighter">{source}</span>
                                  {/each}
                                </span>
                              </div>
                          </button>
                          
                          {#if ext.ownership_state === 'missing'}
                            <button class="ml-4 px-4 py-2 text-[11px] font-bold bg-accent text-black rounded-lg hover:scale-105 active:scale-95 transition-all shadow-[0_0_15px_rgba(15,239,136,0.3)] flex items-center gap-1.5 border-none cursor-pointer" on:click|stopPropagation={() => handleSelect(ext, 'download')}>
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

          <div class="p-3 bg-black/40 border-t border-glass-border flex justify-between items-center text-[10px] text-muted uppercase tracking-widest font-bold">
            <div class="flex gap-4">
              <span><span class="text-white bg-white/10 px-1 rounded mr-1">↵</span> Select</span>
              <span><span class="text-white bg-white/10 px-1 rounded mr-1">↑↓</span> Navigate</span>
              <span><span class="text-white bg-white/10 px-1 rounded mr-1">Esc</span> Close</span>
            </div>
            <div>
              Powered by <span class="text-accent">OmniSearch</span>
            </div>
          </div>
        </div>
      </div>
    {/if}
  {:else}
    <div class="relative flex items-center group">
      <div class="absolute left-3 text-muted pointer-events-none group-focus-within:text-accent transition-colors">
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
        placeholder="{placeholder} (Ctrl+K)"
        class="w-full pl-10 pr-10 py-2.5 text-sm bg-surface border border-glass-border rounded-global text-white focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/50 transition-all placeholder:text-muted/50"
      />

      <div class="absolute right-3 flex items-center gap-2">
        {#if isSearching}
          <div class="w-4 h-4 border-2 border-white/10 border-t-accent rounded-full animate-spin"></div>
        {:else if !isFocused}
          <div class="text-[10px] text-muted bg-white/5 border border-white/10 rounded px-1.5 py-0.5 font-mono">/</div>
        {/if}
      </div>
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
      <div class="absolute top-full left-0 right-0 mt-2 bg-surface border border-glass-border shadow-2xl rounded-global overflow-y-auto max-h-[60vh] backdrop-blur-md pb-2 custom-scrollbar">
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
  {/if}
</div>

<style>
  .custom-scrollbar::-webkit-scrollbar {
    width: 6px;
  }
  .custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 10px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.2);
  }

  .active-item {
    background: rgba(255, 255, 255, 0.08) !important;
  }
  .active-border {
    border-color: var(--accent) !important;
    box-shadow: 0 0 10px rgba(15, 239, 136, 0.2);
  }
  .active-text {
    color: var(--accent) !important;
  }

  /* Animations for modal */
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  @keyframes zoomIn {
    from { transform: scale(0.95); opacity: 0; }
    to { transform: scale(1); opacity: 1; }
  }
  .animate-in {
    animation: fadeIn 0.2s ease-out;
  }
  .fade-in {
    opacity: 1;
  }
  .zoom-in {
    animation: zoomIn 0.2s ease-out;
  }
</style>
