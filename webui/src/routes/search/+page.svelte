<!--
  /search — Dynamic Route (YAML-driven)
  ──────────────────────────────────────
  ARCHITECTURE NOTE (Sandboxed View Architecture):
    • This route is *dynamic* — its layout comes from `search-dashboard.yaml`.
    • The actual search state (query, results) is owned here in Svelte and
      passed down to Web Components via CustomEvents + a broadcast store.
    • The YAML defines the shell layout (which cards appear, in what order).
      Each card is a sandboxed Web Component that receives data, not raw API
      access.

  Web Component ↔ Svelte Protocol
  ────────────────────────────────
    • `echosync-search-bar` dispatches `es-search-query` CustomEvent.
    • `echosync-search-results` listens to `es-search-results` CustomEvent.
    • `echosync-search-hero` listens to `es-search-active` CustomEvent.
    • This page sits in the middle: bridges events between Web Components and
      the real API, keeping auth tokens and raw HTTP logic out of plugins.
-->
<script>
  import { onMount, onDestroy } from 'svelte';
  import { providers } from '../../stores/providers';
  import apiClient from '../../api/client';
  import YamlDashboardRenderer from '../../components/YamlDashboardRenderer.svelte';

  // ── Search state (owned by Svelte, not the YAML) ─────────────────────
  let results          = [];
  let searching        = false;
  let error            = '';
  let lastSearchedQuery = '';
  let searchedOnce     = false;
  let searchQuery      = '';

  // ── YAML source URL ───────────────────────────────────────────────────
  // Served from webui/static/dashboards/ — available in both Vite dev and
  // production Docker builds (Flask serves the SvelteKit build output).
  const YAML_URL = '/dashboards/search-dashboard.yaml';

  // ── Core search logic ─────────────────────────────────────────────────
  async function handleSearch(query) {
    if (!query?.trim()) return;
    searching = true;
    error = '';
    lastSearchedQuery = query;
    searchQuery       = query;
    searchedOnce      = true;

    // Notify Web Components that a search is active
    window.dispatchEvent(new CustomEvent('es-search-active', { detail: { query } }));

    try {
      const res = await apiClient.get(`/search/discovery?q=${encodeURIComponent(query)}`);
      results = res.data?.results || [];
    } catch (err) {
      error   = err.response?.data?.error || err.message;
      results = [];
    } finally {
      searching = false;
    }

    // Broadcast results to any listening Web Component
    window.dispatchEvent(new CustomEvent('es-search-results', {
      detail: { results, query, error, searching: false }
    }));
  }

  async function handleAction(item, action) {
    try {
      await apiClient.post('/search/route', { item, action, target: 'default' });
    } catch (err) {
      console.error('Search action failed:', err.message);
    }
  }

  // ── Bridge: Web Component → Svelte ────────────────────────────────────
  function onWcSearchQuery(e) {
    handleSearch(e.detail?.query ?? '');
  }

  onMount(() => {
    providers.load().catch(() => {});
    window.addEventListener('es-search-query', onWcSearchQuery);

    // If we have a ?q= param in the URL, auto-search on mount
    const urlQ = new URLSearchParams(window.location.search).get('q');
    if (urlQ) handleSearch(urlQ);
  });

  onDestroy(() => {
    window.removeEventListener('es-search-query', onWcSearchQuery);
  });

  // ── Fallback keydown (for the native input below) ─────────────────────
  function handleKeydown(e) {
    if (e.key === 'Enter') handleSearch(searchQuery);
  }

  // ── YamlDashboardRenderer events ──────────────────────────────────────
  function onRendererReady(e) {
    // Layout is ready — push initial state to Web Components
    window.dispatchEvent(new CustomEvent('es-search-results', {
      detail: { results: [], query: '', error: '', searching: false }
    }));
  }

  function onRendererError(e) {
    // YAML failed to load — page falls back to native Svelte UI below
    console.warn('[/search] YAML renderer failed, using native fallback:', e.detail);
  }

  $: groupedResults = results.reduce((acc, item) => {
    const t = item.type || 'unknown';
    if (!acc[t]) acc[t] = [];
    acc[t].push(item);
    return acc;
  }, {});
</script>

<svelte:head>
  <title>Search • EchoSync</title>
</svelte:head>

