<script>
    import { goto } from '$app/navigation';

    let query = '';
    let results = { artists: [], albums: [], tracks: [] };
    let showDropdown = false;
    let loading = false;
    let debounceTimer;

    const performSearch = async (q) => {
        if (!q || q.length < 2) {
            results = { artists: [], albums: [], tracks: [] };
            showDropdown = false;
            loading = false;
            return;
        }

        loading = true;
        try {
            const res = await fetch(`/api/manager/search?q=${encodeURIComponent(q)}`);
            if (res.ok) {
                const data = await res.json();
                results = data;
                showDropdown = true;
            }
        } catch (error) {
            console.error('Search failed:', error);
        } finally {
            loading = false;
        }
    };

    function handleInput() {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            performSearch(query);
        }, 300);
    }

    function handleClickOutside(event) {
        // Ensure we're in the browser environment
        if (typeof window !== 'undefined') {
            const container = document.querySelector('.omnibar-container');
            if (container && !container.contains(event.target)) {
                showDropdown = false;
            }
        }
    }

    function navigate(type, id) {
        showDropdown = false;
        query = '';
        if (type === 'artist') {
            goto(`/library?artist=${id}`);
        } else if (type === 'album') {
             // Assuming library view can filter by album or jump to it
             // For now, let's just log or implement a basic route if known
             console.log('Navigate to album', id);
        } else if (type === 'track') {
             console.log('Navigate to track', id);
        }
    }
</script>

<svelte:window on:click={handleClickOutside} />

<div class="omnibar-container relative w-full max-w-2xl mx-auto z-40">
    <div class="relative">
        <input
            type="text"
            bind:value={query}
            on:input={handleInput}
            placeholder="Search library..."
            class="w-full bg-gray-800 border border-gray-700 rounded-lg py-2 px-4 pl-10 text-white placeholder-gray-400 focus:outline-none focus:border-blue-500 transition-colors"
            on:focus={() => { if (query.length >= 2) showDropdown = true; }}
        />
        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg class="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
        </div>
        {#if loading}
            <div class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
                <svg class="animate-spin h-5 w-5 text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
            </div>
        {/if}
    </div>

    {#if showDropdown && (results.artists?.length > 0 || results.albums?.length > 0 || results.tracks?.length > 0)}
        <div class="absolute top-full left-0 right-0 mt-2 bg-gray-900 border border-gray-700 rounded-lg shadow-xl max-h-[60vh] overflow-y-auto z-50">
            {#if results.artists && results.artists.length > 0}
                <div class="p-2">
                    <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-2">Artists</h3>
                    {#each results.artists as artist}
                        <button
                            class="w-full text-left flex items-center p-2 hover:bg-gray-800 rounded-md transition-colors group"
                            on:click={() => navigate('artist', artist.id)}
                        >
                            {#if artist.image_url}
                                <img src={artist.image_url} alt={artist.name} class="w-8 h-8 rounded-full object-cover mr-3" />
                            {:else}
                                <div class="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center mr-3">
                                    <span class="text-xs text-gray-400">?</span>
                                </div>
                            {/if}
                            <span class="text-white font-medium group-hover:text-blue-400 transition-colors">{artist.name}</span>
                        </button>
                    {/each}
                </div>
            {/if}

            {#if results.albums && results.albums.length > 0}
                <div class="p-2 border-t border-gray-800">
                    <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-2">Albums</h3>
                    {#each results.albums as album}
                        <button
                            class="w-full text-left flex items-center p-2 hover:bg-gray-800 rounded-md transition-colors group"
                            on:click={() => navigate('album', album.id)}
                        >
                            {#if album.cover_image_url}
                                <img src={album.cover_image_url} alt={album.title} class="w-8 h-8 rounded object-cover mr-3" />
                            {:else}
                                <div class="w-8 h-8 rounded bg-gray-700 flex items-center justify-center mr-3">
                                    <span class="text-xs text-gray-400">?</span>
                                </div>
                            {/if}
                            <div class="flex flex-col">
                                <span class="text-white font-medium group-hover:text-blue-400 transition-colors">{album.title}</span>
                                <span class="text-xs text-gray-400">{album.artist_name} • {album.year || 'Unknown'}</span>
                            </div>
                        </button>
                    {/each}
                </div>
            {/if}

            {#if results.tracks && results.tracks.length > 0}
                <div class="p-2 border-t border-gray-800">
                    <h3 class="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-2">Tracks</h3>
                    {#each results.tracks as track}
                        <button
                            class="w-full text-left flex items-center p-2 hover:bg-gray-800 rounded-md transition-colors group"
                            on:click={() => navigate('track', track.id)}
                        >
                            <div class="flex flex-col">
                                <span class="text-white font-medium group-hover:text-blue-400 transition-colors">{track.title}</span>
                                <span class="text-xs text-gray-400">{track.artist_name} • {track.album_title}</span>
                            </div>
                        </button>
                    {/each}
                </div>
            {/if}
        </div>
    {/if}
</div>
