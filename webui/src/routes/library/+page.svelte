<script>
  import { onMount } from 'svelte';
  import apiClient from '../../api/client';

  let tracks = [];
  let loading = true;
  let error = '';
  let query = '';
  let limit = 50;
  let offset = 0;
  let totalCount = 0;

  async function loadTracks() {
    loading = true;
    error = '';
    try {
      const endpoint = query 
        ? `/tracks/search?title=${encodeURIComponent(query)}&limit=${limit}`
        : `/tracks?limit=${limit}&offset=${offset}`;
      
      const response = await apiClient.get(endpoint);
      tracks = response.data.items || [];
      totalCount = response.data.count || 0;
    } catch (err) {
      error = `Failed to load library: ${err.response?.data?.error || err.message}`;
    } finally {
      loading = false;
    }
  }

  function handleSearch() {
    offset = 0;
    loadTracks();
  }

  async function deleteTrack(id) {
    if (!confirm('Are you sure you want to remove this track from your library?')) return;
    
    try {
      await apiClient.delete(`/tracks/${id}`);
      tracks = tracks.filter(t => t.track_id !== id);
    } catch (err) {
      alert(`Delete failed: ${err.response?.data?.error || err.message}`);
    }
  }

  function getStatusColor(status) {
    switch (status?.toLowerCase()) {
      case 'complete':
      case 'verified':
        return 'var(--accent)';
      case 'downloading':
      case 'queued':
        return '#0ea5e9';
      case 'missing':
        return '#ef4444';
      default:
        return '#94a3b8';
    }
  }

  onMount(loadTracks);
</script>

<svelte:head>
  <title>Library • SoulSync</title>
</svelte:head>

<section class="page">
  <header class="page__header">
    <div>
      <p class="eyebrow">Collection</p>
      <h1>Music Library</h1>
      <p class="sub">Manage your canonical track collection and download status.</p>
    </div>
  </header>

  <div class="library-controls card">
    <div class="search-box">
      <span class="search-icon">🔍</span>
      <input type="text" 
             bind:value={query} 
             placeholder="Search library by title or artist..." 
             on:keydown={(e) => e.key === 'Enter' && handleSearch()} />
    </div>
    <div class="stats">
      <span class="muted">Total Tracks:</span>
      <strong>{totalCount}</strong>
    </div>
  </div>

  <div class="tracks-container card">
    {#if loading}
      <div class="loading-state">
        <div class="spinner"></div>
        <p>Loading your library...</p>
      </div>
    {:else if error}
      <div class="error-state">
        <p>{error}</p>
        <button class="btn btn--small" on:click={loadTracks}>Retry</button>
      </div>
    {:else if tracks.length === 0}
      <div class="empty-state">
        <p class="muted">Your library is empty.</p>
        <a href="/sync" class="btn btn--small">Sync some playlists</a>
      </div>
    {:else}
      <div class="table-wrapper">
        <table class="tracks-table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Artist</th>
              <th>Album</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each tracks as track}
              <tr>
                <td>
                  <div class="track-title">
                    <strong>{track.title}</strong>
                    {#if track.isrc}
                      <span class="isrc">{track.isrc}</span>
                    {/if}
                  </div>
                </td>
                <td>{Array.isArray(track.artists) ? track.artists.join(', ') : track.artists}</td>
                <td>{track.album || '-'}</td>
                <td>
                  <span class="status-pill" style="--status-color: {getStatusColor(track.download_status)}">
                    {track.download_status || 'Unknown'}
                  </span>
                </td>
                <td>
                  <div class="actions">
                    <button class="icon-btn" title="Delete" on:click={() => deleteTrack(track.track_id)}>
                      🗑️
                    </button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</section>

<style>
  .page {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .library-controls {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 20px;
    background: var(--glass);
    backdrop-filter: blur(12px);
    border: 1px solid var(--glass-border);
    border-radius: 14px;
  }

  .search-box {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1;
    max-width: 400px;
  }

  .search-icon { font-size: 16px; opacity: 0.5; }

  .search-box input {
    background: transparent;
    border: none;
    color: #fff;
    font-size: 14px;
    width: 100%;
    outline: none;
  }

  .stats {
    font-size: 14px;
    display: flex;
    gap: 8px;
  }

  .tracks-container {
    background: var(--glass);
    backdrop-filter: blur(12px);
    border: 1px solid var(--glass-border);
    border-radius: 14px;
    padding: 0;
    overflow: hidden;
  }

  .table-wrapper {
    overflow-x: auto;
  }

  .tracks-table {
    width: 100%;
    border-collapse: collapse;
    text-align: left;
    font-size: 14px;
  }

  .tracks-table th {
    padding: 16px 20px;
    background: rgba(255, 255, 255, 0.03);
    color: #94a3b8;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.05em;
  }

  .tracks-table td {
    padding: 14px 20px;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    vertical-align: middle;
  }

  .tracks-table tr:hover td {
    background: rgba(255, 255, 255, 0.02);
  }

  .track-title {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .isrc {
    font-size: 10px;
    color: #64748b;
    font-family: monospace;
  }

  .status-pill {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    background: color-mix(in srgb, var(--status-color) 15%, transparent);
    color: var(--status-color);
    border: 1px solid color-mix(in srgb, var(--status-color) 30%, transparent);
  }

  .icon-btn {
    background: transparent;
    border: none;
    cursor: pointer;
    font-size: 16px;
    opacity: 0.6;
    transition: opacity 0.2s, transform 0.2s;
  }

  .icon-btn:hover {
    opacity: 1;
    transform: scale(1.2);
  }

  .loading-state, .empty-state, .error-state {
    padding: 80px 20px;
    text-align: center;
    color: #94a3b8;
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid rgba(255, 255, 255, 0.1);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 16px;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .btn--small {
    padding: 6px 12px;
    font-size: 12px;
    background: var(--accent);
    color: #000;
    border-radius: 6px;
    text-decoration: none;
    font-weight: 600;
    margin-top: 12px;
    display: inline-block;
  }

  .muted { color: #94a3b8; }
</style>
