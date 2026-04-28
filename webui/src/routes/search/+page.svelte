<script>
  import { onMount } from 'svelte';
  import { providers, searchProviders } from '../../stores/providers';
  import apiClient from '../../api/client';
  import Omnibar from '../../lib/components/Omnibar.svelte';

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

  onMount(() => {
    providers.load();
  });
</script>

<svelte:head>
  <title>Search • Echosync</title>
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
    <!-- Main Search Area -->
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
                          <strong>{item.title || 'Unknown Title'}</strong>
                        </div>
                        <p class="muted">{item.artist ? item.artist + ' • ' : ''}{item.provider}</p>
                        {#if item.confidence}
                          <div class="confidence-bar">
                            <div class="confidence-fill" style="width: {item.confidence * 100}%"></div>
                          </div>
                        {/if}
                      </div>
                      <div class="result-actions">
                        {#if item.is_local}
                          <button class="action-btn active:scale-95 transition-all duration-200" title="Play" on:click={() => handleAction(item, 'play')}>
                            ▶️
                          </button>
                        {:else}
                          <button class="action-btn active:scale-95 transition-all duration-200" title="Download" on:click={() => handleAction(item, 'download')}>
                            📥
                          </button>
                        {/if}
                      </div>
                    </div>
                  {/each}
                </div>
              </div>
            {/each}
          </div>
        {:else if lastSearchedQuery && !searching}
          <div class="empty-state">
            <p>No results found for "{lastSearchedQuery}"</p>
          </div>
        {:else}
          <div class="empty-state">
            <p class="muted">Press <kbd class="bg-white/10 px-1.5 py-0.5 rounded border border-white/10 font-mono text-white">Ctrl+K</kbd> or <kbd class="bg-white/10 px-1.5 py-0.5 rounded border border-white/10 font-mono text-white">/</kbd> to start searching.</p>
            <p class="text-xs text-muted/60 mt-2">You can also use the search bar above.</p>
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
    display: block; /* Removed grid since sidebar is gone */
    max-width: 1200px;
    margin: 0 auto;
    width: 100%;
  }

  .search-main {
    width: 100%;
  }

  .results-list {
    display: flex;
    flex-direction: column;
    gap: 32px;
  }

  .result-section {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .section-title {
    font-size: 18px;
    font-weight: 700;
    color: #e2e8f0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding-bottom: 8px;
    margin: 0;
  }

  .section-items {
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

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .capitalize { text-transform: capitalize; }
  .muted { color: #94a3b8; }
</style>
