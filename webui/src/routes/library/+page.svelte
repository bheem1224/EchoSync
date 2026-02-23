<script>
  import { onMount } from 'svelte';
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
      handleDeepLinks();
    } catch (err) {
      error = err.message;
    } finally {
      loading = false;
    }
  }

  function handleDeepLinks() {
      const artistId = $page.url.searchParams.get('artist_id');
      const highlightTrackId = $page.url.searchParams.get('highlight');

      if (artistId) {
          const artist = libraryIndex.find(a => a.id == artistId);
          if (artist) {
              selectArtist(artist);

              if (highlightTrackId) {
                  // Wait for DOM update
                  setTimeout(() => {
                      const row = document.getElementById(`track-${highlightTrackId}`);
                      if (row) {
                          row.scrollIntoView({ behavior: 'smooth', block: 'center' });
                          row.classList.add('flash-highlight');
                          setTimeout(() => row.classList.remove('flash-highlight'), 2000);
                      }
                  }, 300);
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
      // Clear URL params without reload
      window.history.pushState({}, '', '/library');
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

  function formatDuration(ms) {
      if (!ms) return '-:--';
      const seconds = Math.floor(ms / 1000);
      const m = Math.floor(seconds / 60);
      const s = seconds % 60;
      return `${m}:${s.toString().padStart(2, '0')}`;
  }

  onMount(loadLibrary);
</script>

{#if loading}
    <div class="text-center p-12 text-gray-500">Loading library index...</div>
{:else if error}
    <div class="text-center p-12 text-red-500">Error: {error}</div>
{:else}

    <!-- GRID VIEW -->
    {#if viewMode === 'grid'}
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-6">
            {#each visibleArtists as artist (artist.id)}
                <div
                    class="bg-gray-800 rounded-xl p-4 border border-gray-700 hover:translate-y-[-4px] hover:bg-white/5 transition-all cursor-pointer group"
                    on:click={() => selectArtist(artist)}
                    on:keydown={(e) => e.key === 'Enter' && selectArtist(artist)}
                    role="button"
                    tabindex="0"
                >
                    <div class="w-full aspect-square bg-black rounded-full mb-3 overflow-hidden flex items-center justify-center shadow-lg group-hover:shadow-2xl transition-shadow">
                        {#if artist.image_url}
                            <img src={artist.image_url} alt={artist.name} loading="lazy" class="w-full h-full object-cover" />
                        {:else}
                            <span class="text-4xl opacity-50">👤</span>
                        {/if}
                    </div>
                    <div class="text-center">
                        <h3 class="text-sm font-bold text-white truncate">{artist.name}</h3>
                        <span class="text-xs text-gray-500">{artist.albums.length} Albums</span>
                    </div>
                </div>
            {/each}
        </div>

        {#if visibleCount < libraryIndex.length}
            <div class="text-center mt-10">
                <button
                    class="px-6 py-2 bg-transparent border border-gray-700 text-gray-400 rounded-full hover:text-white hover:border-white transition-colors"
                    on:click={loadMore}
                >
                    Load More
                </button>
            </div>
        {/if}

        {#if libraryIndex.length === 0}
            <div class="text-center p-12 text-gray-500">No artists found.</div>
        {/if}

    <!-- DETAIL VIEW -->
    {:else if viewMode === 'detail' && selectedArtist}
        <div class="animate-fade-in">
            <button class="text-blue-400 hover:text-blue-300 font-semibold mb-6 flex items-center gap-2" on:click={backToGrid}>
                <span>←</span> Back to Artists
            </button>

            <div class="flex items-center gap-6 mb-10 bg-gradient-to-r from-white/5 to-transparent p-6 rounded-2xl border border-white/5">
                <img
                    src={selectedArtist.image_url || ''}
                    alt={selectedArtist.name}
                    class="w-32 h-32 rounded-full object-cover shadow-2xl bg-gray-800"
                    on:error={(e) => e.target.style.display='none'}
                />
                <div>
                    <h2 class="text-4xl font-bold text-white mb-2">{selectedArtist.name}</h2>
                    <p class="text-gray-400">{selectedArtist.albums.reduce((acc, a) => acc + a.tracks.length, 0)} Tracks</p>
                </div>
            </div>

            <div class="space-y-10">
                {#each selectedArtist.albums as album (album.id)}
                    <div class="bg-gray-800/50 rounded-2xl border border-gray-700 p-6">
                        <div class="flex items-center gap-4 mb-6">
                            <div class="w-16 h-16 bg-white/10 rounded-lg overflow-hidden flex items-center justify-center shrink-0">
                                {#if album.cover_image_url}
                                    <img src={album.cover_image_url} alt={album.title} class="w-full h-full object-cover"/>
                                {:else}
                                    <span class="text-2xl">💿</span>
                                {/if}
                            </div>
                            <div>
                                <h3 class="text-xl font-bold text-white">{album.title}</h3>
                                <span class="text-sm text-gray-500">{album.year || 'Unknown Year'}</span>
                            </div>
                        </div>

                        <div class="space-y-1">
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
    .flash-highlight {
        animation: flash 1s ease-out;
    }

    @keyframes flash {
        0% { background-color: rgba(59, 130, 246, 0.5); }
        100% { background-color: transparent; }
    }
</style>
