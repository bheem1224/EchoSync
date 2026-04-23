<script>
  import { onMount, tick } from 'svelte';
  import { page } from '$app/stores';
  import apiClient from '../../api/client';
  import { player } from '../../stores/player';
  import TrackRow from '$lib/components/TrackRow.svelte';

  // Collection Data
  let libraryIndex = [];
  let loading = true;
  let error = '';

  // UI State
  let viewMode = 'grid'; // 'grid' | 'detail'
  let selectedArtist = null;

  // Pagination / Virtualization for Artists Grid
  let visibleCount = 50;
  const PAGE_SIZE = 50;

  async function loadLibrary() {
    loading = true;
    try {
      const res = await apiClient.get('/library/index');
      libraryIndex = res.data || [];
      // Initial deep link check handled by reactive statement below
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  // Reactive deep linking logic
  $: if (libraryIndex.length > 0 && $page.url.searchParams.has('artist_id')) {
      handleDeepLinks();
  }

  async function handleDeepLinks() {
      const artistId = $page.url.searchParams.get('artist_id');
      const highlightTrackId = $page.url.searchParams.get('highlight_track');
      const highlightAlbumId = $page.url.searchParams.get('highlight_album');

      if (artistId) {
          const artistIndex = libraryIndex.findIndex(a => a.id == artistId);
          if (artistIndex !== -1) {
              const artist = libraryIndex[artistIndex];

              if (artistIndex >= visibleCount) {
                  visibleCount = artistIndex + PAGE_SIZE;
              }

              selectArtist(artist);
              await tick();

              let targetId = null;
              if (highlightTrackId) targetId = `track-${highlightTrackId}`;
              else if (highlightAlbumId) targetId = `album-${highlightAlbumId}`;

              if (targetId) {
                  const element = document.getElementById(targetId);
                  if (element) {
                      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                      element.classList.add('flash-highlight');
                      setTimeout(() => element.classList.remove('flash-highlight'), 2000);
                  }
              }
          }
      }
  }

  $: visibleArtists = libraryIndex.slice(0, visibleCount);

  function loadMore() {
      if (visibleCount < libraryIndex.length) {
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
      const url = new URL(window.location);
      url.search = '';
      window.history.pushState({}, '', url);
  }

  // --- Actions ---

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
          updateLocalStateAfterDelete(trackId, album);
      } catch (err) {
          alert(`Failed to force delete: ${err.message}`);
      }
  }

  function updateLocalStateAfterDelete(trackId, album) {
      album.tracks = album.tracks.filter(t => t.id !== trackId);
      if (album.tracks.length === 0) {
           selectedArtist.albums = selectedArtist.albums.filter(a => a.id !== album.id);
      }
      libraryIndex = [...libraryIndex];
      if (selectedArtist) selectedArtist = {...selectedArtist};
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

{#if loading}
    <div class="empty-state">
        <div class="spinner"></div>
        <p>Loading library index...</p>
    </div>
{:else if error}
    <div class="error-msg text-center p-12">{error}</div>
{:else}

    <!-- GRID VIEW -->
    {#if viewMode === 'grid'}
        <div class="artist-grid">
            {#each visibleArtists as artist (artist.id)}
                <div
                    class="card artist-card"
                    on:click={() => selectArtist(artist)}
                    on:keydown={(e) => e.key === 'Enter' && selectArtist(artist)}
                    role="button"
                    tabindex="0"
                >
                    <div class="card-image">
                        {#if artist.image_url}
                            <img src={artist.image_url} alt={artist.name} loading="lazy" />
                        {:else}
                            <span class="placeholder">👤</span>
                        {/if}
                    </div>
                    <div class="card-info">
                        <h3>{artist.name}</h3>
                        <span class="sub">{artist.albums.length} Albums</span>
                    </div>
                </div>
            {/each}
        </div>

        {#if visibleCount < libraryIndex.length}
            <div class="text-center mt-10">
                <button
                    class="btn active:scale-95 transition-all duration-200"
                    on:click={loadMore}
                >
                    Load More
                </button>
            </div>
        {/if}

        {#if libraryIndex.length === 0}
            <div class="empty-state">
                <p>No artists found.</p>
            </div>
        {/if}

    <!-- DETAIL VIEW -->
    {:else if viewMode === 'detail' && selectedArtist}
        <div class="animate-fade-in">
            <button class="btn btn-link mb-6 active:scale-95 transition-all duration-200" on:click={backToGrid}>
                ← Back to Artists
            </button>

            <div class="artist-header card">
                <img
                    src={selectedArtist.image_url || ''}
                    alt={selectedArtist.name}
                    class="artist-hero-img"
                    on:error={(e) => e.target.style.display='none'}
                />
                <div>
                    <h2>{selectedArtist.name}</h2>
                    <p class="sub">{selectedArtist.albums.reduce((acc, a) => acc + a.tracks.length, 0)} Tracks</p>
                </div>
            </div>

            <div class="space-y-8 mt-8">
                {#each selectedArtist.albums as album (album.id)}
                    <div class="card" id="album-{album.id}">
                        <div class="album-header">
                            <div class="album-cover-container">
                                {#if album.cover_image_url}
                                    <img src={album.cover_image_url} alt={album.title} class="album-cover"/>
                                {:else}
                                    <span class="placeholder-icon">💿</span>
                                {/if}
                            </div>
                            <div>
                                <h3>{album.title}</h3>
                                <span class="sub">{album.year || 'Unknown Year'}</span>
                            </div>
                        </div>

                        <div class="tracks-list">
                            {#each album.tracks as track}
                                <div id="track-{track.id}">
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
                                </div>
                            {/each}
                        </div>
                    </div>
                {/each}
            </div>
        </div>
    {/if}

{/if}

<style>
    .artist-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
        gap: 16px;
    }

    .card {
        background: var(--glass);
        border: 1px solid var(--glass-border);
        border-radius: 12px;
        overflow: hidden;
        transition: transform 0.2s;
    }

    .artist-card {
        padding: 16px;
        cursor: pointer;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
    }

    .artist-card:hover {
        background: rgba(255,255,255,0.05);
        transform: translateY(-2px);
    }

    .card-image {
        width: 100%;
        aspect-ratio: 1;
        border-radius: 50%;
        background: #000;
        margin-bottom: 12px;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }

    .card-image img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }

    .placeholder { font-size: 32px; opacity: 0.5; }

    .card-info h3 {
        font-size: 14px;
        font-weight: 600;
        margin: 0;
        color: var(--text);
        width: 100%;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .sub { font-size: 12px; color: var(--muted); }

    .btn {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.1);
        color: var(--text);
        padding: 8px 16px;
        border-radius: 99px;
        cursor: pointer;
        font-size: 13px;
    }
    .btn:hover { background: rgba(255,255,255,0.1); }

    .btn-link {
        background: none; border: none; padding: 0;
        color: var(--accent); font-weight: 600;
    }

    /* Detail View */
    .artist-header {
        padding: 24px;
        display: flex;
        align-items: center;
        gap: 24px;
        background: linear-gradient(to right, rgba(255,255,255,0.03), transparent);
    }

    .artist-hero-img {
        width: 100px;
        height: 100px;
        border-radius: 50%;
        object-fit: cover;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
    }

    .artist-header h2 { font-size: 28px; margin: 0; color: var(--text); }

    .album-header {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 16px;
        border-bottom: 1px solid var(--glass-border);
        background: rgba(0,0,0,0.2);
    }

    .album-cover-container {
        width: 50px;
        height: 50px;
        background: #000;
        border-radius: 4px;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .album-cover { width: 100%; height: 100%; object-fit: cover; }
    .placeholder-icon { font-size: 20px; }

    .album-header h3 { margin: 0; font-size: 16px; color: var(--text); }

    .tracks-list { padding: 4px 0; }

    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 60px;
        color: var(--muted);
    }
    .spinner {
        width: 30px; height: 30px;
        border: 3px solid rgba(255,255,255,0.1);
        border-top-color: var(--accent);
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-bottom: 16px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    .flash-highlight {
        animation: flash 1s ease-out;
    }

    @keyframes flash {
        0% { background-color: rgba(15, 239, 136, 0.3); }
        100% { background-color: transparent; }
    }
</style>
