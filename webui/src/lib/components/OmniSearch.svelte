<script>
  import { onMount, onDestroy } from 'svelte';
  import { goto } from '$app/navigation';
  import apiClient, { API_BASE_URL } from '../../api/client';
  import { plugins } from '../../stores/plugins';
  import { player } from '../../stores/player';

  // ── Svelte 5 Props ────────────────────────────────────────────────────
  let { 
    inline = false, 
    mode = "inline", 
    forcedPrefix = "", 
    placeholder = "Search library, settings, or type ? for web search...", 
    onselect = null 
  } = $props();

  const getPluginName = (id) => Object.values($plugins?.items ?? []).find(p => p.id === id)?.name || $plugins?.find?.(p => p.id === id)?.name || 'Unknown Plugin';

  // ── Component State ───────────────────────────────────────────────────
  let query = $state("");
  let isFocused = $state(false);
  let isOpen = $state(false); // Used in Omnibar modal mode
  let showHelpBooklet = $state(false);
  let isSearching = $state(false);
  let searchTimer;
  let activeIndex = $state(-1);
  let inputRef = $state();
  let activeSearchAbortController = null;

  function formatDuration(ms) {
    if (!ms) return '-:--';
    const seconds = Math.floor(ms / 1000);
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  function getCookie(name) {
    if (typeof document === 'undefined') return null;
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
  }

  function appendStreamChunk(chunk) {
    const items = chunk.results || [];
    
    const newTracks = [...results.library.tracks];
    const newAlbums = [...results.library.albums];
    const newArtists = [...results.library.artists];
    const newExternal = [...results.external];
    
    for (const item of items) {
      if (item.is_local) {
        if (item.type === 'tracks') {
          if (!newTracks.some(t => t.id === item.id)) {
            newTracks.push(item);
          }
        } else if (item.type === 'albums') {
          if (!newAlbums.some(a => a.id === item.id)) {
            newAlbums.push(item);
          }
        } else if (item.type === 'artists') {
          if (!newArtists.some(ar => ar.id === item.id)) {
            newArtists.push(item);
          }
        }
      } else {
        const itemIsrc = (item.isrc || item.identifiers?.isrc || '').toLowerCase();
        const itemTitle = (item.title || item.name || '').toLowerCase();
        const itemArtist = (item.artist || item.artist_name || '').toLowerCase();
        
        const isLocalDuplicate = newTracks.some(t => {
          const tIsrc = (t.isrc || t.identifiers?.isrc || '').toLowerCase();
          const tTitle = (t.title || t.name || '').toLowerCase();
          const tArtist = (t.artist || t.artist_name || '').toLowerCase();
          return (itemIsrc && tIsrc === itemIsrc) || (tTitle === itemTitle && tArtist === itemArtist);
        });
        
        if (isLocalDuplicate) {
          continue;
        }
        
        const existingIndex = newExternal.findIndex(ext => {
          const extIsrc = (ext.isrc || ext.identifiers?.isrc || '').toLowerCase();
          const extTitle = (ext.title || ext.name || '').toLowerCase();
          const extArtist = (ext.artist || ext.artist_name || '').toLowerCase();
          return (itemIsrc && extIsrc === itemIsrc) || (extTitle === itemTitle && extArtist === itemArtist);
        });
        
        if (existingIndex !== -1) {
          const existingItem = newExternal[existingIndex];
          const existingScore = existingItem.metadata_quality_score || 50;
          const newScore = item.metadata_quality_score || 50;
          
          if (newScore > existingScore) {
            newExternal[existingIndex] = item;
          }
        } else {
          newExternal.push(item);
        }
      }
    }
    
    results.library.tracks = newTracks;
    results.library.albums = newAlbums;
    results.library.artists = newArtists;
    newExternal.sort((a, b) => (b.metadata_quality_score || 50) - (a.metadata_quality_score || 50));
    results.external = newExternal;
  }

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
    { label: "Settings: Downloads", path: "/settings/downloads" },
    { label: "Settings: Jobs", path: "/settings/jobs" },
    { label: "Settings: Metadata", path: "/settings/metadata" },
    { label: "Settings: Misc", path: "/settings/misc" },
    { label: "Settings: Search", path: "/settings/search" },
    { label: "Dashboard", path: "/dashboard" },
    { label: "Sync Queue", path: "/sync" },
    { label: "Library Manager", path: "/library/manager" },
    { label: "Review Queue", path: "/library/review-queue" },
    { label: "Search", path: "/search" },
    { label: "Discover", path: "/discover" }
  ];

  const settingsLexicon = {
    "quality": "/settings/preferences",
    "transcode": "/settings/preferences",
    "theme": "/settings/preferences",
    "dark mode": "/settings/preferences",
    "accent": "/settings/preferences",
    "downloads": "/settings/downloads",
    "downloading": "/settings/downloads",
    "download clients": "/settings/download-clients",
    "sabnzbd": "/settings/download-clients",
    "qbittorrent": "/settings/download-clients",
    "aria2": "/settings/download-clients",
    "plex": "/settings/servers",
    "jellyfin": "/settings/servers",
    "navidrome": "/settings/servers",
    "subsonic": "/settings/servers",
    "spotify": "/settings/music-services",
    "tidal": "/settings/music-services",
    "deezer": "/settings/music-services",
    "plugins": "/settings/plugin-store",
    "extensions": "/settings/plugin-store",
    "addons": "/settings/plugin-store",
    "metadata": "/settings/metadata",
    "logs": "/settings/system",
    "database": "/settings/system",
    "storage": "/settings/system",
    "network": "/settings/system",
    "jobs": "/settings/jobs",
    "tasks": "/settings/jobs",
    "scheduler": "/settings/jobs"
  };

  const GUIDE_ITEMS = [
    { prefix: "> ", label: ">", desc: "Search Settings & Commands" },
    { prefix: "! ", label: "!", desc: "Search & Manage Plugins" },
    { prefix: "? ", label: "?", desc: "Search Web to Download New Music" },
    { prefix: "# ", label: "#", desc: "Search Library Only" },
    { prefix: "@ ", label: "@", desc: "Search Artists Only" }
  ];

  // ── Derived State ─────────────────────────────────────────────────────
  const evaluatedQuery = $derived((forcedPrefix + query).trimStart());
  const showGuide = $derived((isFocused || (mode === 'modal' && isOpen)) && query === "" && forcedPrefix === "");
  const showResults = $derived((isFocused || (mode === 'modal' && isOpen) || inline) && evaluatedQuery.length > 0);

  // Flattened results for keyboard navigation
  const flattenedResults = $derived([
    ...results.settings.map(r => ({ ...r, type: 'setting' })),
    ...results.library.artists.map(r => ({ ...r, type: 'artist' })),
    ...results.library.albums.map(r => ({ ...r, type: 'album' })),
    ...results.library.tracks.map(r => ({ ...r, type: 'track' })),
    ...results.plugins.map(r => ({ ...r, type: 'plugin' })),
    ...results.external.map(r => ({ ...r, type: 'external' }))
  ]);

  // ── Token Search Parser ────────────────────────────────────────────────
  function parseInput(rawQuery) {
    let cleanQuery = rawQuery;
    let pluginFilter = null;
    let settingsContext = false;

    // 1. Intercept ?help token
    if (rawQuery.trim().toLowerCase() === "?help") {
      showHelpBooklet = true;
      query = "";
      return { cleanQuery: "", pluginFilter: null, settingsContext: false };
    }

    // 2. Intercept @plugin_name token
    const pluginMatch = rawQuery.match(/^@([a-zA-Z0-9_\-\.]+)\s*(.*)/);
    if (pluginMatch) {
      const pluginCandidate = pluginMatch[1];
      const allPluginsList = Object.values($plugins?.items ?? []);
      const isKnown = allPluginsList.some(p => p.name.toLowerCase() === pluginCandidate.toLowerCase() || String(p.id) === pluginCandidate);
      const common = ['spotify', 'tidal', 'plex', 'jellyfin', 'navidrome', 'slskd', 'soulseek'];
      
      if (isKnown || common.includes(pluginCandidate.toLowerCase())) {
        pluginFilter = pluginCandidate;
        cleanQuery = pluginMatch[2];
      }
    }

    // 3. Intercept #settings token
    const settingsMatch = rawQuery.match(/^#settings\s*(.*)/);
    if (settingsMatch) {
      settingsContext = true;
      cleanQuery = settingsMatch[1];
    }

    return { cleanQuery, pluginFilter, settingsContext };
  }

  // ── Search Handlers ───────────────────────────────────────────────────
  function applyPrefix(prefix) {
    query = prefix;
    inputRef?.focus();
  }

  function handleInput() {
    activeIndex = -1;
    clearTimeout(searchTimer);
    
    // Keystroke Token Parser
    const { cleanQuery, pluginFilter, settingsContext } = parseInput(evaluatedQuery);

    if (showHelpBooklet) return;

    if (!evaluatedQuery) {
      clearResults();
      return;
    }

    // Settings search (either via #settings, > prefix, or local fallback)
    if (settingsContext || evaluatedQuery.startsWith(">") || (!evaluatedQuery.match(/^[>!?#@]/) && !forcedPrefix)) {
      const searchTerm = settingsContext 
        ? cleanQuery.trim().toLowerCase() 
        : (evaluatedQuery.startsWith(">") ? evaluatedQuery.replace(/^>\s*/, '').toLowerCase() : evaluatedQuery.toLowerCase());
      
      if (searchTerm) {
        const lexiconMatches = Object.entries(settingsLexicon)
          .filter(([keyword, path]) => keyword.includes(searchTerm))
          .map(([keyword, path]) => path);

        results.settings = SETTINGS_ROUTES.filter(route => 
          route.label.toLowerCase().includes(searchTerm) ||
          lexiconMatches.includes(route.path)
        );
      } else {
        results.settings = SETTINGS_ROUTES;
      }
    } else {
      results.settings = [];
    }

    isSearching = true;
    searchTimer = setTimeout(async () => {
      await performSearch(cleanQuery, pluginFilter);
    }, 300);
  }

  async function performSearch(cleanQuery = null, pluginFilter = null) {
    if (activeSearchAbortController) {
      activeSearchAbortController.abort();
    }
    activeSearchAbortController = new AbortController();
    const signal = activeSearchAbortController.signal;

    try {
      const termToSearch = cleanQuery !== null ? cleanQuery : evaluatedQuery;
      const prefixMatch = termToSearch.match(/^([>!?#@])\s*(.*)/);
      const prefix = prefixMatch ? prefixMatch[1] : null;
      const term = prefixMatch ? prefixMatch[2] : termToSearch;

      if (!term.trim() && !prefix && !pluginFilter) {
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
            const termLower = term.trim().toLowerCase();
            const allPlugins = Object.values($plugins?.items ?? []);
            results.plugins = allPlugins.filter(p => 
              (p.name && p.name.toLowerCase().includes(termLower)) ||
              (p.id && String(p.id).toLowerCase().includes(termLower)) ||
              (p.description && p.description.toLowerCase().includes(termLower))
            );
        } else {
            results.plugins = Object.values($plugins?.items ?? []);
        }
        results.external = [];
        clearLibrary();
        results.settings = [];
      }
      else if (prefix === '?' || pluginFilter) {
        // Discovery search: append pluginFilter if token parser detected it
        if (term.trim() || pluginFilter) {
            let url = `/search/discovery?q=${encodeURIComponent(term)}`;
            if (pluginFilter) {
              url += `&plugins=${encodeURIComponent(pluginFilter)}`;
            }
            const res = await apiClient.get(url);
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
            const res = await apiClient.get(`/manager/search?q=${encodeURIComponent(term)}`);
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
            const res = await apiClient.get(`/manager/search?q=${encodeURIComponent(term)}&types=artists`);
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
                const res = await apiClient.get(`/manager/search?q=${encodeURIComponent(value)}&field=${encodeURIComponent(key)}`);
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
            const csrfToken = getCookie('echo_csrf');
            const headers = {};
            if (csrfToken) {
                headers['X-Echo-CSRF'] = csrfToken;
            }

            clearLibrary();
            results.external = [];

            const response = await apiClient.get(`/v1/core/search/?q=${encodeURIComponent(term)}&types=tracks,albums,artists`);

            if (!response.ok) {
                throw new Error(`Search failed: ${response.statusText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let isDone = false;

            while (!isDone) {
                const { value, done } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const dataStr = line.slice(6).trim();
                        if (dataStr) {
                            try {
                                const chunk = JSON.parse(dataStr);
                                if (chunk.status === 'done') {
                                    isDone = true;
                                    break;
                                }
                                appendStreamChunk(chunk);
                            } catch (e) {
                                console.error("Failed to parse SSE chunk:", e);
                            }
                        }
                    }
                }
            }
        } else {
            clearLibrary();
            results.external = [];
        }
        results.plugins = [];
      }
    } catch (err) {
      console.error("OmniSearch performSearch error:", err);
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

  // ── Keyboard / Select Handlers ────────────────────────────────────────
  function handleKeydown(e) {
    if (e.key === 'Escape') {
      if (!inline && mode === 'modal') {
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
      } else if (inline) {
        performSearch();
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

  async function handleAction(item, action) {
    try {
      if (action === 'play' && item.source === 'local') {
        player.play(item);
        if (!inline) {
          closeModal();
          inputRef?.blur();
          clearResults();
        }
        return;
      }
      
      const response = await apiClient.post('/search/route', { item, action, target: 'default' });
      if (action === 'play' && response.data?.track) {
        player.play(response.data.track);
        if (!inline) {
          closeModal();
          inputRef?.blur();
          clearResults();
        }
      }
    } catch (err) {
      console.error('Search action failed:', err.message);
    }
  }

  function handleSelect(item, type) {
    if (type === 'setting') {
      goto(item.path);
    } else if (type === 'artist') {
      goto(`/library?artist_id=${item.id}`);
    } else if (type === 'album') {
      goto(`/library?artist_id=${item.artist_id}&highlight_album=${item.id}`);
    } else if (type === 'track') {
      goto(`/library?artist_id=${item.artist_id}&highlight_track=${item.id}`);
    } else if (type === 'plugin') {
      goto(`/settings/plugin-store`);
    }

    if (onselect) onselect({ item, type });
    
    if (!inline) {
      closeModal();
      inputRef?.blur();
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
      if (!inline && mode === 'modal') {
        if (isOpen) closeModal();
        else openModal();
      } else if (inputRef) {
        inputRef.focus();
      }
    }
  }

  onMount(() => {
    plugins.load().catch(() => {});
    if (typeof window !== 'undefined') window.addEventListener('keydown', handleGlobalKeydown);
    if (typeof window !== 'undefined') window.addEventListener('es-omnibar-toggle', openModal);
  });

  onDestroy(() => {
    if (typeof window !== 'undefined') window.removeEventListener('keydown', handleGlobalKeydown);
    if (typeof window !== 'undefined') window.removeEventListener('es-omnibar-toggle', openModal);
  });
</script>

{#if inline}
  <!-- ── STATIC INLINE SEARCH HERO (Search Page /search) ── -->
  <div class="search-hero">
    <div class="search-hero__content">
      <p class="eyebrow">Discovery</p>
      <h1 class="hero-title">
        <span class="hero-title__static">Unified</span>
        <span class="hero-title__typing" aria-live="polite">Search</span>
      </h1>

      <div class="search-input-wrapper">
        <div class="search-icon" aria-hidden="true">
          <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </div>
        <input
          bind:this={inputRef}
          type="text"
          bind:value={query}
          on:input={handleInput}
          on:keydown={handleKeydown}
          placeholder="Search for tracks, albums, or plugins..."
          class="hero-search-input"
          autocomplete="off"
          spellcheck="false"
        />

        <!-- Help Booklet Toggle -->
        <button 
          type="button" 
          class="booklet-btn" 
          title="Search Shortcuts Guide"
          on:click={() => showHelpBooklet = true}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="book-icon"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
        </button>

        {#if isSearching}
          <div class="search-spinner" aria-label="Searching…">
            <div class="spinner-ring"></div>
          </div>
        {:else}
          <button
            class="search-submit-btn"
            on:click={() => performSearch()}
          >
            Search
          </button>
        {/if}
      </div>

      <p class="shortcut-tip">
        Press <kbd>Ctrl+K</kbd> anywhere to search globally
      </p>
    </div>
  </div>

  {#if showResults}
    <div class="search-fallback mt-8">
      <div class="results-list">
        {#each Object.entries(results.library) as [libType, items]}
          {#if items.length > 0 && libType !== 'tracks'}
            <div class="result-section">
              <h3 class="section-title">Library {libType}</h3>
              <div class="section-items">
                {#each items as item}
                  <div class="result-card">
                    <div class="result-info">
                      <div class="result-main">
                        <div class="cover-placeholder" aria-hidden="true">
                          {libType === 'artists' ? '👤' : '💿'}
                        </div>
                        <div>
                          <strong class="result-title">{item.title || item.name || 'Unknown'}</strong>
                          <p class="result-artist">{item.artist_name || item.artist || ''}</p>
                        </div>
                      </div>
                    </div>
                    <div class="result-meta flex items-center gap-2">
                      {#if item.source === 'local'}
                        <span class="badge badge-primary">LOCAL LIBRARY</span>
                      {:else if item.plugin_id}
                        <span class="badge badge-secondary">{$plugins.find(p => p.id === item.plugin_id)?.name || 'Plugin'}</span>
                      {/if}
                      <div class="result-actions flex items-center">
                        <button class="action-btn play-btn flex items-center justify-center" title="Play" on:click={() => handleAction(item, 'play')}>
                          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
                        </button>
                      </div>
                    </div>
                  </div>
                {/each}
              </div>
            </div>
          {/if}
        {/each}

        {#if results.library.tracks.length > 0}
          <div class="result-section">
            <h3 class="section-title">Library Tracks</h3>
            <div class="section-items">
              {#each results.library.tracks as item}
                <div class="result-card">
                  <div class="result-info">
                    <div class="result-main">
                      {#if item.cover_art}
                        <img src={item.cover_art} alt={item.title} class="cover-art" />
                      {:else}
                        <div class="cover-placeholder" aria-hidden="true">🎵</div>
                      {/if}
                      <div>
                        <strong class="result-title">{item.title || item.name || 'Unknown'}</strong>
                        <p class="result-artist">
                          {#if item.artist_id}
                            <a href="/library?artist_id={item.artist_id}" class="artist-link">{item.artist || item.artist_name || ''}</a>
                          {:else}
                            <a href="/library?q={encodeURIComponent(item.artist || item.artist_name || '')}" class="artist-link">{item.artist || item.artist_name || ''}</a>
                          {/if}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div class="result-meta flex items-center gap-2">
                    {#if item.source === 'local'}
                      <span class="badge badge-primary">LOCAL LIBRARY</span>
                    {:else if item.plugin_id}
                      <span class="badge badge-secondary">{getPluginName(item.plugin_id)}</span>
                    {/if}
                    <div class="result-actions flex items-center">
                      <button class="action-btn play-btn flex items-center justify-center" title="Play" on:click|stopPropagation={() => handleAction(item, 'play')}>
                        <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
                      </button>
                      {#if item.artist_id}
                        <a href="/library?artist_id={item.artist_id}" class="library-btn-link">
                          <button class="action-btn library-btn" title="View in Library">
                            <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                          </button>
                        </a>
                      {/if}
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        {#if results.external.length > 0}
          <div class="result-section">
            <h3 class="section-title">Discovery Results</h3>
            <div class="section-items">
              {#each results.external as item}
                <div class="result-card">
                  <div class="result-info">
                    <div class="result-main">
                      {#if item.cover_art}
                        <img src={item.cover_art} alt={item.title} class="cover-art" />
                      {:else}
                        <div class="cover-placeholder" aria-hidden="true">🎵</div>
                      {/if}
                      <div>
                        <strong class="result-title">{item.title || item.name || 'Unknown'}</strong>
                        <p class="result-artist">
                          {#if item.artist_id}
                            <a href="/library?artist_id={item.artist_id}" class="artist-link">{item.artist || item.artist_name || ''}</a>
                          {:else}
                            <a href="/library?q={encodeURIComponent(item.artist || item.artist_name || '')}" class="artist-link">{item.artist || item.artist_name || ''}</a>
                          {/if}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div class="result-meta flex items-center gap-2">
                    {#if item.source === 'local'}
                      <span class="badge badge-primary">LOCAL LIBRARY</span>
                    {:else if item.plugin_id}
                      <span class="badge badge-secondary">{getPluginName(item.plugin_id)}</span>
                    {/if}
                    <div class="result-actions flex items-center">
                      {#if item.is_local}
                        <button class="action-btn play-btn flex items-center justify-center" title="Play" on:click|stopPropagation={() => handleAction(item, 'play')}>
                          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
                        </button>
                        {#if item.artist_id}
                          <a href="/library?artist_id={item.artist_id}" class="library-btn-link">
                            <button class="action-btn library-btn" title="View in Library">
                              <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                            </button>
                          </a>
                        {:else}
                          <a href="/library?q={encodeURIComponent(item.artist || item.artist_name || '')}" class="library-btn-link">
                            <button class="action-btn library-btn" title="View in Library">
                              <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                            </button>
                          </a>
                        {/if}
                      {:else}
                        <button class="action-btn download-btn" title="Download" on:click={() => handleAction(item, 'download')}>
                          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        </button>
                      {/if}
                    </div>
                  </div>
                </div>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}

{:else}
  <!-- ── ABSOLUTE / MODAL SEARCH BAR (Omnibar layout) ── -->
  <div class="relative w-full" on:focusout={(e) => { if (!e.currentTarget.contains(e.relatedTarget)) isFocused = false; }}>
    {#if mode === 'modal'}
      {#if isOpen}
        <div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-start justify-center pt-[15vh] px-4" on:click|self={closeModal}>
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
                class="w-full pl-14 pr-14 py-3 text-lg bg-transparent text-white focus:outline-none transition-all placeholder:text-muted/60"
              />

              <div class="absolute right-7 flex items-center gap-3">
                <button 
                  type="button" 
                  class="booklet-btn-compact" 
                  title="Search Shortcuts Guide"
                  on:click|stopPropagation={() => showHelpBooklet = true}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="book-icon"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
                </button>
                {#if isSearching}
                  <div class="w-5 h-5 border-2 border-white/10 border-t-accent rounded-full animate-spin"></div>
                {/if}
              </div>
            </div>

            <div class="max-h-[60vh] overflow-y-auto pb-2 custom-scrollbar">
              {#if showGuide}
                <div class="flex flex-col py-2">
                  <div class="text-muted text-[10px] font-bold px-5 py-2 uppercase tracking-widest opacity-60">Shortcuts</div>
                  {#each GUIDE_ITEMS as item}
                    <button class="flex items-center gap-4 px-5 py-3 text-left bg-transparent border-none cursor-pointer hover:bg-white/5 active:bg-white/10 transition-colors" on:click={() => applyPrefix(item.prefix)}>
                      <span class="bg-white/10 text-white font-mono px-2 py-0.5 rounded text-xs min-w-[24px] text-center border border-white/5">{item.label}</span>
                      <span class="text-slate-300 text-sm font-medium">{item.desc}</span>
                    </button>
                  {/each}
                </div>
              {:else if showResults}
                 <div class="results-content">
                    {#if !isSearching && flattenedResults.length === 0}
                      <div class="text-muted text-sm p-8 text-center">No results found for "{query}"</div>
                    {/if}

                    <!-- Combined rendering categories -->
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
                          <div 
                            class="w-full text-left px-5 py-3 text-sm text-slate-200 hover:bg-white/10 transition-colors border-none bg-transparent flex items-center justify-between group"
                            class:active-item={activeIndex === getFlattenedIndex('track', i)}
                          >
                            <button class="flex-1 text-left border-none bg-transparent cursor-pointer flex items-center gap-4 min-w-0" on:click={() => handleSelect(track, 'track')}>
                                {#if track.cover_art}
                                  <img src={track.cover_art} alt={track.title} class="w-10 h-10 rounded object-cover shadow-lg border border-white/5 group-hover:border-accent/40" class:active-border={activeIndex === getFlattenedIndex('track', i)} />
                                {:else}
                                  <div class="w-10 h-10 rounded bg-white/5 flex items-center justify-center text-xs border border-white/5 group-hover:border-accent/40" class:active-border={activeIndex === getFlattenedIndex('track', i)}>🎵</div>
                                {/if}
                                <div class="flex flex-col min-w-0 flex-1">
                                  <span class="font-medium truncate group-hover:text-accent transition-colors" class:active-text={activeIndex === getFlattenedIndex('track', i)}>{track.title || track.name}</span>
                                  <span class="text-xs text-muted truncate">{track.artist || track.artist_name || ''}</span>
                                  <span class="text-[9px] text-muted flex gap-1 mt-1">
                                    <span class="bg-white/5 px-1.5 py-0.5 rounded border border-white/5 font-mono uppercase tracking-tighter">{track.source === 'local' ? 'Local Library' : (track.source || 'Local Library')}</span>
                                    <span class="bg-white/5 px-1.5 py-0.5 rounded border border-white/5 font-mono uppercase tracking-tighter">{track.plugin || 'plex'}</span>
                                  </span>
                                </div>
                            </button>
                            
                            <div class="flex items-center gap-2">
                              <button class="px-3 py-1.5 text-[10px] font-bold bg-accent text-black rounded hover:scale-105 active:scale-95 transition-all flex items-center gap-1 border-none cursor-pointer" on:click|stopPropagation={() => handleAction(track, 'play')}>
                                ▶️ Play
                              </button>
                              {#if track.artist_id}
                                <a href="/library?artist_id={track.artist_id}" class="no-underline">
                                  <button class="px-3 py-1.5 text-[10px] font-bold bg-white/10 text-white border border-white/10 rounded hover:bg-white/20 transition-all cursor-pointer">
                                    📁 View
                                  </button>
                                </a>
                              {/if}
                            </div>
                          </div>
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
                                    {#each ext.sources || [] as src}
                                      <span class="bg-white/5 px-1.5 py-0.5 rounded border border-white/5 font-mono uppercase tracking-tighter">{src}</span>
                                    {/each}
                                  </span>
                                </div>
                            </button>
                            
                            {#if ext.ownership_state === 'missing'}
                              <button class="ml-4 px-4 py-2 text-[11px] font-bold bg-accent text-black rounded-lg hover:scale-105 active:scale-95 transition-all shadow-[0_0_15px_rgba(15,239,136,0.3)] flex items-center gap-1.5 border-none cursor-pointer" on:click|stopPropagation={() => handleAction(ext, 'download')}>
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
      <!-- Compact inline layout (e.g. Header bar) -->
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
          class="w-full pl-10 pr-14 py-2.5 text-sm bg-surface border border-glass-border rounded-global text-white focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/50 transition-all placeholder:text-muted/50"
        />

        <div class="absolute right-3 flex items-center gap-2">
          <button 
            type="button" 
            class="booklet-btn-compact" 
            title="Search Shortcuts Guide"
            on:click|stopPropagation={() => showHelpBooklet = true}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="book-icon"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
          </button>
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
        <div class="absolute top-full left-0 right-0 mt-2 bg-surface border border-glass-border shadow-2xl rounded-global overflow-visible max-h-[60vh] backdrop-blur-md pb-2 custom-scrollbar">
          {#if !isSearching && flattenedResults.length === 0}
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
                <div 
                  class="w-full track-row group hover:bg-white/5 rounded-md px-3 py-2 grid grid-cols-[40px_1fr_60px_auto] items-center gap-2 transition-colors cursor-pointer relative"
                  on:click={() => handleSelect(track, 'track')}
                  role="button"
                  tabindex="0"
                  on:keydown={(e) => e.key === 'Enter' && handleSelect(track, 'track')}
                >
                  <span class="text-gray-500 text-xs font-mono">{track.track_number || '-'}</span>
                  <span class="text-white text-sm font-medium truncate">{track.title} <span class="text-xs text-muted ml-1">— {track.artist_name || ''}</span></span>
                  <span class="text-gray-500 text-xs font-mono text-right">{track.duration ? formatDuration(track.duration) : '-:--'}</span>

                  <div class="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                          class="p-1.5 rounded-full hover:bg-blue-500/20 text-blue-400 transition-colors active:scale-95 border-none bg-transparent cursor-pointer flex items-center justify-center"
                          on:click|stopPropagation={() => handleAction(track, 'play')}
                          title="Play"
                      >
                          <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>
                      </button>

                      <div class="relative menu-container">
                          <button
                              class="p-1.5 rounded-full hover:bg-gray-700 text-gray-400 hover:text-white transition-colors active:scale-95 border-none bg-transparent cursor-pointer flex items-center justify-center"
                              on:click|stopPropagation={() => {}} 
                              title="Options"
                          >
                              <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/></svg>
                          </button>
                      </div>
                  </div>
                </div>
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
                          {#each ext.sources || [] as src}
                            <span class="bg-white/5 px-1 py-0.5 rounded">{src}</span>
                          {/each}
                        </span>
                      </div>
                  </button>
                  
                  {#if ext.ownership_state === 'missing'}
                    <button class="ml-4 px-3 py-1.5 text-[10px] font-bold bg-accent text-black rounded hover:scale-105 active:scale-95 transition-all shadow-lg flex items-center gap-1 border-none cursor-pointer" on:click|stopPropagation={() => handleAction(ext, 'download')}>
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
{/if}

<!-- ── SHORTCUTS BOOKLET MODAL ── -->
{#if showHelpBooklet}
  <div class="fixed inset-0 bg-black/80 backdrop-blur-md z-[200] flex items-center justify-center p-4" on:click|self={() => showHelpBooklet = false}>
    <div class="w-full max-w-lg bg-surface border border-glass-border shadow-2xl rounded-2xl overflow-hidden animate-in fade-in zoom-in duration-200 p-6 relative">
      <button 
        type="button" 
        class="absolute top-4 right-4 text-muted hover:text-white bg-transparent border-none cursor-pointer text-lg"
        on:click={() => showHelpBooklet = false}
      >
        ✕
      </button>

      <h3 class="text-xl font-bold text-white mb-4 flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-accent"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
        Search Shortcuts Guide
      </h3>
      
      <p class="text-slate-300 text-sm mb-6">
        Power up your searches with advanced tokens. Type these prefixes at the start of your query to filter instantly:
      </p>

      <div class="flex flex-col gap-4 mb-6">
        <!-- Legacy Shortcut Tokens -->
        <div class="bg-black/20 border border-white/5 p-3.5 rounded-xl">
          <div class="flex items-center justify-between mb-1.5">
            <span class="bg-accent/10 text-accent font-mono text-xs px-2 py-0.5 rounded border border-accent/20">&gt;</span>
            <span class="text-xs text-muted">Search Settings & Commands</span>
          </div>
          <p class="text-slate-300 text-xs font-medium">Example: <code class="text-white bg-white/5 px-1.5 py-0.5 rounded">&gt; preferences</code></p>
        </div>

        <div class="bg-black/20 border border-white/5 p-3.5 rounded-xl">
          <div class="flex items-center justify-between mb-1.5">
            <span class="bg-accent/10 text-accent font-mono text-xs px-2 py-0.5 rounded border border-accent/20">!</span>
            <span class="text-xs text-muted flex items-center gap-2">
              Search & Manage Plugins
              <button 
                type="button" 
                class="text-[10px] text-accent hover:underline bg-transparent border-none cursor-pointer font-semibold p-0"
                on:click|stopPropagation={() => { showHelpBooklet = false; goto('/settings/plugin-store'); }}
              >
                Open Plugin Store
              </button>
            </span>
          </div>
          <p class="text-slate-300 text-xs font-medium">Example: <code class="text-white bg-white/5 px-1.5 py-0.5 rounded">! spotify</code></p>
        </div>

        <div class="bg-black/20 border border-white/5 p-3.5 rounded-xl">
          <div class="flex items-center justify-between mb-1.5">
            <span class="bg-accent/10 text-accent font-mono text-xs px-2 py-0.5 rounded border border-accent/20">#</span>
            <span class="text-xs text-muted">Search Library Only</span>
          </div>
          <p class="text-slate-300 text-xs font-medium">Example: <code class="text-white bg-white/5 px-1.5 py-0.5 rounded"># abbey road</code></p>
        </div>

        <div class="bg-black/20 border border-white/5 p-3.5 rounded-xl">
          <div class="flex items-center justify-between mb-1.5">
            <span class="bg-accent/10 text-accent font-mono text-xs px-2 py-0.5 rounded border border-accent/20">@</span>
            <span class="text-xs text-muted">Search Artists Only</span>
          </div>
          <p class="text-slate-300 text-xs font-medium">Example: <code class="text-white bg-white/5 px-1.5 py-0.5 rounded">@ beatles</code></p>
        </div>

        <!-- Advanced Tokens -->
        <div class="bg-black/20 border border-white/5 p-3.5 rounded-xl">
          <div class="flex items-center justify-between mb-1.5">
            <span class="bg-accent/10 text-accent font-mono text-xs px-2 py-0.5 rounded border border-accent/20">@plugin</span>
            <span class="text-xs text-muted">Filter by specific plugin</span>
          </div>
          <p class="text-slate-300 text-xs font-medium">Example: <code class="text-white bg-white/5 px-1.5 py-0.5 rounded">@spotify Let It Be</code></p>
        </div>

        <div class="bg-black/20 border border-white/5 p-3.5 rounded-xl">
          <div class="flex items-center justify-between mb-1.5">
            <span class="bg-accent/10 text-accent font-mono text-xs px-2 py-0.5 rounded border border-accent/20">#settings</span>
            <span class="text-xs text-muted">Search application settings & pages</span>
          </div>
          <p class="text-slate-300 text-xs font-medium">Example: <code class="text-white bg-white/5 px-1.5 py-0.5 rounded">#settings preferences</code></p>
        </div>

        <div class="bg-black/20 border border-white/5 p-3.5 rounded-xl">
          <div class="flex items-center justify-between mb-1.5">
            <span class="bg-accent/10 text-accent font-mono text-xs px-2 py-0.5 rounded border border-accent/20">?help</span>
            <span class="text-xs text-muted">Open this help booklet</span>
          </div>
          <p class="text-slate-300 text-xs font-medium">Example: <code class="text-white bg-white/5 px-1.5 py-0.5 rounded">?help</code></p>
        </div>
      </div>

      <button 
        type="button" 
        class="btn btn-primary w-full mt-4"
        on:click={() => showHelpBooklet = false}
      >
        Got it!
      </button>
    </div>
  </div>
{/if}

<style>
  /* ── Hero section (inline only) ── */
  .search-hero {
    background: linear-gradient(135deg, rgba(20, 184, 166, 0.05) 0%, rgba(14, 165, 233, 0.04) 100%);
    border: 1px solid rgba(255, 255, 255, 0.03);
    border-radius: 24px;
    padding: 56px 40px 48px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }
  .search-hero::before {
    content: '';
    position: absolute; inset: 0;
    background: radial-gradient(circle at 50% 0%, rgba(20, 184, 166, 0.04) 0%, transparent 70%);
    pointer-events: none;
  }
  .search-hero__content { position: relative; z-index: 1; max-width: 760px; margin: 0 auto; }

  .eyebrow {
    font-size: 10px; font-weight: 900; letter-spacing: 0.3em;
    text-transform: uppercase; color: var(--color-primary, #1db954);
    margin: 0 0 12px;
  }

  .hero-title {
    font-size: clamp(32px, 6vw, 52px);
    font-weight: 900; letter-spacing: -1px;
    line-height: 1.1; margin: 0 0 32px; display: flex;
    align-items: baseline; justify-content: center; gap: 12px;
  }
  .hero-title__static {
    background: linear-gradient(to right, #fff, #94a3b8);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .hero-title__typing {
    color: var(--color-primary, #1db954);
    border-right: 3px solid var(--color-primary, #1db954);
    padding-right: 4px;
    animation: blink-cursor 1s step-end infinite;
  }
  @keyframes blink-cursor {
    0%, 100% { border-color: var(--color-primary, #1db954); }
    50%       { border-color: transparent; }
  }

  .search-input-wrapper {
    display: flex; align-items: center;
    background: rgba(6, 6, 10, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px; padding: 6px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.35);
    transition: border-color 0.25s, box-shadow 0.25s, transform 0.25s;
  }
  .search-input-wrapper:focus-within {
    border-color: var(--color-primary, #1db954);
    box-shadow: 0 0 0 3px rgba(29, 185, 84, 0.12), 0 10px 40px rgba(0,0,0,0.35);
    transform: translateY(-2px);
  }
  .search-icon { padding: 0 14px; color: #64748b; transition: color 0.25s; }
  .search-input-wrapper:focus-within .search-icon { color: var(--color-primary, #1db954); }

  .hero-search-input {
    flex: 1; background: transparent; border: none;
    color: #fff; font-size: 17px; padding: 12px 0; outline: none;
  }
  .hero-search-input::placeholder { color: rgba(255,255,255,0.25); }

  .search-submit-btn {
    background: var(--color-primary, #1db954); color: #000;
    font-weight: 800; font-size: 14px;
    padding: 12px 22px; border-radius: 11px;
    border: none; cursor: pointer;
    transition: filter 0.2s, transform 0.15s;
    white-space: nowrap;
  }
  .search-submit-btn:hover  { filter: brightness(1.1); }
  .search-submit-btn:active { transform: scale(0.97); }

  .search-spinner { padding: 8px 14px; }
  .spinner-ring {
    width: 22px; height: 22px;
    border: 2px solid rgba(255,255,255,0.1);
    border-top-color: var(--color-primary, #1db954);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .shortcut-tip { margin-top: 18px; font-size: 12px; color: #64748b; }
  .shortcut-tip kbd {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 4px; padding: 2px 7px;
    color: #fff; margin: 0 3px; font-size: 11px;
  }

  /* Booklet Buttons */
  .booklet-btn {
    background: transparent;
    border: none;
    cursor: pointer;
    color: #64748b;
    padding: 8px 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.2s;
  }
  .booklet-btn:hover {
    color: var(--color-primary, #1db954);
  }
  .booklet-btn-compact {
    background: transparent;
    border: none;
    cursor: pointer;
    color: rgba(255,255,255,0.4);
    padding: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.2s;
  }
  .booklet-btn-compact:hover {
    color: var(--accent, #0fef88);
  }

  /* Results rendering classes */
  .results-list { display: flex; flex-direction: column; gap: 36px; }
  .result-section { display: flex; flex-direction: column; gap: 16px; }
  .section-title {
    font-size: 11px; font-weight: 900; text-transform: uppercase;
    letter-spacing: 0.15em; color: var(--color-primary, #1db954); opacity: 0.75;
    margin: 0;
  }
  .section-items { display: flex; flex-direction: column; gap: 8px; }
  .result-card {
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 16px;
    background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.04);
    border-radius: 14px; transition: background 0.2s, border-color 0.2s, transform 0.15s;
  }
  .result-card:hover { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.09); transform: scale(1.005); }
  .result-info, .result-main { display: flex; align-items: center; }
  .result-main { gap: 12px; }
  .cover-art { width: 44px; height: 44px; border-radius: 8px; object-fit: cover; flex-shrink: 0; }
  .cover-placeholder { width: 44px; height: 44px; border-radius: 8px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
  .result-title { display: block; font-weight: 700; font-size: 14px; color: #fff; }
  .result-artist { margin: 2px 0 0; font-size: 12px; color: rgba(255,255,255,0.4); }
  .result-meta { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
  
  .plugin-badge { font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(255,255,255,0.35); background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); padding: 3px 8px; border-radius: 6px; }
  .plugin-badge.clickable { cursor: pointer; transition: all 0.2s; }
  .plugin-badge.clickable:hover { color: #fff; background: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.15); }
  .plugin-link { text-decoration: none; }

  .source-badge {
    font-size: 10px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--color-primary, #1db954);
    background: rgba(29, 185, 84, 0.08);
    border: 1px solid rgba(29, 185, 84, 0.15);
    padding: 3px 8px;
    border-radius: 6px;
  }
  .artist-link {
    color: rgba(255,255,255,0.4);
    text-decoration: none;
    transition: color 0.2s;
  }
  .artist-link:hover {
    color: var(--color-primary, #1db954);
    text-decoration: underline;
  }
  .library-btn-link {
    display: inline-block;
    text-decoration: none;
    padding: 0;
    margin: 0;
    background: none;
    border: none;
  }
  .library-btn {
    background: rgba(255, 255, 255, 0.05);
    color: #fff;
  }
  .library-btn:hover {
    background: rgba(14, 165, 233, 0.2);
    border-color: rgba(14, 165, 233, 0.4);
    color: #0ea5e9;
  }

  .result-actions { display: flex; gap: 6px; }
  .action-btn { width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.18s; border: none; }
  .play-btn     { background: rgba(255,255,255,0.05); color: #fff; }
  .play-btn:hover { background: var(--color-primary, #1db954); color: #000; }
  .download-btn { background: var(--color-primary, #1db954); color: #000; }
  .download-btn:hover { filter: brightness(1.1); transform: scale(1.08); }

  .custom-scrollbar::-webkit-scrollbar { width: 6px; }
  .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
  .custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.1); border-radius: 10px; }
  .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.2); }

  .active-item { background: rgba(255, 255, 255, 0.08) !important; }
  .active-border { border-color: var(--accent) !important; box-shadow: 0 0 10px rgba(15, 239, 136, 0.2); }
  .active-text { color: var(--accent) !important; }

  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  @keyframes zoomIn { from { transform: scale(0.95); opacity: 0; } to { transform: scale(1); opacity: 1; } }
  .animate-in { animation: fadeIn 0.2s ease-out; }
  .fade-in { opacity: 1; }
  .zoom-in { animation: zoomIn 0.2s ease-out; }
</style>
