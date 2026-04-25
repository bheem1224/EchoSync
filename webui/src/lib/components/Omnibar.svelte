<script>
  import { onMount, tick } from 'svelte';
  import { goto } from '$app/navigation';

  let isOpen = false;
  let searchQuery = '';
  let selectedIndex = 0;
  let inputRef;
  let activeServer = 'Media Server';
  let searchResults = { artists: [], albums: [], tracks: [] };
  let isSearching = false;
  let searchTimer;

  const allActions = [
    { title: 'Dashboard', path: '/dashboard', icon: '🏠' },
    { title: 'Search', path: '/search', icon: '🔍' },
    { title: 'Library Manager', path: '/library/manager', icon: '📚' },
    { title: 'Review Queue', path: '/library/review-queue', icon: '📝' },
    { title: 'Sync Queue', path: '/sync', icon: '🔄' },
    { title: 'Settings: General', path: '/settings/system', icon: '⚙️' },
    { title: 'Settings: Preferences', path: '/settings/preferences', icon: '🎨' },
    { title: 'Settings: Metadata', path: '/settings/metadata', icon: '🏷️' },
    { title: 'Settings: Downloads', path: '/settings/downloads', icon: '⬇️' },
    { title: 'Settings: Music Services', path: '/settings/music-services', icon: '🎵' },
    { title: 'Settings: Download Clients', path: '/settings/download-clients', icon: '📥' },
    { title: 'Settings: Servers', path: '/settings/servers', icon: '🖥️' },
    { title: 'Settings: Plugin Store', path: '/settings/plugin-store', icon: '🧩' },
    { title: 'Settings: Background Jobs', path: '/settings/jobs', icon: '⏱️' },
    { title: 'Settings: Misc', path: '/settings/misc', icon: '🛠️' }
  ];

  $: filteredActions = allActions.filter(action =>
    action.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  $: isLibrarySearch = searchQuery.trim().length >= 2;
  $: libraryItems = isLibrarySearch
    ? [
        ...searchResults.artists.map(item => ({ kind: 'artist', item })),
        ...searchResults.albums.map(item => ({ kind: 'album', item })),
        ...searchResults.tracks.map(item => ({ kind: 'track', item })),
        { kind: 'external', item: { query: searchQuery } }
      ]
    : filteredActions;

  $: if (libraryItems.length > 0 && selectedIndex >= libraryItems.length) {
    selectedIndex = libraryItems.length - 1;
  }

  function itemGlobalIndex(type, idx) {
    if (type === 'artist') return idx;
    if (type === 'album') return searchResults.artists.length + idx;
    if (type === 'track') return searchResults.artists.length + searchResults.albums.length + idx;
    return 0;
  }

  function isSelected(index) {
    return index === selectedIndex ? 'bg-surface-hover text-accent border-l-2 border-accent' : 'text-primary hover:bg-surface-hover/50 border-l-2 border-transparent';
  }

  function handleToggleEvent() {
    isOpen = !isOpen;
    if (isOpen) {
      searchQuery = '';
      selectedIndex = 0;
      searchResults = { artists: [], albums: [], tracks: [] };
      tick().then(() => inputRef && inputRef.focus());
    }
  }

  onMount(() => {
    window.addEventListener('es-omnibar-toggle', handleToggleEvent);
    loadActiveServer();
    return () => {
      window.removeEventListener('es-omnibar-toggle', handleToggleEvent);
    };
  });

  async function loadActiveServer() {
    try {
      const response = await fetch('/api/media-server/active');
      if (response.ok) {
        const data = await response.json();
        if (data?.active_server) {
          activeServer = data.active_server;
        }
      }
    } catch (error) {
      console.error('Unable to load active media server:', error);
    }
  }

  async function performSearch() {
    if (!isLibrarySearch) {
      searchResults = { artists: [], albums: [], tracks: [] };
      return;
    }

    isSearching = true;
    try {
      const response = await fetch(`/api/manager/search?q=${encodeURIComponent(searchQuery)}`);
      if (response.ok) {
        searchResults = await response.json();
      } else {
        searchResults = { artists: [], albums: [], tracks: [] };
      }
    } catch (error) {
      console.error('Library search failed:', error);
      searchResults = { artists: [], albums: [], tracks: [] };
    } finally {
      isSearching = false;
    }
  }

  function handleInput() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(performSearch, 180);
  }

  function handleKeydown(e) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      isOpen = !isOpen;
      if (isOpen) {
        searchQuery = '';
        selectedIndex = 0;
        searchResults = { artists: [], albums: [], tracks: [] };
        tick().then(() => inputRef && inputRef.focus());
      }
    } else if (isOpen) {
      if (e.key === 'Escape') {
        e.preventDefault();
        isOpen = false;
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        selectedIndex = (selectedIndex + 1) % Math.max(libraryItems.length, 1);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        selectedIndex = (selectedIndex - 1 + Math.max(libraryItems.length, 1)) % Math.max(libraryItems.length, 1);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        executeAction();
      }
    }
  }

  function executeAction() {
    if (libraryItems.length === 0) {
      return;
    }

    const activeItem = libraryItems[selectedIndex];
    if (!activeItem) {
      return;
    }

    if (!isLibrarySearch) {
      isOpen = false;
      goto(activeItem.path);
      return;
    }

    selectResult(activeItem);
  }

  function selectResult(entry) {
    if (entry.kind === 'external') {
      dispatchDownloadIntent();
      return;
    }

    const item = entry.item;

    if (entry.kind === 'artist') {
      goto(`/library?artist_id=${item.id}`);
    } else if (entry.kind === 'album') {
      const query = item.artist_id ? `/library?artist_id=${item.artist_id}&highlight_album=${item.id}` : `/library?highlight_album=${item.id}`;
      goto(query);
    } else if (entry.kind === 'track') {
      const query = item.artist_id ? `/library?artist_id=${item.artist_id}&highlight_track=${item.id}` : `/library?highlight_track=${item.id}`;
      goto(query);
    }

    isOpen = false;
  }

  function dispatchDownloadIntent() {
    window.dispatchEvent(new CustomEvent('DOWNLOAD_INTENT', {
      detail: {
        query: searchQuery,
        provider: activeServer,
        source: 'omnibar'
      }
    }));
    isOpen = false;
  }

  function handleOverlayClick(e) {
    if (e.target === e.currentTarget) {
      isOpen = false;
    }
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div
    class="fixed inset-0 bg-black/50 backdrop-blur-sm z-[9999] flex justify-center items-start pt-[15vh] px-4 animate-fade-in"
    on:click={handleOverlayClick}
  >
    <div class="w-[90vw] max-w-2xl bg-surface border border-glass-border rounded-global shadow-2xl overflow-hidden flex flex-col transform transition-all animate-scale-in">
      <div class="flex items-center px-4 border-b border-glass-border">
        <span class="text-secondary text-xl mr-2">🔍</span>
        <input
          bind:this={inputRef}
          bind:value={searchQuery}
          type="text"
          placeholder="Type a command or search..."
          on:input={handleInput}
          class="flex-1 py-4 bg-transparent outline-none text-primary text-lg placeholder-secondary"
        />
        <div class="text-xs text-secondary bg-surface-hover px-2 py-1 rounded border border-glass-border flex items-center gap-1 font-mono">
          <span>ESC</span>
        </div>
      </div>

      {#if isLibrarySearch}
        <div class="max-h-[60vh] overflow-y-auto py-2 space-y-4 px-2">
          {#if isSearching}
            <div class="py-12 px-4 text-center text-secondary">Searching library…</div>
          {:else}
            {#if searchResults.artists.length || searchResults.albums.length || searchResults.tracks.length}
              {#if searchResults.artists.length}
                <div class="space-y-2">
                  <div class="px-4 text-xs uppercase tracking-[0.25em] text-secondary">Artists</div>
                  {#each searchResults.artists as artist, i}
                    <button
                      class="w-full text-left px-4 py-3 rounded-lg transition-colors focus:outline-none {isSelected(itemGlobalIndex('artist', i))}"
                      on:click={() => selectResult({ kind: 'artist', item: artist })}
                      on:mousemove={() => selectedIndex = itemGlobalIndex('artist', i)}
                    >
                      <div class="font-medium text-primary">{artist.name}</div>
                    </button>
                  {/each}
                </div>
              {/if}

              {#if searchResults.albums.length}
                <div class="space-y-2">
                  <div class="px-4 text-xs uppercase tracking-[0.25em] text-secondary">Albums</div>
                  {#each searchResults.albums as album, i}
                    <button
                      class="w-full text-left px-4 py-3 rounded-lg transition-colors focus:outline-none {isSelected(itemGlobalIndex('album', i))}"
                      on:click={() => selectResult({ kind: 'album', item: album })}
                      on:mousemove={() => selectedIndex = itemGlobalIndex('album', i)}
                    >
                      <div class="font-medium text-primary">{album.title}</div>
                      <div class="text-sm text-secondary">{album.artist_name}</div>
                    </button>
                  {/each}
                </div>
              {/if}

              {#if searchResults.tracks.length}
                <div class="space-y-2">
                  <div class="px-4 text-xs uppercase tracking-[0.25em] text-secondary">Tracks</div>
                  {#each searchResults.tracks as track, i}
                    <button
                      class="w-full text-left px-4 py-3 rounded-lg transition-colors focus:outline-none {isSelected(itemGlobalIndex('track', i))}"
                      on:click={() => selectResult({ kind: 'track', item: track })}
                      on:mousemove={() => selectedIndex = itemGlobalIndex('track', i)}
                    >
                      <div class="font-medium text-primary">{track.title}</div>
                      <div class="text-sm text-secondary">{track.artist_name} — {track.album_title}</div>
                    </button>
                  {/each}
                </div>
              {/if}
            {:else}
              <div class="py-12 px-4 text-center text-secondary">No library results for "{searchQuery}".</div>
            {/if}
          {/if}

          <div class="px-4 py-3 border-t border-glass-border">
            <div class="text-xs uppercase tracking-[0.25em] text-secondary mb-2">External</div>
            <button
              class="w-full text-left px-4 py-3 rounded-lg bg-surface-hover border border-glass-border text-primary hover:border-accent/40 transition-colors {isSelected(searchResults.artists.length + searchResults.albums.length + searchResults.tracks.length)}"
              on:click={dispatchDownloadIntent}
              on:mousemove={() => selectedIndex = searchResults.artists.length + searchResults.albums.length + searchResults.tracks.length}
            >
              Search {activeServer} for "{searchQuery}"
            </button>
          </div>
        </div>
      {:else}
        <div class="max-h-[60vh] overflow-y-auto py-2">
          {#if filteredActions.length > 0}
            {#each filteredActions as action, i}
              <button
                class="w-full text-left px-4 py-3 flex items-center gap-3 transition-colors focus:outline-none {i === selectedIndex ? 'bg-surface-hover text-accent border-l-2 border-accent' : 'text-primary hover:bg-surface-hover/50 border-l-2 border-transparent'} active:scale-95"
                on:click={() => handleClick(i)}
                on:mousemove={() => selectedIndex = i}
              >
                <span class="text-xl">{action.icon}</span>
                <span class="font-medium flex-1">{action.title}</span>
                {#if i === selectedIndex}
                  <span class="text-xs text-accent/70 font-mono">⏎</span>
                {/if}
              </button>
            {/each}
          {:else}
            <div class="py-12 px-4 text-center text-secondary">No commands match "{searchQuery}".</div>
          {/if}
        </div>
      {/if}

      <div class="px-4 py-2 border-t border-glass-border bg-black/20 flex justify-between items-center text-xs text-secondary">
        <div class="flex items-center gap-4">
          <span class="flex items-center gap-1"><kbd class="bg-surface-hover border border-glass-border rounded px-1 font-mono">↑</kbd><kbd class="bg-surface-hover border border-glass-border rounded px-1 font-mono">↓</kbd> to navigate</span>
          <span class="flex items-center gap-1"><kbd class="bg-surface-hover border border-glass-border rounded px-1 font-mono">↵</kbd> to select</span>
        </div>
        <span>EchoSync Omnibar</span>
      </div>
    </div>
  </div>
{/if}

<style>
  .animate-fade-in {
    animation: fadeIn 0.15s ease-out forwards;
  }
  .animate-scale-in {
    animation: scaleIn 0.1s ease-out forwards;
    transform-origin: top center;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes scaleIn {
    from { opacity: 0; transform: scale(0.98); }
    to { opacity: 1; transform: scale(1); }
  }

  .selected {
    background: rgba(14, 165, 233, 0.08);
  }

  .result-button {
    width: 100%;
    text-align: left;
  }

  .result-button:hover,
  .result-button:focus {
    background: rgba(255,255,255,0.04);
  }

  /* Styling scrollbar for glass effect */
  ::-webkit-scrollbar {
    width: 6px;
  }
  ::-webkit-scrollbar-track {
    background: transparent;
  }
  ::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 10px;
  }
  ::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.2);
  }
</style>

