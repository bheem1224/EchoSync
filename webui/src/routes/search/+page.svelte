<script>
  import { onMount } from 'svelte';
  import { providers, searchProviders } from '../../stores/providers';
  import apiClient from '../../api/client';

  let query = '';
  let selectedProviders = [];
  let searchTypes = ['tracks'];
  let results = [];
  let searching = false;
  let error = '';

  async function handleSearch() {
    if (!query.trim()) return;

    searching = true;
    error = '';
    results = [];

    try {
      const params = new URLSearchParams();
      params.append('q', query);
      if (selectedProviders.length > 0) {
        params.append('providers', selectedProviders.join(','));
      }
      if (searchTypes.length > 0) {
        params.append('types', searchTypes.join(','));
      }

      const response = await apiClient.get(`/search?${params.toString()}`);
      results = response.data.results || [];
    } catch (err) {
      error = `Search failed: ${err.response?.data?.error || err.message}`;
    } finally {
      searching = false;
    }
  }

  function toggleProvider(id) {
    if (selectedProviders.includes(id)) {
      selectedProviders = selectedProviders.filter(i => i !== id);
    } else {
      selectedProviders = [...selectedProviders, id];
    }
  }

  function toggleType(type) {
    if (searchTypes.includes(type)) {
      searchTypes = searchTypes.filter(t => t !== type);
    } else {
      searchTypes = [...searchTypes, type];
    }
  }

  async function handleAction(item, action) {
    try {
      await apiClient.post('/api/search/route', {
        item,
        action,
        target: 'default'
      });
      alert(`${action} initiated for ${item.title}`);
    } catch (err) {
      alert(`Action failed: ${err.response?.data?.error || err.message}`);
    }
  }

  onMount(() => {
    providers.load();
  });
</script>

<svelte:head>
  <title>Search • SoulSync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <div>
      <p class="eyebrow">Discovery</p>
      <h1>Unified Search</h1>
      <p class="sub">Search across all enabled music services and downloaders.</p>
    </div>
  </header>

  <div class="search-layout">
    <!-- Sidebar Filters -->
    <aside class="search-filters">
      <div class="card">
        <h3>Search Types</h3>
        <div class="filter-group">
          {#each ['tracks', 'albums', 'artists', 'playlists'] as type}
            <label class="filter-item">
              <input type="checkbox" 
                     checked={searchTypes.includes(type)} 
                     on:change={() => toggleType(type)} />
              <span class="capitalize">{type}</span>
            </label>
          {/each}
        </div>

        <div class="divider"></div>

        <h3>Providers</h3>
        <div class="filter-group">
          {#each $searchProviders as p}
            <label class="filter-item">
              <input type="checkbox" 
                     checked={selectedProviders.includes(p.id)} 
                     on:change={() => toggleProvider(p.id)} />
              <span>{p.name}</span>
            </label>
          {/each}
          {#if $searchProviders.length === 0}
            <p class="muted small">No search providers available.</p>
          {/if}
        </div>
      </div>
    </aside>

    <!-- Main Search Area -->
    <main class="search-main">
      <div class="search-bar card">
        <input type="text" 
               bind:value={query} 
               placeholder="Search for tracks, artists, or albums..." 
               on:keydown={(e) => e.key === 'Enter' && handleSearch()} />
        <button class="btn btn--primary" on:click={handleSearch} disabled={searching}>
          {#if searching}
            <div class="spinner spinner--small"></div>
          {:else}
            Search
          {/if}
        </button>
      </div>

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
            {#each results as item}
              <div class="result-card card">
                <div class="result-info">
                  <div class="result-main">
                    <span class="result-type-tag">{item.type}</span>
                    <strong>{item.title}</strong>
                  </div>
                  <p class="muted">{item.artist} • {item.provider}</p>
                  {#if item.confidence}
                    <div class="confidence-bar">
                      <div class="confidence-fill" style="width: {item.confidence * 100}%"></div>
                    </div>
                  {/if}
                </div>
                <div class="result-actions">
                  <button class="action-btn" title="Download" on:click={() => handleAction(item, 'download')}>
                    📥
                  </button>
                  <button class="action-btn" title="Add to Library" on:click={() => handleAction(item, 'library')}>
                    ➕
                  </button>
                </div>
              </div>
            {/each}
          </div>
        {:else if query && !searching}
          <div class="empty-state">
            <p>No results found for "{query}"</p>
          </div>
        {:else}
          <div class="empty-state">
            <p class="muted">Enter a query to start searching.</p>
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
    gap: 24px;
  }

  .search-layout {
    display: grid;
    grid-template-columns: 240px 1fr;
    gap: 24px;
    align-items: start;
  }

  @media (max-width: 900px) {
    .search-layout {
      grid-template-columns: 1fr;
    }
  }

  .search-filters .card {
    padding: 20px;
    background: var(--glass);
    backdrop-filter: blur(12px);
    border: 1px solid var(--glass-border);
    border-radius: 14px;
    position: sticky;
    top: 20px;
  }

  .search-filters h3 {
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
    margin: 0 0 16px;
  }

  .filter-group {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .filter-item {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 14px;
    cursor: pointer;
    color: #e2e8f0;
  }

  .divider {
    height: 1px;
    background: rgba(255, 255, 255, 0.05);
    margin: 20px 0;
  }

  .search-bar {
    display: flex;
    gap: 12px;
    padding: 12px;
    margin-bottom: 24px;
    background: var(--glass);
    backdrop-filter: blur(12px);
    border: 1px solid var(--glass-border);
    border-radius: 14px;
  }

  .search-bar input {
    flex: 1;
    background: transparent;
    border: none;
    color: #fff;
    font-size: 16px;
    padding: 8px 12px;
    outline: none;
  }

  .btn--primary {
    background: var(--accent);
    color: #000;
    padding: 8px 24px;
    border-radius: 8px;
    font-weight: 700;
    border: none;
    cursor: pointer;
  }

  .btn--primary:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  .results-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .result-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    transition: transform 0.2s, background 0.2s;
  }

  .result-card:hover {
    background: rgba(255, 255, 255, 0.05);
    transform: translateX(4px);
  }

  .result-main {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 4px;
  }

  .result-type-tag {
    font-size: 9px;
    text-transform: uppercase;
    font-weight: 800;
    padding: 2px 6px;
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.1);
    color: #94a3b8;
  }

  .confidence-bar {
    height: 3px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 2px;
    width: 100px;
    margin-top: 8px;
    overflow: hidden;
  }

  .confidence-fill {
    height: 100%;
    background: var(--accent);
    box-shadow: 0 0 8px var(--accent);
  }

  .result-actions {
    display: flex;
    gap: 8px;
  }

  .action-btn {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 16px;
  }

  .action-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    border-color: var(--accent);
    transform: scale(1.1);
  }

  .error-card {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.2);
    color: #ef4444;
    padding: 16px;
    border-radius: 12px;
    margin-bottom: 24px;
  }

  .loading-state, .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 80px 20px;
    color: #94a3b8;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid rgba(255, 255, 255, 0.1);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 16px;
  }

  .spinner--small {
    width: 18px;
    height: 18px;
    border-width: 2px;
    margin-bottom: 0;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .capitalize { text-transform: capitalize; }
  .muted { color: #94a3b8; }
  .small { font-size: 12px; }
</style>
