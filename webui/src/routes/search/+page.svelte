<script>
  import { onMount } from 'svelte';
  import { providers, searchProviders } from '../../stores/providers';
  import apiClient from '../../api/client';

  let results = $state([]);
  let searching = $state(false);
  let error = $state('');
  let lastSearchedQuery = $state('');

  const groupedResults = $derived(results.reduce((acc, item) => {
    const t = item.type || 'unknown';
    if (!acc[t]) acc[t] = [];
    acc[t].push(item);
    return acc;
  }, {}));

  async function handleAction(item, action) {
    try {
      await apiClient.post('/search/route', {
        item,
        action,
        target: 'default'
      });
      alert(`${action} initiated for ${item.title}`);
    } catch (err) {
      alert(`Action failed: ${err.response?.data?.error || err.message}`);
    }
  }

  let searchQuery = $state('');
  let searchedOnce = $state(false);

  async function handleSearch() {
    if (!searchQuery.trim()) return;
    searching = true;
    error = '';
    lastSearchedQuery = searchQuery;
    searchedOnce = true;
    
    try {
      // Use the discovery endpoint for broad web + library search
      const res = await apiClient.get(`/search/discovery?q=${encodeURIComponent(searchQuery)}`);
      results = res.data?.results || [];
    } catch (err) {
      error = err.response?.data?.error || err.message;
      results = [];
    } finally {
      searching = false;
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') handleSearch();
  }

  onMount(() => {
    providers.load();
  });
</script>

<svelte:head>
  <title>Search • EchoSync</title>
</svelte:head>

<section class="page">
  <div class="search-hero">
    <div class="search-hero__content">
      <p class="eyebrow">Discovery</p>
      <h1>Unified Search</h1>
      
      <div class="search-input-wrapper group">
        <div class="search-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </div>
        <input 
          type="text" 
          bind:value={searchQuery} 
          on:keydown={handleKeydown}
          placeholder="Search for tracks, albums, or artists..." 
          class="hero-search-input"
        />
        <button class="search-submit-btn" on:click={handleSearch}>
          Search
        </button>
      </div>

      <div class="shortcut-tip">
        <span>Tip: Press <kbd>Ctrl+K</kbd> anywhere to search globally</span>
      </div>
    </div>
  </div>

  <div class="search-layout">
    <main class="search-main">
      {#if error}
        <div class="error-card">
          <p>{error}</p>
        </div>
      {/if}

      <div class="results-container">
        {#if searching}
          <div class="loading-state">
            <div class="spinner"></div>
            <p>Searching across services...</p>
          </div>
        {:else if results.length > 0}
          <div class="results-list">
            {#each Object.entries(groupedResults) as [type, items]}
              <div class="result-section">
                <h3 class="section-title capitalize">{type}</h3>
                <div class="section-items">
                  {#each items as item}
                    <div class="result-card card">
                      <div class="result-info">
                        <div class="result-main">
                          {#if item.cover_art}
                            <img src={item.cover_art} alt={item.title} class="w-12 h-12 rounded object-cover mr-3 shadow-md" />
                          {:else}
                            <div class="w-12 h-12 rounded bg-white/5 flex items-center justify-center mr-3 border border-white/5">🎵</div>
                          {/if}
                          <div>
                            <strong class="block text-white">{item.title || item.name || 'Unknown'}</strong>
                            <p class="text-xs text-muted mt-0.5">{item.artist || item.artist_name || ''}</p>
                          </div>
                        </div>
                      </div>
                      <div class="result-meta flex items-center gap-4">
                         <span class="text-[10px] uppercase tracking-widest font-bold text-muted bg-white/5 px-2 py-1 rounded border border-white/5">
                           {item.provider}
                         </span>
                        <div class="result-actions">
                          {#if item.is_local || item.ownership_state === 'owned'}
                            <button class="action-btn play-btn" title="Play" on:click={() => handleAction(item, 'play')}>
                              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
                            </button>
                          {:else}
                            <button class="action-btn download-btn" title="Download" on:click={() => handleAction(item, 'download')}>
                              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            </button>
                          {/if}
                        </div>
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        {:else if searchedOnce && !searching}
          <div class="empty-state">
            <div class="empty-icon">🔍</div>
            <p>No results found for "{lastSearchedQuery}"</p>
            <p class="text-xs mt-2 opacity-60">Try different keywords or check your provider settings.</p>
          </div>
        {:else if !searching}
           <div class="initial-state">
             <div class="search-graphic">
               <div class="circle circle-1"></div>
               <div class="circle circle-2"></div>
               <div class="circle circle-3"></div>
               <div class="search-logo">EchoSync</div>
             </div>
             <p class="text-xl font-medium text-white/80">Enter a query to explore the musical multiverse</p>
             <p class="text-sm text-muted/60 mt-2 max-w-md text-center">Search results will appear here from all your configured streaming and discovery providers.</p>
           </div>
        {/if}
      </div>
    </main>
  </div>
</section>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: 32px;
  }

  .search-hero {
    background: linear-gradient(135deg, rgba(20, 184, 166, 0.05) 0%, rgba(14, 165, 233, 0.05) 100%);
    border: 1px solid rgba(255, 255, 255, 0.03);
    border-radius: 24px;
    padding: 60px 40px;
    text-align: center;
    position: relative;
    overflow: hidden;
  }

  .search-hero::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at center, rgba(20, 184, 166, 0.03) 0%, transparent 70%);
    pointer-events: none;
  }

  .search-hero__content {
    position: relative;
    z-index: 1;
    max-width: 800px;
    margin: 0 auto;
  }

  .search-hero h1 {
    font-size: 48px;
    font-weight: 800;
    margin-bottom: 32px;
    letter-spacing: -1px;
    background: linear-gradient(to right, #fff, #94a3b8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .search-input-wrapper {
    position: relative;
    display: flex;
    align-items: center;
    background: rgba(10, 10, 15, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 6px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  }

  .search-input-wrapper:focus-within {
    border-color: var(--accent);
    box-shadow: 0 0 30px rgba(20, 184, 166, 0.15);
    transform: translateY(-2px);
  }

  .search-icon {
    padding: 0 16px;
    color: #64748b;
    transition: color 0.3s;
  }

  .search-input-wrapper:focus-within .search-icon {
    color: var(--accent);
  }

  .hero-search-input {
    flex: 1;
    background: transparent;
    border: none;
    color: #fff;
    font-size: 18px;
    padding: 12px 0;
    outline: none;
  }

  .search-submit-btn {
    background: var(--accent);
    color: #000;
    font-weight: 700;
    padding: 12px 24px;
    border-radius: 12px;
    border: none;
    cursor: pointer;
    transition: all 0.2s;
  }

  .search-submit-btn:hover {
    transform: scale(1.05);
    filter: brightness(1.1);
  }

  .shortcut-tip {
    margin-top: 20px;
    font-size: 12px;
    color: #64748b;
  }

  .shortcut-tip kbd {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 4px;
    padding: 2px 6px;
    color: #fff;
    margin: 0 4px;
  }

  .search-layout {
    max-width: 1000px;
    margin: 0 auto;
    width: 100%;
  }

  .result-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 16px;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 14px;
    transition: all 0.2s;
  }

  .result-card:hover {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(255, 255, 255, 0.1);
    transform: scale(1.01);
  }

  .action-btn {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s;
    border: none;
  }

  .play-btn {
    background: rgba(255, 255, 255, 0.05);
    color: #fff;
  }

  .play-btn:hover {
    background: var(--accent);
    color: #000;
  }

  .download-btn {
    background: var(--accent);
    color: #000;
  }

  .download-btn:hover {
    filter: brightness(1.1);
    transform: scale(1.1);
  }

  .initial-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 100px 20px;
    color: #94a3b8;
  }

  .search-graphic {
    position: relative;
    width: 120px;
    height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 40px;
  }

  .circle {
    position: absolute;
    border: 1px solid var(--accent);
    border-radius: 50%;
    opacity: 0.2;
    animation: pulse 4s infinite;
  }

  .circle-1 { width: 100%; height: 100%; animation-delay: 0s; }
  .circle-2 { width: 70%; height: 70%; animation-delay: 1s; }
  .circle-3 { width: 40%; height: 40%; animation-delay: 2s; }

  @keyframes pulse {
    0% { transform: scale(1); opacity: 0.2; }
    50% { transform: scale(1.2); opacity: 0.4; }
    100% { transform: scale(1); opacity: 0.2; }
  }

  .search-logo {
    font-weight: 900;
    font-size: 14px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--accent);
    text-shadow: 0 0 20px rgba(20, 184, 166, 0.4);
  }

  .results-list {
    display: flex;
    flex-direction: column;
    gap: 40px;
  }

  .result-section {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .section-title {
    font-size: 14px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--accent);
    opacity: 0.8;
  }

  .section-items {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .capitalize { text-transform: capitalize; }
  .muted { color: #64748b; }
</style>