<section class="page">
  <!--
    ── Hero / Search Bar ───────────────────────────────────────────────────
    Always rendered by Svelte (frozen top section), even on the dynamic route.
    The YAML may render ADDITIONAL cards below, but cannot replace this hero.
  -->
  <div class="search-hero">
    <div class="search-hero__content">
      <p class="eyebrow">Discovery</p>
      <h1 class="hero-title">
        <span class="hero-title__static">Unified</span>
        <span class="hero-title__typing" aria-live="polite">Search</span>
      </h1>

      <div class="search-input-wrapper" class:focused={false}>
        <div class="search-icon" aria-hidden="true">
          <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </div>
        <input
          id="search-main-input"
          type="text"
          bind:value={searchQuery}
          on:keydown={handleKeydown}
          placeholder="Search for tracks, albums, or artists…"
          class="hero-search-input"
          autocomplete="off"
          spellcheck="false"
        />
        {#if searching}
          <div class="search-spinner" aria-label="Searching…">
            <div class="spinner-ring"></div>
          </div>
        {:else}
          <button
            id="search-submit-btn"
            class="search-submit-btn"
            on:click={() => handleSearch(searchQuery)}
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

  <!--
    ── YAML Dynamic Section ────────────────────────────────────────────────
    YamlDashboardRenderer handles the layout below the search bar.
    Plugin-injected cards appear here; they communicate via CustomEvents.
    If YAML fails, the native Svelte fallback results list is shown instead.
  -->
  <div class="search-dynamic-zone">
    <YamlDashboardRenderer
      yamlUrl={YAML_URL}
      on:ready={onRendererReady}
      on:error={onRendererError}
    >
      <!-- Slot: what to show when YAML defines no views (or YAML 404s) -->
      <div class="search-fallback">
        {#if error}
          <div class="error-card" role="alert">
            <span>⚠</span> {error}
          </div>
        {/if}

        {#if searching}
          <div class="loading-state">
            <div class="spinner"></div>
            <p>Searching across services…</p>
          </div>
        {:else if results.length > 0}
          <div class="results-list">
            {#each Object.entries(groupedResults) as [type, items]}
              <div class="result-section">
                <h3 class="section-title">{type}</h3>
                <div class="section-items">
                  {#each items as item}
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
                            <p class="result-artist">{item.artist || item.artist_name || ''}</p>
                          </div>
                        </div>
                      </div>
                      <div class="result-meta">
                        <span class="provider-badge">{item.provider}</span>
                        <div class="result-actions">
                          {#if item.is_local || item.ownership_state === 'owned'}
                            <button class="action-btn play-btn" title="Play" on:click={() => handleAction(item, 'play')}>
                              <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
                            </button>
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
            {/each}
          </div>

        {:else if searchedOnce}
          <div class="empty-state">
            <div class="empty-icon">🔍</div>
            <p>No results found for "{lastSearchedQuery}"</p>
            <p class="empty-hint">Try different keywords or check your provider settings.</p>
          </div>

        {:else}
          <!-- Pre-search animated state -->
          <div class="initial-state">
            <div class="search-graphic" aria-hidden="true">
              <div class="circle circle-1"></div>
              <div class="circle circle-2"></div>
              <div class="circle circle-3"></div>
              <div class="search-logo">EchoSync</div>
            </div>
            <p class="initial-tagline">Enter a query to explore the musical multiverse</p>
            <p class="initial-sub">Results from all configured streaming and discovery providers</p>
          </div>
        {/if}
      </div>
    </YamlDashboardRenderer>
  </div>
</section>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: 32px;
    max-width: 1000px;
    margin: 0 auto;
  }

  /* ── Hero ─────────────────────────────────────────────────────────── */
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

  /* Typing animation for the hero title */
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

  /* ── Search input ────────────────────────────────────────────────── */
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

  /* Searching spinner inside input */
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

  /* ── Dynamic zone ────────────────────────────────────────────────── */
  .search-dynamic-zone { min-height: 200px; }
  .search-fallback { width: 100%; }

  /* ── Error card ──────────────────────────────────────────────────── */
  .error-card {
    display: flex; align-items: center; gap: 10px;
    padding: 14px 18px; margin-bottom: 16px;
    background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3);
    border-radius: 10px; color: #ef4444; font-size: 14px;
  }

  /* ── Loading state ───────────────────────────────────────────────── */
  .loading-state {
    display: flex; align-items: center; justify-content: center;
    flex-direction: column; gap: 12px;
    padding: 80px 20px; color: rgba(255,255,255,0.4); font-size: 14px;
  }
  .spinner {
    width: 32px; height: 32px;
    border: 2px solid rgba(255,255,255,0.08);
    border-top-color: var(--color-primary, #1db954);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
  }

  /* ── Results ─────────────────────────────────────────────────────── */
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
  .provider-badge { font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: rgba(255,255,255,0.35); background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); padding: 3px 8px; border-radius: 6px; }
  .result-actions { display: flex; gap: 6px; }
  .action-btn { width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.18s; border: none; }
  .play-btn     { background: rgba(255,255,255,0.05); color: #fff; }
  .play-btn:hover { background: var(--color-primary, #1db954); color: #000; }
  .download-btn { background: var(--color-primary, #1db954); color: #000; }
  .download-btn:hover { filter: brightness(1.1); transform: scale(1.08); }

  /* ── Empty / initial states ──────────────────────────────────────── */
  .empty-state {
    display: flex; flex-direction: column; align-items: center;
    padding: 80px 20px; color: rgba(255,255,255,0.4); text-align: center;
  }
  .empty-icon { font-size: 40px; margin-bottom: 16px; opacity: 0.3; }
  .empty-hint { font-size: 12px; margin-top: 6px; opacity: 0.6; }

  .initial-state {
    display: flex; flex-direction: column; align-items: center;
    padding: 80px 20px;
  }
  .search-graphic {
    position: relative; width: 120px; height: 120px;
    display: flex; align-items: center; justify-content: center;
    margin-bottom: 40px;
  }
  .circle {
    position: absolute; border: 1px solid var(--color-primary, #1db954);
    border-radius: 50%; opacity: 0.15;
    animation: pulse-ring 4s ease-in-out infinite;
  }
  .circle-1 { width: 100%; height: 100%; animation-delay: 0s; }
  .circle-2 { width: 68%;  height: 68%;  animation-delay: 1s; }
  .circle-3 { width: 38%;  height: 38%;  animation-delay: 2s; }
  @keyframes pulse-ring {
    0%   { transform: scale(1);   opacity: 0.15; }
    50%  { transform: scale(1.18); opacity: 0.3; }
    100% { transform: scale(1);   opacity: 0.15; }
  }
  .search-logo {
    font-weight: 900; font-size: 12px; letter-spacing: 2px;
    text-transform: uppercase; color: var(--color-primary, #1db954);
    text-shadow: 0 0 20px rgba(29, 185, 84, 0.35);
  }
  .initial-tagline { font-size: 18px; font-weight: 600; color: rgba(255,255,255,0.7); margin: 0 0 8px; text-align: center; }
  .initial-sub { font-size: 13px; color: rgba(255,255,255,0.35); max-width: 400px; text-align: center; line-height: 1.6; }
</style>
