<script>
  import { onMount } from 'svelte';
  import apiClient from '../../api/client';
  import { player } from '../../stores/player';
  import TrackRow from '$lib/components/TrackRow.svelte';
  import Omnibar from '$lib/components/Omnibar.svelte';
  import ManagerDashboard from '$lib/components/ManagerDashboard.svelte';

  let libraryIndex = [];
  let loading = true;
  let error = '';
  let searchQuery = '';

  let viewMode = 'grid'; // 'grid' | 'detail'
  let activeTab = 'library'; // 'library' | 'manager'
  let selectedArtist = null;

  // Lazy loading state
  let visibleCount = 50;
  const PAGE_SIZE = 50;

  async function loadLibrary() {
    loading = true;
    try {
      const res = await apiClient.get('/library/index');
      libraryIndex = res.data || [];
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  // Filtered artists (if user wants to filter the grid, but Omnibar does global search)
  // We can keep this filter if the user types in the omnibar, BUT Omnibar has its own dropdown.
  // Ideally, Omnibar handles global search. This filter might be redundant or confusing if Omnibar is here.
  // However, the prompt says "change the search of library".
  // If we replace the simple input with Omnibar, the Omnibar's dropdown handles navigation.
  // We can also bind the query to filter the grid if we want "live filtering".
  // But Omnibar does async backend search.
  // Let's keep the grid unfiltered unless we want to implement client-side filtering too.
  // For now, let's assume Omnibar is the primary search and navigation tool.
  // We'll keep `filteredArtists` just as `libraryIndex` to show everything, or maybe implement client-side filter if needed later.

  $: filteredArtists = libraryIndex; // Default show all

  // Visible subset
  $: visibleArtists = filteredArtists.slice(0, visibleCount);

  function loadMore() {
      if (visibleCount < filteredArtists.length) {
          visibleCount += PAGE_SIZE;
      }
  }

  function selectArtist(artist) {
      selectedArtist = artist;
      viewMode = 'detail';
      window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function backToGrid() {
      selectedArtist = null;
      viewMode = 'grid';
  }

  function switchTab(tab) {
      activeTab = tab;
      // If switching to library, maybe reset view?
      if (tab === 'library') {
          // keep current view state
      }
  }

  function playTrack(track, artist, album) {
      player.play({
          ...track,
          artist: artist.name,
          album: album.title,
          cover: album.cover_image_url || artist.image_url
      });
  }

  async function deleteTrack(trackId, album) {
      if (!confirm("Are you sure you want to delete this track? This action cannot be undone.")) return;
      await performDelete(trackId, album);
  }

  async function performDelete(trackId, album) {
      try {
          await apiClient.delete(`/library/${trackId}`);
          updateLocalStateAfterDelete(trackId, album);
      } catch (err) {
          alert(`Failed to delete: ${err.message}`);
      }
  }

  async function forceDeleteTrack(trackId, album) {
      if (!confirm("⚠️ FORCE DELETE: This will set the system flag to DELETE (0.1). Continue?")) return;
      try {
          await apiClient.post(`/manager/track/${trackId}/override`, { action: 'delete' });
          updateLocalStateAfterDelete(trackId, album); // Optimistic remove
      } catch (err) {
          alert(`Failed to force delete: ${err.message}`);
      }
  }

  function updateLocalStateAfterDelete(trackId, album) {
       // Update local state
      // Remove track from album
      album.tracks = album.tracks.filter(t => t.id !== trackId);

      // If album empty, remove album? (Optional, let's keep it simple)
      if (album.tracks.length === 0) {
           selectedArtist.albums = selectedArtist.albums.filter(a => a.id !== album.id);
      }

      // Force reactivity
      libraryIndex = [...libraryIndex];
      if (selectedArtist) selectedArtist = {...selectedArtist}; // trigger update
  }

  async function forceUpgradeTrack(trackId) {
      if (!confirm("Force Upgrade? This will mark the track as needing an upgrade.")) return;
      try {
          await apiClient.post(`/manager/track/${trackId}/override`, { action: 'upgrade' });
          alert("Marked for upgrade.");
      } catch (err) {
          alert(`Failed: ${err.message}`);
      }
  }

  async function fetchMetadata(trackId) {
       try {
          const res = await apiClient.post(`/manager/track/${trackId}/fetch_metadata`);
          if (res.data.success) {
              alert(`Metadata Fetched:\nTitle: ${res.data.metadata.title}\nArtist: ${res.data.metadata.artist}\nConfidence: ${res.data.confidence}`);
          } else {
              alert('Metadata fetch returned no match.');
          }
      } catch (err) {
          alert(`Failed to fetch metadata: ${err.message}`);
      }
  }

  onMount(loadLibrary);
</script>

<svelte:head>
  <title>Library • SoulSync</title>
</svelte:head>

<div class="library-page">
  <header class="header">
    <div class="flex items-center gap-8">
        <div>
            <h1>Library</h1>
            <p class="subtitle">Your Collection</p>
        </div>

        <!-- Tabs -->
        <div class="flex bg-gray-800 p-1 rounded-lg">
            <button
                class="px-4 py-1.5 rounded-md text-sm font-medium transition-colors {activeTab === 'library' ? 'bg-blue-600 text-white shadow' : 'text-gray-400 hover:text-white'}"
                on:click={() => switchTab('library')}
            >
                Library
            </button>
            <button
                class="px-4 py-1.5 rounded-md text-sm font-medium transition-colors {activeTab === 'manager' ? 'bg-purple-600 text-white shadow' : 'text-gray-400 hover:text-white'}"
                on:click={() => switchTab('manager')}
            >
                Manager
            </button>
        </div>
    </div>

    <div class="search-container flex-1 max-w-xl">
        <Omnibar />
    </div>
  </header>

  <div class="content-area">
      {#if activeTab === 'manager'}
          <ManagerDashboard />
      {:else}
          {#if loading}
              <div class="loading">Loading library index...</div>
          {:else if error}
              <div class="error">Error: {error}</div>
          {:else}

              <!-- GRID VIEW -->
              {#if viewMode === 'grid'}
                  <div class="artist-grid">
                      {#each visibleArtists as artist (artist.id)}
                          <div class="artist-card" on:click={() => selectArtist(artist)} on:keydown={(e) => e.key === 'Enter' && selectArtist(artist)} role="button" tabindex="0">
                              <div class="card-image">
                                  {#if artist.image_url}
                                      <img src={artist.image_url} alt={artist.name} loading="lazy" />
                                  {:else}
                                      <div class="placeholder">👤</div>
                                  {/if}
                              </div>
                              <div class="card-info">
                                  <h3>{artist.name}</h3>
                                  <span class="count">{artist.albums.length} Albums</span>
                              </div>
                          </div>
                      {/each}
                  </div>

                  {#if visibleCount < filteredArtists.length}
                      <div class="load-more">
                          <button class="btn-ghost" on:click={loadMore}>Load More</button>
                      </div>
                  {/if}

                  {#if filteredArtists.length === 0}
                      <div class="empty-state">No artists found.</div>
                  {/if}

              <!-- DETAIL VIEW -->
              {:else if viewMode === 'detail' && selectedArtist}
                  <div class="detail-view">
                      <button class="back-btn" on:click={backToGrid}>← Back to Artists</button>

                      <div class="artist-header">
                          {#if selectedArtist.image_url}
                              <img src={selectedArtist.image_url} alt={selectedArtist.name} class="artist-hero-img"/>
                          {/if}
                          <div class="artist-hero-info">
                              <h2>{selectedArtist.name}</h2>
                              <p>{selectedArtist.albums.reduce((acc, a) => acc + a.tracks.length, 0)} Tracks</p>
                          </div>
                      </div>

                      <div class="albums-list">
                          {#each selectedArtist.albums as album (album.id)}
                              <div class="album-section">
                                  <div class="album-header">
                                      {#if album.cover_image_url}
                                          <img src={album.cover_image_url} alt={album.title} class="album-cover"/>
                                      {:else}
                                          <div class="album-placeholder">💿</div>
                                      {/if}
                                      <div class="album-info">
                                          <h3>{album.title}</h3>
                                          <span class="year">{album.year || 'Unknown Year'}</span>
                                      </div>
                                  </div>

                                  <div class="tracks-list">
                                      {#each album.tracks as track}
                                          <TrackRow
                                              {track}
                                              artist={selectedArtist}
                                              {album}
                                              onPlay={playTrack}
                                              onDelete={deleteTrack}
                                              onFetchMetadata={fetchMetadata}
                                              onForceUpgrade={forceUpgradeTrack}
                                              onForceDelete={forceDeleteTrack}
                                          />
                                      {/each}
                                  </div>
                              </div>
                          {/each}
                      </div>
                  </div>
              {/if}
          {/if}
      {/if}
  </div>
</div>

<style>
  .library-page {
      padding-bottom: 40px;
  }

  .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
      flex-wrap: wrap;
      gap: 24px;
  }

  .subtitle {
      color: var(--text-muted);
      margin: 0;
  }

  /* Omnibar styles are self-contained */

  .artist-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
      gap: 20px;
  }

  .artist-card {
      background: var(--bg-card);
      border-radius: 12px;
      padding: 12px;
      border: 1px solid var(--border-subtle);
      cursor: pointer;
      transition: transform 0.2s, background 0.2s;
  }

  .artist-card:hover {
      transform: translateY(-4px);
      background: rgba(255,255,255,0.05);
  }

  .card-image {
      width: 100%;
      aspect-ratio: 1;
      background: #000;
      border-radius: 8px;
      margin-bottom: 12px;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
  }

  .card-image img {
      width: 100%;
      height: 100%;
      object-fit: cover;
  }

  .placeholder {
      font-size: 40px;
      opacity: 0.5;
  }

  .card-info h3 {
      font-size: 14px;
      margin: 0 0 4px 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
  }

  .count {
      font-size: 12px;
      color: var(--text-muted);
  }

  .load-more {
      text-align: center;
      margin-top: 40px;
  }

  .btn-ghost {
      padding: 10px 20px;
      background: transparent;
      border: 1px solid var(--border-subtle);
      color: var(--text-muted);
      border-radius: 99px;
      cursor: pointer;
  }

  .btn-ghost:hover {
      color: #fff;
      border-color: #fff;
  }

  /* Detail View */
  .back-btn {
      background: none;
      border: none;
      color: var(--color-primary);
      cursor: pointer;
      font-weight: 600;
      margin-bottom: 20px;
      padding: 0;
  }

  .artist-header {
      display: flex;
      align-items: center;
      gap: 24px;
      margin-bottom: 40px;
      background: linear-gradient(to right, rgba(255,255,255,0.02), transparent);
      padding: 24px;
      border-radius: 16px;
  }

  .artist-hero-img {
      width: 120px;
      height: 120px;
      border-radius: 50%;
      object-fit: cover;
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
  }

  .artist-hero-info h2 {
      margin: 0;
      font-size: 32px;
  }

  .album-section {
      margin-bottom: 40px;
      background: var(--bg-card);
      border-radius: 16px;
      padding: 20px;
      border: 1px solid var(--border-subtle);
  }

  .album-header {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 20px;
  }

  .album-cover, .album-placeholder {
      width: 60px;
      height: 60px;
      border-radius: 4px;
      object-fit: cover;
  }

  .album-placeholder {
      background: rgba(255,255,255,0.1);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24px;
  }

  .album-info h3 {
      margin: 0;
      font-size: 18px;
  }

  .year {
      color: var(--text-muted);
      font-size: 14px;
  }

  .loading, .error, .empty-state {
      text-align: center;
      padding: 60px;
      color: var(--text-muted);
  }

  @media (max-width: 600px) {
      .artist-grid {
          grid-template-columns: repeat(2, 1fr);
      }
      .header {
          flex-direction: column;
          align-items: stretch;
      }
      .search-container {
          width: 100%;
          max-width: none;
      }
  }
</style>
